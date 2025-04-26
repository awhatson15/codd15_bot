from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from bot.models.database import (
    get_notification_settings, 
    setup_notifications,
    get_car_number
)
from bot.keyboards.keyboards import (
    get_main_menu, 
    get_notification_settings_keyboard, 
    get_notification_interval_keyboard,
    get_notification_threshold_keyboard,
    get_queue_threshold_keyboard
)
from bot.config.config import load_config
from bot.utils.message_utils import safe_edit_message
from bot.services.parser import CoddParser


class NotificationState(StatesGroup):
    waiting_for_interval = State()
    waiting_for_threshold = State()
    waiting_for_queue_threshold = State()


async def cmd_settings(message: Message):
    """Обработчик команды /settings для настройки уведомлений."""
    await message.answer("Загрузка настроек уведомлений...")
    
    # Получаем текущие настройки из БД
    settings = await get_notification_settings(message.from_user.id)
    
    # Если настроек нет, создаем пустой словарь
    if not settings:
        settings = {
            'interval_mode': False,
            'interval_minutes': 2,
            'position_change': False,
            'threshold_change': False,
            'threshold_value': 10,
            'queue_threshold': False,
            'queue_threshold_value': 10,
            'enabled': True
        }
    
    await message.answer(
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- При достижении номера: {'✅' if settings.get('queue_threshold', False) else '❌'}\n"
        f"- Номер в очереди: {settings.get('queue_threshold_value', 10)}\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def settings_callback(callback: CallbackQuery):
    """Обработчик инлайн-кнопки 'Настроить уведомления'."""
    await callback.answer()
    
    # Получаем текущие настройки из БД
    settings = await get_notification_settings(callback.from_user.id)
    
    # Если настроек нет, создаем пустой словарь
    if not settings:
        settings = {
            'interval_mode': False,
            'interval_minutes': 2,
            'position_change': False,
            'threshold_change': False,
            'threshold_value': 10,
            'queue_threshold': False,
            'queue_threshold_value': 10,
            'enabled': True
        }
    
    await callback.message.edit_text(
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- При достижении номера: {'✅' if settings.get('queue_threshold', False) else '❌'}\n"
        f"- Номер в очереди: {settings.get('queue_threshold_value', 10)}\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_notifications_callback(callback: CallbackQuery):
    """Обработчик включения/отключения уведомлений."""
    await callback.answer()
    
    settings = await get_notification_settings(callback.from_user.id)
    
    if not settings:
        # Если настройки не найдены, создаем их со значениями по умолчанию
        config = load_config()
        settings = {
            'interval_mode': False,
            'interval_minutes': config.default_notification_interval,
            'position_change': False,
            'threshold_change': False,
            'threshold_value': 10,
            'enabled': True
        }
    else:
        # Инвертируем текущее значение
        settings['enabled'] = not settings['enabled']
    
    # Обновляем настройки в БД
    await setup_notifications(callback.from_user.id, settings)
    
    # Обновляем сообщение с новыми настройками
    await safe_edit_message(
        callback.message,
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_interval_mode_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик включения/отключения интервального режима."""
    await callback.answer()
    
    settings = await get_notification_settings(callback.from_user.id)
    
    if not settings:
        config = load_config()
        settings = {
            'interval_mode': True,  # Включаем режим
            'interval_minutes': config.default_notification_interval,
            'position_change': False,
            'threshold_change': False,
            'threshold_value': 10,
            'enabled': True
        }
    else:
        # Инвертируем текущее значение
        settings['interval_mode'] = not settings['interval_mode']
    
    # Если включили режим, предлагаем выбрать интервал
    if settings['interval_mode']:
        await safe_edit_message(
            callback.message,
            f"⏱️ <b>Выберите интервал уведомлений</b>\n\n"
            f"Текущий интервал: {settings['interval_minutes']} мин.\n"
            f"Выберите новое значение или введите своё (в минутах):",
            reply_markup=get_notification_interval_keyboard()
        )
        await state.set_state(NotificationState.waiting_for_interval)
    else:
        # Если выключили режим, просто обновляем настройки
        await setup_notifications(callback.from_user.id, settings)
        
        await safe_edit_message(
            callback.message,
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_notification_settings_keyboard(settings)
        )


async def process_interval_input(message: Message, state: FSMContext):
    """Обработчик ввода интервала уведомлений."""
    try:
        interval = int(message.text.strip())
        
        if interval < 1:
            await message.answer(
                "❌ Интервал не может быть меньше 1 минуты. Пожалуйста, введите корректное значение:"
            )
            return
        
        # Получаем текущие настройки
        settings = await get_notification_settings(message.from_user.id)
        
        if not settings:
            config = load_config()
            settings = {
                'interval_mode': True,
                'interval_minutes': interval,
                'position_change': False,
                'threshold_change': False,
                'threshold_value': 10,
                'enabled': True
            }
        else:
            settings['interval_mode'] = True
            settings['interval_minutes'] = interval
        
        # Обновляем настройки в БД
        await setup_notifications(message.from_user.id, settings)
        
        # Завершаем состояние
        await state.clear()
        
        await message.answer(
            f"✅ Интервал уведомлений установлен на {interval} мин.\n\n"
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_notification_settings_keyboard(settings)
        )
    except ValueError:
        await message.answer("❌ Введите корректное числовое значение для интервала уведомлений")


async def interval_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора интервала уведомлений из кнопок."""
    await callback.answer()
    
    # Получаем значение интервала из callback_data
    callback_data = callback.data.split('_')[1]
    
    if callback_data == 'back':
        # Сбрасываем состояние
        await state.clear()
        
        # Получаем текущие настройки
        settings = await get_notification_settings(callback.from_user.id)
        
        # Возвращаемся в основное меню настроек
        await callback.message.edit_text(
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_notification_settings_keyboard(settings)
        )
        return
    
    # Преобразуем callback_data в число
    interval = int(callback_data)
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback.from_user.id)
    
    # Обновляем настройки
    settings['interval_mode'] = True
    settings['interval_minutes'] = interval
    
    # Сохраняем настройки
    await setup_notifications(callback.from_user.id, settings)
    
    # Завершаем состояние
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ Интервал уведомлений установлен на {interval} мин.\n\n"
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_position_change_callback(callback: CallbackQuery):
    """Обработчик включения/отключения уведомлений при изменении позиции."""
    await callback.answer()
    
    settings = await get_notification_settings(callback.from_user.id)
    
    if not settings:
        # Если настройки не найдены, создаем их со значениями по умолчанию
        config = load_config()
        settings = {
            'interval_mode': False,
            'interval_minutes': config.default_notification_interval,
            'position_change': True,  # Включаем режим
            'threshold_change': False,
            'threshold_value': 10,
            'enabled': True
        }
    else:
        # Инвертируем текущее значение
        settings['position_change'] = not settings['position_change']
    
    # Обновляем настройки в БД
    await setup_notifications(callback.from_user.id, settings)
    
    # Обновляем сообщение с новыми настройками
    await callback.message.edit_text(
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_threshold_change_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик включения/отключения уведомлений при сдвиге очереди."""
    await callback.answer()
    
    settings = await get_notification_settings(callback.from_user.id)
    
    if not settings:
        config = load_config()
        settings = {
            'interval_mode': False,
            'interval_minutes': config.default_notification_interval,
            'position_change': False,
            'threshold_change': True,  # Включаем режим
            'threshold_value': 10,
            'enabled': True
        }
    else:
        # Инвертируем текущее значение
        settings['threshold_change'] = not settings['threshold_change']
    
    # Если включили режим, предлагаем выбрать порог сдвига
    if settings['threshold_change']:
        await callback.message.edit_text(
            f"📊 <b>Выберите порог сдвига очереди</b>\n\n"
            f"Текущий порог: {settings['threshold_value']} позиций\n"
            f"Выберите новое значение или введите своё:",
            reply_markup=get_notification_threshold_keyboard()
        )
        await state.set_state(NotificationState.waiting_for_threshold)
    else:
        # Если выключили режим, просто обновляем настройки
        await setup_notifications(callback.from_user.id, settings)
        
        await callback.message.edit_text(
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_notification_settings_keyboard(settings)
        )


async def process_threshold_input(message: Message, state: FSMContext):
    """Обработчик ввода порога сдвига очереди."""
    try:
        threshold = int(message.text.strip())
        
        if threshold < 1:
            await message.answer(
                "❌ Порог сдвига не может быть меньше 1 позиции. Пожалуйста, введите корректное значение:"
            )
            return
        
        # Получаем текущие настройки
        settings = await get_notification_settings(message.from_user.id)
        
        if not settings:
            config = load_config()
            settings = {
                'interval_mode': False,
                'interval_minutes': config.default_notification_interval,
                'position_change': False,
                'threshold_change': True,
                'threshold_value': threshold,
                'enabled': True
            }
        else:
            settings['threshold_change'] = True
            settings['threshold_value'] = threshold
        
        # Обновляем настройки в БД
        await setup_notifications(message.from_user.id, settings)
        
        # Завершаем состояние
        await state.clear()
        
        await message.answer(
            f"✅ Порог сдвига очереди установлен на {threshold} позиций.\n\n"
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_notification_settings_keyboard(settings)
        )
    except ValueError:
        await message.answer("❌ Введите корректное числовое значение для порога сдвига очереди")


async def threshold_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора порога сдвига очереди из кнопок."""
    await callback.answer()
    
    # Получаем значение порога из callback_data
    callback_data = callback.data.split('_')[1]
    
    if callback_data == 'back':
        # Сбрасываем состояние
        await state.clear()
        
        # Получаем текущие настройки
        settings = await get_notification_settings(callback.from_user.id)
        
        # Возвращаемся в основное меню настроек
        await callback.message.edit_text(
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_notification_settings_keyboard(settings)
        )
        return
    
    # Преобразуем callback_data в число
    threshold = int(callback_data)
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback.from_user.id)
    
    # Обновляем настройки
    settings['threshold_change'] = True
    settings['threshold_value'] = threshold
    
    # Сохраняем настройки
    await setup_notifications(callback.from_user.id, settings)
    
    # Завершаем состояние
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ Порог сдвига очереди установлен на {threshold} позиций.\n\n"
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def back_to_main_callback(callback: CallbackQuery):
    """Обработчик кнопки "Назад в меню"."""
    await callback.answer()
    
    # Получаем данные о машине
    car_number = await get_car_number(callback.from_user.id)
    
    if car_number:
        # Парсим текущую позицию в очереди
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
    else:
        await safe_edit_message(
            callback.message,
            "❌ У вас не задан номер автомобиля.\n"
            "Используйте команду /start для настройки.",
            reply_markup=get_main_menu()
        )


async def interval_back_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' в настройке интервала."""
    await callback.answer()
    
    # Сбрасываем состояние
    await state.clear()
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback.from_user.id)
    
    await safe_edit_message(
        callback.message,
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def threshold_back_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' в настройке порога."""
    await callback.answer()
    
    # Сбрасываем состояние
    await state.clear()
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback.from_user.id)
    
    await safe_edit_message(
        callback.message,
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_queue_threshold_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки включения/выключения уведомлений при достижении порогового номера."""
    await callback.answer()
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback.from_user.id)
    
    if settings:
        # Если уже включен режим, открываем настройку порога
        if settings.get('queue_threshold', False):
            # Устанавливаем состояние ожидания ввода порога
            await state.set_state(NotificationState.waiting_for_queue_threshold)
            
            await callback.message.edit_text(
                f"⏱ <b>Настройка порогового значения очереди</b>\n\n"
                f"Текущее значение: {settings.get('queue_threshold_value', 10)}\n\n"
                f"Введите номер в очереди (1-100), при достижении которого вы хотите получать уведомления,\n"
                f"или выберите из предложенных вариантов:",
                reply_markup=get_queue_threshold_keyboard()
            )
        else:
            # Включаем режим при достижении порога и открываем настройку
            settings['queue_threshold'] = True
            await setup_notifications(callback.from_user.id, settings)
            
            # Устанавливаем состояние ожидания ввода порога
            await state.set_state(NotificationState.waiting_for_queue_threshold)
            
            await callback.message.edit_text(
                f"⏱ <b>Настройка порогового значения очереди</b>\n\n"
                f"Текущее значение: {settings.get('queue_threshold_value', 10)}\n\n"
                f"Введите номер в очереди (1-100), при достижении которого вы хотите получать уведомления,\n"
                f"или выберите из предложенных вариантов:",
                reply_markup=get_queue_threshold_keyboard()
            )
    else:
        # Если настроек нет, создаем с включенным режимом
        settings = {
            'queue_threshold': True,
            'queue_threshold_value': 10
        }
        
        # Обновляем настройки в БД
        await setup_notifications(callback.from_user.id, settings)
        
        # Устанавливаем состояние ожидания ввода порога
        await state.set_state(NotificationState.waiting_for_queue_threshold)
        
        await callback.message.edit_text(
            f"⏱ <b>Настройка порогового значения очереди</b>\n\n"
            f"Текущее значение: 10\n\n"
            f"Введите номер в очереди (1-100), при достижении которого вы хотите получать уведомления,\n"
            f"или выберите из предложенных вариантов:",
            reply_markup=get_queue_threshold_keyboard()
        )


async def process_queue_threshold_input(message: Message, state: FSMContext):
    """Обработчик ввода порогового значения очереди для уведомлений."""
    try:
        # Преобразуем введенное значение в число
        threshold = int(message.text.strip())
        
        # Проверяем на допустимые значения
        if threshold < 1 or threshold > 100:
            await message.answer("❌ Введите значение от 1 до 100")
            return
        
        # Получаем текущие настройки
        settings = await get_notification_settings(message.from_user.id)
        
        # Если настроек нет, создаем новые
        if not settings:
            settings = {
                'queue_threshold': True,
                'queue_threshold_value': threshold,
                'enabled': True
            }
        else:
            settings['queue_threshold'] = True
            settings['queue_threshold_value'] = threshold
        
        # Обновляем настройки в БД
        await setup_notifications(message.from_user.id, settings)
        
        # Завершаем состояние
        await state.clear()
        
        await message.answer(
            f"✅ Пороговое значение очереди установлено на {threshold}.\n\n"
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings.get('interval_mode', False) else '❌'}\n"
            f"- Интервал: {settings.get('interval_minutes', 2)} мин.\n"
            f"- При изменении позиции: {'✅' if settings.get('position_change', False) else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings.get('threshold_change', False) else '❌'}\n"
            f"- Порог сдвига: {settings.get('threshold_value', 10)} позиций\n"
            f"- При достижении номера: {'✅' if settings.get('queue_threshold', False) else '❌'}\n"
            f"- Номер в очереди: {settings.get('queue_threshold_value', 10)}\n"
            f"- Уведомления: {'✅ Включены' if settings.get('enabled', True) else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_notification_settings_keyboard(settings)
        )
    except ValueError:
        await message.answer("❌ Введите корректное числовое значение для порогового номера очереди")


async def queue_threshold_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора порогового значения очереди из кнопок."""
    await callback.answer()
    
    # Получаем значение порога из callback_data
    callback_data = callback.data.split('_')[2]
    
    if callback_data == 'back':
        # Сбрасываем состояние
        await state.clear()
        
        # Получаем текущие настройки
        settings = await get_notification_settings(callback.from_user.id)
        
        # Возвращаемся в основное меню настроек
        await callback.message.edit_text(
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings.get('interval_mode', False) else '❌'}\n"
            f"- Интервал: {settings.get('interval_minutes', 2)} мин.\n"
            f"- При изменении позиции: {'✅' if settings.get('position_change', False) else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings.get('threshold_change', False) else '❌'}\n"
            f"- Порог сдвига: {settings.get('threshold_value', 10)} позиций\n"
            f"- При достижении номера: {'✅' if settings.get('queue_threshold', False) else '❌'}\n"
            f"- Номер в очереди: {settings.get('queue_threshold_value', 10)}\n"
            f"- Уведомления: {'✅ Включены' if settings.get('enabled', True) else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_notification_settings_keyboard(settings)
        )
        return
    
    # Преобразуем callback_data в число
    threshold = int(callback_data)
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback.from_user.id)
    
    # Обновляем настройки
    settings['queue_threshold'] = True
    settings['queue_threshold_value'] = threshold
    
    # Сохраняем настройки
    await setup_notifications(callback.from_user.id, settings)
    
    # Завершаем состояние
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ Пороговое значение очереди установлено на {threshold}.\n\n"
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings.get('interval_mode', False) else '❌'}\n"
        f"- Интервал: {settings.get('interval_minutes', 2)} мин.\n"
        f"- При изменении позиции: {'✅' if settings.get('position_change', False) else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings.get('threshold_change', False) else '❌'}\n"
        f"- Порог сдвига: {settings.get('threshold_value', 10)} позиций\n"
        f"- При достижении номера: {'✅' if settings.get('queue_threshold', False) else '❌'}\n"
        f"- Номер в очереди: {settings.get('queue_threshold_value', 10)}\n"
        f"- Уведомления: {'✅ Включены' if settings.get('enabled', True) else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def queue_threshold_back_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' в настройке порога очереди."""
    await callback.answer()
    
    # Сбрасываем состояние
    await state.clear()
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback.from_user.id)
    
    await safe_edit_message(
        callback.message,
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings.get('interval_mode', False) else '❌'}\n"
        f"- Интервал: {settings.get('interval_minutes', 2)} мин.\n"
        f"- При изменении позиции: {'✅' if settings.get('position_change', False) else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings.get('threshold_change', False) else '❌'}\n"
        f"- Порог сдвига: {settings.get('threshold_value', 10)} позиций\n"
        f"- При достижении номера: {'✅' if settings.get('queue_threshold', False) else '❌'}\n"
        f"- Номер в очереди: {settings.get('queue_threshold_value', 10)}\n"
        f"- Уведомления: {'✅ Включены' if settings.get('enabled', True) else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        reply_markup=get_notification_settings_keyboard(settings)
    )


