from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.database.models import User
from bot.database.session import SessionLocal
from bot.keyboards.main_menu import main_menu_keyboard, section_keyboard
from bot.states.onboarding import OnboardingStates

router = Router()


async def get_registered_user(telegram_id: int) -> User | None:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        return

    user = await get_registered_user(telegram_user.id)
    if user is None:
        await state.set_state(OnboardingStates.choose_target_language)
        await message.answer(
            "Привет. Я помогу учить иностранный язык.\n\n"
            "Для начала выбери язык, который хочешь изучать:",
            reply_markup=main_menu_keyboard(is_registered=False),
        )
        return

    await state.clear()
    await message.answer(
        f"С возвращением, <b>{telegram_user.full_name}</b>.\nВыбери действие:",
        reply_markup=main_menu_keyboard(is_registered=True),
    )


@router.callback_query(F.data == "menu:home")
async def home_handler(callback: CallbackQuery, state: FSMContext) -> None:
    telegram_user = callback.from_user
    user = await get_registered_user(telegram_user.id)
    await state.clear()
    await callback.answer()

    if callback.message is None:
        return

    if user is None:
        await callback.message.edit_text(
            "Привет. Я помогу учить иностранный язык.\n\n"
            "Для начала выбери язык, который хочешь изучать:",
            reply_markup=main_menu_keyboard(is_registered=False),
        )
        return

    await callback.message.edit_text(
        f"С возвращением, <b>{telegram_user.full_name}</b>.\nВыбери действие:",
        reply_markup=main_menu_keyboard(is_registered=True),
    )


@router.callback_query(F.data == "menu:profile_setup")
async def profile_setup_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.choose_target_language)
    if callback.message is None:
        await callback.answer()
        return
    await callback.message.edit_text(
        "Профиль пока в стадии MVP.\n\n"
        "На следующем спринте здесь будет выбор родного языка, изучаемого языка и уровня.",
        reply_markup=section_keyboard(is_registered=False),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:learn")
async def learn_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None:
        return
    user = await get_registered_user(callback.from_user.id)
    await callback.message.edit_text(
        "Раздел обучения будет реализован в следующем спринте.\n"
        "Пока здесь будет выбор наборов слов и карточек.",
        reply_markup=section_keyboard(is_registered=user is not None),
    )


@router.callback_query(F.data == "menu:quiz")
async def quiz_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None:
        return
    user = await get_registered_user(callback.from_user.id)
    await callback.message.edit_text(
        "Раздел тестирования пока в разработке.\n"
        "Здесь появятся квизы, проверка ответов и результаты.",
        reply_markup=section_keyboard(is_registered=user is not None),
    )


@router.callback_query(F.data == "menu:stats")
async def stats_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None:
        return
    user = await get_registered_user(callback.from_user.id)
    await callback.message.edit_text(
        "Раздел статистики будет подключен после реализации тренировок и сохранения прогресса.",
        reply_markup=section_keyboard(is_registered=user is not None),
    )


@router.callback_query(F.data == "menu:help")
async def help_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None:
        return
    user = await get_registered_user(callback.from_user.id)
    await callback.message.edit_text(
        "EngyBot помогает изучать язык короткими сессиями:\n"
        "- учить слова по темам\n"
        "- проходить мини-тесты\n"
        "- отслеживать прогресс",
        reply_markup=section_keyboard(is_registered=user is not None),
    )
