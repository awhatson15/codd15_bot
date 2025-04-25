def format_car_info(car_number, model, queue_position, reg_date):
    """Форматирование информации об автомобиле"""
    info = f"<b>Автомобиль номер:</b> <code>{car_number}</code>\n"
    info += f"<b>Модель:</b> {model}\n"
    info += f"<b>Ваш номер в очереди:</b> {queue_position}\n"
    info += f"<b>Дата регистрации:</b> {reg_date}\n"
    return info