def get_settings_router() -> Router:
    """Создание роутера для настроек уведомлений."""
    router = Router()
    
    # Команда настроек
    router.message.register(cmd_settings, Command("settings"))
    
    # Обработчики инлайн-кнопок
    router.callback_query.register(settings_callback, F.data == "settings")
    router.callback_query.register(toggle_notifications_callback, F.data == "toggle_notifications")
    router.callback_query.register(toggle_interval_mode_callback, F.data == "toggle_interval")
    router.callback_query.register(toggle_position_change_callback, F.data == "toggle_position")
    router.callback_query.register(toggle_threshold_change_callback, F.data == "toggle_threshold")
    router.callback_query.register(toggle_queue_threshold_callback, F.data == "toggle_queue_threshold")
    router.callback_query.register(back_to_main_callback, F.data == "back_to_main")
    
    # Обработчики ввода числовых значений
    router.message.register(process_interval_input, NotificationState.waiting_for_interval)
    router.message.register(process_threshold_input, NotificationState.waiting_for_threshold)
    router.message.register(process_queue_threshold_input, NotificationState.waiting_for_queue_threshold)
    
    # Обработчики выбора значений из кнопок
    router.callback_query.register(
        interval_callback, 
        F.data.startswith("interval_"), 
        NotificationState.waiting_for_interval
    )
    
    router.callback_query.register(
        threshold_callback, 
        F.data.startswith("threshold_"), 
        NotificationState.waiting_for_threshold
    )
    
    router.callback_query.register(
        queue_threshold_callback, 
        F.data.startswith("queue_threshold_"), 
        NotificationState.waiting_for_queue_threshold
    )
    
    # Обработчики кнопок "Назад"
    router.callback_query.register(
        interval_back_callback, 
        F.data == "interval_back", 
        NotificationState.waiting_for_interval
    )
    
    router.callback_query.register(
        threshold_back_callback, 
        F.data == "threshold_back", 
        NotificationState.waiting_for_threshold
    )
    
    router.callback_query.register(
        queue_threshold_back_callback, 
        F.data == "queue_threshold_back", 
        NotificationState.waiting_for_queue_threshold
    )
    
    return router 