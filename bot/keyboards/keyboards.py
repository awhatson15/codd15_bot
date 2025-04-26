from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_main_menu() -> InlineKeyboardBuilder:
    """Основное меню бота."""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="🔍 Проверить очередь", callback_data="check_queue"),
        InlineKeyboardButton(text="⚙️ Настроить уведомления", callback_data="settings"),
        InlineKeyboardButton(text="💬 Анонимный чат", callback_data="open_chat"),
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
    
    # При достижении порога очереди
    queue_threshold_text = f"{'✅' if settings.get('queue_threshold', False) else '❌'} При достижении номера ({settings.get('queue_threshold_value', 10)})"
    builder.add(InlineKeyboardButton(text=queue_threshold_text, callback_data="toggle_queue_threshold"))
    
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


def get_queue_threshold_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для выбора порогового значения очереди."""
    builder = InlineKeyboardBuilder()
    
    # Варианты порогов номера очереди
    thresholds = [3, 5, 10, 15, 20, 30]
    buttons = [InlineKeyboardButton(text=f"Номер {threshold}", callback_data=f"queue_threshold_{threshold}") for threshold in thresholds]
    
    builder.add(*buttons)
    
    # Добавляем кнопку "Назад"
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="queue_threshold_back"))
    
    # Устанавливаем по 3 кнопки в ряд
    builder.adjust(3, 3, 1)
    return builder.as_markup()


def get_chat_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для анонимного чата."""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="✏️ Написать сообщение", callback_data="send_message"),
        InlineKeyboardButton(text="🔄 Обновить чат", callback_data="refresh_chat"),
        InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data="report_message"),
        InlineKeyboardButton(text="❌ Выйти из чата", callback_data="exit_chat"),
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main"),
    ]
    
    builder.add(*buttons)
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_chat_message_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для сообщения в чате."""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="👍 Спасибо", callback_data="like_message"),
        InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data="report_message"),
    ]
    
    builder.add(*buttons)
    builder.adjust(2)
    return builder.as_markup()


def get_chat_report_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для жалобы на сообщение."""
    builder = InlineKeyboardBuilder()
    
    reasons = [
        "Оскорбление",
        "Спам",
        "Нецензурная лексика",
        "Личные данные"
    ]
    
    buttons = [
        InlineKeyboardButton(text=reason, callback_data=f"report_reason_{i}")
        for i, reason in enumerate(reasons)
    ]
    
    # Добавляем кнопку отмены
    buttons.append(InlineKeyboardButton(text="Отмена", callback_data="cancel_report"))
    
    builder.add(*buttons)
    builder.adjust(1)
    return builder.as_markup()


def get_back_to_chat_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для возврата в чат."""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="◀️ Вернуться в чат", callback_data="back_to_chat"))
    
    return builder.as_markup() 