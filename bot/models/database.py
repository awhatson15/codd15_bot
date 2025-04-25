import asyncio
import aiosqlite
import os
import sqlite3
from typing import Dict, List, Optional, Tuple, Union

from bot.config.config import load_config


def ensure_db_dir_exists():
    """Убедиться, что директория с базой данных существует."""
    config = load_config()
    db_dir = os.path.dirname(config.database_path)
    os.makedirs(db_dir, exist_ok=True)


async def init_db():
    """Инициализация базы данных."""
    ensure_db_dir_exists()
    config = load_config()
    
    async with aiosqlite.connect(config.database_path) as db:
        # Таблица пользователей
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            car_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица настроек уведомлений
        await db.execute('''
        CREATE TABLE IF NOT EXISTS notification_settings (
            user_id INTEGER PRIMARY KEY,
            interval_mode BOOLEAN DEFAULT FALSE,
            interval_minutes INTEGER DEFAULT 2,
            position_change BOOLEAN DEFAULT FALSE,
            threshold_change BOOLEAN DEFAULT FALSE,
            threshold_value INTEGER DEFAULT 10,
            enabled BOOLEAN DEFAULT TRUE,
            last_notification TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        # Таблица с данными об автомобилях в очереди
        await db.execute('''
        CREATE TABLE IF NOT EXISTS queue_data (
            car_number TEXT PRIMARY KEY,
            model TEXT,
            queue_position INTEGER,
            registration_date TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица истории очереди
        await db.execute('''
        CREATE TABLE IF NOT EXISTS queue_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_number TEXT,
            queue_position INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (car_number) REFERENCES queue_data(car_number)
        )
        ''')
        
        await db.commit()


async def add_user(user_id: int, username: str = None) -> bool:
    """Добавить нового пользователя."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            await db.execute(
                'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                (user_id, username)
            )
            await db.commit()
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False


async def update_car_number(user_id: int, car_number: str) -> bool:
    """Обновить номер автомобиля пользователя."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            await db.execute(
                'UPDATE users SET car_number = ? WHERE user_id = ?',
                (car_number, user_id)
            )
            await db.commit()
        return True
    except Exception as e:
        print(f"Error updating car number: {e}")
        return False


async def get_car_number(user_id: int) -> Optional[str]:
    """Получить номер автомобиля пользователя."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            async with db.execute(
                'SELECT car_number FROM users WHERE user_id = ?',
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None
    except Exception as e:
        print(f"Error getting car number: {e}")
        return None


async def setup_notifications(user_id: int, settings: Dict) -> bool:
    """Обновить настройки уведомлений."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            # Проверяем, существует ли запись
            async with db.execute(
                'SELECT 1 FROM notification_settings WHERE user_id = ?',
                (user_id,)
            ) as cursor:
                exists = await cursor.fetchone()
            
            if exists:
                # Обновляем существующую запись
                query = """
                UPDATE notification_settings SET 
                    interval_mode = ?,
                    interval_minutes = ?,
                    position_change = ?,
                    threshold_change = ?,
                    threshold_value = ?,
                    enabled = ?
                WHERE user_id = ?
                """
                params = (
                    settings.get('interval_mode', False),
                    settings.get('interval_minutes', config.default_notification_interval),
                    settings.get('position_change', False),
                    settings.get('threshold_change', False),
                    settings.get('threshold_value', 10),
                    settings.get('enabled', True),
                    user_id
                )
            else:
                # Создаем новую запись
                query = """
                INSERT INTO notification_settings (
                    user_id, interval_mode, interval_minutes, 
                    position_change, threshold_change, threshold_value, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    user_id,
                    settings.get('interval_mode', False),
                    settings.get('interval_minutes', config.default_notification_interval),
                    settings.get('position_change', False),
                    settings.get('threshold_change', False),
                    settings.get('threshold_value', 10),
                    settings.get('enabled', True)
                )
                
            await db.execute(query, params)
            await db.commit()
            return True
    except Exception as e:
        print(f"Error setting up notifications: {e}")
        return False


async def get_notification_settings(user_id: int) -> Optional[Dict]:
    """Получить настройки уведомлений пользователя."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            async with db.execute(
                '''SELECT 
                    interval_mode, interval_minutes, position_change, 
                    threshold_change, threshold_value, enabled, last_notification
                FROM notification_settings WHERE user_id = ?''',
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                
                if not result:
                    return None
                    
                return {
                    'interval_mode': bool(result[0]),
                    'interval_minutes': int(result[1]),
                    'position_change': bool(result[2]),
                    'threshold_change': bool(result[3]),
                    'threshold_value': int(result[4]),
                    'enabled': bool(result[5]),
                    'last_notification': result[6]
                }
    except Exception as e:
        print(f"Error getting notification settings: {e}")
        return None


async def update_queue_data(car_data: Dict[str, Dict]) -> bool:
    """Обновить данные об очереди."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            for car_number, data in car_data.items():
                # Проверяем, есть ли изменения в очереди
                async with db.execute(
                    'SELECT queue_position FROM queue_data WHERE car_number = ?',
                    (car_number,)
                ) as cursor:
                    result = await cursor.fetchone()
                    old_position = result[0] if result else None
                
                # Обновляем данные об автомобиле
                await db.execute(
                    '''INSERT OR REPLACE INTO queue_data 
                       (car_number, model, queue_position, registration_date, last_updated) 
                       VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                    (car_number, data['model'], data['queue_position'], data['registration_date'])
                )
                
                # Сохраняем историю изменений позиции, если она изменилась
                if old_position is None or old_position != data['queue_position']:
                    await db.execute(
                        'INSERT INTO queue_history (car_number, queue_position) VALUES (?, ?)',
                        (car_number, data['queue_position'])
                    )
            
            await db.commit()
            return True
    except Exception as e:
        print(f"Error updating queue data: {e}")
        return False


async def get_car_data(car_number: str) -> Optional[Dict]:
    """Получить данные об автомобиле."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            async with db.execute(
                '''SELECT model, queue_position, registration_date 
                   FROM queue_data WHERE car_number = ?''',
                (car_number,)
            ) as cursor:
                result = await cursor.fetchone()
                
                if not result:
                    return None
                    
                return {
                    'car_number': car_number,
                    'model': result[0],
                    'queue_position': result[1],
                    'registration_date': result[2]
                }
    except Exception as e:
        print(f"Error getting car data: {e}")
        return None


