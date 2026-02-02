FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry
RUN pip install --no-cache-dir poetry

# В контейнере удобнее ставить зависимости прямо в system site-packages (без virtualenv),
# иначе легко получить ситуацию, когда python не видит установленные пакеты.
RUN poetry config virtualenvs.create false

# Копируем файлы зависимостей
COPY pyproject.toml ./

# Копируем код приложения
COPY . .

# Устанавливаем зависимости и проект (если есть poetry.lock, он будет использован автоматически)
# Poetry 2.x: вместо --no-dev используется --without dev
# Используем --no-root, так как мы не устанавливаем текущий проект как пакет
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# Используем Poetry для запуска команд
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8080"]
