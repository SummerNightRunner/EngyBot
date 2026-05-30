from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.main_menu import (
    card_keyboard,
    course_menu_keyboard,
    course_units_keyboard,
    dialogue_keyboard,
    dialogue_step_keyboard,
    grammar_units_keyboard,
    nav_keyboard,
    unit_actions_keyboard,
    word_sets_keyboard,
)
from bot.services.content import filter_words_for_level

from .start import (
    bilingual_block,
    build_unit_context,
    build_word_set_meta,
    edit_screen,
    format_grammar_unit,
    get_active_word_sets,
    get_course_unit,
    get_course_units,
    get_dialogue_by_id,
    get_dialogue_scenarios,
    get_grammar_unit,
    get_grammar_units,
    get_registered_user,
    get_word_set,
    grammar_label,
    render_word_card,
    topic_label,
    translated_label,
    user_labels,
)

router = Router()


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
        + bilingual_block(
            "Open a unit or jump directly to vocabulary, grammar, or dialogues.",
            "Откройте юнит или перейдите сразу к словам, грамматике или диалогам."
            if bilingual and target_language == "en"
            else None,
        ),
        course_menu_keyboard(labels),
    )


@router.callback_query(F.data == "menu:units")
async def units_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    user_level = user.level if user is not None else None
    target_language = user.target_language if user is not None else "en"
    bilingual = user.bilingual_ui if user is not None else True
    units = get_course_units(user_level)
    payload = [
        (
            unit["id"],
            bilingual_block(
                unit["title"],
                f"Юнит {unit['level']}" if bilingual and target_language == "en" else None,
                italic_secondary=False,
            ).replace("\n", " • "),
            unit["level"],
            unit["summary"],
        )
        for unit in units
    ]
    await edit_screen(
        callback,
        bilingual_block(
            "Units organize the course into linked blocks: vocabulary, grammar, dialogue, and practice.",
            "Юниты собирают курс в связанные блоки: словарь, грамматика, диалоги и практика."
            if bilingual and target_language == "en"
            else None,
        ),
        course_units_keyboard(payload),
    )


@router.callback_query(F.data.startswith("unit:view:"))
async def unit_view_handler(callback: CallbackQuery) -> None:
    unit_id = callback.data.split(":")[-1]
    unit = get_course_unit(unit_id)
    if unit is None:
        await edit_screen(callback, "Юнит не найден.", nav_keyboard(back_to="menu:units"))
        return

    user = await get_registered_user(callback.from_user.id)
    context = await build_unit_context(unit, user)
    target_language = user.target_language if user is not None else "en"
    bilingual = user.bilingual_ui if user is not None else True

    topic_lines = "\n".join(f"• {label}" for _, label in context["topic_links"]) or "• —"
    grammar_lines = "\n".join(f"• {label}" for _, label in context["grammar_links"]) or "• —"
    dialogue_lines = "\n".join(f"• {label}" for _, label in context["dialogue_links"]) or "• —"

    text = (
        f"<b>{unit['title']}</b>\n"
        f"{bilingual_block(f'Level: {unit['level']}', f'Уровень: {unit['level']}' if bilingual and target_language == 'en' else None)}\n\n"
        f"{unit['summary']}\n\n"
        f"{bilingual_block('Vocabulary focus', 'Словарный фокус' if bilingual and target_language == 'en' else None)}\n"
        f"{topic_lines}\n\n"
        f"{bilingual_block('Grammar focus', 'Грамматический фокус' if bilingual and target_language == 'en' else None)}\n"
        f"{grammar_lines}\n\n"
        f"{bilingual_block('Dialogue practice', 'Диалоговая практика' if bilingual and target_language == 'en' else None)}\n"
        f"{dialogue_lines}"
    )

    await edit_screen(
        callback,
        text,
        unit_actions_keyboard(
            unit_id=unit["id"],
            topic_links=context["topic_links"],
            grammar_links=context["grammar_links"],
            dialogue_links=context["dialogue_links"],
        ),
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
