import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config.config import load_config
from bot.handlers import register_all_handlers
from bot.models.database import init_db
from bot.services.notifications import start_notification_service

# Флаг для предотвращения повторной инициализации
_is_initialized = False

async def main():
    global _is_initialized
    
    # Если бот уже инициализирован, выходим
    if _is_initialized:
        return
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Создание логгера для парсера с детальным логированием
    parser_logger = logging.getLogger("parser")
    parser_logger.setLevel(logging.DEBUG)
    
    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация базы данных
    await init_db()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.bot_token)
    dp = Dispatcher(bot, storage=MemoryStorage())
    
    # Регистрация команд
    await bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Справка"),
        BotCommand("check", "Проверить очередь"),
        BotCommand("settings", "Настройки уведомлений"),
    ])
    
    # Регистрация всех обработчиков
    register_all_handlers(dp)
    
    # Запуск сервиса уведомлений
    await start_notification_service(bot)
    
    # Установка флага инициализации
    _is_initialized = True
    
    # Запуск бота
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main()) 