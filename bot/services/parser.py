import asyncio
import logging
import re
import json
import time
import os
from datetime import datetime
from typing import Dict, Optional, List
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor

import aiohttp
import requests
from bs4 import BeautifulSoup

from bot.config.config import load_config


# Настройка отдельного логгера для парсера
def setup_parser_logger():
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Получаем логгер
        parser_logger = logging.getLogger("parser")
        
        # Проверяем, не настроен ли он уже (чтобы избежать дублирования)
        if not parser_logger.handlers:
            # Определяем уровень логирования
            log_level = getattr(logging, config.log_level, logging.INFO)
            if config.debug_mode:
                log_level = logging.DEBUG
                
            parser_logger.setLevel(log_level)
            
            # Используем только консольный вывод для надежности
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)
            parser_logger.addHandler(console_handler)
            
        return parser_logger
    except Exception as e:
        # Если что-то пошло не так, создаем базовый логгер без файлового вывода
        print(f"ERROR: Failed to setup logger: {e}. Using basic configuration.")
        basic_logger = logging.getLogger("parser")
        basic_logger.setLevel(logging.INFO)
        
        if not basic_logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)
            basic_logger.addHandler(console_handler)
        
        return basic_logger


# Инициализируем логгер парсера
parser_logger = setup_parser_logger()


