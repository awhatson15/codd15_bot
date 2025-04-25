from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from database.db import save_user, save_car
from keyboards.inline import get_main_keyboard
from texts import WELCOME_MESSAGE, HELP_TEXT

class CarRegistration(StatesGroup):
    waiting_for_car_number = State()

async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    # Сохраняем информацию о пользователе
    await save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    # Сбрасываем состояние
    await state.finish()
    
    # Отправляем приветственное сообщение и запрашиваем номер авто
    await message.answer(WELCOME_MESSAGE)
    await CarRegistration.waiting_for_car_number.set()
    
    await message.answer("Пожалуйста, введите номер автомобиля в формате P131XM61-AP234015:")

async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(HELP_TEXT)

async def cmd_set_car(message: types.Message, state: FSMContext):
    """Обработчик команды /set_car для изменения номера авто"""
    await state.finish()
    await CarRegistration.waiting_for_car_number.set()
    await message.answer("Пожалуйста, введите новый номер автомобиля в формате P131XM61-AP234015:")

def register_command_handlers(dp: Dispatcher):
    """Регистрация обработчиков команд"""
    dp.register_message_handler(cmd_start, commands=["start"], state="*")
    dp.register_message_handler(cmd_help, commands=["help"], state="*")
    dp.register_message_handler(cmd_set_car, commands=["set_car"], state="*")
    