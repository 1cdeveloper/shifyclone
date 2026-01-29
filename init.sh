#!/bin/bash
# Скрипт для инициализации проекта (выполнить после первого запуска docker compose)

echo "Выполняю миграции БД..."
docker compose exec django poetry run python manage.py migrate

echo "Создание суперпользователя (опционально)..."
docker compose exec django poetry run python manage.py createsuperuser

echo "Готово! Проект инициализирован."

