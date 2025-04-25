import re
import aiohttp
import json
import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from database.db import save_car, get_last_queue_data
from handlers.commands import CarRegistration
from keyboards.inline import get_main_keyboard
from services.utils import format_car_info

logger = logging.getLogger(__name__)

async def handle_car_number(message: types.Message, state: FSMContext):
    """Обработка номера автомобиля"""
    car_number = message.text.strip()
    
    # Проверка формата номера авто (P131XM61-AP234015)
    if not re.match(r'^[A-Z0-9]{7,8}-[A-Z]{2}\d{6}$', car_number):
        await message.answer("Некорректный формат номера. Пожалуйста, используйте формат P131XM61-AP234015:")
        return
    
    # Сохраняем номер авто в базе
    car_id = await save_car(message.from_user.id, car_number)
    
    # Получаем данные об очереди для этого автомобиля
    queue_data = await get_last_queue_data(car_number)
    
    if not queue_data:
        await message.answer(
            "Автомобиль с таким номером не найден в системе или информация еще не обновлена. "
            "Пожалуйста, проверьте номер или подождите немного."
        )
        return
    
    # Формируем сообщение с информацией
    queue_position, model, reg_date, _ = queue_data
    info_message = format_car_info(car_number, model, queue_position, reg_date)
    
    # Отправляем информацию и клавиатуру
    await state.finish()  # Завершаем состояние ввода номера
    
    # Сохраняем номер авто в контексте пользователя
    await state.update_data(car_id=car_id, car_number=car_number)
    
    await message.answer(
        info_message,
        reply_markup=get_main_keyboard(),
        parse_mode=types.ParseMode.HTML
    )

def register_message_handlers(dp: Dispatcher):
    """Регистрация обработчиков сообщений"""
    dp.register_message_handler(
        handle_car_number,
        state=CarRegistration.waiting_for_car_number,
        content_types=types.ContentTypes.TEXT
    )
    