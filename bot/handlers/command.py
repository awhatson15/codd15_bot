from aiogram import Dispatcher, types

from bot.keyboards.keyboards import get_main_menu
from bot.utils.message_utils import safe_edit_message


async def cmd_help(message: types.Message):
    """Обработчик команды /help."""
    await message.answer(
        "🔎 *Справка по использованию бота*\n\n"
        "*ЦОДД Электронная очередь* - бот для отслеживания очереди автомобилей на странице ЦОДД.\n\n"
        "*Доступные команды:*\n"
        "/start - Запустить бота и ввести/изменить номер автомобиля\n"
        "/check - Проверить текущую позицию в очереди\n"
        "/settings - Настроить уведомления\n"
        "/help - Показать эту справку\n\n"
        "*Настройки уведомлений:*\n"
        "- Интервальный режим: периодические уведомления через заданный интервал времени\n"
        "- При изменении позиции: уведомление при каждом изменении позиции в очереди\n"
        "- При сдвиге очереди: уведомление, когда очередь сдвинется на указанное число позиций\n\n"
        "Вы можете включить несколько режимов одновременно.",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )


async def help_callback(callback_query: types.CallbackQuery):
    """Обработчик инлайн-кнопки 'Справка'."""
    await callback_query.answer()
    
    await safe_edit_message(
        callback_query.message,
        "🔎 *Справка по использованию бота*\n\n"
        "*ЦОДД Электронная очередь* - бот для отслеживания очереди автомобилей на странице ЦОДД.\n\n"
        "*Доступные команды:*\n"
        "/start - Запустить бота и ввести/изменить номер автомобиля\n"
        "/check - Проверить текущую позицию в очереди\n"
        "/settings - Настроить уведомления\n"
        "/help - Показать эту справку\n\n"
        "*Настройки уведомлений:*\n"
        "- Интервальный режим: периодические уведомления через заданный интервал времени\n"
        "- При изменении позиции: уведомление при каждом изменении позиции в очереди\n"
        "- При сдвиге очереди: уведомление, когда очередь сдвинется на указанное число позиций\n\n"
        "Вы можете включить несколько режимов одновременно.",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )


def register_command_handlers(dp: Dispatcher):
    """Регистрация обработчиков для команд."""
    dp.register_message_handler(cmd_help, commands=["help"])
    dp.register_callback_query_handler(help_callback, lambda c: c.data == "help") 