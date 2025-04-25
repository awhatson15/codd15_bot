import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database.db import init_db
from handlers.commands import register_command_handlers
from handlers.messages import register_message_handlers
from handlers.callbacks import register_callback_handlers
from services.notifications import NotificationService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Начать работу с ботом"),
        BotCommand(command="/help", description="Справка по использованию бота"),
        BotCommand(command="/set_car", description="Изменить номер авто"),
    ]
    await bot.set_my_commands(commands)

async def on_startup(dp):
    # Инициализация базы данных
    await init_db()
    
    # Установка команд бота
    await set_commands(bot)
    
    # Запуск сервиса уведомлений
    notification_service = NotificationService(bot)
    notification_service.start()
    
    logger.info("Бот успешно запущен!")

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    
    # Регистрация обработчиков
    register_command_handlers(dp)
    register_message_handlers(dp)
    register_callback_handlers(dp)
    
    # Запуск бота
    try:
        await on_startup(dp)
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
    