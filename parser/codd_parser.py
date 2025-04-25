import aiohttp
import aiosqlite
import asyncio
import json
import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup

from config import CODD_URL, CODD_API_URL, DB_PATH

logger = logging.getLogger(__name__)

class CoDDParser:
    """Парсер данных с сайта ЦОДД"""

    def __init__(self):
        self.session = None
    
    async def _get_session(self):
        """Получение HTTP сессии"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _close_session(self):
        """Закрытие HTTP сессии"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _fetch_page(self, url):
        """Получение страницы по URL"""
        session = await self._get_session()
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Ошибка при получении страницы: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при получении страницы: {e}")
            return None
    
    async def get_car_info(self, car_number):
        """Получение информации об автомобиле по номеру"""
        try:
            # Формируем URL для запроса к API
            request_url = f"{CODD_API_URL}?car={car_number}"
            
            # Получаем данные
            session = await self._get_session()
            async with session.get(request_url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Проверяем, что получили корректные данные
                    if not data or 'queue' not in data:
                        logger.warning(f"Некорректные данные для автомобиля {car_number}")
                        return None
                    
                    # Извлекаем необходимую информацию
                    queue_info = data['queue']
                    
                    return {
                        'car_number': car_number,
                        'model': queue_info.get('model', 'Неизвестно'),
                        'queue_position': queue_info.get('queue_num', 0),
                        'reg_date': queue_info.get('reg_date', 'Неизвестно')
                    }
                else:
                    logger.error(f"Ошибка при получении данных для {car_number}: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении информации о машине {car_number}: {e}")
            return None
    
    async def get_all_cars_from_db(self):
        """Получение всех номеров автомобилей из базы данных"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT DISTINCT car_number FROM user_cars"
                )
                results = await cursor.fetchall()
                return [row[0] for row in results]
        
        except Exception as e:
            logger.error(f"Ошибка при получении автомобилей из базы данных: {e}")
            return []
    
    async def save_queue_data(self, car_info):
        """Сохранение данных об очереди в базу данных"""
        if not car_info:
            return
        
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """INSERT INTO queue_history 
                       (car_number, queue_position, model, reg_date) 
                       VALUES (?, ?, ?, ?)""",
                    (
                        car_info['car_number'],
                        car_info['queue_position'],
                        car_info['model'],
                        car_info['reg_date']
                    )
                )
                await db.commit()
                logger.debug(f"Сохранены данные для автомобиля {car_info['car_number']}")
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных для {car_info['car_number']}: {e}")
    
    async def parse_and_update_all(self):
        """Парсинг и обновление данных для всех автомобилей"""
        try:
            # Получаем все номера автомобилей из базы данных
            car_numbers = await self.get_all_cars_from_db()
            
            if not car_numbers:
                logger.info("Нет зарегистрированных автомобилей для обновления")
                return
            
            logger.info(f"Начало обновления данных для {len(car_numbers)} автомобилей")
            
            # Обрабатываем каждый автомобиль
            for car_number in car_numbers:
                try:
                    # Получаем информацию об автомобиле
                    car_info = await self.get_car_info(car_number)
                    
                    if car_info:
                        # Сохраняем данные в базу
                        await self.save_queue_data(car_info)
                    
                    # Небольшая пауза между запросами, чтобы не перегрузить API
                    await asyncio.sleep(1)
                
                except Exception as e:
                    logger.error(f"Ошибка при обработке автомобиля {car_number}: {e}")
            
            logger.info(f"Завершено обновление данных для {len(car_numbers)} автомобилей")
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных: {e}")
        
        finally:
            # Закрываем HTTP сессию
            await self._close_session()
            