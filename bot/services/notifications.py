import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config.config import load_config
from bot.models.database import (
    get_users_for_notification, 
    update_last_notification, get_notification_settings
)
from bot.services.parser import CoddParser


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.config = load_config()
        self.logger = logging.getLogger("notifications")
        self.scheduler = AsyncIOScheduler()
        self.parser = CoddParser()
        
        # Хранение данных в памяти вместо БД
        self.car_positions = {}  # Словарь для отслеживания позиций автомобилей
        self.first_car_position = None  # Позиция первого автомобиля в очереди
    
    async def start(self):
        """Запуск сервиса уведомлений."""
        self.logger.info("Запуск сервиса уведомлений")
        
        # Используем интервал из конфигурации
        check_interval = self.config.notification_check_interval
        self.logger.info(f"Интервал проверки уведомлений: {check_interval} секунд")
        
        # Планируем выполнение проверки уведомлений с настраиваемым интервалом
        self.scheduler.add_job(
            self.check_notifications,
            'interval',
            seconds=check_interval,
            id='check_notifications'
        )
        
        self.scheduler.start()
    
    async def close(self):
        """Останавливает планировщик и освобождает ресурсы."""
        self.logger.info("Остановка сервиса уведомлений")
        self.scheduler.shutdown(wait=False)
        self.logger.info("Сервис уведомлений остановлен")
        
        if hasattr(self.parser, 'close'):
            await self.parser.close()
    
    async def check_notifications(self):
        """Проверка и отправка уведомлений пользователям."""
        try:
            # Получаем список пользователей для уведомлений
            users = await get_users_for_notification()
            self.logger.info(f"Проверка уведомлений для {len(users)} пользователей")
            
            # Обновляем позицию первого автомобиля в очереди
            await self._update_first_car_position()
            
            for user_id, car_number, settings in users:
                try:
                    await self.process_user_notification(user_id, car_number, settings)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке уведомления для пользователя {user_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Ошибка при проверке уведомлений: {e}")
    
    async def process_user_notification(self, user_id: int, car_number: str, settings: Dict):
        """Обработка уведомлений для конкретного пользователя."""
        # Получаем данные об автомобиле напрямую через парсер
        car_data = await self.parser.parse_car_data(car_number)
        if not car_data:
            self.logger.warning(f"Нет данных об автомобиле {car_number} для пользователя {user_id}")
            return
        
        # Сохраняем текущую позицию для отслеживания изменений
        current_position = car_data['queue_position']
        if car_number not in self.car_positions:
            self.car_positions[car_number] = current_position
            # Пропускаем первое уведомление, чтобы избежать ложных срабатываний
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
            last_position = self.car_positions.get(car_number)
            
            if last_position and last_position != current_position:
                send_notification = True
                position_change = last_position - current_position
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
                
                # Обновляем сохраненную позицию
                self.car_positions[car_number] = current_position
        
        # 3. При сдвиге очереди на N позиций
        if settings.get('threshold_change') and self.first_car_position is not None:
            last_first_position = self._get_last_first_position()
            current_first_position = self.first_car_position
            
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
    
    async def _update_first_car_position(self):
        """Обновляет позицию первого автомобиля в очереди."""
        try:
            # Получаем данные о первой машине в очереди
            # Это пример, на практике нужно реализовать логику получения первой машины
            # через парсер или другие методы
            first_car_data = await self.parser.get_first_car_position()
            
            if first_car_data is not None:
                # Сохраняем предыдущую позицию
                old_position = self.first_car_position
                
                # Обновляем текущую позицию
                self.first_car_position = first_car_data
                
                self.logger.info(f"Позиция первого автомобиля обновлена: {self.first_car_position}")
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении позиции первого автомобиля: {e}")
    
    def _get_last_first_position(self) -> Optional[int]:
        """Возвращает сохраненную позицию первого автомобиля."""
        return getattr(self, '_last_first_position', self.first_car_position)


async def start_notification_service(bot: Bot):
    """Запуск сервиса уведомлений."""
    notification_service = NotificationService(bot)
    await notification_service.start()
    return notification_service 