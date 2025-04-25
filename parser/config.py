import os
from dotenv import load_dotenv

load_dotenv()

# URL для парсинга
CODD_URL = "https://codd15.ru/ticket.html"

# API для получения данных
CODD_API_URL = "https://codd15.ru/api/v1/queue"

# Путь к базе данных
DB_PATH = os.getenv("DB_PATH", "data/codd_queue.db")
