import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot

from database.db import (
    get_cars_for_notification, get_last_queue_data,
    get_previous_queue_data, update_last_notification
)
from services.utils import format_car_info

logger = logging.getLogger(__name__)

class NotificationService:
    """Сервис для отправки уведомлений пользователям"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        """Запуск планировщика уведомлений"""
        # Проверяем уведомления каждую минуту
        self.scheduler.add_job(
            self.check_notifications,
            IntervalTrigger(minutes=1),
            id='check_notifications'
        )
        self.scheduler.start()
        logger.info("Планировщик уведомлений запущен")
        
    async def check_notifications(self):
        """Проверка необходимости отправки уведомлений"""
        try:
            # Получаем все машины с активными уведомлениями
            cars = await get_cars_for_notification()
            
            for user_id, car_id, car_number, interval_mode, position_change, shift_threshold, last_notification in cars:
                # Получаем текущие данные об очереди
                current_data = await get_last_queue_data(car_number)
                
                if not current_data:
                    continue  # Пропускаем, если нет данных
                    
                current_position, model, reg_date, timestamp = current_data
                
                # Время последнего уведомления, если его нет - используем datetime.min
                last_notif_time = last_notification if last_notification else datetime.min
                
                # Флаг, показывающий, нужно ли отправлять уведомление
                should_notify = False
                notification_reason = ""
                
                # Проверяем интервальный режим
                if interval_mode > 0:
                    # Если прошло больше минут, чем указано в интервале - отправляем уведомление
                    if datetime.now() - last_notif_time > timedelta(minutes=interval_mode):
                        should_notify = True
                        notification_reason = f"Плановое уведомление (каждые {interval_mode} мин.)"
                
                # Проверяем изменение позиции
                if position_change and not should_notify:
                    # Получаем предыдущие данные об очереди
                    prev_data = await get_previous_queue_data(car_number)
                    
                    if prev_data and prev_data[0] != current_position:
                        should_notify = True
                        change = prev_data[0] - current_position
                        direction = "🔽 уменьшилась" if change > 0 else "🔼 увеличилась"
                        notification_reason = f"Позиция в очереди {direction} на {abs(change)}"
                
                # Проверяем порог сдвига очереди
                if shift_threshold > 0 and not should_notify:
                    # Получаем предыдущие данные об очереди
                    prev_data = await get_previous_queue_data(car_number)
                    
                    if prev_data:
                        change = prev_data[0] - current_position
                        if abs(change) >= shift_threshold:
                            should_notify = True
                            direction = "🔽 уменьшилась" if change > 0 else "🔼 увеличилась"
                            notification_reason = f"Очередь {direction} на {abs(change)} позиций"
                
                # Отправляем уведомление, если нужно
                if should_notify:
                    # Формируем сообщение с информацией
                    info_message = f"<b>{notification_reason}</b>\n\n"
                    info_message += format_car_info(car_number, model, current_position, reg_date)
                    
                    # Отправляем уведомление
                    try:
                        await self.bot.send_message(
                            user_id,
                            info_message,
                            parse_mode="HTML"
                        )
                        
                        # Обновляем время последнего уведомления
                        await update_last_notification(user_id, car_id)
                        
                        logger.info(f"Отправлено уведомление пользователю {user_id} для авто {car_number}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
        
        except Exception as e:
            logger.error(f"Ошибка в сервисе уведомлений: {e}")
            