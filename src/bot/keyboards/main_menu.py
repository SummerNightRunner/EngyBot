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


def section_keyboard(*, is_registered: bool) -> InlineKeyboardMarkup:
    buttons = []
    if is_registered:
        buttons.append([InlineKeyboardButton(text="В меню", callback_data="menu:home")])
    else:
        buttons.append([InlineKeyboardButton(text="Настроить профиль", callback_data="menu:profile_setup")])
    buttons.append([InlineKeyboardButton(text="Помощь", callback_data="menu:help")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
