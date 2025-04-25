import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from database.db import (
    get_car_info, get_last_queue_data, update_notification_settings,
    get_notification_settings, disable_all_notifications
)
from handlers.commands import CarRegistration
from keyboards.inline import (
    get_main_keyboard, get_notification_settings_keyboard,
    get_interval_keyboard, get_shift_keyboard, get_back_keyboard
)
from services.utils import format_car_info
from texts import HELP_TEXT

logger = logging.getLogger(__name__)

class NotificationSettings(StatesGroup):
    waiting_for_interval = State()
    waiting_for_shift = State()

async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка всех коллбэков"""
    await callback_query.answer()
    
    # Получаем данные из контекста
    user_data = await state.get_data()
    car_id = user_data.get('car_id')
    car_number = user_data.get('car_number')
    
    if not car_id or not car_number:
        # Если нет данных об автомобиле, получаем их из базы
        car_info = await get_car_info(callback_query.from_user.id)
        if not car_info:
            await callback_query.message.answer("Пожалуйста, сначала зарегистрируйте автомобиль через /start")
            return
            
        car_id, car_number = car_info
        await state.update_data(car_id=car_id, car_number=car_number)
    
    callback_data = callback_query.data
    
    if callback_data == "check_queue":
        # Проверка очереди
        queue_data = await get_last_queue_data(car_number)
        
        if not queue_data:
            await callback_query.message.edit_text(
                "Информация об автомобиле не найдена или еще не обновлена.",
                reply_markup=get_main_keyboard()
            )
            return
            
        queue_position, model, reg_date, _ = queue_data
        info_message = format_car_info(car_number, model, queue_position, reg_date)
        
        await callback_query.message.edit_text(
            info_message,
            reply_markup=get_main_keyboard(),
            parse_mode=types.ParseMode.HTML
        )
            
    elif callback_data == "notification_settings":
        # Настройка уведомлений
        settings = await get_notification_settings(callback_query.from_user.id, car_id)
        
        if not settings:
            await callback_query.message.answer("Ошибка при получении настроек уведомлений. Пожалуйста, попробуйте снова.")
            return
            
        interval_mode, position_change, shift_threshold, _ = settings
        
        message_text = "Настройки уведомлений:\n\n"
        message_text += f"✓ Интервальные уведомления: {'каждые ' + str(interval_mode) + ' мин.' if interval_mode else 'Отключены'}\n"
        message_text += f"✓ Уведомления при изменении позиции: {'Включены' if position_change else 'Отключены'}\n"
        message_text += f"✓ Уведомления при сдвиге очереди: {'На ' + str(shift_threshold) + ' позиций' if shift_threshold else 'Отключены'}\n"
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=get_notification_settings_keyboard(),
            parse_mode=types.ParseMode.HTML
        )
            
    elif callback_data == "set_interval":
        # Установка интервала уведомлений
        await callback_query.message.edit_text(
            "Выберите интервал уведомлений или введите своё значение в минутах:",
            reply_markup=get_interval_keyboard()
        )
        await NotificationSettings.waiting_for_interval.set()
            
    elif callback_data == "toggle_position_change":
        # Переключение уведомлений при изменении позиции
        settings = await get_notification_settings(callback_query.from_user.id, car_id)
        
        if not settings:
            await callback_query.message.answer("Ошибка при получении настроек уведомлений. Пожалуйста, попробуйте снова.")
            return
            
        _, position_change, _, _ = settings
        
        # Инвертируем значение
        new_position_change = 0 if position_change else 1
        
        # Обновляем настройки
        await update_notification_settings(
            callback_query.from_user.id, car_id, "position", new_position_change
        )
        
        # Перезагружаем меню настроек
        await process_callback(callback_query, state)
            
    elif callback_data == "set_shift":
        # Установка порога сдвига очереди
        await callback_query.message.edit_text(
            "Выберите порог сдвига очереди (сколько позиций должно измениться для уведомления):",
            reply_markup=get_shift_keyboard()
        )
        await NotificationSettings.waiting_for_shift.set()
            
    elif callback_data.startswith("interval_"):
        # Обработка выбора предустановленного интервала
        interval = int(callback_data.split("_")[1])
        await update_notification_settings(
            callback_query.from_user.id, car_id, "interval", interval
        )
        await state.finish()
        await callback_query.message.edit_text("Настройки уведомлений обновлены!")
        
        # Возвращаемся к меню настроек
        await process_callback(types.CallbackQuery(
            id=callback_query.id,
            from_user=callback_query.from_user,
            chat_instance=callback_query.chat_instance,
            message=callback_query.message,
            data="notification_settings"
        ), state)
            
    elif callback_data.startswith("shift_"):
        # Обработка выбора предустановленного порога сдвига
        shift = int(callback_data.split("_")[1])
        await update_notification_settings(
            callback_query.from_user.id, car_id, "shift", shift
        )
        await state.finish()
        await callback_query.message.edit_text("Настройки уведомлений обновлены!")
        
        # Возвращаемся к меню настроек
        await process_callback(types.CallbackQuery(
            id=callback_query.id,
            from_user=callback_query.from_user,
            chat_instance=callback_query.chat_instance,
            message=callback_query.message,
            data="notification_settings"
        ), state)
            
    elif callback_data == "disable_notifications":
        # Отключение всех уведомлений
        await disable_all_notifications(callback_query.from_user.id, car_id)
        await callback_query.message.edit_text(
            "Все уведомления отключены.",
            reply_markup=get_main_keyboard()
        )
            
    elif callback_data == "change_car":
        # Изменение номера авто
        await state.finish()
        await CarRegistration.waiting_for_car_number.set()
        await callback_query.message.edit_text("Пожалуйста, введите новый номер автомобиля в формате P131XM61-AP234015:")
            
    elif callback_data == "help":
        # Показать справку
        await callback_query.message.edit_text(
            HELP_TEXT,
            reply_markup=get_back_keyboard(),
            parse_mode=types.ParseMode.HTML
        )
            
    elif callback_data == "back_to_menu":
        # Возврат в главное меню
        queue_data = await get_last_queue_data(car_number)
        
        if not queue_data:
            await callback_query.message.edit_text(
                "Информация об автомобиле не найдена.",
                reply_markup=get_main_keyboard()
            )
            return
            
        queue_position, model, reg_date, _ = queue_data
        info_message = format_car_info(car_number, model, queue_position, reg_date)
        
        await callback_query.message.edit_text(
            info_message,
            reply_markup=get_main_keyboard(),
            parse_mode=types.ParseMode.HTML
        )

async def process_interval_input(message: types.Message, state: FSMContext):
    """Обработка пользовательского ввода интервала"""
    try:
        interval = int(message.text.strip())
        
        if interval <= 0:
            await message.answer("Интервал должен быть положительным числом. Пожалуйста, введите корректное значение:")
            return
            
        if interval > 1440:  # Максимум 24 часа (1440 минут)
            await message.answer("Интервал слишком большой (максимум 1440 минут). Пожалуйста, введите меньшее значение:")
            return
            
        user_data = await state.get_data()
        car_id = user_data.get('car_id')
        # Обновляем настройки интервала уведомлений
        await update_notification_settings(
            message.from_user.id, car_id, "interval", interval
        )
        
        # Завершаем состояние ввода
        await state.finish()
        
        # Возвращаемся к меню настроек
        await message.answer(
            "Интервал уведомлений успешно установлен на " + str(interval) + " минут.",
            reply_markup=get_notification_settings_keyboard()
        )
        
    except ValueError:
        await message.answer("Пожалуйста, введите число в минутах:")

async def process_shift_input(message: types.Message, state: FSMContext):
    """Обработка пользовательского ввода порога сдвига очереди"""
    try:
        shift = int(message.text.strip())
        
        if shift <= 0:
            await message.answer("Порог сдвига должен быть положительным числом. Пожалуйста, введите корректное значение:")
            return
            
        user_data = await state.get_data()
        car_id = user_data.get('car_id')
        
        # Обновляем настройки порога сдвига
        await update_notification_settings(
            message.from_user.id, car_id, "shift", shift
        )
        
        # Завершаем состояние ввода
        await state.finish()
        
        # Возвращаемся к меню настроек
        await message.answer(
            "Порог сдвига очереди успешно установлен на " + str(shift) + " позиций.",
            reply_markup=get_notification_settings_keyboard()
        )
        
    except ValueError:
        await message.answer("Пожалуйста, введите число позиций:")

def register_callback_handlers(dp: Dispatcher):
    """Регистрация обработчиков коллбэков"""
    # Обработчик всех коллбэков с главной клавиатуры
    dp.register_callback_query_handler(
        process_callback,
        lambda c: True,
        state="*"
    )
    
    # Обработчик пользовательского ввода интервала
    dp.register_message_handler(
        process_interval_input,
        state=NotificationSettings.waiting_for_interval,
        content_types=types.ContentTypes.TEXT
    )
    
    # Обработчик пользовательского ввода порога сдвига
    dp.register_message_handler(
        process_shift_input,
        state=NotificationSettings.waiting_for_shift,
        content_types=types.ContentTypes.TEXT
    )
    