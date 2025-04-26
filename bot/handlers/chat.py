from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from bot.models.database import (
    generate_anonymous_id,
    save_chat_message,
    get_recent_messages,
    report_message,
    toggle_chat_participation,
    is_user_banned,
    get_active_chat_users,
    get_car_number
)
from bot.keyboards.keyboards import (
    get_chat_keyboard,
    get_chat_message_keyboard,
    get_chat_report_keyboard,
    get_back_to_chat_keyboard
)
from bot.utils.message_utils import safe_edit_message
from bot.services.parser import CoddParser
from bot.services.notifications import process_chat_notifications


class ChatState(StatesGroup):
    in_chat = State()
    waiting_for_message = State()
    report_reason = State()


async def cmd_chat(message: Message, state: FSMContext):
    """Обработчик команды /chat для входа в анонимный чат."""
    # Проверка на случай, если state равен None
    if state is None:
        # Просто отправляем команду /chat и возвращаемся
        await message.answer(
            "Для входа в анонимный чат водителей используйте команду /chat напрямую, а не через меню."
        )
        return
        
    # Проверяем, есть ли у пользователя автомобиль в очереди
    car_number = await get_car_number(message.from_user.id)
    
    if not car_number:
        await message.answer(
            "❌ Для участия в чате требуется зарегистрировать автомобиль.\n"
            "Используйте команду /start для добавления автомобиля."
        )
        return
    
    # Проверяем, находится ли автомобиль в очереди
    parser = CoddParser()
    car_data = await parser.parse_car_data(car_number)
    
    if not car_data:
        await message.answer(
            f"❌ Ваш автомобиль {car_number} не найден в очереди.\n"
            "В чате могут участвовать только водители из очереди."
        )
        return
    
    # Проверяем, не забанен ли пользователь
    if await is_user_banned(message.from_user.id):
        await message.answer(
            "⛔ Вы временно заблокированы в чате за нарушение правил.\n"
            "Попробуйте снова позже."
        )
        return
    
    # Генерируем анонимный ID
    anonymous_id = await generate_anonymous_id(message.from_user.id)
    
    # Получаем последние сообщения
    messages = await get_recent_messages(20)
    
    # Включаем участие в чате
    await toggle_chat_participation(message.from_user.id, True)
    
    # Количество активных пользователей
    active_users = await get_active_chat_users()
    
    # Формируем сообщение чата
    chat_header = (
        f"💬 <b>Анонимный чат водителей</b>\n\n"
        f"Ваш псевдоним: <b>{anonymous_id}</b>\n"
        f"Позиция в очереди: <b>{car_data['queue_position']}</b>\n"
        f"Активных участников: <b>{len(active_users)}</b>\n\n"
        f"<i>Участники видят только ваш псевдоним и позицию в очереди</i>\n"
        f"<i>Уважайте других участников чата!</i>\n\n"
        f"<b>Последние сообщения:</b>\n"
    )
    
    messages_text = ""
    if not messages:
        messages_text = "В чате пока нет сообщений. Будьте первым!"
    else:
        for msg in messages:
            position_text = f" (#{msg['queue_position']})" if msg['queue_position'] else ""
            messages_text += f"<b>{msg['anonymous_id']}</b>{position_text}:\n{msg['message_text']}\n\n"
    
    # Объединяем сообщение и отправляем с клавиатурой
    await message.answer(
        f"{chat_header}{messages_text}",
        reply_markup=get_chat_keyboard()
    )
    
    # Устанавливаем состояние "в чате"
    await state.set_state(ChatState.in_chat)


async def refresh_chat_callback(callback: CallbackQuery, state: FSMContext):
    """Обновляет содержимое чата."""
    await callback.answer("Обновляем чат...")
    
    # Получаем последние сообщения
    messages = await get_recent_messages(20)
    
    # Количество активных пользователей
    active_users = await get_active_chat_users()
    
    # Получаем данные пользователя
    anonymous_id = await generate_anonymous_id(callback.from_user.id)
    car_number = await get_car_number(callback.from_user.id)
    
    # Позиция в очереди
    queue_position = "?"
    if car_number:
        parser = CoddParser()
        car_data = await parser.parse_car_data(car_number)
        if car_data:
            queue_position = car_data['queue_position']
    
    # Формируем сообщение чата
    chat_header = (
        f"💬 <b>Анонимный чат водителей</b>\n\n"
        f"Ваш псевдоним: <b>{anonymous_id}</b>\n"
        f"Позиция в очереди: <b>{queue_position}</b>\n"
        f"Активных участников: <b>{len(active_users)}</b>\n\n"
        f"<i>Обновлено: только что</i>\n\n"
        f"<b>Последние сообщения:</b>\n"
    )
    
    messages_text = ""
    if not messages:
        messages_text = "В чате пока нет сообщений. Будьте первым!"
    else:
        for msg in messages:
            position_text = f" (#{msg['queue_position']})" if msg['queue_position'] else ""
            messages_text += f"<b>{msg['anonymous_id']}</b>{position_text}:\n{msg['message_text']}\n\n"
    
    # Обновляем сообщение
    await safe_edit_message(
        callback.message,
        f"{chat_header}{messages_text}",
        reply_markup=get_chat_keyboard()
    )


