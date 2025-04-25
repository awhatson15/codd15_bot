from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu() -> InlineKeyboardMarkup:
    """Основное меню бота."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        InlineKeyboardButton("🔍 Проверить очередь", callback_data="check_queue"),
        InlineKeyboardButton("⚙️ Настроить уведомления", callback_data="settings"),
        InlineKeyboardButton("🔕 Отключить уведомления", callback_data="toggle_notifications"),
        InlineKeyboardButton("🚗 Изменить номер авто", callback_data="change_car"),
        InlineKeyboardButton("❓ Справка", callback_data="help"),
    ]
    
    keyboard.add(*buttons)
    return keyboard


def get_notification_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Клавиатура для настроек уведомлений."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Интервальный режим
    interval_text = f"{'✅' if settings.get('interval_mode', False) else '❌'} Интервальный режим ({settings.get('interval_minutes', 2)} мин.)"
    keyboard.add(InlineKeyboardButton(interval_text, callback_data="toggle_interval"))
    
    # При изменении позиции
    position_text = f"{'✅' if settings.get('position_change', False) else '❌'} При изменении позиции"
    keyboard.add(InlineKeyboardButton(position_text, callback_data="toggle_position"))
    
    # При сдвиге очереди
    threshold_text = f"{'✅' if settings.get('threshold_change', False) else '❌'} При сдвиге очереди ({settings.get('threshold_value', 10)} позиций)"
    keyboard.add(InlineKeyboardButton(threshold_text, callback_data="toggle_threshold"))
    
    # Общее включение/отключение уведомлений
    enabled_text = f"{'🔔 Уведомления включены' if settings.get('enabled', True) else '🔕 Уведомления выключены'}"
    keyboard.add(InlineKeyboardButton(enabled_text, callback_data="toggle_notifications"))
    
    # Кнопка "Назад в меню"
    keyboard.add(InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main"))
    
    return keyboard


def get_notification_interval_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора интервала уведомлений."""
    keyboard = InlineKeyboardMarkup(row_width=3)
    
    # Варианты интервалов
    intervals = [2, 5, 10, 15, 30, 60]
    buttons = [InlineKeyboardButton(f"{interval} мин.", callback_data=f"interval_{interval}") for interval in intervals]
    
    # Добавляем кнопки по 3 в ряд
    for i in range(0, len(buttons), 3):
        keyboard.row(*buttons[i:i + 3])
    
    # Добавляем кнопку "Назад"
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="interval_back"))
    
    return keyboard


def get_notification_threshold_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора порога сдвига очереди."""
    keyboard = InlineKeyboardMarkup(row_width=3)
    
    # Варианты порогов
    thresholds = [5, 10, 15, 20, 30, 50]
    buttons = [InlineKeyboardButton(f"{threshold} позиций", callback_data=f"threshold_{threshold}") for threshold in thresholds]
    
    # Добавляем кнопки по 3 в ряд
    for i in range(0, len(buttons), 3):
        keyboard.row(*buttons[i:i + 3])
    
    # Добавляем кнопку "Назад"
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="threshold_back"))
    
    return keyboard 