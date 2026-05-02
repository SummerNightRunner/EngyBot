from __future__ import annotations

import random

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from bot.database.models import TrainingAttempt, User, UserWordProgress, Word, WordSet
from bot.database.session import SessionLocal
from bot.keyboards.main_menu import (
    card_keyboard,
    dialogue_keyboard,
    dialogue_step_keyboard,
    guest_menu_keyboard,
    help_keyboard,
    language_keyboard,
    level_keyboard,
    main_menu_keyboard,
    nav_keyboard,
    profile_keyboard,
    quiz_formats_keyboard,
    quiz_options_keyboard,
    review_keyboard,
    start_quiz_keyboard,
    word_sets_keyboard,
)
from bot.services.content import DIALOGUE_SCENARIOS, QUIZ_FORMATS, WORD_DEFINITIONS, level_is_allowed
from bot.states.training import QuizStates

router = Router()


LANGUAGE_NAMES = {
    "ru": "Русский",
    "en": "Английский",
    "de": "Немецкий",
}


async def get_registered_user(telegram_id: int) -> User | None:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def get_active_word_sets(user_level: str | None = None) -> list[WordSet]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(WordSet)
            .where(WordSet.is_active.is_(True))
            .options(selectinload(WordSet.words))
            .order_by(WordSet.level, WordSet.title)
        )
        word_sets = list(result.scalars().all())

    if user_level is None:
        return word_sets

    return [word_set for word_set in word_sets if level_is_allowed(user_level, word_set.level)]


async def get_word_set(word_set_id: int) -> WordSet | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(WordSet).where(WordSet.id == word_set_id).options(selectinload(WordSet.words))
        )
        return result.scalar_one_or_none()


async def get_review_words(telegram_id: int, limit: int = 8) -> list[Word]:
    user = await get_registered_user(telegram_id)
    if user is None:
        return []

    async with SessionLocal() as session:
        result = await session.execute(
            select(Word)
            .join(UserWordProgress, UserWordProgress.word_id == Word.id)
            .where(UserWordProgress.user_id == user.id)
            .order_by(
                UserWordProgress.last_result.asc(),
                (UserWordProgress.wrong_count - UserWordProgress.correct_count).desc(),
                UserWordProgress.updated_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_words_by_ids(word_ids: list[int]) -> list[Word]:
    if not word_ids:
        return []

    async with SessionLocal() as session:
        result = await session.execute(select(Word).where(Word.id.in_(word_ids)))
        words = list(result.scalars().all())

    by_id = {word.id: word for word in words}
    return [by_id[word_id] for word_id in word_ids if word_id in by_id]


def get_dialogue_scenarios(user_level: str | None = None) -> list[dict]:
    if user_level is None:
        return DIALOGUE_SCENARIOS
    return [scenario for scenario in DIALOGUE_SCENARIOS if level_is_allowed(user_level, scenario["level"])]


def get_dialogue_by_id(scenario_id: str) -> dict | None:
    for scenario in DIALOGUE_SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario
    return None


async def get_daily_words(telegram_id: int, limit: int = 5) -> list[Word]:
    user = await get_registered_user(telegram_id)
    user_level = user.level if user is not None else None
    word_sets = await get_active_word_sets(user_level)
    pool: list[Word] = []
    for word_set in word_sets:
        pool.extend(word_set.words)

    if len(pool) <= limit:
        return pool

    return random.sample(pool, k=limit)


async def edit_screen(callback: CallbackQuery, text: str, reply_markup) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=reply_markup)


async def show_home(target: Message | CallbackQuery, state: FSMContext) -> None:
    telegram_user = target.from_user
    if telegram_user is None:
        return

    user = await get_registered_user(telegram_user.id)
    await state.clear()

    if isinstance(target, Message):
        send = target.answer
    else:
        if target.message is None:
            await target.answer()
            return
        await target.answer()
        send = target.message.edit_text

    if user is None:
        await send(
            "Привет! Я ваш помощник в изучении иностранных языков.\n\n"
            "Сначала настройте профиль: выберите родной язык, язык для изучения и уровень.",
            reply_markup=guest_menu_keyboard(),
        )
        return

    await send(
        f"Привет, <b>{telegram_user.full_name}</b>! Я ваш помощник в изучении иностранных языков.\n"
        "Что вы хотите сделать сегодня?",
        reply_markup=main_menu_keyboard(),
    )


async def persist_profile(telegram_user, state: FSMContext) -> User:
    data = await state.get_data()
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                full_name=telegram_user.full_name,
                source_language=data["source_language"],
                target_language=data["target_language"],
                level=data["level"],
            )
            session.add(user)
        else:
            user.username = telegram_user.username
            user.full_name = telegram_user.full_name
            user.source_language = data["source_language"]
            user.target_language = data["target_language"]
            user.level = data["level"]

        await session.commit()
        await session.refresh(user)
        return user


def format_profile(user: User) -> str:
    return (
        "<b>Профиль пользователя</b>\n\n"
        f"Родной язык: {LANGUAGE_NAMES.get(user.source_language, user.source_language)}\n"
        f"Изучаемый язык: {LANGUAGE_NAMES.get(user.target_language, user.target_language)}\n"
        f"Уровень: {user.level}"
    )


def build_quiz_prompt(quiz_format: str, current_word, word_set: WordSet, index: int, total: int) -> str:
    if quiz_format == "gap":
        masked_example = current_word.example.replace(current_word.target_text, "_____")
        return (
            f"<b>Квиз: {QUIZ_FORMATS[quiz_format]}</b>\n"
            f"Тема: {word_set.title}\n"
            f"Вопрос {index + 1} из {total}\n\n"
            "Какое слово должно стоять на месте пропуска?\n"
            f"<i>{masked_example}</i>"
        )

    if quiz_format == "definition":
        definition = WORD_DEFINITIONS.get(
            current_word.target_text,
            f"Выберите слово, которое соответствует значению: {current_word.source_text}.",
        )
        return (
            f"<b>Квиз: {QUIZ_FORMATS[quiz_format]}</b>\n"
            f"Тема: {word_set.title}\n"
            f"Вопрос {index + 1} из {total}\n\n"
            f"{definition}"
        )

    return (
        f"<b>Квиз: {QUIZ_FORMATS[quiz_format]}</b>\n"
        f"Тема: {word_set.title}\n"
        f"Вопрос {index + 1} из {total}\n\n"
        "Выберите правильное слово из списка:\n"
        f"<b>{current_word.source_text}</b>"
    )


async def show_quiz_question(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    review_mode = data.get("review_mode", False)
    daily_mode = data.get("daily_mode", False)
    question_index = data["quiz_index"]
    quiz_format = data["quiz_format"]

    if review_mode:
        review_words = await get_words_by_ids(data["review_word_ids"])
        if not review_words:
            await state.clear()
            await edit_screen(callback, "Слова для повторения не найдены.", nav_keyboard(back_to="menu:review"))
            return
        current_word = review_words[question_index]
        total_questions = len(review_words)
        topic_title = "Повторение ошибок"
        options_pool = review_words
    elif daily_mode:
        daily_words = await get_words_by_ids(data["daily_word_ids"])
        if not daily_words:
            await state.clear()
            await edit_screen(callback, "Слова для практики дня не найдены.", nav_keyboard(back_to="menu:daily"))
            return
        current_word = daily_words[question_index]
        total_questions = len(daily_words)
        topic_title = "Практика дня"
        options_pool = daily_words
    else:
        word_set = await get_word_set(data["quiz_word_set_id"])
        if word_set is None or not word_set.words:
            await state.clear()
            await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:quiz"))
            return
        current_word = word_set.words[question_index]
        total_questions = len(word_set.words)
        topic_title = word_set.title
        options_pool = word_set.words

    options = [word.target_text for word in options_pool]
    random.shuffle(options)
    options = options[:4]
    if current_word.target_text not in options:
        options[-1] = current_word.target_text
    random.shuffle(options)

    await state.update_data(correct_answer=current_word.target_text, current_word_id=current_word.id)
    await edit_screen(
        callback,
        build_quiz_prompt(
            quiz_format,
            current_word,
            WordSet(title=topic_title, description=None, level="", is_active=True),
            question_index,
            total_questions,
        ),
        quiz_options_keyboard(options),
    )


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await show_home(message, state)


@router.callback_query(F.data == "menu:home")
async def home_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await show_home(callback, state)


@router.callback_query(F.data == "profile:start_setup")
async def profile_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_screen(
        callback,
        "Шаг 1 из 3.\n\nВыберите свой родной язык:",
        language_keyboard("profile:source"),
    )


@router.callback_query(F.data.startswith("profile:source:"))
async def profile_source_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(source_language=callback.data.split(":")[-1])
    await edit_screen(
        callback,
        "Шаг 2 из 3.\n\nВыберите язык, который хотите изучать:",
        language_keyboard("profile:target"),
    )


@router.callback_query(F.data.startswith("profile:target:"))
async def profile_target_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(target_language=callback.data.split(":")[-1])
    await edit_screen(
        callback,
        "Шаг 3 из 3.\n\nВыберите уровень владения языком:",
        level_keyboard(),
    )


@router.callback_query(F.data.startswith("profile:level:"))
async def profile_level_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(level=callback.data.split(":")[-1])
    user = await persist_profile(callback.from_user, state)
    await state.clear()
    await edit_screen(callback, "Профиль сохранен.\n\n" + format_profile(user), profile_keyboard())


@router.callback_query(F.data == "menu:profile")
async def profile_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    if user is None:
        await edit_screen(
            callback,
            "Профиль еще не настроен.\n\nСначала завершите настройку профиля.",
            nav_keyboard(back_to="profile:start_setup"),
        )
        return
    await edit_screen(callback, format_profile(user), profile_keyboard())


@router.callback_query(F.data == "menu:learn")
async def learn_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    word_sets = await get_active_word_sets(user_level)
    payload = [(word_set.id, word_set.title, word_set.level) for word_set in word_sets]
    text = "Выберите тему:"
    if user_level is not None:
        text = f"Выберите тему для уровня {user_level}:"
    await edit_screen(callback, text, word_sets_keyboard(payload, mode="learn"))


@router.callback_query(F.data == "menu:dialogue")
async def dialogue_menu_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    scenarios = get_dialogue_scenarios(user_level)
    payload = [(item["id"], item["title"], item["level"], item["theme"]) for item in scenarios]
    text = "Выберите мини-диалог:"
    if user_level is not None:
        text = f"Выберите мини-диалог для уровня {user_level}:"
    await edit_screen(callback, text, dialogue_keyboard(payload))


@router.callback_query(F.data.startswith("dialogue:"))
async def dialogue_handler(callback: CallbackQuery) -> None:
    _, scenario_id, raw_index = callback.data.split(":")
    scenario = get_dialogue_by_id(scenario_id)
    if scenario is None:
        await edit_screen(callback, "Диалог не найден.", nav_keyboard(back_to="menu:dialogue"))
        return

    index = min(int(raw_index), len(scenario["lines"]) - 1)
    line = scenario["lines"][index]
    await edit_screen(
        callback,
        f"<b>{scenario['title']}</b>\n"
        f"Тема: {scenario['theme']}\n"
        f"Уровень: {scenario['level']}\n\n"
        f"{line}\n\n"
        f"Реплика {index + 1} из {len(scenario['lines'])}",
        dialogue_step_keyboard(scenario_id, index, len(scenario["lines"])),
    )


@router.callback_query(F.data.startswith("learn:set:"))
async def learn_set_handler(callback: CallbackQuery) -> None:
    word_set = await get_word_set(int(callback.data.split(":")[-1]))
    if word_set is None or not word_set.words:
        await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:learn"))
        return
    word = word_set.words[0]
    await edit_screen(
        callback,
        f"<b>{word_set.title}</b>\n"
        f"Уровень: {word_set.level}\n"
        f"{word_set.description}\n\n"
        f"<b>{word.target_text}</b> — {word.source_text}\n"
        f"Пример: {word.example}\n\n"
        f"Слово 1 из {len(word_set.words)}",
        card_keyboard(word_set.id, 0, len(word_set.words)),
    )


@router.callback_query(F.data.startswith("learn:card:"))
async def learn_card_handler(callback: CallbackQuery) -> None:
    _, _, word_set_id, index = callback.data.split(":")
    word_set = await get_word_set(int(word_set_id))
    if word_set is None or not word_set.words:
        await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:learn"))
        return
    current_index = min(int(index), len(word_set.words) - 1)
    word = word_set.words[current_index]
    await edit_screen(
        callback,
        f"<b>{word_set.title}</b>\n\n"
        f"Уровень: {word_set.level}\n"
        f"<b>{word.target_text}</b> — {word.source_text}\n"
        f"Пример: {word.example}\n\n"
        f"Слово {current_index + 1} из {len(word_set.words)}",
        card_keyboard(word_set.id, current_index, len(word_set.words)),
    )


@router.callback_query(F.data == "menu:quiz")
async def quiz_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_screen(
        callback,
        "Отлично! Давайте начнем с квиза!\n\nВыберите формат:",
        quiz_formats_keyboard(),
    )


@router.callback_query(F.data == "menu:daily")
async def daily_practice_handler(callback: CallbackQuery, state: FSMContext) -> None:
    words = await get_daily_words(callback.from_user.id, limit=5)
    if len(words) < 2:
        await edit_screen(
            callback,
            "Для практики дня пока недостаточно слов.\n\n"
            "Сначала настройте профиль или расширьте учебный контент.",
            nav_keyboard(back_to="menu:home", include_home=False),
        )
        return

    await state.set_state(QuizStates.in_progress)
    await state.update_data(
        daily_mode=True,
        daily_word_ids=[word.id for word in words],
        review_mode=False,
        quiz_word_set_id=None,
        quiz_index=0,
        quiz_correct=0,
        quiz_format="choice",
    )
    await show_quiz_question(callback, state)


@router.callback_query(F.data == "menu:review")
async def review_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "<b>Повторение</b>\n\n"
        "Здесь можно посмотреть слабые слова и пройти короткий квиз по ошибкам.",
        review_keyboard(),
    )


@router.callback_query(F.data == "review:words")
async def review_words_handler(callback: CallbackQuery) -> None:
    words = await get_review_words(callback.from_user.id)
    if not words:
        await edit_screen(
            callback,
            "Раздел повторения пока пуст.\n\n"
            "Пройдите несколько квизов, и здесь появятся слова, с которыми были ошибки или трудности.",
            nav_keyboard(back_to="menu:review"),
        )
        return

    lines = []
    for word in words:
        lines.append(f"• <b>{word.target_text}</b> — {word.source_text}")
        if word.example:
            lines.append(f"  <i>{word.example}</i>")

    await edit_screen(
        callback,
        "<b>Слова для повторения</b>\n\n"
        "Здесь собраны слова, которые стоит повторить в первую очередь:\n\n"
        + "\n".join(lines),
        nav_keyboard(back_to="menu:review"),
    )


@router.callback_query(F.data == "review:quiz")
async def review_quiz_handler(callback: CallbackQuery, state: FSMContext) -> None:
    words = await get_review_words(callback.from_user.id, limit=6)
    if len(words) < 2:
        await edit_screen(
            callback,
            "Для квиза по ошибкам пока недостаточно данных.\n\n"
            "Сначала завершите несколько обычных квизов и допустите хотя бы пару ошибок.",
            nav_keyboard(back_to="menu:review"),
        )
        return

    await state.set_state(QuizStates.in_progress)
    await state.update_data(
        review_mode=True,
        daily_mode=False,
        review_word_ids=[word.id for word in words],
        quiz_word_set_id=None,
        quiz_index=0,
        quiz_correct=0,
        quiz_format="choice",
    )
    await show_quiz_question(callback, state)


@router.callback_query(F.data.startswith("quiz:format:"))
async def quiz_format_handler(callback: CallbackQuery, state: FSMContext) -> None:
    quiz_format = callback.data.split(":")[-1]
    await state.clear()
    await state.update_data(selected_quiz_format=quiz_format)

    if quiz_format == "match":
        user = await get_registered_user(callback.from_user.id)
        user_level = user.level if user is not None else None
        word_sets = await get_active_word_sets(user_level)
        preview = []
        for word_set in word_sets[:2]:
            for word in word_set.words[:3]:
                preview.append(f"{word.target_text} — {word.source_text}")
        await edit_screen(
            callback,
            "<b>Квиз: Соответствие</b>\n\n"
            "Этот формат оформлен как тренировочный экран с готовыми парами слов.\n\n"
            + "\n".join(preview),
            nav_keyboard(back_to="menu:quiz"),
        )
        return

    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    word_sets = await get_active_word_sets(user_level)
    payload = [(word_set.id, word_set.title, word_set.level) for word_set in word_sets]
    await edit_screen(
        callback,
        f"Выберите тему для квиза формата «{QUIZ_FORMATS[quiz_format]}»:",
        word_sets_keyboard(payload, mode=f"quiz:{quiz_format}"),
    )


@router.callback_query(F.data.startswith("quiz:choice:set:"))
@router.callback_query(F.data.startswith("quiz:gap:set:"))
@router.callback_query(F.data.startswith("quiz:definition:set:"))
async def quiz_set_handler(callback: CallbackQuery, state: FSMContext) -> None:
    _, quiz_format, _, raw_id = callback.data.split(":")
    await state.update_data(selected_quiz_format=quiz_format)
    word_set = await get_word_set(int(raw_id))
    if word_set is None or not word_set.words:
        await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:quiz"))
        return
    await edit_screen(
        callback,
        f"<b>{word_set.title}</b>\n"
        f"{word_set.description}\n\n"
        f"Формат квиза: {QUIZ_FORMATS[quiz_format]}\n"
        f"Количество вопросов: {len(word_set.words)}",
        start_quiz_keyboard(word_set.id, quiz_format),
    )


@router.callback_query(F.data.startswith("quiz:start:"))
async def quiz_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, quiz_format, raw_id = callback.data.split(":")
    word_set = await get_word_set(int(raw_id))
    if word_set is None or not word_set.words:
        await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:quiz"))
        return
    await state.set_state(QuizStates.in_progress)
    await state.update_data(
        daily_mode=False,
        review_mode=False,
        quiz_word_set_id=word_set.id,
        quiz_index=0,
        quiz_correct=0,
        quiz_format=quiz_format,
    )
    await show_quiz_question(callback, state)


@router.callback_query(QuizStates.in_progress, F.data.startswith("quiz:answer:"))
async def quiz_answer_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected_answer = callback.data.removeprefix("quiz:answer:")
    is_correct = selected_answer == data["correct_answer"]
    correct_count = data["quiz_correct"] + int(is_correct)
    next_index = data["quiz_index"] + 1
    review_mode = data.get("review_mode", False)
    daily_mode = data.get("daily_mode", False)

    if review_mode:
        review_words = await get_words_by_ids(data["review_word_ids"])
        if not review_words:
            await state.clear()
            await edit_screen(callback, "Слова для повторения не найдены.", nav_keyboard(back_to="menu:review"))
            return
        total_questions = len(review_words)
        quiz_title = "Повторение ошибок"
        word_set_id = None
    elif daily_mode:
        daily_words = await get_words_by_ids(data["daily_word_ids"])
        if not daily_words:
            await state.clear()
            await edit_screen(callback, "Слова для практики дня не найдены.", nav_keyboard(back_to="menu:daily"))
            return
        total_questions = len(daily_words)
        quiz_title = "Практика дня"
        word_set_id = None
    else:
        word_set = await get_word_set(data["quiz_word_set_id"])
        if word_set is None or not word_set.words:
            await state.clear()
            await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:quiz"))
            return
        total_questions = len(word_set.words)
        quiz_title = word_set.title
        word_set_id = word_set.id

    if next_index >= total_questions:
        user = await get_registered_user(callback.from_user.id)
        if user is not None:
            async with SessionLocal() as session:
                progress_result = await session.execute(
                    select(UserWordProgress).where(
                        UserWordProgress.user_id == user.id,
                        UserWordProgress.word_id == data["current_word_id"],
                    )
                )
                progress = progress_result.scalar_one_or_none()
                if progress is None:
                    progress = UserWordProgress(user_id=user.id, word_id=data["current_word_id"])
                    session.add(progress)
                if is_correct:
                    progress.correct_count += 1
                else:
                    progress.wrong_count += 1
                progress.last_result = is_correct

                if word_set_id is not None:
                    session.add(
                        TrainingAttempt(
                            user_id=user.id,
                            word_set_id=word_set_id,
                            correct_answers=correct_count,
                            total_questions=total_questions,
                        )
                    )
                await session.commit()
        await state.clear()
        back_to = "menu:daily" if daily_mode else ("menu:review" if review_mode else "menu:quiz")
        await edit_screen(
            callback,
            "<b>Квиз завершен</b>\n\n"
            f"Формат: {QUIZ_FORMATS[data['quiz_format']]}\n"
            f"Тема: {quiz_title}\n"
            f"Правильных ответов: {correct_count} из {total_questions}",
            nav_keyboard(back_to=back_to),
        )
        return

    user = await get_registered_user(callback.from_user.id)
    if user is not None:
        async with SessionLocal() as session:
            progress_result = await session.execute(
                select(UserWordProgress).where(
                    UserWordProgress.user_id == user.id,
                    UserWordProgress.word_id == data["current_word_id"],
                )
            )
            progress = progress_result.scalar_one_or_none()
            if progress is None:
                progress = UserWordProgress(user_id=user.id, word_id=data["current_word_id"])
                session.add(progress)
            if is_correct:
                progress.correct_count += 1
            else:
                progress.wrong_count += 1
            progress.last_result = is_correct
            await session.commit()

    await state.update_data(quiz_index=next_index, quiz_correct=correct_count)
    await show_quiz_question(callback, state)


@router.callback_query(F.data == "menu:stats")
async def stats_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    if user is None:
        await edit_screen(
            callback,
            "Сначала настройте профиль, чтобы бот мог сохранять результаты обучения.",
            nav_keyboard(back_to="profile:start_setup"),
        )
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(
                func.count(TrainingAttempt.id),
                func.coalesce(func.sum(TrainingAttempt.correct_answers), 0),
                func.coalesce(func.sum(TrainingAttempt.total_questions), 0),
            ).where(TrainingAttempt.user_id == user.id)
        )
        attempts_count, correct_answers, total_questions = result.one()
        weak_result = await session.execute(
            select(func.count(UserWordProgress.id)).where(
                UserWordProgress.user_id == user.id,
                UserWordProgress.wrong_count > UserWordProgress.correct_count,
            )
        )
        weak_words = weak_result.scalar_one()

    accuracy = 0 if total_questions == 0 else round(correct_answers / total_questions * 100)
    await edit_screen(
        callback,
        "<b>Статистика</b>\n\n"
        f"Пройдено квизов: {attempts_count}\n"
        f"Правильных ответов: {correct_answers}\n"
        f"Всего вопросов: {total_questions}\n"
        f"Точность: {accuracy}%\n"
        f"Слабые слова: {weak_words}",
        nav_keyboard(back_to="menu:home", include_home=False),
    )


@router.callback_query(F.data == "menu:help")
async def help_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    await edit_screen(
        callback,
        "Привет! Я ваш помощник в изучении иностранных языков. Что вы хотите сделать сегодня?\n\n"
        "1. Изучить слова\n"
        "2. Пройти квиз",
        help_keyboard(user is not None),
    )


@router.callback_query(F.data == "help:usage")
async def help_usage_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    await edit_screen(
        callback,
        "Сценарий 1: Изучение слов\n"
        "1. Запустить бота\n"
        "2. Выбрать изучение слов\n"
        "3. Выбрать тему\n"
        "4. Изучить слова с переводом\n\n"
        "Сценарий 2: Прохождение квиза\n"
        "1. Открыть раздел квизов\n"
        "2. Выбрать формат\n"
        "3. Выбрать тему\n"
        "4. Ответить на вопросы\n"
        "5. Посмотреть результат",
        nav_keyboard(back_to="menu:help", include_home=user is not None),
    )


@router.callback_query(F.data == "help:mvp")
async def help_mvp_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    await edit_screen(
        callback,
        "MVP включает:\n"
        "- 5 тематических наборов слов\n"
        "- уровни A1, A2 и B1\n"
        "- карточки со словами и примерами\n"
        "- несколько форматов квизов\n"
        "- сохранение статистики обучения",
        nav_keyboard(back_to="menu:help", include_home=user is not None),
    )
