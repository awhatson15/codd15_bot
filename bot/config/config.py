import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    bot_token: str
    codd_url: str
    database_path: str
    parser_interval: int
    default_notification_interval: int


def load_config() -> Config:
    """Загрузка конфигурации из переменных окружения."""
    load_dotenv()
    
    return Config(
        bot_token=os.getenv("BOT_TOKEN"),
        codd_url=os.getenv("CODD_URL", "https://codd15.ru/ticket.html"),
        database_path=os.getenv("DATABASE_PATH", "./database/queue_data.db"),
        parser_interval=int(os.getenv("PARSER_INTERVAL", 60)),
        default_notification_interval=int(os.getenv("DEFAULT_NOTIFICATION_INTERVAL", 2)),
    ) 