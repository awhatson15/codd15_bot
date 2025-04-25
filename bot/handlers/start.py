from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from bot.models.database import add_user, update_car_number, get_car_number
from bot.keyboards.keyboards import get_main_menu
from bot.services.parser import CoddParser


class CarNumberState(StatesGroup):
    waiting_for_car_number = State()


async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start."""
    # Сбрасываем предыдущее состояние
    await state.finish()
    
    # Добавляем пользователя в БД
    await add_user(message.from_user.id, message.from_user.username)
    
    # Проверяем, есть ли у пользователя уже введенный номер автомобиля
    current_car_number = await get_car_number(message.from_user.id)
    
    if current_car_number:
        # Если номер уже есть, показываем информацию и спрашиваем, хочет ли пользователь изменить его
        parser = CoddParser()
        car_data = await parser.parse_car_data(current_car_number)
        
        if car_data:
            await message.answer(
                f"👋 Добро пожаловать в бот *ЦОДД Электронная очередь*!\n\n"
                f"У вас уже введен номер автомобиля: `{current_car_number}`\n"
                f"Модель: {car_data['model']}\n"
                f"Ваш номер в очереди: *{car_data['queue_position']}*\n"
                f"Дата регистрации: {car_data['registration_date']}",
                parse_mode="Markdown",
                reply_markup=get_main_menu()
            )
        else:
            # Если номер есть, но данные не найдены
            await message.answer(
                f"👋 Добро пожаловать в бот *ЦОДД Электронная очередь*!\n\n"
                f"У вас уже введен номер автомобиля: `{current_car_number}`\n\n"
                f"❓ Однако информация об этом автомобиле не найдена в очереди.\n"
                f"Возможно, номер указан неверно или автомобиль уже не в очереди.",
                parse_mode="Markdown",
                reply_markup=get_main_menu()
            )
    else:
        # Если номера нет, приветствуем пользователя и запрашиваем номер
        await message.answer(
            "👋 Добро пожаловать в бот *ЦОДД Электронная очередь*!\n\n"
            "Я помогу вам отслеживать позицию вашего автомобиля в электронной очереди ЦОДД.\n\n"
            "Пожалуйста, введите номер вашего автомобиля с прицепом через дефис.\n"
            "Формат: `[гос. номер автомобиля]-[гос. номер прицепа]`\n"
            "Пример: `P131XM61-AP234015`",
            parse_mode="Markdown"
        )
        
        # Устанавливаем состояние ожидания ввода номера
        await CarNumberState.waiting_for_car_number.set()


async def process_car_number(message: types.Message, state: FSMContext):
    """Обработчик ввода номера автомобиля."""
    car_number = message.text.strip()
    
    # Проверка формата номера
    if "-" not in car_number or len(car_number) < 5:
        await message.answer(
            "❌ Неверный формат номера. Введите номер в формате:\n"
            "`[гос. номер автомобиля]-[гос. номер прицепа]`\n"
            "Пример: `P131XM61-AP234015`",
            parse_mode="Markdown"
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
            f"Автомобиль номер: `{car_data['car_number']}`\n"
            f"Модель: {car_data['model']}\n"
            f"Ваш номер в очереди: *{car_data['queue_position']}*\n"
            f"Дата регистрации: {car_data['registration_date']}",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            f"⚠️ Автомобиль с номером `{car_number}` не найден в очереди.\n"
            f"Пожалуйста, проверьте правильность ввода номера или попробуйте позже.",
            parse_mode="Markdown"
        )
        # Оставляем пользователя в состоянии ожидания ввода номера
        return
    
    # Завершаем состояние только если успешно добавили номер
    await state.finish()


def register_start_handlers(dp: Dispatcher):
    """Регистрация обработчиков команды /start."""
    dp.register_message_handler(cmd_start, commands=["start"], state="*")
    dp.register_message_handler(process_car_number, state=CarNumberState.waiting_for_car_number) 