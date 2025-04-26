from aiogram import Router, F
from aiogram.types import Message


async def echo(message: Message):
    """Эхо-обработчик для неизвестных команд и сообщений."""
    await message.answer(
        "❓ Я не понимаю эту команду. Используйте меню или /help для справки."
    )


def get_common_router() -> Router:
    """Создание роутера для общих обработчиков."""
    router = Router()
    
    # Эхо-обработчик должен быть последним
    # F.text - этот фильтр заменяет проверку на текстовые сообщения в Aiogram 3.x
    router.message.register(echo, F.text)
    
    return router 