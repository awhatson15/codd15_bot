import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
import statistics
from typing import Dict, List, Optional, Tuple

from bot.config.config import load_config
from bot.models.database import get_db_connection
from bot.services.parser import CoddParser


class QueueAnalytics:
    def __init__(self):
        self.config = load_config()
        self.logger = logging.getLogger("analytics")
        self.parser = CoddParser()
        
    async def setup(self):
        """Инициализация таблиц БД для аналитики."""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # Создаем таблицы, если они не существуют
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS queue_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    hour INTEGER NOT NULL,
                    queue_length INTEGER NOT NULL,
                    first_position INTEGER,
                    last_position INTEGER,
                    cars_processed INTEGER
                )
            ''')
            
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS queue_velocity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    hour INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    positions_per_hour REAL,
                    cars_processed INTEGER,
                    is_aggregated BOOLEAN DEFAULT 0,
                    UNIQUE(date, hour, is_aggregated)
                )
            ''')
            
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS day_of_week_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day_of_week INTEGER NOT NULL,
                    hour INTEGER NOT NULL,
                    avg_positions_per_hour REAL,
                    min_positions_per_hour REAL,
                    max_positions_per_hour REAL,
                    std_deviation REAL,
                    sample_count INTEGER,
                    last_updated DATETIME,
                    UNIQUE(day_of_week, hour)
                )
            ''')
            
            await conn.commit()
            await cursor.close()
            await conn.close()
            
            self.logger.info("Таблицы для аналитики успешно инициализированы")
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации таблиц аналитики: {e}")
            
    async def record_snapshot(self):
        """Записывает текущий снимок состояния очереди."""
        try:
            current_time = datetime.now()
            day_of_week = current_time.weekday()  # 0-6, пн-вс
            hour = current_time.hour
            
            # Получаем данные о всех автомобилях
            cars_data = await self.parser.parse_all_cars()
            if not cars_data:
                self.logger.warning("Не удалось получить данные о автомобилях для снимка")
                return False
                
            # Анализируем данные
            positions = []
            for car_info in cars_data.values():
                position = car_info.get('queue_position')
                if position and position > 0:
                    positions.append(position)
            
            # Вычисляем метрики
            if not positions:
                self.logger.warning("Нет данных о позициях для снимка")
                return False
                
            queue_length = len(positions)
            first_position = min(positions) if positions else None
            last_position = max(positions) if positions else None
            
            # Получаем предыдущий снимок для вычисления скорости
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # Находим последний снимок
            await cursor.execute('''
                SELECT first_position, timestamp 
                FROM queue_snapshots 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            
            prev_snapshot = await cursor.fetchone()
            cars_processed = None
            
            if prev_snapshot:
                prev_first = prev_snapshot[0]
                prev_time = datetime.fromisoformat(prev_snapshot[1].replace(' ', 'T'))
                
                # Рассчитываем количество обработанных автомобилей
                if prev_first and first_position and prev_first > first_position:
                    cars_processed = prev_first - first_position
                    
                    # Записываем скорость в queue_velocity
                    time_diff = (current_time - prev_time).total_seconds() / 3600  # в часах
                    if time_diff > 0:
                        positions_per_hour = cars_processed / time_diff
                        
                        # Сохраняем данные о скорости
                        await cursor.execute('''
                            INSERT OR REPLACE INTO queue_velocity 
                            (date, hour, day_of_week, positions_per_hour, cars_processed, is_aggregated)
                            VALUES (?, ?, ?, ?, ?, 0)
                        ''', (
                            current_time.date().isoformat(),
                            hour,
                            day_of_week,
                            positions_per_hour,
                            cars_processed
                        ))
            
            # Записываем снимок
            await cursor.execute('''
                INSERT INTO queue_snapshots 
                (timestamp, day_of_week, hour, queue_length, first_position, last_position, cars_processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_time.isoformat(),
                day_of_week,
                hour,
                queue_length,
                first_position,
                last_position,
                cars_processed
            ))
            
            await conn.commit()
            
            # Обновляем агрегированные статистики
            await self.update_day_of_week_stats(day_of_week, hour)
            
            # Удаляем старые данные
            await self.cleanup_old_data()
            
            await cursor.close()  # Закрываем только курсор, но не соединение
            
            self.logger.info(f"Записан снимок очереди: длина={queue_length}, первая позиция={first_position}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при записи снимка очереди: {e}")
            return False
    
    async def update_day_of_week_stats(self, day_of_week: int, hour: int):
        """Обновляет агрегированные статистики по дню недели и часу."""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # Получаем данные о скорости для указанного дня недели и часа за последние 90 дней
            ninety_days_ago = (datetime.now() - timedelta(days=90)).date().isoformat()
            
            await cursor.execute('''
                SELECT positions_per_hour 
                FROM queue_velocity 
                WHERE day_of_week = ? AND hour = ? AND date >= ? AND positions_per_hour > 0
                ORDER BY date DESC
            ''', (day_of_week, hour, ninety_days_ago))
            
            rows = await cursor.fetchall()
            if not rows:
                await cursor.close()
                return
                
            # Преобразуем в список скоростей
            speeds = [row[0] for row in rows]
            
            # Вычисляем статистики
            avg_speed = sum(speeds) / len(speeds)
            min_speed = min(speeds)
            max_speed = max(speeds)
            std_dev = statistics.stdev(speeds) if len(speeds) > 1 else 0
            
            # Обновляем запись в day_of_week_stats
            await cursor.execute('''
                INSERT OR REPLACE INTO day_of_week_stats 
                (day_of_week, hour, avg_positions_per_hour, min_positions_per_hour, 
                max_positions_per_hour, std_deviation, sample_count, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                day_of_week,
                hour,
                avg_speed,
                min_speed,
                max_speed,
                std_dev,
                len(speeds),
                datetime.now().isoformat()
            ))
            
            await conn.commit()
            await cursor.close()
            
            self.logger.info(f"Обновлена статистика для дня {day_of_week}, часа {hour}: "
                            f"avg={avg_speed:.2f}, samples={len(speeds)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении статистики дня недели: {e}")
    
    async def cleanup_old_data(self):
        """Удаляет устаревшие данные из БД."""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            # Удаляем снимки старше 90 дней
            ninety_days_ago = (datetime.now() - timedelta(days=90)).isoformat()
            
            await cursor.execute('''
                DELETE FROM queue_snapshots WHERE timestamp < ?
            ''', (ninety_days_ago,))
            
            # Агрегируем старые данные о скорости (старше 30 дней) по дням недели и часам
            thirty_days_ago = (datetime.now() - timedelta(days=30)).date().isoformat()
            
            # Проверяем, есть ли неагрегированные данные старше 30 дней
            await cursor.execute('''
                SELECT COUNT(*) FROM queue_velocity 
                WHERE date < ? AND is_aggregated = 0
            ''', (thirty_days_ago,))
            
            count = (await cursor.fetchone())[0]
            
            if count > 0:
                # Агрегируем данные по дням недели и часам
                await cursor.execute('''
                    INSERT OR REPLACE INTO queue_velocity 
                    (date, hour, day_of_week, positions_per_hour, cars_processed, is_aggregated)
                    SELECT 
                        date(date, 'start of month') as month_start,
                        hour,
                        day_of_week,
                        AVG(positions_per_hour) as avg_speed,
                        SUM(cars_processed) as total_cars,
                        1 as is_aggregated
                    FROM queue_velocity
                    WHERE date < ? AND is_aggregated = 0
                    GROUP BY month_start, hour, day_of_week
                ''', (thirty_days_ago,))
                
                # Удаляем исходные данные, которые были агрегированы
                await cursor.execute('''
                    DELETE FROM queue_velocity 
                    WHERE date < ? AND is_aggregated = 0
                ''', (thirty_days_ago,))
                
                self.logger.info(f"Агрегировано {count} старых записей о скорости")
            
            await conn.commit()
            await cursor.close()
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке старых данных: {e}")
    
    async def get_average_velocity(self, day_of_week: Optional[int] = None, 
                                 hour: Optional[int] = None) -> float:
        """Возвращает среднюю скорость движения очереди для указанного времени."""
        try:
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            query = '''
                SELECT avg_positions_per_hour
                FROM day_of_week_stats
                WHERE 1=1
            '''
            params = []
            
            if day_of_week is not None:
                query += " AND day_of_week = ?"
                params.append(day_of_week)
                
            if hour is not None:
                query += " AND hour = ?"
                params.append(hour)
            
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            
            await cursor.close()
            
            if not rows:
                return 0.0
                
            # Если запрошены все часы или дни, находим среднее
            speeds = [row[0] for row in rows]
            return sum(speeds) / len(speeds)
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении средней скорости: {e}")
            return 0.0
    
    async def predict_waiting_time(self, current_position: int) -> Dict:
        """Предсказывает время ожидания для указанной позиции."""
        try:
            # Получаем текущее время
            now = datetime.now()
            day_of_week = now.weekday()
            hour = now.hour
            
            # Получаем среднюю скорость для текущего времени
            avg_speed = await self.get_average_velocity(day_of_week, hour)
            if avg_speed <= 0:
                # Если нет данных для текущего часа, берем среднее за все время
                avg_speed = await self.get_average_velocity()
            
            # Если все еще нет данных, используем значение по умолчанию
            if avg_speed <= 0:
                avg_speed = 5.0  # предполагаем 5 позиций в час
            
            # Вычисляем примерное время ожидания в часах
            waiting_hours = current_position / avg_speed
            
            # Получаем стандартное отклонение для оценки доверительного интервала
            conn = await get_db_connection()
            cursor = await conn.cursor()
            
            await cursor.execute('''
                SELECT std_deviation
                FROM day_of_week_stats
                WHERE day_of_week = ? AND hour = ?
            ''', (day_of_week, hour))
            
            row = await cursor.fetchone()
            std_dev = row[0] if row else 0
            
            await cursor.close()
            
            # Вычисляем оптимистичный и пессимистичный прогнозы
            # Используем скорость +/- 1 стандартное отклонение
            optimistic_speed = avg_speed + std_dev
            pessimistic_speed = max(0.1, avg_speed - std_dev)  # не менее 0.1 поз/час
            
            optimistic_hours = current_position / optimistic_speed if optimistic_speed > 0 else float('inf')
            pessimistic_hours = current_position / pessimistic_speed if pessimistic_speed > 0 else float('inf')
            
            # Форматируем результат
            return {
                'expected_hours': round(waiting_hours, 1),
                'min_hours': round(optimistic_hours, 1),
                'max_hours': round(pessimistic_hours, 1),
                'expected_date': (now + timedelta(hours=waiting_hours)).isoformat(),
                'speed': round(avg_speed, 2),
                'position': current_position
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при прогнозировании времени ожидания: {e}")
            return {
                'expected_hours': 0,
                'min_hours': 0,
                'max_hours': 0,
                'expected_date': now.isoformat(),
                'error': str(e)
            }
    
    async def close(self):
        """Освобождает ресурсы сервиса аналитики."""
        self.logger.info("Закрытие сервиса аналитики")
        if hasattr(self.parser, 'close'):
            await self.parser.close()
        self.logger.info("Сервис аналитики остановлен")

async def start_analytics_service():
    """Запуск сервиса аналитики."""
    analytics_service = QueueAnalytics()
    await analytics_service.setup()
    return analytics_service 