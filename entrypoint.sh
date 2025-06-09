#!/bin/sh

# Ожидание готовности PostgreSQL
echo "Waiting for PostgreSQL to start..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
done
echo "PostgreSQL started"

# Применение миграций Alembic
cd src
alembic upgrade head

# Запуск Uvicorn сервера
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload