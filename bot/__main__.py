import asyncio
import logging
import sys
from collections import OrderedDict

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.utils.token import TokenValidationError

from bot.config.config import load_config
from bot.handlers import get_all_routers
from bot.middlewares.deduplication import DeduplicationMiddleware
from bot.models.database import init_db
from bot.services.notifications import start_notification_service
from bot.utils.health_check import start_health_server

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)

# Создание логгера для парсера с детальным логированием
parser_logger = logging.getLogger("parser")
parser_logger.setLevel(logging.DEBUG)

# Кеш для хранения последних обработанных message_id
# Используем OrderedDict чтобы автоматически удалять старые записи
_processed_messages = OrderedDict()
_processed_updates = OrderedDict()
_MAX_CACHE_SIZE = 100


async def main():
    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация базы данных
    await init_db()
    
    # Запуск health check сервера
    await start_health_server()
    
    # Выбор хранилища состояний
    if config.use_redis:
        storage = RedisStorage.from_url(config.redis_url)
        logging.info(f"Используется Redis для хранения состояний: {config.redis_url}")
    else:
        storage = MemoryStorage()
        logging.info("Используется MemoryStorage для хранения состояний")
    
    # Инициализация бота и диспетчера
    try:
        bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)
        dp = Dispatcher(storage=storage)
        
        # Регистрация middleware
        dp.update.middleware(DeduplicationMiddleware())
        
        # Регистрация всех роутеров
        for router in get_all_routers():
            dp.include_router(router)
        
        # Регистрация команд
        await bot.set_my_commands([
            {"command": "start", "description": "Запустить бота"},
            {"command": "help", "description": "Справка"},
            {"command": "check", "description": "Проверить очередь"},
            {"command": "settings", "description": "Настройки уведомлений"},
        ])
        
        # Запуск сервиса уведомлений
        asyncio.create_task(start_notification_service(bot))
        
        # Запуск бота
        logging.info("Бот запущен")
        await dp.start_polling(bot)
        
    except TokenValidationError:
        logging.critical("Неверный токен бота. Пожалуйста, проверьте настройки.")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)
    finally:
        if 'bot' in locals():
            await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен") 