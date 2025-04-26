from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
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
    get_notification_threshold_keyboard
)
from bot.config.config import load_config
from bot.utils.message_utils import safe_edit_message
from bot.services.parser import CoddParser


class NotificationState(StatesGroup):
    waiting_for_interval = State()
    waiting_for_threshold = State()


async def cmd_settings(message: types.Message):
    """Обработчик команды /settings для настройки уведомлений."""
    settings = await get_notification_settings(message.from_user.id)
    
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
        await setup_notifications(message.from_user.id, settings)
    
    await message.answer(
        f"⚙️ *Настройки уведомлений*\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def settings_callback(callback_query: types.CallbackQuery):
    """Обработчик инлайн-кнопки 'Настроить уведомления'."""
    await callback_query.answer()
    
    settings = await get_notification_settings(callback_query.from_user.id)
    
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
        await setup_notifications(callback_query.from_user.id, settings)
    
    await safe_edit_message(
        callback_query.message,
        f"⚙️ *Настройки уведомлений*\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_notifications_callback(callback_query: types.CallbackQuery):
    """Обработчик включения/отключения уведомлений."""
    await callback_query.answer()
    
    settings = await get_notification_settings(callback_query.from_user.id)
    
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
    await setup_notifications(callback_query.from_user.id, settings)
    
    # Обновляем сообщение с новыми настройками
    await safe_edit_message(
        callback_query.message,
        f"⚙️ *Настройки уведомлений*\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_interval_mode_callback(callback_query: types.CallbackQuery):
    """Обработчик включения/отключения интервального режима."""
    await callback_query.answer()
    
    settings = await get_notification_settings(callback_query.from_user.id)
    
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
            callback_query.message,
            f"⏱️ *Выберите интервал уведомлений*\n\n"
            f"Текущий интервал: {settings['interval_minutes']} мин.\n"
            f"Выберите новое значение или введите своё (в минутах):",
            parse_mode="Markdown",
            reply_markup=get_notification_interval_keyboard()
        )
        await NotificationState.waiting_for_interval.set()
    else:
        # Если выключили режим, просто обновляем настройки
        await setup_notifications(callback_query.from_user.id, settings)
        
        await safe_edit_message(
            callback_query.message,
            f"⚙️ *Настройки уведомлений*\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            parse_mode="Markdown",
            reply_markup=get_notification_settings_keyboard(settings)
        )


async def process_interval_input(message: types.Message, state: FSMContext):
    """Обработчик ввода интервала уведомлений."""
    try:
        interval = int(message.text.strip())
        
        if interval < 1:
            await message.answer(
                "❌ Интервал не может быть меньше 1 минуты. Пожалуйста, введите корректное значение:",
                reply_markup=get_notification_interval_keyboard()
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
        await state.finish()
        
        await message.answer(
            f"✅ Интервал уведомлений установлен на {interval} мин.\n\n"
            f"⚙️ *Настройки уведомлений*\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            parse_mode="Markdown",
            reply_markup=get_notification_settings_keyboard(settings)
        )
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число (количество минут):",
            reply_markup=get_notification_interval_keyboard()
        )


async def interval_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора интервала уведомлений из кнопок."""
    await callback_query.answer()
    
    # Проверяем, не является ли это нажатием кнопки "Назад"
    callback_data = callback_query.data.split('_')[1]
    if callback_data == 'back':
        # Сбрасываем состояние
        await state.finish()
        
        # Получаем текущие настройки
        settings = await get_notification_settings(callback_query.from_user.id)
        
        # Возвращаемся в основное меню настроек
        await callback_query.message.edit_text(
            f"⚙️ *Настройки уведомлений*\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            parse_mode="Markdown",
            reply_markup=get_notification_settings_keyboard(settings)
        )
        return
    
    interval = int(callback_data)
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback_query.from_user.id)
    
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
    await setup_notifications(callback_query.from_user.id, settings)
    
    # Завершаем состояние
    await state.finish()
    
    await callback_query.message.edit_text(
        f"✅ Интервал уведомлений установлен на {interval} мин.\n\n"
        f"⚙️ *Настройки уведомлений*\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_position_change_callback(callback_query: types.CallbackQuery):
    """Обработчик включения/отключения уведомлений при изменении позиции."""
    await callback_query.answer()
    
    settings = await get_notification_settings(callback_query.from_user.id)
    
    if not settings:
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
    await setup_notifications(callback_query.from_user.id, settings)
    
    # Обновляем сообщение с новыми настройками
    await callback_query.message.edit_text(
        f"⚙️ *Настройки уведомлений*\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def toggle_threshold_change_callback(callback_query: types.CallbackQuery):
    """Обработчик включения/отключения уведомлений при сдвиге очереди."""
    await callback_query.answer()
    
    settings = await get_notification_settings(callback_query.from_user.id)
    
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
    
    # Если включили режим, предлагаем выбрать порог
    if settings['threshold_change']:
        await callback_query.message.edit_text(
            f"📊 *Выберите порог сдвига очереди*\n\n"
            f"Текущий порог: {settings['threshold_value']} позиций\n"
            f"Выберите новое значение или введите своё:",
            parse_mode="Markdown",
            reply_markup=get_notification_threshold_keyboard()
        )
        await NotificationState.waiting_for_threshold.set()
    else:
        # Если выключили режим, просто обновляем настройки
        await setup_notifications(callback_query.from_user.id, settings)
        
        await callback_query.message.edit_text(
            f"⚙️ *Настройки уведомлений*\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            parse_mode="Markdown",
            reply_markup=get_notification_settings_keyboard(settings)
        )


async def process_threshold_input(message: types.Message, state: FSMContext):
    """Обработчик ввода порога сдвига очереди."""
    try:
        threshold = int(message.text.strip())
        
        if threshold < 1:
            await message.answer(
                "❌ Порог не может быть меньше 1 позиции. Пожалуйста, введите корректное значение:",
                reply_markup=get_notification_threshold_keyboard()
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
        await state.finish()
        
        await message.answer(
            f"✅ Порог сдвига очереди установлен на {threshold} позиций.\n\n"
            f"⚙️ *Настройки уведомлений*\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            parse_mode="Markdown",
            reply_markup=get_notification_settings_keyboard(settings)
        )
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число (количество позиций):",
            reply_markup=get_notification_threshold_keyboard()
        )


async def threshold_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора порога сдвига очереди из кнопок."""
    await callback_query.answer()
    
    # Проверяем, не является ли это нажатием кнопки "Назад"
    callback_data = callback_query.data.split('_')[1]
    if callback_data == 'back':
        # Сбрасываем состояние
        await state.finish()
        
        # Получаем текущие настройки
        settings = await get_notification_settings(callback_query.from_user.id)
        
        # Возвращаемся в основное меню настроек
        await callback_query.message.edit_text(
            f"⚙️ *Настройки уведомлений*\n\n"
            f"Текущие настройки:\n"
            f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
            f"- Интервал: {settings['interval_minutes']} мин.\n"
            f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
            f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
            f"- Порог сдвига: {settings['threshold_value']} позиций\n"
            f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
            f"Выберите, что хотите изменить:",
            parse_mode="Markdown",
            reply_markup=get_notification_settings_keyboard(settings)
        )
        return
    
    threshold = int(callback_data)
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback_query.from_user.id)
    
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
    await setup_notifications(callback_query.from_user.id, settings)
    
    # Завершаем состояние
    await state.finish()
    
    await callback_query.message.edit_text(
        f"✅ Порог сдвига очереди установлен на {threshold} позиций.\n\n"
        f"⚙️ *Настройки уведомлений*\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def back_to_main_callback(callback_query: types.CallbackQuery):
    """Обработчик кнопки "Назад в меню"."""
    await callback_query.answer()
    
    # Получаем номер автомобиля пользователя
    car_number = await get_car_number(callback_query.from_user.id)
    
    if car_number:
        # Если автомобиль указан, получаем о нем информацию
        parser = CoddParser()
        car_data = await parser.parse_car_data(car_number)
        
        if car_data:
            await safe_edit_message(
                callback_query.message,
                f"🚗 *Информация о вашем автомобиле в очереди*\n\n"
                f"Автомобиль номер: `{car_data['car_number']}`\n"
                f"Модель: {car_data['model']}\n"
                f"Ваш номер в очереди: *{car_data['queue_position']}*\n"
                f"Дата регистрации: {car_data['registration_date']}\n\n"
                f"Выберите действие:",
                parse_mode="Markdown",
                reply_markup=get_main_menu()
            )
        else:
            await safe_edit_message(
                callback_query.message,
                f"❓ Информация о вашем автомобиле с номером `{car_number}` не найдена в очереди.\n"
                f"Возможно, номер указан неверно или сервис временно недоступен.\n\n"
                f"Выберите действие:",
                parse_mode="Markdown",
                reply_markup=get_main_menu()
            )
    else:
        # Если автомобиль не указан, просто показываем меню
        await safe_edit_message(
            callback_query.message,
            "🚗 Выберите действие:",
            reply_markup=get_main_menu()
        )


async def interval_back_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' в настройке интервала."""
    await callback_query.answer()
    
    # Сбрасываем состояние
    await state.finish()
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback_query.from_user.id)
    
    # Возвращаемся в основное меню настроек
    await safe_edit_message(
        callback_query.message,
        f"⚙️ *Настройки уведомлений*\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard(settings)
    )


async def threshold_back_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' в настройке порога."""
    await callback_query.answer()
    
    # Сбрасываем состояние
    await state.finish()
    
    # Получаем текущие настройки
    settings = await get_notification_settings(callback_query.from_user.id)
    
    # Возвращаемся в основное меню настроек
    await safe_edit_message(
        callback_query.message,
        f"⚙️ *Настройки уведомлений*\n\n"
        f"Текущие настройки:\n"
        f"- Интервальный режим: {'✅' if settings['interval_mode'] else '❌'}\n"
        f"- Интервал: {settings['interval_minutes']} мин.\n"
        f"- При изменении позиции: {'✅' if settings['position_change'] else '❌'}\n"
        f"- При сдвиге очереди: {'✅' if settings['threshold_change'] else '❌'}\n"
        f"- Порог сдвига: {settings['threshold_value']} позиций\n"
        f"- Уведомления: {'✅ Включены' if settings['enabled'] else '❌ Выключены'}\n\n"
        f"Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard(settings)
    )


def register_settings_handlers(dp: Dispatcher):
    """Регистрация обработчиков для настроек уведомлений."""
    dp.register_message_handler(cmd_settings, commands=["settings"])
    dp.register_callback_query_handler(settings_callback, lambda c: c.data == "settings")
    dp.register_callback_query_handler(toggle_notifications_callback, lambda c: c.data == "toggle_notifications")
    dp.register_callback_query_handler(toggle_interval_mode_callback, lambda c: c.data == "toggle_interval")
    dp.register_callback_query_handler(toggle_position_change_callback, lambda c: c.data == "toggle_position")
    dp.register_callback_query_handler(toggle_threshold_change_callback, lambda c: c.data == "toggle_threshold")
    dp.register_callback_query_handler(back_to_main_callback, lambda c: c.data == "back_to_main")
    
    # Обработчики ввода числовых значений
    dp.register_message_handler(process_interval_input, state=NotificationState.waiting_for_interval)
    dp.register_message_handler(process_threshold_input, state=NotificationState.waiting_for_threshold)
    
    # Обработчики выбора значений из кнопок
    dp.register_callback_query_handler(
        interval_callback, 
        lambda c: c.data.startswith("interval_"), 
        state=NotificationState.waiting_for_interval
    )
    dp.register_callback_query_handler(
        threshold_callback, 
        lambda c: c.data.startswith("threshold_"), 
        state=NotificationState.waiting_for_threshold
    )
    
    # Обработчики кнопок "Назад"
    dp.register_callback_query_handler(
        interval_back_callback, 
        lambda c: c.data == "interval_back", 
        state=NotificationState.waiting_for_interval
    )
    dp.register_callback_query_handler(
        threshold_back_callback, 
        lambda c: c.data == "threshold_back", 
        state=NotificationState.waiting_for_threshold
    ) 