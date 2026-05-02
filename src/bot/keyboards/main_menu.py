from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


LANGUAGE_OPTIONS = [
    ("Русский", "ru"),
    ("Английский", "en"),
    ("Немецкий", "de"),
]

LEVEL_OPTIONS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Практика дня", callback_data="menu:daily")],
            [InlineKeyboardButton(text="Изучить слова", callback_data="menu:learn")],
            [InlineKeyboardButton(text="Мини-диалоги", callback_data="menu:dialogue")],
            [InlineKeyboardButton(text="Пройти квиз", callback_data="menu:quiz")],
            [InlineKeyboardButton(text="Повторение", callback_data="menu:review")],
            [InlineKeyboardButton(text="Профиль", callback_data="menu:profile")],
            [InlineKeyboardButton(text="Статистика", callback_data="menu:stats")],
            [InlineKeyboardButton(text="Помощь", callback_data="menu:help")],
        ]
    )


def guest_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать настройку", callback_data="profile:start_setup")],
            [InlineKeyboardButton(text="Помощь", callback_data="menu:help")],
        ]
    )


def language_keyboard(prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{prefix}:{code}")]
        for label, code in LANGUAGE_OPTIONS
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def level_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=level, callback_data=f"profile:level:{level}")] for level in LEVEL_OPTIONS]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить профиль", callback_data="profile:start_setup")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:home")],
        ]
    )


def help_keyboard(is_registered: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Как пользоваться ботом", callback_data="help:usage")],
        [InlineKeyboardButton(text="Что умеет MVP", callback_data="help:mvp")],
    ]
    if not is_registered:
        rows.append([InlineKeyboardButton(text="Начать настройку", callback_data="profile:start_setup")])
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def word_sets_keyboard(word_sets: list[tuple[int, str, str]], *, mode: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{title} ({level})", callback_data=f"{mode}:set:{word_set_id}")]
        for word_set_id, title, level in word_sets
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_formats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Выбор правильного варианта", callback_data="quiz:format:choice")],
            [InlineKeyboardButton(text="Заполнение пропусков", callback_data="quiz:format:gap")],
            [InlineKeyboardButton(text="Угадай слово по определению", callback_data="quiz:format:definition")],
            [InlineKeyboardButton(text="Соответствие", callback_data="quiz:format:match")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:home")],
        ]
    )


def card_keyboard(word_set_id: int, index: int, total: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if index + 1 < total:
        rows.append([InlineKeyboardButton(text="Следующее слово", callback_data=f"learn:card:{word_set_id}:{index + 1}")])
    rows.append([InlineKeyboardButton(text="К списку тем", callback_data="menu:learn")])
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_quiz_keyboard(word_set_id: int, quiz_format: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать квиз", callback_data=f"quiz:start:{quiz_format}:{word_set_id}")],
            [InlineKeyboardButton(text="К форматам квизов", callback_data="menu:quiz")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:home")],
        ]
    )


def quiz_options_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=option, callback_data=f"quiz:answer:{option}")] for option in options]
    rows.append([InlineKeyboardButton(text="Прервать квиз", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def nav_keyboard(*, back_to: str | None = None, include_home: bool = True) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if back_to is not None:
        rows.append([InlineKeyboardButton(text="Назад", callback_data=back_to)])
    if include_home:
        rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Слабые слова", callback_data="review:words")],
            [InlineKeyboardButton(text="Квиз по ошибкам", callback_data="review:quiz")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:home")],
        ]
    )


def dialogue_keyboard(scenarios: list[tuple[str, str, str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{title} [{level}] - {theme}", callback_data=f"dialogue:{scenario_id}:0")]
        for scenario_id, title, level, theme in scenarios
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dialogue_step_keyboard(scenario_id: str, index: int, total: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if index + 1 < total:
        rows.append([InlineKeyboardButton(text="Следующая реплика", callback_data=f"dialogue:{scenario_id}:{index + 1}")])
    rows.append([InlineKeyboardButton(text="К списку диалогов", callback_data="menu:dialogue")])
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
