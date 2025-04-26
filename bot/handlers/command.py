from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from bot.keyboards.keyboards import get_main_menu
from bot.utils.message_utils import safe_edit_message


async def cmd_help(message: Message):
    """Обработчик команды /help."""
    await message.answer(
        "🔎 <b>Справка по использованию бота</b>\n\n"
        "<b>ЦОДД Электронная очередь</b> - бот для отслеживания очереди автомобилей на странице ЦОДД.\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Запустить бота и ввести/изменить номер автомобиля\n"
        "/check - Проверить текущую позицию в очереди\n"
        "/settings - Настроить уведомления\n"
        "/help - Показать эту справку\n\n"
        "<b>Настройки уведомлений:</b>\n"
        "- Интервальный режим: периодические уведомления через заданный интервал времени\n"
        "- При изменении позиции: уведомление при каждом изменении позиции в очереди\n"
        "- При сдвиге очереди: уведомление, когда очередь сдвинется на указанное число позиций\n\n"
        "Вы можете включить несколько режимов одновременно.",
        reply_markup=get_main_menu()
    )


async def help_callback(callback: CallbackQuery):
    """Обработчик инлайн-кнопки 'Справка'."""
    await callback.answer()
    
    await safe_edit_message(
        callback.message,
        "🔎 <b>Справка по использованию бота</b>\n\n"
        "<b>ЦОДД Электронная очередь</b> - бот для отслеживания очереди автомобилей на странице ЦОДД.\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - Запустить бота и ввести/изменить номер автомобиля\n"
        "/check - Проверить текущую позицию в очереди\n"
        "/settings - Настроить уведомления\n"
        "/help - Показать эту справку\n\n"
        "<b>Настройки уведомлений:</b>\n"
        "- Интервальный режим: периодические уведомления через заданный интервал времени\n"
        "- При изменении позиции: уведомление при каждом изменении позиции в очереди\n"
        "- При сдвиге очереди: уведомление, когда очередь сдвинется на указанное число позиций\n\n"
        "Вы можете включить несколько режимов одновременно.",
        reply_markup=get_main_menu()
    )


def get_command_router() -> Router:
    """Создание роутера для команд."""
    router = Router()
    
    router.message.register(cmd_help, Command("help"))
    router.callback_query.register(help_callback, F.data == "help")
    
    return router 