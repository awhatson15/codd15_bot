from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging

from bot.models.database import update_car_number, get_car_number, delete_car_number
from bot.services.parser import CoddParser
from bot.keyboards.keyboards import get_main_menu
from bot.utils.message_utils import safe_edit_message


class ChangeCarState(StatesGroup):
    waiting_for_new_car_number = State()


async def cmd_check_queue(message: types.Message):
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
            f"🚗 *Информация о вашем автомобиле в очереди*\n\n"
            f"Автомобиль номер: `{car_data['car_number']}`\n"
            f"Модель: {car_data['model']}\n"
            f"Ваш номер в очереди: *{car_data['queue_position']}*\n"
            f"Дата регистрации: {car_data['registration_date']}",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            f"❓ Информация о вашем автомобиле с номером `{car_number}` не найдена в очереди.\n"
            f"Возможно, номер указан неверно или сервис временно недоступен.",
            reply_markup=get_main_menu()
        )


async def check_queue_callback(callback_query: types.CallbackQuery):
    """Обработчик инлайн-кнопки 'Проверить очередь'."""
    await callback_query.answer()
    
    # Получаем текущий номер автомобиля
    car_number = await get_car_number(callback_query.from_user.id)
    
    if not car_number:
        await safe_edit_message(
            callback_query.message,
            "❌ У вас не задан номер автомобиля.\n"
            "Используйте команду /start для настройки."
        )
        return
    
    # Получаем данные об автомобиле
    parser = CoddParser()
    car_data = await parser.parse_car_data(car_number)
    
    if car_data:
        await safe_edit_message(
            callback_query.message,
            f"🚗 *Информация о вашем автомобиле в очереди*\n\n"
            f"Автомобиль номер: `{car_data['car_number']}`\n"
            f"Модель: {car_data['model']}\n"
            f"Ваш номер в очереди: *{car_data['queue_position']}*\n"
            f"Дата регистрации: {car_data['registration_date']}",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await safe_edit_message(
            callback_query.message,
            f"❓ Информация о вашем автомобиле с номером `{car_number}` не найдена в очереди.\n"
            f"Возможно, номер указан неверно или сервис временно недоступен.",
            reply_markup=get_main_menu()
        )


async def change_car_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопки 'Изменить номер авто'."""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "🚗 Введите новый номер автомобиля с прицепом через дефис.\n"
        "Формат: `[гос. номер автомобиля]-[гос. номер прицепа]`\n"
        "Пример: `P131XM61-AP234015`",
        parse_mode="Markdown"
    )
    
    await ChangeCarState.waiting_for_new_car_number.set()


async def process_new_car_number(message: types.Message, state: FSMContext):
    """Обработчик ввода нового номера автомобиля."""
    car_number = message.text.strip()
    
    # Валидация номера
    if "-" not in car_number or len(car_number) < 5:
        await message.answer(
            "❌ Неверный формат номера. Введите номер в формате:\n"
            "`[гос. номер автомобиля]-[гос. номер прицепа]`\n"
            "Пример: `P131XM61-AP234015`",
            parse_mode="Markdown"
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
            f"Новый номер: `{car_data['car_number']}`\n"
            f"Модель: {car_data['model']}\n"
            f"Ваш номер в очереди: *{car_data['queue_position']}*\n"
            f"Дата регистрации: {car_data['registration_date']}",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            f"⚠️ Автомобиль с номером `{car_number}` не найден в очереди.\n"
            f"Пожалуйста, проверьте правильность ввода номера или попробуйте позже.",
            parse_mode="Markdown"
        )
        # Оставляем пользователя в состоянии ожидания ввода номера
        return
    
    # Завершаем состояние только если успешно изменили номер
    await state.finish()


async def delete_car_callback(callback_query: types.CallbackQuery):
    """Обработчик инлайн-кнопки 'Удалить номер авто'."""
    await callback_query.answer()
    
    # Получаем текущий номер автомобиля
    car_number = await get_car_number(callback_query.from_user.id)
    
    if not car_number:
        await safe_edit_message(
            callback_query.message,
            "❌ У вас не задан номер автомобиля.",
            reply_markup=get_main_menu()
        )
        return
    
    # Удаляем номер автомобиля
    success = await delete_car_number(callback_query.from_user.id)
    
    if success:
        await safe_edit_message(
            callback_query.message,
            f"✅ Номер автомобиля `{car_number}` успешно удален из отслеживания.\n\n"
            f"Для добавления нового автомобиля используйте кнопку 'Изменить номер авто'.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await safe_edit_message(
            callback_query.message,
            "❌ Произошла ошибка при удалении номера автомобиля.",
            reply_markup=get_main_menu()
        )


def register_car_handlers(dp: Dispatcher):
    """Регистрация обработчиков для операций с автомобилем."""
    dp.register_message_handler(cmd_check_queue, commands=["check"])
    dp.register_callback_query_handler(check_queue_callback, lambda c: c.data == "check_queue")
    dp.register_callback_query_handler(change_car_callback, lambda c: c.data == "change_car")
    dp.register_callback_query_handler(delete_car_callback, lambda c: c.data == "delete_car")
    dp.register_message_handler(process_new_car_number, state=ChangeCarState.waiting_for_new_car_number) 