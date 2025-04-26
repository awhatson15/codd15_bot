from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import add_user, update_car_number, get_car_number
from bot.keyboards.keyboards import get_main_menu
from bot.services.parser import CoddParser


class CarNumberState(StatesGroup):
    waiting_for_car_number = State()


async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    # Сбрасываем предыдущее состояние
    await state.clear()
    
    # Добавляем пользователя в БД
    await add_user(message.from_user.id, message.from_user.username)
    
    # Проверяем, есть ли у пользователя уже введенный номер автомобиля
    current_car_number = await get_car_number(message.from_user.id)
    
    if current_car_number:
        # Если номер уже есть, показываем информацию
        parser = CoddParser()
        car_data = await parser.parse_car_data(current_car_number)
        
        if car_data:
            await message.answer(
                f"👋 Добро пожаловать в бот <b>ЦОДД Электронная очередь</b>!\n\n"
                f"У вас уже введен номер автомобиля: <code>{current_car_number}</code>\n"
                f"Модель: {car_data['model']}\n"
                f"Ваш номер в очереди: <b>{car_data['queue_position']}</b>\n"
                f"Дата регистрации: {car_data['registration_date']}",
                reply_markup=get_main_menu()
            )
        else:
            # Если номер есть, но данные не найдены
            await message.answer(
                f"👋 Добро пожаловать в бот <b>ЦОДД Электронная очередь</b>!\n\n"
                f"У вас уже введен номер автомобиля: <code>{current_car_number}</code>\n\n"
                f"❓ Однако информация об этом автомобиле не найдена в очереди.\n"
                f"Возможно, номер указан неверно или автомобиль уже не в очереди.",
                reply_markup=get_main_menu()
            )
    else:
        # Если номера нет, приветствуем пользователя и запрашиваем номер
        await message.answer(
            "👋 Добро пожаловать в бот <b>ЦОДД Электронная очередь</b>!\n\n"
            "Я помогу вам отслеживать позицию вашего автомобиля в электронной очереди ЦОДД.\n\n"
            "Пожалуйста, введите номер вашего автомобиля с прицепом через дефис.\n"
            "Формат: <code>[гос. номер автомобиля]-[гос. номер прицепа]</code>\n"
            "Пример: <code>P131XM61-AP234015</code>"
        )
        
        # Устанавливаем состояние ожидания ввода номера
        await state.set_state(CarNumberState.waiting_for_car_number)


async def process_car_number(message: Message, state: FSMContext):
    """Обработчик ввода номера автомобиля."""
    car_number = message.text.strip()
    
    # Проверка формата номера
    if "-" not in car_number or len(car_number) < 5:
        await message.answer(
            "❌ Неверный формат номера. Введите номер в формате:\n"
            "<code>[гос. номер автомобиля]-[гос. номер прицепа]</code>\n"
            "Пример: <code>P131XM61-AP234015</code>"
        )
        return
    
    # Получаем данные об автомобиле через парсер
    parser = CoddParser()
    car_data = await parser.parse_car_data(car_number)
    
    if car_data:
        # Только если данные получены, обновляем номер автомобиля в БД
        await update_car_number(message.from_user.id, car_number)
        
        await message.answer(
            f"✅ Автомобиль успешно добавлен!\n\n"
            f"Автомобиль номер: <code>{car_data['car_number']}</code>\n"
            f"Модель: {car_data['model']}\n"
            f"Ваш номер в очереди: <b>{car_data['queue_position']}</b>\n"
            f"Дата регистрации: {car_data['registration_date']}",
            reply_markup=get_main_menu()
        )
        
        # Завершаем состояние только если успешно добавили номер
        await state.clear()
    else:
        await message.answer(
            f"⚠️ Автомобиль с номером <code>{car_number}</code> не найден в очереди.\n"
            f"Пожалуйста, проверьте правильность ввода номера или попробуйте позже."
        )
        # Оставляем пользователя в состоянии ожидания ввода номера


def get_start_router() -> Router:
    """Создание роутера для команды /start."""
    router = Router()
    
    # Регистрируем только для команды start и сбрасываем любое состояние
    router.message.register(cmd_start, CommandStart())
    
    # Регистрируем обработчик ввода номера автомобиля только для конкретного состояния
    router.message.register(process_car_number, CarNumberState.waiting_for_car_number)
    
    return router 