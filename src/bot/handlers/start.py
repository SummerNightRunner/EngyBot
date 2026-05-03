from __future__ import annotations

import json
import random
import re
from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from bot.database.models import DailyPractice, TrainingAttempt, User, UserWordProgress, Word, WordSet
from bot.database.session import SessionLocal
from bot.keyboards.main_menu import (
    card_keyboard,
    course_menu_keyboard,
    dialogue_keyboard,
    dialogue_step_keyboard,
    grammar_units_keyboard,
    guest_menu_keyboard,
    help_keyboard,
    language_keyboard,
    level_keyboard,
    main_menu_keyboard,
    nav_keyboard,
    practice_menu_keyboard,
    profile_keyboard,
    quiz_feedback_keyboard,
    quiz_formats_keyboard,
    quiz_options_keyboard,
    review_keyboard,
    start_quiz_keyboard,
    stats_keyboard,
    word_sets_keyboard,
)
from bot.services.content import (
    DIALOGUE_SCENARIOS,
    QUIZ_FORMATS,
    WORD_DEFINITIONS,
    filter_words_for_level,
    load_grammar_units,
    get_word_set_level_range,
    level_is_allowed,
)
from bot.states.training import QuizStates

router = Router()


LANGUAGE_NAMES = {
    "ru": "Русский",
    "en": "Английский",
    "de": "Немецкий",
}

GRAMMAR_UNITS = load_grammar_units()

TOPIC_LABELS = {
    "Путешествия": {"en": "Travel"},
    "Город и транспорт": {"en": "City & Transport"},
    "Дом и быт": {"en": "Home & Daily Life"},
    "Еда и напитки": {"en": "Food & Drinks"},
    "Путешествия": {"en": "Travel"},
    "Семья и отношения": {"en": "Family & Relationships"},
    "Хобби и досуг": {"en": "Hobbies & Leisure"},
    "Повседневная жизнь и распорядок": {"en": "Daily Routine"},
    "Одежда и внешность": {"en": "Clothes & Appearance"},
    "Здоровье и образ жизни": {"en": "Health & Lifestyle"},
    "Образование и обучение": {"en": "Education & Learning"},
    "Покупки и деньги": {"en": "Shopping & Money"},
    "Работа и карьера": {"en": "Work & Career"},
    "Технологии и медиа": {"en": "Technology & Media"},
    "Природа и экология": {"en": "Nature & Environment"},
    "Эмоции и общение": {"en": "Emotions & Communication"},
    "Культура и общество": {"en": "Culture & Society"},
    "Наука и инновации": {"en": "Science & Innovation"},
    "Аргументация и дебаты": {"en": "Argumentation & Debate"},
}

UI_TEXT = {
    "course": {"en": "Course", "ru": "Курс"},
    "practice": {"en": "Practice", "ru": "Практика"},
    "review": {"en": "Review", "ru": "Повторение"},
    "profile": {"en": "Profile", "ru": "Профиль"},
    "stats": {"en": "Progress", "ru": "Статистика"},
    "help": {"en": "Help", "ru": "Помощь"},
    "vocabulary": {"en": "Vocabulary", "ru": "Слова"},
    "grammar": {"en": "Grammar", "ru": "Грамматика"},
    "dialogues": {"en": "Dialogues", "ru": "Диалоги"},
    "daily": {"en": "Daily Practice", "ru": "Практика дня"},
    "quiz": {"en": "Mixed Quiz", "ru": "Квиз"},
    "home": {"en": "Home", "ru": "В меню"},
    "edit_profile": {"en": "Edit profile", "ru": "Изменить профиль"},
    "toggle_bilingual_on": {"en": "Bilingual UI: On", "ru": "Два языка: Вкл"},
    "toggle_bilingual_off": {"en": "Bilingual UI: Off", "ru": "Два языка: Выкл"},
    "course_title": {"en": "Course", "ru": "Курс"},
    "practice_title": {"en": "Practice", "ru": "Практика"},
}


def translated_label(key: str, target_language: str, source_language: str, bilingual: bool) -> str:
    entry = UI_TEXT[key]
    target = entry.get(target_language, entry.get("en", key))
    source = entry.get(source_language, entry.get("ru", key))
    if not bilingual or target == source:
        return target
    return f"{target} ({source})"


def bilingual_block(
    primary: str,
    secondary: str | None = None,
    *,
    italic_secondary: bool = True,
) -> str:
    if not secondary or secondary == primary:
        return primary
    secondary_text = f"<i>{secondary}</i>" if italic_secondary else secondary
    return f"{primary}\n{secondary_text}"


def quiz_format_label(quiz_format: str, user: User | None) -> str:
    entry = QUIZ_FORMATS[quiz_format]
    target_language = user.target_language if user is not None else "en"
    source_language = user.source_language if user is not None else "ru"
    bilingual = user.bilingual_ui if user is not None else True
    primary = entry.get(target_language, entry["en"])
    secondary = entry.get(source_language, entry["ru"]) if bilingual else None
    return bilingual_block(primary, secondary)


def topic_label(title: str, target_language: str, source_language: str, bilingual: bool) -> str:
    entry = TOPIC_LABELS.get(title, {})
    target = entry.get(target_language, title)
    source = title if source_language == "ru" else entry.get(source_language, title)
    if not bilingual or target == source:
        return target
    return f"{target} ({source})"


def grammar_label(title: str, target_language: str, source_language: str, bilingual: bool) -> str:
    source = title
    if source_language == "ru":
        translated = {
            "to be and subject pronouns": "to be и личные местоимения",
            "articles and plurals": "артикли и множественное число",
            "present simple": "present simple",
            "there is / there are / have got": "there is / there are / have got",
            "can / can't and basic questions": "can / can't и базовые вопросы",
            "present continuous": "present continuous",
            "past simple": "past simple",
            "some / any / much / many": "some / any / much / many",
            "comparatives and superlatives": "сравнительная и превосходная степени",
            "going to and basic future": "going to и базовое будущее",
            "prepositions of time and place": "предлоги времени и места",
            "present perfect": "present perfect",
            "past continuous": "past continuous",
            "first conditional": "first conditional",
            "must / have to / should": "must / have to / should",
            "relative clauses": "relative clauses",
            "gerunds and infinitives": "gerunds и infinitives",
            "passive voice": "passive voice",
            "reported speech": "reported speech",
            "second and third conditionals": "second и third conditionals",
            "modal deduction": "modal deduction",
            "linkers and discourse markers": "связки и discourse markers",
            "inversion and emphasis": "inversion и emphasis",
            "participle clauses": "participle clauses",
            "hedging and stance": "hedging и stance",
            "advanced sentence combining": "сложные sentence patterns",
            "nominalisation and register control": "nominalisation и register",
            "rhetorical and argumentation grammar": "риторика и grammar for argumentation",
        }
        source = translated.get(title, title)
    if not bilingual:
        return title
    return f"{title} ({source})"


def user_labels(user: User | None) -> dict[str, str]:
    target_language = user.target_language if user is not None else "en"
    source_language = user.source_language if user is not None else "ru"
    bilingual = user.bilingual_ui if user is not None else True
    labels = {
        key: translated_label(key, target_language, source_language, bilingual)
        for key in (
            "course",
            "practice",
            "review",
            "profile",
            "stats",
            "help",
            "vocabulary",
            "grammar",
            "dialogues",
            "daily",
            "quiz",
            "home",
            "edit_profile",
        )
    }
    labels["toggle_bilingual"] = translated_label(
        "toggle_bilingual_off" if user is not None and user.bilingual_ui else "toggle_bilingual_on",
        target_language,
        source_language,
        bilingual,
    )
    return labels


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

    return [word_set for word_set in word_sets if filter_words_for_level(word_set.words, user_level)]


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


def get_grammar_units(user_level: str | None = None) -> list[dict]:
    if user_level is None:
        return GRAMMAR_UNITS
    return [unit for unit in GRAMMAR_UNITS if level_is_allowed(user_level, unit["level"])]


def get_grammar_unit(unit_id: str) -> dict | None:
    for unit in GRAMMAR_UNITS:
        if unit["id"] == unit_id:
            return unit
    return None


def format_grammar_unit(unit: dict) -> str:
    patterns = "\n".join(f"• <code>{pattern}</code>" for pattern in unit["patterns"])
    examples = "\n".join(f"• {example}" for example in unit["examples"])
    return (
        f"<b>{unit['title']}</b>\n"
        f"Уровень: {unit['level']}\n\n"
        f"{unit['summary']}\n\n"
        f"<b>Зачем это нужно</b>\n{unit['why_it_matters']}\n\n"
        f"<b>Шаблоны</b>\n{patterns}\n\n"
        f"<b>Примеры</b>\n{examples}"
    )


def render_word_card(
    *,
    word_set: WordSet,
    word: Word,
    current_index: int,
    total: int,
    user: User | None,
) -> str:
    target_language = user.target_language if user is not None else "en"
    source_language = user.source_language if user is not None else "ru"
    bilingual = user.bilingual_ui if user is not None else True
    title = topic_label(word_set.title, target_language, source_language, bilingual)
    primary = f"<b>{word.target_text}</b>"
    secondary = word.source_text if bilingual else None
    return (
        f"<b>{title}</b>\n\n"
        f"Level range: {get_word_set_level_range(word_set, user.level if user is not None else None)}\n\n"
        f"{bilingual_block(primary, secondary, italic_secondary=True)}\n\n"
        f"{word.example}\n\n"
        f"Item {current_index + 1} of {total}"
    )


async def get_daily_words(telegram_id: int, limit: int = 5) -> list[Word]:
    user = await get_registered_user(telegram_id)
    user_level = user.level if user is not None else None
    word_sets = await get_active_word_sets(user_level)
    pool: list[Word] = []
    for word_set in word_sets:
        pool.extend(filter_words_for_level(word_set.words, user_level))

    if len(pool) <= limit:
        return pool

    return random.sample(pool, k=limit)


def load_daily_word_ids(practice: DailyPractice) -> list[int]:
    return json.loads(practice.word_ids_json)


def format_daily_completion(practice: DailyPractice, words: list[Word]) -> str:
    total_questions = len(words)
    completed_at = practice.completed_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC") if practice.completed_at else "сегодня"
    return (
        "<b>Практика дня завершена</b>\n\n"
        f"Дата: {practice.practice_date.isoformat()}\n"
        f"Правильных ответов: {practice.correct_answers} из {total_questions}\n"
        f"Завершено: {completed_at}\n\n"
        "Новый набор слов появится завтра."
    )


async def get_or_create_daily_practice(telegram_id: int, limit: int = 5) -> DailyPractice | None:
    user = await get_registered_user(telegram_id)
    if user is None:
        return None

    today = datetime.now(UTC).date()
    async with SessionLocal() as session:
        result = await session.execute(
            select(DailyPractice).where(
                DailyPractice.user_id == user.id,
                DailyPractice.practice_date == today,
            )
        )
        practice = result.scalar_one_or_none()
        if practice is not None:
            return practice

        word_sets = await get_active_word_sets(user.level)
        pool: list[Word] = []
        for word_set in word_sets:
            pool.extend(filter_words_for_level(word_set.words, user.level))

        if len(pool) < 2:
            return None

        generator = random.Random(f"{user.id}:{today.isoformat()}")
        selected_words = pool if len(pool) <= limit else generator.sample(pool, k=limit)
        practice = DailyPractice(
            user_id=user.id,
            practice_date=today,
            word_ids_json=json.dumps([word.id for word in selected_words]),
            current_index=0,
            correct_answers=0,
            is_completed=False,
        )
        session.add(practice)
        await session.commit()
        await session.refresh(practice)
        return practice


def build_word_set_meta(word_set: WordSet, user_level: str | None) -> str:
    visible_words = filter_words_for_level(word_set.words, user_level)
    if not visible_words:
        visible_words = word_set.words
    level_range = get_word_set_level_range(word_set, user_level)
    return f"{level_range} | {len(visible_words)} слов"


async def get_theme_progress(telegram_id: int) -> list[dict]:
    user = await get_registered_user(telegram_id)
    if user is None:
        return []

    word_sets = await get_active_word_sets(user.level)
    progress_rows: list[dict] = []

    async with SessionLocal() as session:
        progress_result = await session.execute(
            select(UserWordProgress).where(UserWordProgress.user_id == user.id)
        )
        progress_entries = list(progress_result.scalars().all())

    progress_by_word_id = {entry.word_id: entry for entry in progress_entries}

    for word_set in word_sets:
        visible_words = filter_words_for_level(word_set.words, user.level)
        total = len(visible_words)
        mastered = 0
        difficult = 0
        for word in visible_words:
            entry = progress_by_word_id.get(word.id)
            if entry is None:
                continue
            if entry.correct_count > entry.wrong_count:
                mastered += 1
            elif entry.wrong_count > entry.correct_count:
                difficult += 1

        percent = 0 if total == 0 else round(mastered / total * 100)
        progress_rows.append(
            {
                "title": word_set.title,
                "level": get_word_set_level_range(word_set, user.level),
                "total": total,
                "mastered": mastered,
                "difficult": difficult,
                "percent": percent,
            }
        )

    return progress_rows


async def get_daily_goal_summary(telegram_id: int) -> dict | None:
    user = await get_registered_user(telegram_id)
    if user is None:
        return None

    async with SessionLocal() as session:
        attempts_result = await session.execute(
            select(TrainingAttempt).where(TrainingAttempt.user_id == user.id).order_by(TrainingAttempt.created_at.desc())
        )
        attempts = list(attempts_result.scalars().all())
        practices_result = await session.execute(
            select(DailyPractice).where(DailyPractice.user_id == user.id).order_by(DailyPractice.practice_date.desc())
        )
        daily_practices = list(practices_result.scalars().all())

    today = datetime.now(UTC).date()
    today_attempts = sum(1 for attempt in attempts if attempt.created_at.date() == today)
    today_correct = sum(attempt.correct_answers for attempt in attempts if attempt.created_at.date() == today)
    today_total = sum(attempt.total_questions for attempt in attempts if attempt.created_at.date() == today)

    for practice in daily_practices:
        if practice.practice_date != today or not practice.is_completed:
            continue
        total_questions = len(load_daily_word_ids(practice))
        today_attempts += 1
        today_correct += practice.correct_answers
        today_total += total_questions

    unique_days = sorted({attempt.created_at.date() for attempt in attempts}, reverse=True)
    unique_days.extend(
        sorted(
            {
                practice.practice_date
                for practice in daily_practices
                if practice.is_completed
            },
            reverse=True,
        )
    )
    unique_days = sorted(set(unique_days), reverse=True)
    streak = 0
    cursor = today
    for day in unique_days:
        if day == cursor:
            streak += 1
            cursor = cursor - timedelta(days=1)
        elif day > cursor:
            continue
        else:
            break

    goal_target = 3
    return {
        "today_attempts": today_attempts,
        "today_correct": today_correct,
        "today_total": today_total,
        "goal_target": goal_target,
        "goal_done": min(today_attempts, goal_target),
        "streak": streak,
    }


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

    labels = user_labels(user)
    await send(
        f"Привет, <b>{telegram_user.full_name}</b>! Я ваш помощник в изучении иностранных языков.\n"
        "Что вы хотите сделать сегодня?",
        reply_markup=main_menu_keyboard(labels),
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
                bilingual_ui=True,
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
        f"Уровень: {user.level}\n"
        f"Интерфейс с двумя языками: {'включен' if user.bilingual_ui else 'выключен'}"
    )


def build_quiz_prompt(quiz_format: str, current_word, word_set: WordSet, index: int, total: int, user: User | None) -> str:
    topic_title = topic_label(
        word_set.title,
        user.target_language if user is not None else "en",
        user.source_language if user is not None else "ru",
        user.bilingual_ui if user is not None else True,
    )
    format_title = quiz_format_label(quiz_format, user)

    if quiz_format == "gap":
        masked_example = build_gap_sentence(current_word)
        return (
            f"<b>{format_title}</b>\n"
            f"{topic_title}\n"
            f"Question {index + 1} of {total}\n\n"
            f"{bilingual_block('Fill in the gap.', 'Заполните пропуск.')}\n"
            f"<i>{masked_example}</i>"
        )

    if quiz_format == "definition":
        definition = WORD_DEFINITIONS.get(
            current_word.target_text,
            f"Choose the word that matches: {current_word.source_text}.",
        )
        return (
            f"<b>{format_title}</b>\n"
            f"{topic_title}\n"
            f"Question {index + 1} of {total}\n\n"
            f"{definition}"
        )

    if quiz_format == "match":
        return (
            f"<b>{format_title}</b>\n"
            f"{topic_title}\n"
            f"Question {index + 1} of {total}\n\n"
            f"{bilingual_block('Match the word to the correct meaning.', 'Сопоставьте слово с правильным значением.')}\n"
            f"<b>{current_word.target_text}</b>"
        )

    return (
        f"<b>{format_title}</b>\n"
        f"{topic_title}\n"
        f"Question {index + 1} of {total}\n\n"
        f"{bilingual_block('Choose the correct word.', 'Выберите правильное слово.')}\n"
        f"<b>{current_word.source_text}</b>"
    )


def build_gap_sentence(current_word: Word) -> str:
    example = current_word.example or ""
    pattern = re.compile(re.escape(current_word.target_text), flags=re.IGNORECASE)
    if pattern.search(example):
        return pattern.sub("_____", example, count=1)
    return f"Use the word in context: _____ ({current_word.source_text})"


def supports_gap_mode(word: Word) -> bool:
    if not word.example:
        return False
    return current_word_text_in_example(word)


def current_word_text_in_example(word: Word) -> bool:
    return word.target_text.lower() in word.example.lower()


def choose_quiz_words(words: list[Word], quiz_format: str, limit: int = 7) -> list[Word]:
    pool = words
    if quiz_format == "gap":
        pool = [word for word in words if supports_gap_mode(word)]
    if len(pool) <= limit:
        return pool
    return random.sample(pool, k=limit)


def build_quiz_feedback(
    *,
    is_correct: bool,
    selected_answer: str,
    correct_answer: str,
    current_word: Word,
    quiz_title: str,
    question_index: int,
    total_questions: int,
    correct_count: int,
    is_final: bool,
) -> str:
    status = "✅ Correct" if is_correct else "❌ Not quite"
    lines = [
        status,
        f"<b>{quiz_title}</b>",
        f"Question {question_index + 1} of {total_questions}",
        "",
    ]
    if is_correct:
        lines.append(f"<b>{correct_answer}</b> = {current_word.source_text}")
    else:
        lines.append(f"Your answer: <b>{selected_answer}</b>")
        lines.append(f"Correct answer: <b>{correct_answer}</b>")
        lines.append(f"Meaning: {current_word.source_text}")

    if current_word.example:
        lines.extend(["", f"<i>{current_word.example}</i>"])

    if is_final:
        lines.extend(
            [
                "",
                f"<b>Session complete</b>",
                f"Score: {correct_count}/{total_questions}",
            ]
        )
    return "\n".join(lines)


async def build_quiz_options(
    current_word: Word,
    session_words: list[Word],
    user_level: str | None,
    desired_count: int = 4,
) -> list[str]:
    distractor_targets = {
        word.target_text
        for word in session_words
        if word.id != current_word.id and word.target_text != current_word.target_text
    }

    word_sets = await get_active_word_sets(user_level)
    for word_set in word_sets:
        for word in filter_words_for_level(word_set.words, user_level):
            if word.id == current_word.id or word.target_text == current_word.target_text:
                continue
            distractor_targets.add(word.target_text)

    distractor_pool = list(distractor_targets)
    random.shuffle(distractor_pool)
    selected = distractor_pool[: max(desired_count - 1, 0)]
    options = selected + [current_word.target_text]
    random.shuffle(options)
    return options


async def build_match_options(
    current_word: Word,
    session_words: list[Word],
    user_level: str | None,
    desired_count: int = 4,
) -> list[str]:
    distractor_sources = {
        word.source_text
        for word in session_words
        if word.id != current_word.id and word.source_text != current_word.source_text
    }

    word_sets = await get_active_word_sets(user_level)
    for word_set in word_sets:
        for word in filter_words_for_level(word_set.words, user_level):
            if word.id == current_word.id or word.source_text == current_word.source_text:
                continue
            distractor_sources.add(word.source_text)

    distractor_pool = list(distractor_sources)
    random.shuffle(distractor_pool)
    selected = distractor_pool[: max(desired_count - 1, 0)]
    options = selected + [current_word.source_text]
    random.shuffle(options)
    return options


