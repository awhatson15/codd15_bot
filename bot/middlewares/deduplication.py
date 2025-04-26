import logging
from collections import OrderedDict
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Update, Message, TelegramObject

# Кеш для хранения последних обработанных сообщений
_processed_messages = OrderedDict()
_processed_updates = OrderedDict()
_MAX_CACHE_SIZE = 100


class DeduplicationMiddleware(BaseMiddleware):
    """
    Middleware для предотвращения дублирования сообщений и обновлений.
    Проверяет, было ли сообщение или обновление уже обработано по его ID.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка всех типов обновлений"""
        global _processed_updates
        
        update_id = event.update_id
        
        # Если обновление уже обрабатывалось, пропускаем его
        if update_id in _processed_updates:
            logging.debug(f"Дублирующееся обновление пропущено: {update_id}")
            return None
        
        # Добавляем обновление в кеш обработанных
        _processed_updates[update_id] = True
        
        # Ограничиваем размер кеша
        if len(_processed_updates) > _MAX_CACHE_SIZE:
            # Удаляем самые старые записи
            for _ in range(len(_processed_updates) - _MAX_CACHE_SIZE):
                _processed_updates.popitem(last=False)
                
        # Для сообщений делаем дополнительную проверку
        if hasattr(event, 'message') and isinstance(event.message, Message):
            message = event.message
            message_id = message.message_id
            chat_id = message.chat.id
            
            # Создаем уникальный ключ для сообщения (комбинация chat_id и message_id)
            msg_key = f"{chat_id}:{message_id}"
            
            # Если сообщение уже обрабатывалось, пропускаем его
            if msg_key in _processed_messages:
                logging.debug(f"Дублирующееся сообщение пропущено: {msg_key}")
                return None
            
            # Добавляем сообщение в кеш обработанных
            _processed_messages[msg_key] = True
            
            # Ограничиваем размер кеша
            if len(_processed_messages) > _MAX_CACHE_SIZE:
                # Удаляем самые старые записи
                for _ in range(len(_processed_messages) - _MAX_CACHE_SIZE):
                    _processed_messages.popitem(last=False)
        
        # Если дубликатов не найдено, передаем событие дальше
        return await handler(event, data) 