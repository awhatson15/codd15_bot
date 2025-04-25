import aiosqlite
import logging
import os
from datetime import datetime

from config import DB_PATH

logger = logging.getLogger(__name__)

async def init_db():
    """Инициализация базы данных"""
    # Создаем директорию для БД, если она не существует
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица автомобилей пользователей
        await db.execute('''
        CREATE TABLE IF NOT EXISTS user_cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            car_number TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE (user_id, car_number)
        )
        ''')
        
        # Таблица настроек уведомлений
        await db.execute('''
        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            car_id INTEGER,
            interval_mode INTEGER DEFAULT 0,  -- 0 - выключено, >0 - интервал в минутах
            position_change INTEGER DEFAULT 0, -- 0 - выключено, 1 - включено
            shift_threshold INTEGER DEFAULT 0, -- 0 - выключено, >0 - порог сдвига
            last_notification TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (car_id) REFERENCES user_cars (id)
        )
        ''')
        
        # Таблица истории очереди
        await db.execute('''
        CREATE TABLE IF NOT EXISTS queue_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_number TEXT NOT NULL,
            queue_position INTEGER,
            model TEXT,
            reg_date TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        await db.commit()
        logger.info("База данных инициализирована")

async def save_user(user_id, username, first_name, last_name):
    """Сохранение пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, last_name)
        )
        await db.commit()

async def save_car(user_id, car_number):
    """Сохранение автомобиля пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, есть ли уже такой автомобиль у пользователя
        cursor = await db.execute(
            "SELECT id FROM user_cars WHERE user_id = ? AND car_number = ?",
            (user_id, car_number)
        )
        car = await cursor.fetchone()
        
        if car:
            # Обновляем существующую запись
            await db.execute(
                "UPDATE user_cars SET updated_at = ? WHERE id = ?",
                (datetime.now(), car[0])
            )
            car_id = car[0]
        else:
            # Создаем новую запись
            cursor = await db.execute(
                "INSERT INTO user_cars (user_id, car_number) VALUES (?, ?)",
                (user_id, car_number)
            )
            car_id = cursor.lastrowid
            
            # Создаем настройки уведомлений по умолчанию
            from config import DEFAULT_NOTIFICATION_INTERVAL
            await db.execute(
                """INSERT INTO notification_settings 
                   (user_id, car_id, interval_mode, position_change, shift_threshold) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, car_id, DEFAULT_NOTIFICATION_INTERVAL, 0, 0)
            )
        
        await db.commit()
        return car_id

async def get_car_info(user_id):
    """Получение информации об автомобиле пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT uc.id, uc.car_number 
               FROM user_cars uc
               WHERE uc.user_id = ?
               ORDER BY uc.updated_at DESC
               LIMIT 1""",
            (user_id,)
        )
        return await cursor.fetchone()

async def update_notification_settings(user_id, car_id, setting_type, value):
    """Обновление настроек уведомлений"""
    async with aiosqlite.connect(DB_PATH) as db:
        if setting_type == "interval":
            await db.execute(
                """UPDATE notification_settings 
                   SET interval_mode = ?, updated_at = ?
                   WHERE user_id = ? AND car_id = ?""",
                (value, datetime.now(), user_id, car_id)
            )
        elif setting_type == "position":
            await db.execute(
                """UPDATE notification_settings 
                   SET position_change = ?, updated_at = ?
                   WHERE user_id = ? AND car_id = ?""",
                (value, datetime.now(), user_id, car_id)
            )
        elif setting_type == "shift":
            await db.execute(
                """UPDATE notification_settings 
                   SET shift_threshold = ?, updated_at = ?
                   WHERE user_id = ? AND car_id = ?""",
                (value, datetime.now(), user_id, car_id)
            )
        
        await db.commit()

async def get_notification_settings(user_id, car_id):
    """Получение настроек уведомлений"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT interval_mode, position_change, shift_threshold, last_notification
               FROM notification_settings
               WHERE user_id = ? AND car_id = ?""",
            (user_id, car_id)
        )
        return await cursor.fetchone()

async def update_last_notification(user_id, car_id):
    """Обновление времени последнего уведомления"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE notification_settings 
               SET last_notification = ?
               WHERE user_id = ? AND car_id = ?""",
            (datetime.now(), user_id, car_id)
        )
        await db.commit()

async def get_cars_for_notification():
    """Получение списка автомобилей для уведомления"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем все машины с активными уведомлениями
        cursor = await db.execute(
            """SELECT u.user_id, uc.id, uc.car_number, ns.interval_mode, 
                     ns.position_change, ns.shift_threshold, ns.last_notification
               FROM user_cars uc
               JOIN users u ON uc.user_id = u.user_id
               JOIN notification_settings ns ON uc.id = ns.car_id AND uc.user_id = ns.user_id
               WHERE ns.interval_mode > 0 OR ns.position_change = 1 OR ns.shift_threshold > 0"""
        )
        
        return await cursor.fetchall()

async def save_queue_data(car_number, queue_position, model, reg_date):
    """Сохранение данных об очереди"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO queue_history 
               (car_number, queue_position, model, reg_date) 
               VALUES (?, ?, ?, ?)""",
            (car_number, queue_position, model, reg_date)
        )
        await db.commit()

async def get_last_queue_data(car_number):
    """Получение последних данных об очереди для автомобиля"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT queue_position, model, reg_date, timestamp
               FROM queue_history
               WHERE car_number = ?
               ORDER BY timestamp DESC
               LIMIT 1""",
            (car_number,)
        )
        return await cursor.fetchone()

async def get_previous_queue_data(car_number):
    """Получение предпоследних данных об очереди для автомобиля"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT queue_position, model, reg_date, timestamp
               FROM queue_history
               WHERE car_number = ?
               ORDER BY timestamp DESC
               LIMIT 1 OFFSET 1""",
            (car_number,)
        )
        return await cursor.fetchone()

async def disable_all_notifications(user_id, car_id):
    """Отключение всех уведомлений"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE notification_settings 
               SET interval_mode = 0, position_change = 0, shift_threshold = 0, updated_at = ?
               WHERE user_id = ? AND car_id = ?""",
            (datetime.now(), user_id, car_id)
        )
        await db.commit()
        