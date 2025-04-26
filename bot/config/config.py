import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class Config(BaseModel):
    """Конфигурация бота"""
    bot_token: str
    codd_url: str = "https://codd15.ru/ticket.html"
    database_path: str = "./database/queue_data.db"
    parser_interval: int = 60
    default_notification_interval: int = 2
    use_redis: bool = False
    redis_url: str = "redis://localhost:6379/0"
    debug_mode: bool = False


def load_config() -> Config:
    """Загрузка конфигурации из переменных окружения."""
    load_dotenv()
    
    return Config(
        bot_token=os.getenv("BOT_TOKEN"),
        codd_url=os.getenv("CODD_URL", "https://codd15.ru/ticket.html"),
        database_path=os.getenv("DATABASE_PATH", "./database/queue_data.db"),
        parser_interval=int(os.getenv("PARSER_INTERVAL", 60)),
        default_notification_interval=int(os.getenv("DEFAULT_NOTIFICATION_INTERVAL", 2)),
        use_redis=os.getenv("USE_REDIS", "false").lower() == "true",
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
    ) 