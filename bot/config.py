import os
from dotenv import load_dotenv

load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_NOTIFICATION_INTERVAL = int(os.getenv("DEFAULT_NOTIFICATION_INTERVAL", 2))  # минуты

# Настройки базы данных
DB_PATH = os.getenv("DB_PATH", "data/codd_queue.db")
