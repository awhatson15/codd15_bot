import asyncio
import logging
import sys
from collections import OrderedDict

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler

from bot.config.config import load_config
from bot.handlers import register_all_handlers
from bot.models.database import init_db
from bot.services.notifications import start_notification_service

# Флаг для предотвращения повторной инициализации
_is_initialized = False

# Кеш для хранения последних обработанных message_id
# Используем OrderedDict чтобы автоматически удалять старые записи
_processed_messages = OrderedDict()
_processed_updates = OrderedDict()
_MAX_CACHE_SIZE = 100

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
    
    # Добавляем middleware для дедупликации сообщений
    dp.middleware.setup(DeduplicationMiddleware())
    
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


# Middleware для предотвращения дублирования сообщений
class DeduplicationMiddleware(BaseMiddleware):
    """
    Middleware для предотвращения дублирования сообщений и обновлений.
    Проверяет, было ли сообщение или обновление уже обработано по его ID.
    """
    
    async def on_pre_process_update(self, update, data):
        """Обработка всех типов обновлений"""
        global _processed_updates
        
        update_id = update.update_id
        
        # Если обновление уже обрабатывалось, пропускаем его
        if update_id in _processed_updates:
            logging.debug(f"Дублирующееся обновление пропущено: {update_id}")
            raise CancelHandler()
        
        # Добавляем обновление в кеш обработанных
        _processed_updates[update_id] = True
        
        # Ограничиваем размер кеша
        if len(_processed_updates) > _MAX_CACHE_SIZE:
            # Удаляем самые старые записи
            for _ in range(len(_processed_updates) - _MAX_CACHE_SIZE):
                _processed_updates.popitem(last=False)
    
    async def on_pre_process_message(self, message, data):
        """Дополнительная защита для сообщений"""
        global _processed_messages
        
        # Проверяем, было ли сообщение уже обработано
        message_id = message.message_id
        chat_id = message.chat.id
        
        # Создаем уникальный ключ для сообщения (комбинация chat_id и message_id)
        msg_key = f"{chat_id}:{message_id}"
        
        # Если сообщение уже обрабатывалось, пропускаем его
        if msg_key in _processed_messages:
            logging.debug(f"Дублирующееся сообщение пропущено: {msg_key}")
            raise CancelHandler()
        
        # Добавляем сообщение в кеш обработанных
        _processed_messages[msg_key] = True
        
        # Ограничиваем размер кеша
        if len(_processed_messages) > _MAX_CACHE_SIZE:
            # Удаляем самые старые записи
            for _ in range(len(_processed_messages) - _MAX_CACHE_SIZE):
                _processed_messages.popitem(last=False)


if __name__ == "__main__":
    asyncio.run(main()) 