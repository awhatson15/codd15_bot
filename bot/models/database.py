import asyncio
import aiosqlite
import os
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple, Union

from bot.config.config import load_config

# Получаем логгер для модуля базы данных
logger = logging.getLogger("database")

# Глобальный кэш соединений
_connection_cache = {}
_connection_lock = asyncio.Lock()


def ensure_db_dir_exists():
    """Убедиться, что директория с базой данных существует."""
    config = load_config()
    db_dir = os.path.dirname(config.database_path)
    os.makedirs(db_dir, exist_ok=True)


async def get_db_connection():
    """Возвращает соединение с базой данных из пула или создает новое."""
    ensure_db_dir_exists()
    config = load_config()
    
    # Использование глобальной переменной для хранения соединений
    global _connection_cache, _connection_lock
    
    # Идентификатор соединения - это путь к БД (в случае если у нас несколько БД)
    connection_id = config.database_path
    
    async with _connection_lock:
        # Проверяем, есть ли активное соединение в кэше
        if connection_id in _connection_cache:
            conn = _connection_cache[connection_id]
            try:
                # Проверяем, работает ли соединение
                await conn.execute("SELECT 1")
                return conn
            except Exception:
                # Соединение больше не работает, удаляем из кэша
                logger.debug("Соединение с БД неактивно, создаю новое")
                del _connection_cache[connection_id]
        
        # Создаем новое соединение
        try:
            conn = await aiosqlite.connect(connection_id)
            _connection_cache[connection_id] = conn
            return conn
        except Exception as e:
            logger.error(f"Ошибка при создании соединения с БД: {e}")
            raise


async def close_all_connections():
    """Закрывает все активные соединения с БД."""
    global _connection_cache, _connection_lock
    
    async with _connection_lock:
        for conn_id, conn in list(_connection_cache.items()):
            try:
                await conn.close()
                logger.debug(f"Соединение с БД {conn_id} закрыто")
            except Exception as e:
                logger.error(f"Ошибка при закрытии соединения с БД {conn_id}: {e}")
            
        _connection_cache.clear()


async def init_db():
    """Инициализация базы данных."""
    ensure_db_dir_exists()
    config = load_config()
    
    # Закрываем все активные соединения перед инициализацией
    await close_all_connections()
    
    logger.info(f"Инициализация БД: {config.database_path}")
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
        
        await db.commit()
        logger.info("БД успешно инициализирована")


async def add_user(user_id: int, username: str = None) -> bool:
    """Добавить нового пользователя."""
    try:
        db = await get_db_connection()
        await db.execute(
            'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
            (user_id, username)
        )
        await db.commit()
        logger.info(f"Пользователь добавлен: user_id={user_id}, username={username}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        return False


async def update_car_number(user_id: int, car_number: str) -> bool:
    """Обновить номер автомобиля пользователя."""
    try:
        db = await get_db_connection()
        await db.execute(
            'UPDATE users SET car_number = ? WHERE user_id = ?',
            (car_number, user_id)
        )
        await db.commit()
        logger.info(f"Обновлен номер автомобиля: user_id={user_id}, car_number={car_number}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении номера автомобиля: {e}")
        return False


async def get_car_number(user_id: int) -> Optional[str]:
    """Получить номер автомобиля пользователя."""
    try:
        db = await get_db_connection()
        async with db.execute(
            'SELECT car_number FROM users WHERE user_id = ?',
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении номера автомобиля: {e}")
        return None


# Алиас для удобства использования
get_user_car = get_car_number


async def setup_notifications(user_id: int, settings: Dict) -> bool:
    """Обновить настройки уведомлений."""
    try:
        # Загружаем конфигурацию для получения значения по умолчанию
        config = load_config()
        default_interval = config.default_notification_interval
        
        db = await get_db_connection()
        
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
                settings.get('interval_minutes', default_interval),
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
                settings.get('interval_minutes', default_interval),
                settings.get('position_change', False),
                settings.get('threshold_change', False),
                settings.get('threshold_value', 10),
                settings.get('enabled', True)
            )
            
        await db.execute(query, params)
        await db.commit()
        logger.info(f"Настройки уведомлений обновлены для user_id={user_id}, settings={settings}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при настройке уведомлений: {e}")
        return False


async def get_notification_settings(user_id: int) -> Optional[Dict]:
    """Получить настройки уведомлений пользователя."""
    try:
        db = await get_db_connection()
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
        logger.error(f"Ошибка при получении настроек уведомлений: {e}")
        return None


async def update_last_notification(user_id: int) -> None:
    """Обновить время последнего уведомления."""
    try:
        db = await get_db_connection()
        await db.execute(
            'UPDATE notification_settings SET last_notification = CURRENT_TIMESTAMP WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()
        logger.debug(f"Обновлено время последнего уведомления для user_id={user_id}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении времени последнего уведомления: {e}")


async def get_users_for_notification() -> List[Tuple[int, str, Dict]]:
    """Получить список пользователей для отправки уведомлений."""
    result = []
    
    try:
        db = await get_db_connection()
        query = """
        SELECT 
            u.user_id, u.car_number, 
            ns.interval_mode, ns.interval_minutes, 
            ns.position_change, ns.threshold_change, 
            ns.threshold_value, ns.enabled, ns.last_notification
        FROM users u
        JOIN notification_settings ns ON u.user_id = ns.user_id
        WHERE u.car_number IS NOT NULL AND ns.enabled = 1
        """
        
        async with db.execute(query) as cursor:
            async for row in cursor:
                user_id, car_number = row[0], row[1]
                settings = {
                    'interval_mode': bool(row[2]),
                    'interval_minutes': int(row[3]),
                    'position_change': bool(row[4]),
                    'threshold_change': bool(row[5]),
                    'threshold_value': int(row[6]),
                    'enabled': bool(row[7]),
                    'last_notification': row[8]
                }
                result.append((user_id, car_number, settings))
        
        logger.debug(f"Получен список из {len(result)} пользователей для уведомлений")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей для уведомлений: {e}")
        return []


async def delete_car_number(user_id: int) -> bool:
    """Удалить номер автомобиля пользователя (очистить поле)."""
    try:
        db = await get_db_connection()
        await db.execute(
            'UPDATE users SET car_number = NULL WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()
        logger.info(f"Удален номер автомобиля для user_id={user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении номера автомобиля: {e}")
        return False 