async def get_users_for_notification() -> List[Tuple[int, str, Dict]]:
    """Получить список пользователей для отправки уведомлений."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            query = """
            SELECT 
                u.user_id, 
                u.car_number, 
                ns.interval_mode, 
                ns.interval_minutes, 
                ns.position_change, 
                ns.threshold_change, 
                ns.threshold_value, 
                ns.last_notification
            FROM users u
            JOIN notification_settings ns ON u.user_id = ns.user_id
            WHERE ns.enabled = 1 AND u.car_number IS NOT NULL
            """
            
            async with db.execute(query) as cursor:
                users = []
                async for row in cursor:
                    user_id, car_number = row[0], row[1]
                    settings = {
                        'interval_mode': bool(row[2]),
                        'interval_minutes': int(row[3]),
                        'position_change': bool(row[4]),
                        'threshold_change': bool(row[5]),
                        'threshold_value': int(row[6]),
                        'last_notification': row[7]
                    }
                    users.append((user_id, car_number, settings))
                return users
    except Exception as e:
        print(f"Error getting users for notification: {e}")
        return []
        

async def update_last_notification(user_id: int) -> None:
    """Обновить время последнего уведомления."""
    config = load_config()
    
    try:
        async with aiosqlite.connect(config.database_path) as db:
            await db.execute(
                'UPDATE notification_settings SET last_notification = CURRENT_TIMESTAMP WHERE user_id = ?',
                (user_id,)
            )
            await db.commit()
    except Exception as e:
        print(f"Error updating last notification: {e}") 