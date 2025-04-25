from aiogram import Dispatcher, types


async def echo(message: types.Message):
    """Эхо-обработчик для неизвестных команд и сообщений."""
    await message.answer(
        "❓ Я не понимаю эту команду. Используйте меню или /help для справки."
    )


def register_common_handlers(dp: Dispatcher):
    """Регистрация общих обработчиков."""
    # Эхо-обработчик должен быть последним
    dp.register_message_handler(echo) 