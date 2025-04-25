from aiogram import Dispatcher

from bot.handlers.start import register_start_handlers
from bot.handlers.command import register_command_handlers
from bot.handlers.car import register_car_handlers
from bot.handlers.settings import register_settings_handlers
from bot.handlers.common import register_common_handlers


def register_all_handlers(dp: Dispatcher) -> None:
    """Регистрация всех обработчиков сообщений."""
    handlers = [
        register_start_handlers,
        register_command_handlers,
        register_car_handlers,
        register_settings_handlers,
        register_common_handlers,
    ]
    
    for handler in handlers:
        handler(dp) 