class CoddParser:
    def __init__(self):
        self.config = load_config()
        self.base_url = self.config.codd_url
        self.logger = parser_logger
        # Создаем пул потоков для выполнения синхронных операций
        self.thread_pool = ThreadPoolExecutor(max_workers=5)  # Максимум 5 потоков
    
    async def parse_car_data(self, car_number: str) -> Optional[Dict]:
        """Парсинг данных об автомобиле по его номеру."""
        try:
            self.logger.info(f"Начинаем поиск автомобиля с номером: {car_number}")
            
            # Нормализуем номер авто для поиска
            normalized_car_number = self._normalize_car_number(car_number)
            self.logger.info(f"Нормализованный номер для поиска: {normalized_car_number}")
            
            # Получаем данные напрямую со страницы
            car_data = await self._get_car_data_from_page(normalized_car_number)
            
            if car_data:
                self.logger.info(f"Успешно получены данные для автомобиля {car_number}, позиция: {car_data.get('queue_position', 'не указана')}")
                return {
                    'car_number': car_number,
                    'model': car_data.get('model', 'Не указано'),
                    'queue_position': car_data.get('queue_position', 0),
                    'registration_date': car_data.get('registration_date', 'Не указано')
                }
            
            self.logger.info(f"Автомобиль с номером {car_number} не найден в очереди")
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге данных: {e}")
            self.logger.exception("Стек ошибки:")
            return None
    
    async def _get_car_data_from_page(self, normalized_car_number: str) -> Optional[Dict]:
        """Получение данных об автомобиле напрямую со страницы."""
        try:
            # Используем ThreadPoolExecutor для получения полной страницы с JS-данными
            future = self.thread_pool.submit(self._get_full_page)
            html = await asyncio.wrap_future(future)
            
            if not html:
                self.logger.error("Не удалось получить HTML страницы")
                return None
            
            # Сохраним HTML для анализа только в режиме отладки
            if self.config.debug_mode:
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(html)
                self.logger.info("HTML страницы сохранен в debug_page.html")
            
            # Разбор HTML
            soup = BeautifulSoup(html, 'lxml')
            
            # Сначала ищем JavaScript данные, так как они могут содержать полный список
            car_data = self._extract_data_from_javascript(soup, normalized_car_number)
            if car_data:
                return car_data
            
            # Если не нашли в JS, ищем в таблицах
            car_data = self._extract_data_from_tables(soup, normalized_car_number)
            if car_data:
                return car_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении данных со страницы: {e}")
            return None
    
    def _extract_data_from_javascript(self, soup, normalized_car_number: str) -> Optional[Dict]:
        """Извлечение данных из JavaScript кода на странице."""
        try:
            scripts = soup.find_all('script')
            self.logger.info(f"Найдено {len(scripts)} скриптов на странице")
            
            for i, script in enumerate(scripts):
                if script.string:
                    script_text = script.string
                    self.logger.debug(f"Анализ скрипта {i+1}, длина: {len(script_text)} символов")
                    
                    # Ищем массив данных в JavaScript
                    js_patterns = [
                        r'var\s+queueData\s*=\s*(\[.*?\])\s*;',
                        r'var\s+cars\s*=\s*(\[.*?\])\s*;',
                        r'var\s+queue\s*=\s*(\[.*?\])\s*;',
                        r'var\s+data\s*=\s*(\[.*?\])\s*;',
                        r'data\s*:\s*(\[.*?\])',
                        r'JSON\.parse\(\'(\[.*?\])\'\)'
                    ]
                    
                    for pattern in js_patterns:
                        matches = re.search(pattern, script_text, re.DOTALL)
                        if matches:
                            try:
                                data = json.loads(matches.group(1))
                                self.logger.info(f"Найден массив данных в JavaScript, элементов: {len(data)}")
                                
                                # Сохраняем данные для отладки только в режиме отладки
                                if self.config.debug_mode:
                                    with open("debug_js_data.json", "w", encoding="utf-8") as f:
                                        json.dump(data, f, ensure_ascii=False, indent=2)
                                
                                # Перебираем элементы массива и ищем нужный номер
                                for item in data:
                                    # Проверяем различные возможные ключи
                                    car_keys = ['carNumber', 'carnumber', 'car_number', 'number', 'номер']
                                    for key in car_keys:
                                        if key in item and self._normalize_car_number(str(item[key])) == normalized_car_number:
                                            # Найден нужный автомобиль
                                            self.logger.info(f"Найден автомобиль в JS данных: {item}")
                                            
                                            # Определяем ключи для извлечения данных
                                            model_keys = ['model', 'марка', 'car_model']
                                            position_keys = ['position', 'queue_position', 'pos', 'позиция']
                                            date_keys = ['date', 'registration_date', 'reg_date', 'дата']
                                            
                                            # Извлекаем данные
                                            model = None
                                            for k in model_keys:
                                                if k in item:
                                                    model = item[k]
                                                    break
                                            
                                            position = None
                                            for k in position_keys:
                                                if k in item:
                                                    position = item[k]
                                                    break
                                            
                                            reg_date = None
                                            for k in date_keys:
                                                if k in item:
                                                    reg_date = item[k]
                                                    break
                                            
                                            return {
                                                'model': model or 'Не указано',
                                                'queue_position': int(position) if position else 0,
                                                'registration_date': reg_date or 'Не указано'
                                            }
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Ошибка декодирования JSON из JavaScript: {e}")
            
            return None
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении данных из JavaScript: {e}")
            return None
    
    def _extract_data_from_tables(self, soup, normalized_car_number: str) -> Optional[Dict]:
        """Извлечение данных из таблиц на странице."""
        try:
            tables = soup.find_all('table')
            self.logger.info(f"Найдено {len(tables)} таблиц на странице")
            
            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                self.logger.info(f"Таблица {table_idx+1} содержит {len(rows)} строк")
                
                # Сохраним содержимое таблицы для отладки только в режиме отладки
                if self.config.debug_mode:
                    with open(f"debug_table_{table_idx+1}.txt", "w", encoding="utf-8") as f:
                        for row_idx, row in enumerate(rows):
                            cells = row.find_all(['td', 'th'])
                            cell_texts = [cell.text.strip() for cell in cells]
                            f.write(f"Строка {row_idx+1}: {' | '.join(cell_texts)}\n")
                
                # Анализируем каждую строку таблицы
                for row_idx, row in enumerate(rows):
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue  # Пропускаем строки с недостаточным количеством ячеек
                    
                    # Ищем ячейку с номером автомобиля
                    for cell_idx, cell in enumerate(cells):
                        cell_text = cell.text.strip()
                        if self._normalize_car_number(cell_text) == normalized_car_number:
                            self.logger.info(f"Найден автомобиль в таблице {table_idx+1}, строка {row_idx+1}, ячейка {cell_idx+1}")
                            
                            # Пытаемся определить, какие ячейки содержат нужную информацию
                            position = None
                            model = None
                            reg_date = None
                            
                            # Если это таблица с заголовками, используем их
                            headers = [th.text.strip().lower() for th in table.find_all('th')]
                            if headers:
                                for i, header in enumerate(headers):
                                    if i < len(cells):
                                        if any(word in header for word in ['позиция', 'position', 'место', 'очередь']):
                                            position = cells[i].text.strip()
                                        elif any(word in header for word in ['модель', 'model', 'марка']):
                                            model = cells[i].text.strip()
                                        elif any(word in header for word in ['дата', 'date', 'регистрация']):
                                            reg_date = cells[i].text.strip()
                            
                            # Если не определили по заголовкам, ищем по логике расположения
                            if position is None and len(cells) > 0:
                                try:
                                    # Обычно позиция - это первая колонка
                                    position = cells[0].text.strip()
                                except IndexError:
                                    pass
                            
                            if model is None and len(cells) > 2:
                                try:
                                    # Модель обычно после номера
                                    model = cells[cell_idx + 1].text.strip() if cell_idx + 1 < len(cells) else None
                                except IndexError:
                                    pass
                            
                            if reg_date is None and len(cells) > 3:
                                try:
                                    # Дата обычно последняя колонка
                                    reg_date = cells[-1].text.strip()
                                except IndexError:
                                    pass
                            
                            return {
                                'model': model or 'Не указано',
                                'queue_position': int(position) if position and position.isdigit() else 0,
                                'registration_date': reg_date or 'Не указано'
                            }
            
            return None
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении данных из таблиц: {e}")
            return None
    
    def _get_full_page(self) -> str:
        """Получение полной страницы с помощью обычного requests."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
            }
            
            # Проверка на HTTPS и включение проверки сертификатов
            verify_ssl = True
            if self.base_url.startswith('https://'):
                self.logger.debug("Используется HTTPS-соединение с проверкой сертификатов")
            else:
                self.logger.debug("Используется HTTP-соединение")
            
            # Выполняем запрос с проверкой сертификата для HTTPS
            response = requests.get(
                self.base_url,
                headers=headers,
                verify=verify_ssl,  # Обязательная проверка сертификатов
                timeout=30  # Устанавливаем таймаут для предотвращения зависания
            )
            
            if response.status_code == 200:
                self.logger.info(f"Успешно получена страница, размер HTML: {len(response.text)} байт")
                return response.text
            else:
                self.logger.error(f"Ошибка при получении страницы, код: {response.status_code}")
                return ""
        except requests.exceptions.SSLError as e:
            self.logger.error(f"Ошибка SSL при получении страницы: {e}")
            return ""
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Таймаут при получении страницы: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"Ошибка при получении полной страницы: {e}")
            return ""
    
    async def parse_all_cars(self) -> Dict[str, Dict]:
        """Парсинг данных о всех автомобилях в очереди."""
        try:
            # Получаем данные напрямую со страницы
            cars_data = await self._get_all_cars_from_page()
            
            if cars_data:
                self.logger.info(f"Получены данные о {len(cars_data)} автомобилях")
                return cars_data
            else:
                self.logger.warning("Не удалось получить данные об автомобилях")
                return {}
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге всех автомобилей: {e}")
            return {}
    
    async def _get_all_cars_from_page(self) -> Dict[str, Dict]:
        """Получение всех автомобилей напрямую со страницы."""
        try:
            # Используем ThreadPoolExecutor для получения полной страницы с JS-данными
            future = self.thread_pool.submit(self._get_full_page)
            html = await asyncio.wrap_future(future)
            
            if not html:
                return {}
            
            soup = BeautifulSoup(html, 'lxml')
            cars_data = {}
            
            # Ищем JavaScript данные
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    script_text = script.string
                    js_patterns = [
                        r'var\s+queueData\s*=\s*(\[.*?\])\s*;',
                        r'var\s+cars\s*=\s*(\[.*?\])\s*;',
                        r'var\s+queue\s*=\s*(\[.*?\])\s*;',
                        r'var\s+data\s*=\s*(\[.*?\])\s*;',
                        r'data\s*:\s*(\[.*?\])',
                        r'JSON\.parse\(\'(\[.*?\])\'\)'
                    ]
                    
                    for pattern in js_patterns:
                        matches = re.search(pattern, script_text, re.DOTALL)
                        if matches:
                            try:
                                data = json.loads(matches.group(1))
                                self.logger.info(f"Найден массив данных в JavaScript, элементов: {len(data)}")
                                
                                # Перебираем элементы массива
                                for item in data:
                                    # Проверяем различные возможные ключи для номера автомобиля
                                    car_keys = ['carNumber', 'carnumber', 'car_number', 'number', 'номер']
                                    model_keys = ['model', 'марка', 'car_model']
                                    position_keys = ['position', 'queue_position', 'pos', 'позиция']
                                    date_keys = ['date', 'registration_date', 'reg_date', 'дата']
                                    
                                    car_number = None
                                    for key in car_keys:
                                        if key in item:
                                            car_number = str(item[key])
                                            break
                                    
                                    if car_number:
                                        # Определяем остальные данные
                                        model = None
                                        for k in model_keys:
                                            if k in item:
                                                model = item[k]
                                                break
                                        
                                        position = None
                                        for k in position_keys:
                                            if k in item:
                                                position = item[k]
                                                break
                                        
                                        reg_date = None
                                        for k in date_keys:
                                            if k in item:
                                                reg_date = item[k]
                                                break
                                        
                                        cars_data[car_number] = {
                                            'model': model or 'Не указано',
                                            'queue_position': int(position) if position and str(position).isdigit() else 0,
                                            'registration_date': reg_date or 'Не указано'
                                        }
                                
                                if cars_data:
                                    self.logger.info(f"Получены данные о {len(cars_data)} автомобилях из JavaScript")
                                    return cars_data
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Ошибка декодирования JSON из JavaScript: {e}")
            
            # Если в JavaScript ничего не нашли, ищем в таблицах
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                # Пытаемся определить, какие колонки за что отвечают
                headers = [th.text.strip().lower() for th in table.find_all('th')]
                
                position_idx = None
                car_num_idx = None
                model_idx = None
                date_idx = None
                
                # Определяем индексы колонок по заголовкам
                if headers:
                    for i, header in enumerate(headers):
                        if any(word in header for word in ['позиция', 'position', 'место', 'очередь']):
                            position_idx = i
                        elif any(word in header for word in ['номер', 'number', 'автомобиль']):
                            car_num_idx = i
                        elif any(word in header for word in ['модель', 'model', 'марка']):
                            model_idx = i
                        elif any(word in header for word in ['дата', 'date', 'регистрация']):
                            date_idx = i
                
                # Если не определили индексы, предполагаем стандартный порядок
                if position_idx is None:
                    position_idx = 0
                if car_num_idx is None:
                    car_num_idx = 1
                if model_idx is None:
                    model_idx = 2
                if date_idx is None:
                    date_idx = 3
                
                # Пропускаем заголовки
                for row in rows[1:] if headers else rows:
                    cells = row.find_all('td')
                    if len(cells) > max(position_idx, car_num_idx, model_idx, date_idx):
                        try:
                            car_number = cells[car_num_idx].text.strip()
                            if car_number:
                                position = cells[position_idx].text.strip() if position_idx < len(cells) else ''
                                model = cells[model_idx].text.strip() if model_idx < len(cells) else ''
                                reg_date = cells[date_idx].text.strip() if date_idx < len(cells) else ''
                                
                                cars_data[car_number] = {
                                    'model': model or 'Не указано',
                                    'queue_position': int(position) if position and position.isdigit() else 0,
                                    'registration_date': reg_date or 'Не указано'
                                }
                        except Exception as e:
                            self.logger.error(f"Ошибка при обработке строки таблицы: {e}")
                            continue
            
            self.logger.info(f"Всего получено данных о {len(cars_data)} автомобилях из таблиц")
            return cars_data
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении всех автомобилей со страницы: {e}")
            return {}
    
    def _normalize_car_number(self, car_number: str) -> str:
        """Нормализация номера автомобиля для корректного сравнения."""
        # Удаляем все пробелы и переводим в верхний регистр
        normalized = car_number.strip().upper().replace(' ', '')
        
        # Просто возвращаем нормализованный номер без дополнительных проверок
        return normalized

    async def get_first_car_position(self) -> Optional[int]:
        """Получить позицию первого автомобиля в очереди."""
        try:
            # Получаем данные о всех автомобилях
            cars_data = await self.parse_all_cars()
            
            if not cars_data:
                self.logger.warning("Не удалось получить данные о автомобилях для определения первой позиции")
                return None
            
            # Ищем автомобиль с минимальным номером в очереди
            min_position = float('inf')  # Начальное значение - бесконечность
            
            for car_number, data in cars_data.items():
                position = data.get('queue_position', 0)
                if position > 0 and position < min_position:
                    min_position = position
            
            if min_position != float('inf'):
                self.logger.info(f"Найдена первая позиция в очереди: {min_position}")
                return int(min_position)
            
            self.logger.warning("Не удалось определить первую позицию в очереди")
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении позиции первого автомобиля: {e}")
            return None

    async def close(self):
        """Закрывает пул потоков и освобождает ресурсы."""
        self.logger.info("Закрытие пула потоков")
        self.thread_pool.shutdown(wait=True)
        self.logger.info("Пул потоков закрыт")


async def start_parser():
    """Запуск парсера как отдельного процесса."""
    try:
        parser = CoddParser()
        config = load_config()
        
        parser_logger.info(f"Запуск парсера с интервалом {config.parser_interval} секунд")
        
        try:
            while True:
                parser_logger.info("Запуск цикла парсинга")
                await parser.parse_all_cars()
                parser_logger.info(f"Ожидание {config.parser_interval} секунд до следующего запуска")
                await asyncio.sleep(config.parser_interval)
        except asyncio.CancelledError:
            parser_logger.info("Парсер остановлен")
        finally:
            # Закрываем ресурсы
            await parser.close()
    except Exception as e:
        parser_logger.error(f"Критическая ошибка в парсере: {e}")
        parser_logger.exception("Стек ошибки:")


if __name__ == "__main__":
    asyncio.run(start_parser()) 