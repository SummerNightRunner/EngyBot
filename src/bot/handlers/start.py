from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.database.models import User
from bot.database.session import SessionLocal
from bot.keyboards.main_menu import (
    help_keyboard,
    learn_keyboard,
    main_menu_keyboard,
    nav_keyboard,
    profile_setup_keyboard,
    quiz_keyboard,
    stats_keyboard,
)
from bot.states.onboarding import OnboardingStates

router = Router()


async def get_registered_user(telegram_id: int) -> User | None:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def edit_screen(callback: CallbackQuery, text: str, reply_markup) -> None:
    if callback.message is None:
        await callback.answer()
        return

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=reply_markup)


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
    await edit_screen(
        callback,
        "Профиль пока в стадии MVP.\n\n"
        "Здесь будет настройка родного языка, изучаемого языка и уровня.",
        reply_markup=profile_setup_keyboard(),
    )


@router.callback_query(F.data == "menu:learn")
async def learn_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "Раздел обучения будет реализован в следующем спринте.\n"
        "Здесь будет выбор наборов слов, карточек и учебных сценариев.",
        reply_markup=learn_keyboard(),
    )


@router.callback_query(F.data == "menu:quiz")
async def quiz_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "Раздел тестирования пока в разработке.\n"
        "Здесь появятся квизы, проверка ответов и результаты.",
        reply_markup=quiz_keyboard(),
    )


@router.callback_query(F.data == "menu:stats")
async def stats_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "Раздел статистики будет подключен после реализации тренировок и сохранения прогресса.",
        reply_markup=stats_keyboard(),
    )


@router.callback_query(F.data == "menu:help")
async def help_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    await edit_screen(
        callback,
        "EngyBot помогает изучать язык короткими сессиями:\n"
        "- учить слова по темам\n"
        "- проходить мини-тесты\n"
        "- отслеживать прогресс",
        reply_markup=help_keyboard(is_registered=user is not None),
    )


@router.callback_query(F.data == "profile:target_language")
async def profile_target_language_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "На следующем шаге пользователь сможет выбрать изучаемый язык из списка.\n\n"
        "Пока экран работает как заготовка для полноценного онбординга.",
        reply_markup=nav_keyboard(back_to="menu:profile_setup"),
    )


@router.callback_query(F.data == "profile:about")
async def profile_about_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "Профиль будет хранить:\n"
        "- родной язык\n"
        "- изучаемый язык\n"
        "- уровень пользователя\n"
        "- текущий прогресс",
        reply_markup=nav_keyboard(back_to="menu:profile_setup"),
    )


@router.callback_query(F.data == "learn:sets")
async def learn_sets_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "Здесь появится список тематических наборов:\n"
        "- путешествия\n"
        "- еда\n"
        "- повседневное общение\n"
        "- работа и учеба",
        reply_markup=nav_keyboard(back_to="menu:learn"),
    )


@router.callback_query(F.data == "learn:about")
async def learn_about_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "Механика обучения будет строиться на карточках слов и коротких сессиях.\n\n"
        "Пользователь выбирает тему, получает слова с переводом и примерами, а затем переходит к тренировке.",
        reply_markup=nav_keyboard(back_to="menu:learn"),
    )


@router.callback_query(F.data == "quiz:about")
async def quiz_about_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "В MVP будет несколько форматов проверки:\n"
        "- выбор правильного перевода\n"
        "- сопоставление слова и значения\n"
        "- короткие тематические мини-квизы",
        reply_markup=nav_keyboard(back_to="menu:quiz"),
    )


@router.callback_query(F.data == "quiz:topics")
async def quiz_topics_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "Тестирование будет запускаться по выбранному набору слов.\n\n"
        "Сначала пользователь изучает материал, затем закрепляет его в квизе.",
        reply_markup=nav_keyboard(back_to="menu:quiz"),
    )


@router.callback_query(F.data == "stats:about")
async def stats_about_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "В статистике будут отображаться:\n"
        "- количество пройденных тренировок\n"
        "- количество правильных ответов\n"
        "- активные темы\n"
        "- общий прогресс обучения",
        reply_markup=nav_keyboard(back_to="menu:stats"),
    )


@router.callback_query(F.data == "stats:progress")
async def stats_progress_handler(callback: CallbackQuery) -> None:
    await edit_screen(
        callback,
        "Прогресс будет рассчитываться по истории тренировок и результатам квизов.\n\n"
        "Это позволит показывать пользователю динамику обучения по темам и уровням.",
        reply_markup=nav_keyboard(back_to="menu:stats"),
    )


@router.callback_query(F.data == "help:usage")
async def help_usage_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    await edit_screen(
        callback,
        "Как пользоваться ботом:\n"
        "1. Настроить профиль\n"
        "2. Выбрать тему\n"
        "3. Изучить слова\n"
        "4. Пройти тест\n"
        "5. Посмотреть результат",
        reply_markup=nav_keyboard(back_to="menu:help", include_home=user is not None),
    )


@router.callback_query(F.data == "help:mvp")
async def help_mvp_handler(callback: CallbackQuery) -> None:
    user = await get_registered_user(callback.from_user.id)
    await edit_screen(
        callback,
        "В текущем MVP запланированы такие разделы:\n"
        "- онбординг и профиль\n"
        "- словари и карточки\n"
        "- квизы\n"
        "- статистика\n"
        "- удобная навигация по меню",
        reply_markup=nav_keyboard(back_to="menu:help", include_home=user is not None),
    )
