import logging
from typing import Any, Dict, Optional, Union

from aiogram.types import InlineKeyboardMarkup, Message


async def safe_edit_message(
    message: Message,
    text: str,
    parse_mode: Optional[str] = None, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    **kwargs: Any
) -> Optional[Message]:
    """
    Безопасное обновление сообщения с обработкой ошибки MessageNotModified.
    
    Args:
        message: Сообщение для обновления
        text: Новый текст
        parse_mode: Режим форматирования
        reply_markup: Инлайн-клавиатура
        **kwargs: Дополнительные параметры
        
    Returns:
        Обновлённое сообщение или None в случае ошибки
    """
    try:
        return await message.edit_text(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            **kwargs
        )
    except Exception as e:
        # Игнорируем ошибку MessageNotModified
        if "Message is not modified" not in str(e):
            # Логируем другие ошибки
            logging.error(f"Ошибка при обновлении сообщения: {e}")
        return None 