async def show_quiz_question(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    review_mode = data.get("review_mode", False)
    daily_mode = data.get("daily_mode", False)
    question_index = data["quiz_index"]
    quiz_format = data["quiz_format"]
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None

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
        quiz_words = await get_words_by_ids(data["quiz_word_ids"])
        if not quiz_words:
            await state.clear()
            await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:quiz"))
            return
        current_word = quiz_words[question_index]
        total_questions = len(quiz_words)
        topic_title = data["quiz_title"]
        options_pool = quiz_words

    if quiz_format == "match":
        options = await build_match_options(current_word, options_pool, user_level)
        correct_answer = current_word.source_text
    else:
        options = await build_quiz_options(current_word, options_pool, user_level)
        correct_answer = current_word.target_text

    await state.update_data(correct_answer=correct_answer, current_word_id=current_word.id)
    await edit_screen(
        callback,
        build_quiz_prompt(
            quiz_format,
            current_word,
            WordSet(title=topic_title, description=None, level="", is_active=True),
            question_index,
            total_questions,
            user,
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
    await edit_screen(callback, "Профиль сохранен.\n\n" + format_profile(user), profile_keyboard(user_labels(user)))


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
    await edit_screen(callback, format_profile(user), profile_keyboard(user_labels(user)))


@router.callback_query(F.data == "profile:toggle_bilingual")
async def profile_toggle_bilingual_handler(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            await edit_screen(
                callback,
                "Профиль еще не настроен.\n\nСначала завершите настройку профиля.",
                nav_keyboard(back_to="profile:start_setup"),
            )
            return
        user.bilingual_ui = not user.bilingual_ui
        await session.commit()
        await session.refresh(user)
    await edit_screen(callback, format_profile(user), profile_keyboard(user_labels(user)))


@router.callback_query(F.data == "menu:course")
async def course_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    labels = user_labels(user)
    target_language = user.target_language if user is not None else "en"
    source_language = user.source_language if user is not None else "ru"
    bilingual = user.bilingual_ui if user is not None else True
    await edit_screen(
        callback,
        f"<b>{translated_label('course_title', target_language, source_language, bilingual)}</b>\n\n"
        "Choose what you want to build today: vocabulary, grammar, or guided dialogues."
        if target_language == "en"
        else "<b>Course</b>\n\nChoose what you want to build today: vocabulary, grammar, or guided dialogues.",
        course_menu_keyboard(labels),
    )


@router.callback_query(F.data == "menu:practice")
async def practice_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await get_registered_user(callback.from_user.id)
    labels = user_labels(user)
    target_language = user.target_language if user is not None else "en"
    source_language = user.source_language if user is not None else "ru"
    bilingual = user.bilingual_ui if user is not None else True
    await edit_screen(
        callback,
        f"<b>{translated_label('practice_title', target_language, source_language, bilingual)}</b>\n\n"
        "Train actively: daily sets and mixed quizzes keep recent language fresh."
        if target_language == "en"
        else "<b>Practice</b>\n\nTrain actively: daily sets and mixed quizzes keep recent language fresh.",
        practice_menu_keyboard(labels),
    )


@router.callback_query(F.data == "menu:learn")
async def learn_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    target_language = user.target_language if user is not None else "en"
    source_language = user.source_language if user is not None else "ru"
    bilingual = user.bilingual_ui if user is not None else True
    word_sets = await get_active_word_sets(user_level)
    payload = [
        (
            word_set.id,
            topic_label(word_set.title, target_language, source_language, bilingual),
            build_word_set_meta(word_set, user_level),
        )
        for word_set in word_sets
    ]
    text = "Choose a topic:"
    if user_level is not None:
        text = f"Choose a topic for level {user_level}:"
    await edit_screen(callback, text, word_sets_keyboard(payload, mode="learn"))


@router.callback_query(F.data == "menu:grammar")
async def grammar_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    target_language = user.target_language if user is not None else "en"
    source_language = user.source_language if user is not None else "ru"
    bilingual = user.bilingual_ui if user is not None else True
    units = get_grammar_units(user_level)
    payload = [
        (unit["id"], grammar_label(unit["title"], target_language, source_language, bilingual), unit["level"])
        for unit in units
    ]
    text = (
        "Choose a grammar block.\n\n"
        "Work through tenses, structures, and discourse patterns level by level."
    )
    if user_level is not None:
        text = (
            f"Choose a grammar block for level {user_level}.\n\n"
            "This list includes the grammar topics that should already be active at your level."
        )
    await edit_screen(callback, text, grammar_units_keyboard(payload))


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


@router.callback_query(F.data.startswith("grammar:unit:"))
async def grammar_unit_handler(callback: CallbackQuery) -> None:
    unit_id = callback.data.split(":")[-1]
    unit = get_grammar_unit(unit_id)
    if unit is None:
        await edit_screen(callback, "Грамматический блок не найден.", nav_keyboard(back_to="menu:grammar"))
        return
    await edit_screen(callback, format_grammar_unit(unit), nav_keyboard(back_to="menu:grammar"))


@router.callback_query(F.data.startswith("learn:set:"))
async def learn_set_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    word_set = await get_word_set(int(callback.data.split(":")[-1]))
    if word_set is None:
        await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:learn"))
        return
    words = filter_words_for_level(word_set.words, user_level)
    if not words:
        await edit_screen(
            callback,
            "Для вашего текущего уровня в этой теме пока нет доступных слов.",
            nav_keyboard(back_to="menu:learn"),
        )
        return
    word = words[0]
    await edit_screen(
        callback,
        render_word_card(word_set=word_set, word=word, current_index=0, total=len(words), user=user),
        card_keyboard(word_set.id, 0, len(words)),
    )


@router.callback_query(F.data.startswith("learn:card:"))
async def learn_card_handler(callback: CallbackQuery) -> None:
    _, _, word_set_id, index = callback.data.split(":")
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    word_set = await get_word_set(int(word_set_id))
    if word_set is None:
        await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:learn"))
        return
    words = filter_words_for_level(word_set.words, user_level)
    if not words:
        await edit_screen(
            callback,
            "Для вашего текущего уровня в этой теме пока нет доступных слов.",
            nav_keyboard(back_to="menu:learn"),
        )
        return
    current_index = min(int(index), len(words) - 1)
    word = words[current_index]
    await edit_screen(
        callback,
        render_word_card(
            word_set=word_set,
            word=word,
            current_index=current_index,
            total=len(words),
            user=user,
        ),
        card_keyboard(word_set.id, current_index, len(words)),
    )


@router.callback_query(F.data == "menu:quiz")
async def quiz_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_screen(
        callback,
        "<b>Practice quiz</b>\n\nChoose a format.\n<i>Выберите формат.</i>",
        quiz_formats_keyboard(),
    )


@router.callback_query(F.data == "menu:daily")
async def daily_practice_handler(callback: CallbackQuery, state: FSMContext) -> None:
    practice = await get_or_create_daily_practice(callback.from_user.id, limit=5)
    if practice is None:
        await edit_screen(
            callback,
            "Для практики дня пока недостаточно слов.\n\n"
            "Сначала настройте профиль или расширьте учебный контент.",
            nav_keyboard(back_to="menu:home", include_home=False),
        )
        return

    words = await get_words_by_ids(load_daily_word_ids(practice))
    if len(words) < 2:
        await edit_screen(
            callback,
            "Практика дня пока недоступна: не удалось собрать актуальный набор слов.",
            nav_keyboard(back_to="menu:home", include_home=False),
        )
        return

    if practice.is_completed:
        await state.clear()
        await edit_screen(callback, format_daily_completion(practice, words), nav_keyboard(back_to="menu:home"))
        return

    await state.set_state(QuizStates.in_progress)
    await state.update_data(
        daily_practice_id=practice.id,
        daily_mode=True,
        daily_word_ids=load_daily_word_ids(practice),
        review_mode=False,
        quiz_word_set_id=None,
        quiz_index=practice.current_index,
        quiz_correct=practice.correct_answers,
        quiz_format="choice",
    )
    await show_quiz_question(callback, state)


@router.callback_query(F.data == "menu:review")
async def review_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "<b>Review</b>\n<i>Повторение</i>\n\n"
        "Revisit weak words and run a short mistakes quiz.\n"
        "<i>Здесь можно посмотреть слабые слова и пройти короткий квиз по ошибкам.</i>",
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

    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    word_sets = await get_active_word_sets(user_level)
    payload = [(word_set.id, word_set.title, build_word_set_meta(word_set, user_level)) for word_set in word_sets]
    await edit_screen(
        callback,
        f"Выберите тему для квиза формата «{QUIZ_FORMATS[quiz_format]}»:",
        word_sets_keyboard(payload, mode=f"quiz:{quiz_format}"),
    )


@router.callback_query(F.data.startswith("quiz:choice:set:"))
@router.callback_query(F.data.startswith("quiz:gap:set:"))
@router.callback_query(F.data.startswith("quiz:definition:set:"))
@router.callback_query(F.data.startswith("quiz:match:set:"))
async def quiz_set_handler(callback: CallbackQuery, state: FSMContext) -> None:
    _, quiz_format, _, raw_id = callback.data.split(":")
    await state.update_data(selected_quiz_format=quiz_format)
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    word_set = await get_word_set(int(raw_id))
    if word_set is None:
        await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:quiz"))
        return
    words = filter_words_for_level(word_set.words, user_level)
    if not words:
        await edit_screen(
            callback,
            "Для вашего текущего уровня в этой теме пока нет слов для квиза.",
            nav_keyboard(back_to="menu:quiz"),
        )
        return
    quiz_words = choose_quiz_words(words, quiz_format)
    if len(quiz_words) < 2:
        await edit_screen(
            callback,
            "Для этого формата пока недостаточно подходящих примеров в теме.",
            nav_keyboard(back_to="menu:quiz"),
        )
        return
    await edit_screen(
        callback,
        f"<b>{word_set.title}</b>\n"
        f"{word_set.description}\n\n"
        f"Формат квиза: {QUIZ_FORMATS[quiz_format]}\n"
        f"Диапазон уровней: {get_word_set_level_range(word_set, user_level)}\n"
        f"Количество вопросов: {len(quiz_words)}",
        start_quiz_keyboard(word_set.id, quiz_format),
    )


@router.callback_query(F.data.startswith("quiz:start:"))
async def quiz_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, quiz_format, raw_id = callback.data.split(":")
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    word_set = await get_word_set(int(raw_id))
    if word_set is None:
        await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:quiz"))
        return
    words = filter_words_for_level(word_set.words, user_level)
    if not words:
        await edit_screen(
            callback,
            "Для вашего текущего уровня в этой теме пока нет слов для квиза.",
            nav_keyboard(back_to="menu:quiz"),
        )
        return
    quiz_words = choose_quiz_words(words, quiz_format)
    if len(quiz_words) < 2:
        await edit_screen(
            callback,
            "Для этого формата пока недостаточно подходящих примеров в теме.",
            nav_keyboard(back_to="menu:quiz"),
        )
        return
    await state.set_state(QuizStates.in_progress)
    await state.update_data(
        daily_mode=False,
        review_mode=False,
        quiz_word_set_id=word_set.id,
        quiz_word_ids=[word.id for word in quiz_words],
        quiz_title=word_set.title,
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
        current_word = review_words[data["quiz_index"]]
        total_questions = len(review_words)
        quiz_title = "Повторение ошибок"
        word_set_id = None
    elif daily_mode:
        daily_words = await get_words_by_ids(data["daily_word_ids"])
        if not daily_words:
            await state.clear()
            await edit_screen(callback, "Слова для практики дня не найдены.", nav_keyboard(back_to="menu:daily"))
            return
        current_word = daily_words[data["quiz_index"]]
        total_questions = len(daily_words)
        quiz_title = "Практика дня"
        word_set_id = None
    else:
        quiz_words = await get_words_by_ids(data["quiz_word_ids"])
        if not quiz_words:
            await state.clear()
            await edit_screen(callback, "Набор слов не найден.", nav_keyboard(back_to="menu:quiz"))
            return
        current_word = quiz_words[data["quiz_index"]]
        total_questions = len(quiz_words)
        quiz_title = data["quiz_title"]
        word_set_id = data["quiz_word_set_id"]

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
                    progress = UserWordProgress(
                        user_id=user.id,
                        word_id=data["current_word_id"],
                        correct_count=0,
                        wrong_count=0,
                    )
                    session.add(progress)
                progress.correct_count = progress.correct_count or 0
                progress.wrong_count = progress.wrong_count or 0
                if is_correct:
                    progress.correct_count += 1
                else:
                    progress.wrong_count += 1
                progress.last_result = is_correct

                if daily_mode:
                    practice_result = await session.execute(
                        select(DailyPractice).where(DailyPractice.id == data["daily_practice_id"])
                    )
                    practice = practice_result.scalar_one_or_none()
                    if practice is not None:
                        practice.current_index = total_questions
                        practice.correct_answers = correct_count
                        practice.is_completed = True
                        practice.completed_at = datetime.now(UTC)

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
        await edit_screen(
            callback,
            build_quiz_feedback(
                is_correct=is_correct,
                selected_answer=selected_answer,
                correct_answer=data["correct_answer"],
                current_word=current_word,
                quiz_title=quiz_title,
                question_index=data["quiz_index"],
                total_questions=total_questions,
                correct_count=correct_count,
                is_final=True,
            ),
            quiz_feedback_keyboard(
                next_step=False,
                back_to="menu:daily" if daily_mode else ("menu:review" if review_mode else "menu:quiz"),
            ),
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
                progress = UserWordProgress(
                    user_id=user.id,
                    word_id=data["current_word_id"],
                    correct_count=0,
                    wrong_count=0,
                )
                session.add(progress)
            progress.correct_count = progress.correct_count or 0
            progress.wrong_count = progress.wrong_count or 0
            if is_correct:
                progress.correct_count += 1
            else:
                progress.wrong_count += 1
            progress.last_result = is_correct

            if daily_mode:
                practice_result = await session.execute(
                    select(DailyPractice).where(DailyPractice.id == data["daily_practice_id"])
                )
                practice = practice_result.scalar_one_or_none()
                if practice is not None:
                    practice.current_index = next_index
                    practice.correct_answers = correct_count
            await session.commit()

    await state.update_data(quiz_index=next_index, quiz_correct=correct_count)
    await edit_screen(
        callback,
        build_quiz_feedback(
            is_correct=is_correct,
            selected_answer=selected_answer,
            correct_answer=data["correct_answer"],
            current_word=current_word,
            quiz_title=quiz_title,
            question_index=data["quiz_index"],
            total_questions=total_questions,
            correct_count=correct_count,
            is_final=False,
        ),
        quiz_feedback_keyboard(next_step=True),
    )


@router.callback_query(QuizStates.in_progress, F.data == "quiz:next")
async def quiz_next_handler(callback: CallbackQuery, state: FSMContext) -> None:
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
        stats_keyboard(),
    )


@router.callback_query(F.data == "stats:goal")
async def stats_goal_handler(callback: CallbackQuery) -> None:
    summary = await get_daily_goal_summary(callback.from_user.id)
    if summary is None:
        await edit_screen(
            callback,
            "Сначала настройте профиль, чтобы бот начал отслеживать вашу активность.",
            nav_keyboard(back_to="menu:stats"),
        )
        return

    accuracy = 0
    if summary["today_total"] > 0:
        accuracy = round(summary["today_correct"] / summary["today_total"] * 100)

    await edit_screen(
        callback,
        "<b>Цель дня</b>\n\n"
        f"Пройдено квизов сегодня: {summary['today_attempts']}\n"
        f"Прогресс цели: {summary['goal_done']}/{summary['goal_target']}\n"
        f"Сегодняшняя точность: {accuracy}%\n"
        f"Серия дней подряд: {summary['streak']}",
        nav_keyboard(back_to="menu:stats"),
    )


@router.callback_query(F.data == "stats:themes")
async def stats_themes_handler(callback: CallbackQuery) -> None:
    rows = await get_theme_progress(callback.from_user.id)
    if not rows:
        await edit_screen(
            callback,
            "Прогресс по темам пока пуст.\n\n"
            "Изучите слова и пройдите несколько квизов, чтобы увидеть разбивку по темам.",
            nav_keyboard(back_to="menu:stats"),
        )
        return

    lines = []
    for row in rows:
        lines.append(
            f"• <b>{row['title']}</b> [{row['level']}]\n"
            f"  Освоено: {row['mastered']}/{row['total']} | "
            f"Сложных слов: {row['difficult']} | "
            f"Прогресс: {row['percent']}%"
        )

    await edit_screen(
        callback,
        "<b>Прогресс по темам</b>\n\n" + "\n".join(lines),
        nav_keyboard(back_to="menu:stats"),
    )


@router.callback_query(F.data == "menu:help")
async def help_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    await edit_screen(
        callback,
        "Привет! Я ваш помощник в изучении иностранных языков. Что вы хотите сделать сегодня?\n\n"
        "1. Изучить слова\n"
        "2. Изучить грамматику\n"
        "3. Пройти квиз",
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
        "Сценарий 2: Изучение грамматики\n"
        "1. Открыть раздел грамматики\n"
        "2. Выбрать грамматический блок\n"
        "3. Посмотреть шаблоны и примеры\n\n"
        "Сценарий 3: Прохождение квиза\n"
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
        "- сквозные темы с лексикой от A1 до C2\n"
        "- карточки слов с примерами и прогрессией по уровням\n"
        "- несколько режимов практики и повторения\n"
        "- мини-диалоги и практику дня\n"
        "- сохранение статистики обучения",
        nav_keyboard(back_to="menu:help", include_home=user is not None),
    )
