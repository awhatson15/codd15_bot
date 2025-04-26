from aiogram import Router

from bot.handlers.start import get_start_router
from bot.handlers.command import get_command_router
from bot.handlers.car import get_car_router
from bot.handlers.settings import get_settings_router
from bot.handlers.common import get_common_router


def get_all_routers() -> list[Router]:
    """Получение всех роутеров для регистрации в диспетчере."""
    routers = [
        get_start_router(),
        get_command_router(),
        get_car_router(),
        get_settings_router(),
        get_common_router(),
    ]
    
    return routers 