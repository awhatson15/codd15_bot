from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    """Основная клавиатура бота"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        InlineKeyboardButton("🔄 Проверить очередь", callback_data="check_queue"),
        InlineKeyboardButton("🔔 Настроить уведомления", callback_data="notification_settings")
    )
    keyboard.add(
        InlineKeyboardButton("🔕 Отключить уведомления", callback_data="disable_notifications"),
        InlineKeyboardButton("🚗 Изменить номер авто", callback_data="change_car")
    )
    keyboard.add(InlineKeyboardButton("❓ Справка", callback_data="help"))
    
    return keyboard

def get_notification_settings_keyboard():
    """Клавиатура настроек уведомлений"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    keyboard.add(
        InlineKeyboardButton("⏱ Настроить интервал уведомлений", callback_data="set_interval"),
        InlineKeyboardButton("🔄 Уведомлять при изменении позиции", callback_data="toggle_position_change"),
        InlineKeyboardButton("📊 Уведомлять при сдвиге на N позиций", callback_data="set_shift"),
        InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_menu")
    )
    
    return keyboard

def get_interval_keyboard():
    """Клавиатура выбора интервала уведомлений"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    
    # Добавляем предустановленные интервалы (в минутах)
    keyboard.add(
        InlineKeyboardButton("2 мин", callback_data="interval_2"),
        InlineKeyboardButton("5 мин", callback_data="interval_5"),
        InlineKeyboardButton("10 мин", callback_data="interval_10")
    )
    keyboard.add(
        InlineKeyboardButton("15 мин", callback_data="interval_15"),
        InlineKeyboardButton("30 мин", callback_data="interval_30"),
        InlineKeyboardButton("60 мин", callback_data="interval_60")
    )
    
    # Кнопка отключения интервальных уведомлений
    keyboard.add(InlineKeyboardButton("🔕 Отключить", callback_data="interval_0"))
    
    # Кнопка возврата
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="notification_settings"))
    
    return keyboard

def get_shift_keyboard():
    """Клавиатура выбора порога сдвига очереди"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    
    # Добавляем предустановленные пороги сдвига
    keyboard.add(
        InlineKeyboardButton("1 поз.", callback_data="shift_1"),
        InlineKeyboardButton("3 поз.", callback_data="shift_3"),
        InlineKeyboardButton("5 поз.", callback_data="shift_5")
    )
    keyboard.add(
        InlineKeyboardButton("10 поз.", callback_data="shift_10"),
        InlineKeyboardButton("15 поз.", callback_data="shift_15"),
        InlineKeyboardButton("20 поз.", callback_data="shift_20")
    )
    
    # Кнопка отключения уведомлений о сдвиге
    keyboard.add(InlineKeyboardButton("🔕 Отключить", callback_data="shift_0"))
    
    # Кнопка возврата
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="notification_settings"))
    
    return keyboard

def get_back_keyboard():
    """Клавиатура только с кнопкой возврата"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("◀️ Назад в главное меню", callback_data="back_to_menu"))
    return keyboard
