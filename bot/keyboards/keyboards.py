from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_main_menu() -> InlineKeyboardBuilder:
    """Основное меню бота."""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="🔍 Проверить очередь", callback_data="check_queue"),
        InlineKeyboardButton(text="⚙️ Настроить уведомления", callback_data="settings"),
        InlineKeyboardButton(text="🔕 Отключить уведомления", callback_data="toggle_notifications"),
        InlineKeyboardButton(text="🚗 Изменить номер авто", callback_data="change_car"),
        InlineKeyboardButton(text="🗑️ Удалить номер авто", callback_data="delete_car"),
        InlineKeyboardButton(text="❓ Справка", callback_data="help"),
    ]
    
    builder.add(*buttons)
    builder.adjust(2)
    return builder.as_markup()


def get_notification_settings_keyboard(settings: dict) -> InlineKeyboardBuilder:
    """Клавиатура для настроек уведомлений."""
    builder = InlineKeyboardBuilder()
    
    # Интервальный режим
    interval_text = f"{'✅' if settings.get('interval_mode', False) else '❌'} Интервальный режим ({settings.get('interval_minutes', 2)} мин.)"
    builder.add(InlineKeyboardButton(text=interval_text, callback_data="toggle_interval"))
    
    # При изменении позиции
    position_text = f"{'✅' if settings.get('position_change', False) else '❌'} При изменении позиции"
    builder.add(InlineKeyboardButton(text=position_text, callback_data="toggle_position"))
    
    # При сдвиге очереди
    threshold_text = f"{'✅' if settings.get('threshold_change', False) else '❌'} При сдвиге очереди ({settings.get('threshold_value', 10)} позиций)"
    builder.add(InlineKeyboardButton(text=threshold_text, callback_data="toggle_threshold"))
    
    # Общее включение/отключение уведомлений
    enabled_text = f"{'🔔 Уведомления включены' if settings.get('enabled', True) else '🔕 Уведомления выключены'}"
    builder.add(InlineKeyboardButton(text=enabled_text, callback_data="toggle_notifications"))
    
    # Кнопка "Назад в меню"
    builder.add(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main"))
    
    # Устанавливаем по 1 кнопке в ряд
    builder.adjust(1)
    return builder.as_markup()


def get_notification_interval_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для выбора интервала уведомлений."""
    builder = InlineKeyboardBuilder()
    
    # Варианты интервалов
    intervals = [2, 5, 10, 15, 30, 60]
    buttons = [InlineKeyboardButton(text=f"{interval} мин.", callback_data=f"interval_{interval}") for interval in intervals]
    
    builder.add(*buttons)
    
    # Добавляем кнопку "Назад"
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="interval_back"))
    
    # Устанавливаем по 3 кнопки в ряд
    builder.adjust(3, 3, 1)
    return builder.as_markup()


def get_notification_threshold_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для выбора порога сдвига очереди."""
    builder = InlineKeyboardBuilder()
    
    # Варианты порогов
    thresholds = [5, 10, 15, 20, 30, 50]
    buttons = [InlineKeyboardButton(text=f"{threshold} позиций", callback_data=f"threshold_{threshold}") for threshold in thresholds]
    
    builder.add(*buttons)
    
    # Добавляем кнопку "Назад"
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="threshold_back"))
    
    # Устанавливаем по 3 кнопки в ряд
    builder.adjust(3, 3, 1)
    return builder.as_markup() 