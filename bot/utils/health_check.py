import logging
import asyncio
from aiohttp import web

async def health_check_handler(request):
    """
    Обработчик запросов для проверки работоспособности бота.
    Возвращает статус 200 OK, если бот работает.
    """
    return web.Response(text="OK", status=200)

async def start_health_server(host="0.0.0.0", port=8080):
    """
    Запускает HTTP-сервер для проверки работоспособности бота.
    
    Args:
        host (str): Хост, на котором будет запущен сервер
        port (int): Порт, на котором будет запущен сервер
    """
    app = web.Application()
    app.router.add_get('/health', health_check_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    
    try:
        await site.start()
        logging.info(f"Health check сервер запущен на {host}:{port}")
    except Exception as e:
        logging.error(f"Ошибка при запуске health check сервера: {e}") 