#!/bin/sh
cd /app
# Ожидание готовности PostgreSQL
echo "PostgreSQL started"
alembic upgrade head

# Запуск Uvicorn сервера
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload