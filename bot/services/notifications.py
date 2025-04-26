import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config.config import load_config
from bot.models.database import (
    get_car_data, get_users_for_notification, 
    update_last_notification, get_notification_settings,
    update_queue_data
)
from bot.services.parser import CoddParser


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.config = load_config()
        self.logger = logging.getLogger("notifications")
        self.scheduler = AsyncIOScheduler()
    
    async def start(self):
        """Запуск сервиса уведомлений."""
        self.logger.info("Запуск сервиса уведомлений")
        
        # Планируем выполнение проверки уведомлений каждые 30 секунд
        self.scheduler.add_job(
            self.check_notifications,
            'interval',
            seconds=30,
            id='check_notifications'
        )
        
        self.scheduler.start()
    
    async def check_notifications(self):
        """Проверка и отправка уведомлений пользователям."""
        try:
            # Получаем список пользователей для уведомлений
            users = await get_users_for_notification()
            self.logger.info(f"Проверка уведомлений для {len(users)} пользователей")
            
            for user_id, car_number, settings in users:
                try:
                    await self.process_user_notification(user_id, car_number, settings)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке уведомления для пользователя {user_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Ошибка при проверке уведомлений: {e}")
    
    async def process_user_notification(self, user_id: int, car_number: str, settings: Dict):
        """Обработка уведомлений для конкретного пользователя."""
        # Получаем данные об автомобиле
        car_data = await get_car_data(car_number)
        
        # Если нет данных в базе, попробуем получить напрямую с сайта
        if not car_data:
            self.logger.warning(f"Нет данных об автомобиле {car_number} для пользователя {user_id}. Пробуем парсинг напрямую.")
            parser = CoddParser()
            parsed_car_data = await parser.parse_car_data(car_number)
            
            if parsed_car_data:
                self.logger.info(f"Получены данные с сайта для автомобиля {car_number}")
                # Сохраняем данные в базу для будущих запросов
                await update_queue_data({car_number: {
                    'model': parsed_car_data['model'],
                    'queue_position': parsed_car_data['queue_position'],
                    'registration_date': parsed_car_data['registration_date']
                }})
                car_data = parsed_car_data
            else:
                self.logger.warning(f"Автомобиль {car_number} не найден ни в базе, ни на сайте для пользователя {user_id}")
                return
        
        # Получаем время последнего уведомления
        last_notification = settings.get('last_notification')
        if last_notification:
            try:
                last_notification = datetime.fromisoformat(last_notification.replace(' ', 'T'))
            except:
                last_notification = datetime.now() - timedelta(days=1)
        else:
            last_notification = datetime.now() - timedelta(days=1)
        
        # Проверяем условия для отправки уведомления
        send_notification = False
        notification_text = ""
        
        # 1. Интервальный режим
        if settings.get('interval_mode'):
            interval_minutes = settings.get('interval_minutes', self.config.default_notification_interval)
            next_notification_time = last_notification + timedelta(minutes=interval_minutes)
            
            if datetime.now() > next_notification_time:
                send_notification = True
                notification_text = (
                    f"🚗 *Плановое уведомление о статусе очереди*\n\n"
                    f"Автомобиль номер: `{car_data['car_number']}`\n"
                    f"Модель: {car_data['model']}\n"
                    f"Ваш номер в очереди: *{car_data['queue_position']}*\n"
                    f"Дата регистрации: {car_data['registration_date']}"
                )
        
        # 2. При изменении позиции
        if settings.get('position_change'):
            # Получаем последнюю известную позицию
            last_position = await self._get_last_known_position(user_id, car_number)
            
            if last_position and last_position != car_data['queue_position']:
                send_notification = True
                position_change = last_position - car_data['queue_position']
                change_text = (
                    f"⬆️ повысилась на {abs(position_change)}" if position_change > 0 
                    else f"⬇️ понизилась на {abs(position_change)}"
                )
                
                notification_text = (
                    f"🔄 *Изменение позиции в очереди!*\n\n"
                    f"Автомобиль номер: `{car_data['car_number']}`\n"
                    f"Ваша позиция {change_text}\n"
                    f"Текущий номер в очереди: *{car_data['queue_position']}*\n"
                    f"Предыдущий номер: {last_position}"
                )
        
        # 3. При сдвиге очереди на N позиций
        if settings.get('threshold_change'):
            # Получаем последнюю известную позицию первого авто в очереди
            last_first_position = await self._get_first_position()
            current_first_position = await self._get_current_first_position()
            
            if last_first_position and current_first_position:
                threshold = settings.get('threshold_value', 10)
                position_change = last_first_position - current_first_position
                
                if position_change >= threshold:
                    send_notification = True
                    notification_text = (
                        f"📊 *Очередь сдвинулась на {position_change} позиций!*\n\n"
                        f"Автомобиль номер: `{car_data['car_number']}`\n"
                        f"Ваш номер в очереди: *{car_data['queue_position']}*\n"
                        f"Дата регистрации: {car_data['registration_date']}"
                    )
        
        # Отправляем уведомление, если есть причина
        if send_notification:
            try:
                await self.bot.send_message(
                    user_id,
                    notification_text,
                    parse_mode="Markdown"
                )
                await update_last_notification(user_id)
                self.logger.info(f"Отправлено уведомление пользователю {user_id}")
            except Exception as e:
                self.logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
    
    async def _get_last_known_position(self, user_id: int, car_number: str) -> Optional[int]:
        """Получить последнюю известную позицию автомобиля."""
        # В реальной системе эту информацию нужно хранить в БД
        # В текущей реализации просто возвращаем None, что приведет
        # к отсутствию уведомлений при первом запуске
        return None
    
    async def _get_first_position(self) -> Optional[int]:
        """Получить последнюю известную позицию первого автомобиля в очереди."""
        # В реальной системе эту информацию нужно хранить в БД
        # Здесь просто заглушка
        return None
    
    async def _get_current_first_position(self) -> Optional[int]:
        """Получить текущую позицию первого автомобиля в очереди."""
        # В реальной системе это позиция автомобиля с наименьшим номером в очереди
        # Здесь просто заглушка
        return None


async def start_notification_service(bot: Bot):
    """Запуск сервиса уведомлений."""
    notification_service = NotificationService(bot)
    await notification_service.start() 