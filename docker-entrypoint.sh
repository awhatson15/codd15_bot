#!/bin/bash
set -e

# Создаем директорию для базы данных и устанавливаем права
mkdir -p /app/database
touch /app/database/queue_data.db
chmod -R 777 /app/database
chmod 666 /app/database/queue_data.db

# Информация о правах доступа
echo "Database directory permissions:"
ls -la /app/database

# Меняем владельца на appuser
chown -R appuser:appuser /app/database

# Запускаем команду от имени пользователя appuser
exec su -c "$*" appuser 