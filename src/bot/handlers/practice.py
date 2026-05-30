from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select

from bot.database.models import DailyPractice, TrainingAttempt, UserWordProgress
from bot.database.session import SessionLocal
from bot.keyboards.main_menu import (
    nav_keyboard,
    practice_menu_keyboard,
    quiz_feedback_keyboard,
    quiz_formats_keyboard,
    review_keyboard,
    start_quiz_keyboard,
    word_sets_keyboard,
)
from bot.services.content import filter_words_for_level, get_word_set_level_range
from bot.states.training import QuizStates

from .start import (
    bilingual_block,
    build_quiz_feedback,
    build_word_set_meta,
    choose_quiz_words,
    edit_screen,
    format_daily_completion,
    get_active_word_sets,
    get_or_create_daily_practice,
    get_registered_user,
    get_review_words,
    get_word_set,
    get_words_by_ids,
    load_daily_word_ids,
    show_quiz_question,
    single_line_quiz_format_label,
    topic_label,
    user_labels,
)

router = Router()


@router.callback_query(F.data == "menu:practice")
async def practice_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await get_registered_user(callback.from_user.id)
    labels = user_labels(user)
    target_language = user.target_language if user is not None else "en"
    bilingual = user.bilingual_ui if user is not None else True
    await edit_screen(
        callback,
        (
            f"<b>{labels['practice']}</b>\n\n"
            + bilingual_block(
                "Train actively: daily sets and mixed quizzes keep recent language fresh.",
                "Тренируйтесь активно: практика дня и смешанные квизы помогают закреплять язык."
                if bilingual and target_language == "en"
                else None,
            )
        ),
        practice_menu_keyboard(labels),
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
    await edit_screen(
        callback,
        bilingual_block(
            f"Choose a topic for the {single_line_quiz_format_label(quiz_format, user)} quiz.",
            f"Выберите тему для квиза формата {single_line_quiz_format_label(quiz_format, user)}."
            if bilingual and target_language == "en"
            else None,
        ),
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
    target_language = user.target_language if user is not None else "en"
    source_language = user.source_language if user is not None else "ru"
    bilingual = user.bilingual_ui if user is not None else True
    title = topic_label(word_set.title, target_language, source_language, bilingual)
    await edit_screen(
        callback,
        f"<b>{title}</b>\n"
        f"{word_set.description}\n\n"
        f"{bilingual_block('Quiz format', 'Формат квиза' if bilingual and target_language == 'en' else None)}: "
        f"{single_line_quiz_format_label(quiz_format, user)}\n"
        f"{bilingual_block('Level range', 'Диапазон уровней' if bilingual and target_language == 'en' else None)}: "
        f"{get_word_set_level_range(word_set, user_level)}\n"
        f"{bilingual_block('Questions', 'Количество вопросов' if bilingual and target_language == 'en' else None)}: "
        f"{len(quiz_words)}",
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
    user = await get_registered_user(callback.from_user.id)
    current_options = data.get("current_options", [])
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
                user=user,
            ),
            quiz_feedback_keyboard(
                next_step=False,
                back_to="menu:daily" if daily_mode else ("menu:review" if review_mode else "menu:quiz"),
                options=current_options,
                selected_answer=selected_answer,
                correct_answer=data["correct_answer"],
            ),
        )
        return

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
            user=user,
        ),
        quiz_feedback_keyboard(
            next_step=True,
            options=current_options,
            selected_answer=selected_answer,
            correct_answer=data["correct_answer"],
        ),
    )


@router.callback_query(QuizStates.in_progress, F.data == "quiz:next")
async def quiz_next_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await show_quiz_question(callback, state)
