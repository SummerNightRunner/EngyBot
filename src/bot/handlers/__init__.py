from aiogram import Dispatcher

from bot.handlers.course import router as course_router
from bot.handlers.start import router as start_router


def register_routers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(course_router)
    dispatcher.include_router(start_router)
