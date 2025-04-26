from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging
from datetime import datetime

from bot.keyboards.keyboards import get_main_menu
from bot.utils.message_utils import safe_edit_message
from bot.services.analytics import QueueAnalytics
from bot.services.parser import CoddParser
from bot.models.database import get_user_car
from bot.handlers.chat import cmd_chat

# Создаем экземпляр сервиса аналитики
analytics = QueueAnalytics()


async def cmd_help(message: Message):
    """Обработчик команды /help."""
    await message.answer(
        "🔎 <b>Справка по использованию бота</b>\n\n"
        "<b>ЦОДД Электронная очередь</b> - бот для отслеживания очереди автомобилей на странице ЦОДД.\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Запустить бота и ввести/изменить номер автомобиля\n"
        "/check - Проверить текущую позицию в очереди\n"
        "/settings - Настроить уведомления\n"
        "/help - Показать эту справку\n\n"
        "<b>Настройки уведомлений:</b>\n"
        "- Интервальный режим: периодические уведомления через заданный интервал времени\n"
        "- При изменении позиции: уведомление при каждом изменении позиции в очереди\n"
        "- При сдвиге очереди: уведомление, когда очередь сдвинется на указанное число позиций\n\n"
        "Вы можете включить несколько режимов одновременно.",
        reply_markup=get_main_menu()
    )


async def help_callback(callback: CallbackQuery):
    """Обработчик инлайн-кнопки 'Справка'."""
    await callback.answer()
    
    await safe_edit_message(
        callback.message,
        "🔎 <b>Справка по использованию бота</b>\n\n"
        "<b>ЦОДД Электронная очередь</b> - бот для отслеживания очереди автомобилей на странице ЦОДД.\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Запустить бота и ввести/изменить номер автомобиля\n"
        "/check - Проверить текущую позицию в очереди\n"
        "/settings - Настроить уведомления\n"
        "/help - Показать эту справку\n\n"
        "<b>Настройки уведомлений:</b>\n"
        "- Интервальный режим: периодические уведомления через заданный интервал времени\n"
        "- При изменении позиции: уведомление при каждом изменении позиции в очереди\n"
        "- При сдвиге очереди: уведомление, когда очередь сдвинется на указанное число позиций\n\n"
        "Вы можете включить несколько режимов одновременно.",
        reply_markup=get_main_menu()
    )


async def cmd_stats(message: Message):
    """Показывает статистику очереди."""
    try:
        # Получаем текущее время
        now = datetime.now()
        day_of_week = now.weekday()
        hour = now.hour
        
        # Получаем среднюю скорость
        avg_speed = await analytics.get_average_velocity(day_of_week, hour)
        
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        day_name = days[day_of_week]
        
        await message.answer(
            f"📊 <b>Статистика очереди</b>\n\n"
            f"Текущее время: {hour}:00, {day_name}\n"
            f"Средняя скорость движения очереди: <b>{avg_speed:.2f}</b> позиций/час\n\n"
            f"Используйте /forecast для прогноза времени ожидания"
        )
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды stats: {e}")
        await message.answer("Извините, не удалось получить статистику.")


async def cmd_forecast(message: Message):
    """Показывает прогноз времени ожидания."""
    try:
        # Получаем номер автомобиля пользователя и его позицию
        user_id = message.from_user.id
        car_number = await get_user_car(user_id)
        
        if not car_number:
            await message.answer(
                "Для получения прогноза сначала укажите номер вашего автомобиля через /start"
            )
            return
        
        # Получаем данные о позиции автомобиля
        parser = CoddParser()
        car_data = await parser.parse_car_data(car_number)
        
        if not car_data:
            await message.answer(
                f"Не удалось найти автомобиль с номером {car_number} в очереди.\n"
                f"Проверьте номер или попробуйте позже."
            )
            return
        
        position = car_data['queue_position']
        
        # Получаем прогноз
        forecast = await analytics.predict_waiting_time(position)
        
        # Форматируем ожидаемое время
        expected_date = datetime.fromisoformat(forecast['expected_date'].replace('Z', '+00:00'))
        date_str = expected_date.strftime("%d.%m.%Y %H:%M")
        
        await message.answer(
            f"🔮 <b>Прогноз времени ожидания</b>\n\n"
            f"Автомобиль: <code>{car_number}</code>\n"
            f"Текущая позиция: <b>{position}</b>\n\n"
            f"Примерное время ожидания: <b>{forecast['expected_hours']}</b> часов\n"
            f"Оптимистичный прогноз: {forecast['min_hours']} часов\n"
            f"Пессимистичный прогноз: {forecast['max_hours']} часов\n\n"
            f"Ожидаемое время достижения очереди: <b>{date_str}</b>\n"
            f"(при средней скорости {forecast['speed']} позиций/час)"
        )
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды forecast: {e}")
        await message.answer("Извините, не удалось получить прогноз.")


async def open_chat_callback(callback: CallbackQuery):
    """Обработчик инлайн-кнопки 'Анонимный чат'."""
    await callback.answer()
    
    # Просто отправляем сообщение с инструкцией
    await callback.message.edit_text(
        "💬 <b>Анонимный чат водителей</b>\n\n"
        "Чтобы войти в чат, отправьте команду /chat\n\n"
        "В чате вы сможете общаться с другими водителями анонимно. "
        "Другие участники будут видеть только ваш псевдоним и позицию в очереди.",
        reply_markup=get_main_menu()
    )


def get_command_router() -> Router:
    """Создание роутера для команд."""
    router = Router()
    
    router.message.register(cmd_help, Command("help"))
    router.callback_query.register(help_callback, F.data == "help")
    router.message.register(cmd_stats, Command("stats"))
    router.message.register(cmd_forecast, Command("forecast"))
    router.callback_query.register(open_chat_callback, F.data == "open_chat")
    
    return router 