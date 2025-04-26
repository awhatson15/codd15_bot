from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from bot.models.database import update_car_number, get_car_number, delete_car_number
from bot.services.parser import CoddParser
from bot.keyboards.keyboards import get_main_menu
from bot.utils.message_utils import safe_edit_message


class ChangeCarState(StatesGroup):
    waiting_for_new_car_number = State()


async def cmd_check_queue(message: Message):
    """Обработчик команды /check для проверки очереди."""
    # Получаем текущий номер автомобиля
    car_number = await get_car_number(message.from_user.id)
    
    if not car_number:
        await message.answer(
            "❌ У вас не задан номер автомобиля.\n"
            "Используйте команду /start для настройки."
        )
        return
    
    # Получаем данные об автомобиле
    parser = CoddParser()
    car_data = await parser.parse_car_data(car_number)
    
    if car_data:
        await message.answer(
            f"🚗 <b>Информация о вашем автомобиле в очереди</b>\n\n"
            f"Автомобиль номер: <code>{car_data['car_number']}</code>\n"
            f"Модель: {car_data['model']}\n"
            f"Ваш номер в очереди: <b>{car_data['queue_position']}</b>\n"
            f"Дата регистрации: {car_data['registration_date']}",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            f"❓ Информация о вашем автомобиле с номером <code>{car_number}</code> не найдена в очереди.\n"
            f"Возможно, номер указан неверно или сервис временно недоступен.",
            reply_markup=get_main_menu()
        )


async def check_queue_callback(callback: CallbackQuery):
    """Обработчик инлайн-кнопки 'Проверить очередь'."""
    await callback.answer()
    
    # Получаем текущий номер автомобиля
    car_number = await get_car_number(callback.from_user.id)
    
    if not car_number:
        await safe_edit_message(
            callback.message,
            "❌ У вас не задан номер автомобиля.\n"
            "Используйте команду /start для настройки."
        )
        return
    
    # Получаем данные об автомобиле
    parser = CoddParser()
    car_data = await parser.parse_car_data(car_number)
    
    if car_data:
        await safe_edit_message(
            callback.message,
            f"🚗 <b>Информация о вашем автомобиле в очереди</b>\n\n"
            f"Автомобиль номер: <code>{car_data['car_number']}</code>\n"
            f"Модель: {car_data['model']}\n"
            f"Ваш номер в очереди: <b>{car_data['queue_position']}</b>\n"
            f"Дата регистрации: {car_data['registration_date']}",
            reply_markup=get_main_menu()
        )
    else:
        await safe_edit_message(
            callback.message,
            f"❓ Информация о вашем автомобиле с номером <code>{car_number}</code> не найдена в очереди.\n"
            f"Возможно, номер указан неверно или сервис временно недоступен.",
            reply_markup=get_main_menu()
        )


async def change_car_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопки 'Изменить номер авто'."""
    await callback.answer()
    
    await callback.message.edit_text(
        "🚗 Введите новый номер автомобиля с прицепом через дефис.\n"
        "Формат: <code>[гос. номер автомобиля]-[гос. номер прицепа]</code>\n"
        "Пример: <code>P131XM61-AP234015</code>"
    )
    
    await state.set_state(ChangeCarState.waiting_for_new_car_number)


async def process_new_car_number(message: Message, state: FSMContext):
    """Обработчик ввода нового номера автомобиля."""
    car_number = message.text.strip()
    
    # Валидация номера
    if "-" not in car_number or len(car_number) < 5:
        await message.answer(
            "❌ Неверный формат номера. Введите номер в формате:\n"
            "<code>[гос. номер автомобиля]-[гос. номер прицепа]</code>\n"
            "Пример: <code>P131XM61-AP234015</code>"
        )
        return
    
    # Получаем данные об автомобиле через парсер
    parser = CoddParser()
    car_data = await parser.parse_car_data(car_number)
    
    if car_data:
        # Только если данные получены, обновляем номер автомобиля в БД
        await update_car_number(message.from_user.id, car_number)
        
        await message.answer(
            f"✅ Номер автомобиля успешно изменен!\n\n"
            f"Новый номер: <code>{car_data['car_number']}</code>\n"
            f"Модель: {car_data['model']}\n"
            f"Ваш номер в очереди: <b>{car_data['queue_position']}</b>\n"
            f"Дата регистрации: {car_data['registration_date']}",
            reply_markup=get_main_menu()
        )
        
        # Завершаем состояние только если успешно изменили номер
        await state.clear()
    else:
        await message.answer(
            f"⚠️ Автомобиль с номером <code>{car_number}</code> не найден в очереди.\n"
            f"Пожалуйста, проверьте правильность ввода номера или попробуйте позже."
        )
        # Оставляем пользователя в состоянии ожидания ввода номера


async def delete_car_callback(callback: CallbackQuery):
    """Обработчик инлайн-кнопки 'Удалить номер авто'."""
    await callback.answer()
    
    # Получаем текущий номер автомобиля
    car_number = await get_car_number(callback.from_user.id)
    
    if not car_number:
        await safe_edit_message(
            callback.message,
            "❌ У вас не задан номер автомобиля.",
            reply_markup=get_main_menu()
        )
        return
    
    # Удаляем номер автомобиля
    success = await delete_car_number(callback.from_user.id)
    
    if success:
        await safe_edit_message(
            callback.message,
            f"✅ Номер автомобиля <code>{car_number}</code> успешно удален из отслеживания.\n\n"
            f"Для добавления нового автомобиля используйте кнопку 'Изменить номер авто'.",
            reply_markup=get_main_menu()
        )
    else:
        await safe_edit_message(
            callback.message,
            "❌ Произошла ошибка при удалении номера автомобиля.",
            reply_markup=get_main_menu()
        )


def get_car_router() -> Router:
    """Создание роутера для операций с автомобилем."""
    router = Router()
    
    router.message.register(cmd_check_queue, Command("check"))
    router.callback_query.register(check_queue_callback, F.data == "check_queue")
    router.callback_query.register(change_car_callback, F.data == "change_car")
    router.callback_query.register(delete_car_callback, F.data == "delete_car")
    router.message.register(process_new_car_number, ChangeCarState.waiting_for_new_car_number)
    
    return router 