async def send_message_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Написать сообщение'."""
    await callback.answer()
    
    await callback.message.edit_text(
        "✏️ <b>Введите ваше сообщение</b>\n\n"
        "Ваше сообщение будет отправлено в чат анонимно.\n"
        "Другие участники увидят только ваш псевдоним и позицию в очереди.\n\n"
        "<i>Правила чата:</i>\n"
        "- Запрещена нецензурная лексика\n"
        "- Запрещены оскорбления других участников\n"
        "- Запрещена реклама и спам\n"
        "- Запрещено разглашение личных данных\n\n"
        "Для отмены нажмите кнопку 'Отмена'.",
        reply_markup=get_back_to_chat_keyboard()
    )
    
    # Устанавливаем состояние ожидания ввода сообщения
    await state.set_state(ChatState.waiting_for_message)


async def process_chat_message(message: Message, state: FSMContext):
    """Обработчик ввода сообщения для чата."""
    # Проверяем длину сообщения
    if len(message.text) > 500:
        await message.answer(
            "❌ Сообщение слишком длинное. Максимальная длина - 500 символов.\n"
            "Пожалуйста, сократите сообщение."
        )
        return
    
    # Сохраняем сообщение в БД
    media_info = None
    if message.photo:
        # Если есть фото, сохраняем информацию о нем
        photo = message.photo[-1]  # Берем фото с наилучшим качеством
        media_info = {
            'type': 'photo',
            'id': photo.file_id
        }
    
    message_id = await save_chat_message(message.from_user.id, message.text, media_info)
    
    if message_id:
        # Формируем уведомление об успешной отправке
        await message.answer(
            "✅ Ваше сообщение отправлено в чат.\n"
            "Используйте /chat для просмотра всех сообщений."
        )
        
        # Отправляем уведомления другим пользователям чата
        # Получаем необходимые данные для оповещения
        car_number = await get_car_number(message.from_user.id)
        queue_position = None
        
        if car_number:
            parser = CoddParser()
            car_data = await parser.parse_car_data(car_number)
            if car_data:
                queue_position = car_data['queue_position']
        
        # Получаем анонимный ID
        anonymous_id = await generate_anonymous_id(message.from_user.id)
        
        # Формируем данные сообщения
        message_data = {
            'anonymous_id': anonymous_id,
            'message_text': message.text,
            'queue_position': queue_position,
            'has_media': bool(media_info),
            'media_type': media_info.get('type') if media_info else None,
            'media_id': media_info.get('id') if media_info else None
        }
        
        # Асинхронно отправляем уведомления
        import asyncio
        asyncio.create_task(process_chat_notifications(message.bot, message_data, message.from_user.id))
        
        # Возвращаем пользователя в чат
        await cmd_chat(message, state)
    else:
        await message.answer(
            "❌ Произошла ошибка при отправке сообщения.\n"
            "Пожалуйста, попробуйте позже."
        )


async def report_message_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Пожаловаться на сообщение'."""
    await callback.answer()
    
    # Сохраняем текущий контекст
    await state.update_data(messages_view=callback.message.text)
    
    await callback.message.edit_text(
        "⚠️ <b>Жалоба на сообщение</b>\n\n"
        "Укажите номер сообщения, на которое хотите пожаловаться.\n"
        "Номера сообщений отображаются в скобках рядом с никнеймом.\n\n"
        "Введите номер сообщения (только число):",
        reply_markup=get_back_to_chat_keyboard()
    )
    
    # Устанавливаем состояние ожидания ввода номера сообщения
    await state.set_state(ChatState.report_reason)


async def process_report_reason(message: Message, state: FSMContext):
    """Обработчик ввода причины жалобы."""
    try:
        # Пытаемся преобразовать ввод в число
        message_id = int(message.text.strip())
        
        # Сохраняем жалобу
        result = await report_message(message_id, message.from_user.id, "Жалоба от пользователя")
        
        if result:
            await message.answer(
                "✅ Жалоба отправлена. Спасибо за помощь в поддержании порядка в чате."
            )
        else:
            await message.answer(
                "❌ Не удалось найти указанное сообщение или оно уже удалено."
            )
        
        # Получаем сохраненный текст чата
        data = await state.get_data()
        prev_text = data.get('messages_view', '')
        
        # Возвращаем пользователя в чат
        await cmd_chat(message, state)
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный номер сообщения (только цифры)."
        )


async def exit_chat_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Выйти из чата'."""
    await callback.answer()
    
    # Отключаем участие в чате
    await toggle_chat_participation(callback.from_user.id, False)
    
    # Сбрасываем состояние
    await state.clear()
    
    await callback.message.edit_text(
        "👋 Вы вышли из анонимного чата водителей.\n"
        "Для возвращения в чат используйте команду /chat."
    )


async def back_to_chat_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Вернуться в чат'."""
    await callback.answer()
    
    # Возвращаем в чат
    current_state = await state.get_state()
    await state.set_state(ChatState.in_chat)
    
    # Обновляем чат
    await refresh_chat_callback(callback, state)


def get_chat_router() -> Router:
    """Создание роутера для анонимного чата."""
    router = Router()
    
    # Регистрация команд
    router.message.register(cmd_chat, Command("chat"))
    
    # Регистрация обработчиков инлайн-кнопок
    router.callback_query.register(refresh_chat_callback, F.data == "refresh_chat", ChatState.in_chat)
    router.callback_query.register(send_message_callback, F.data == "send_message", ChatState.in_chat)
    router.callback_query.register(report_message_callback, F.data == "report_message", ChatState.in_chat)
    router.callback_query.register(exit_chat_callback, F.data == "exit_chat", ChatState.in_chat)
    router.callback_query.register(back_to_chat_callback, F.data == "back_to_chat")
    
    # Регистрация обработчиков ввода
    router.message.register(process_chat_message, ChatState.waiting_for_message)
    router.message.register(process_report_reason, ChatState.report_reason)
    
    return router 