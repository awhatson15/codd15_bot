FROM python:3.11-slim

WORKDIR /app

# Установка необходимых пакетов для работы
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка зависимостей до копирования кода для лучшего кеширования слоев
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создание непривилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Создание необходимых директорий и задание прав для монтируемых директорий
RUN mkdir -p /app/logs /app/database && \
    chmod 777 /app/logs /app/database && \
    chown -R appuser:appuser /app

# Копирование исходного кода
COPY . .

# Не используем USER appuser - теперь переключение происходит в entrypoint

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "bot"] 