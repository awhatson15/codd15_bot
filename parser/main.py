import asyncio
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import DB_PATH
from codd_parser import CoDDParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция для запуска парсера"""
    # Создаем директории для базы данных, если они не существуют
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Инициализируем парсер
    parser = CoDDParser()
    
    # Настраиваем планировщик для парсинга каждую минуту
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        parser.parse_and_update_all,
        IntervalTrigger(minutes=1),
        id='parse_codd'
    )
    
    try:
        # Выполняем первоначальный парсинг
        logger.info("Запуск первоначального парсинга...")
        await parser.parse_and_update_all()
        
        # Запускаем планировщик
        scheduler.start()
        logger.info("Парсер запущен, обновление каждую минуту")
        
        # Бесконечный цикл для поддержания работы скрипта
        while True:
            await asyncio.sleep(3600)  # Проверка каждый час
    
    except (KeyboardInterrupt, SystemExit):
        # Останавливаем планировщик при завершении работы
        scheduler.shutdown()
        logger.info("Парсер остановлен")
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
    