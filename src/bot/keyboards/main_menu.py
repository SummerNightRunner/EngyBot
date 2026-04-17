from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(*, is_registered: bool) -> InlineKeyboardMarkup:
    if not is_registered:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Настроить профиль", callback_data="menu:profile_setup")],
                [InlineKeyboardButton(text="Помощь", callback_data="menu:help")],
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Учить слова", callback_data="menu:learn")],
            [InlineKeyboardButton(text="Пройти тест", callback_data="menu:quiz")],
            [InlineKeyboardButton(text="Статистика", callback_data="menu:stats")],
            [InlineKeyboardButton(text="Помощь", callback_data="menu:help")],
        ]
    )


def nav_keyboard(*, back_to: str | None = None, include_home: bool = True) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    if back_to is not None:
        buttons.append([InlineKeyboardButton(text="Назад", callback_data=back_to)])

    if include_home:
        buttons.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def profile_setup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать язык", callback_data="profile:target_language")],
            [InlineKeyboardButton(text="Как будет устроен профиль", callback_data="profile:about")],
            [InlineKeyboardButton(text="Назад", callback_data="menu:home")],
        ]
    )


def learn_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Наборы слов", callback_data="learn:sets")],
            [InlineKeyboardButton(text="Как работает обучение", callback_data="learn:about")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:home")],
        ]
    )


def quiz_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Формат тестов", callback_data="quiz:about")],
            [InlineKeyboardButton(text="Что будет проверяться", callback_data="quiz:topics")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:home")],
        ]
    )


def stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Что будет в статистике", callback_data="stats:about")],
            [InlineKeyboardButton(text="Как считаем прогресс", callback_data="stats:progress")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:home")],
        ]
    )


def help_keyboard(*, is_registered: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Как пользоваться ботом", callback_data="help:usage")],
        [InlineKeyboardButton(text="Что умеет MVP", callback_data="help:mvp")],
    ]

    if not is_registered:
        buttons.append([InlineKeyboardButton(text="Настроить профиль", callback_data="menu:profile_setup")])

    buttons.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
