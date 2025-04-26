import logging
from typing import Any, Dict, Optional, Union

from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest


def escape_markdown(text: str) -> str:
    """
    Экранирование специальных символов Markdown.
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


async def safe_edit_message(
    message: Message,
    text: str,
    reply_markup: Optional[Any] = None,
    **kwargs: Any
) -> Optional[Message]:
    """
    Безопасное обновление сообщения с обработкой ошибки MessageNotModified.
    
    Args:
        message: Сообщение для обновления
        text: Новый текст
        reply_markup: Инлайн-клавиатура
        **kwargs: Дополнительные параметры
        
    Returns:
        Обновлённое сообщение или None в случае ошибки
    """
    try:
        return await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            **kwargs
        )
    except TelegramBadRequest as e:
        # Игнорируем ошибку MessageNotModified
        if "message is not modified" not in str(e).lower():
            # Логируем другие ошибки
            logging.error(f"Ошибка при обновлении сообщения: {e}")
        return None
    except Exception as e:
        logging.error(f"Неожиданная ошибка при обновлении сообщения: {e}")
        return None 