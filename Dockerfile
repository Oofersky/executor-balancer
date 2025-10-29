# Dockerfile для Executor Balancer API
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование и установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка дополнительных зависимостей для БД
RUN pip install --no-cache-dir \
    asyncpg \
    redis \
    psycopg2-binary

# Копирование основного файла приложения
COPY executor_balancer_api.py .

# Копирование модулей приложения
COPY app/ ./app/
COPY static/ ./static/
COPY templates/ ./templates/

# Создание пользователя без root прав
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Открытие порта
EXPOSE 8006

# Проверка здоровья
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# Запуск нашего приложения
CMD ["python", "executor_balancer_api.py"]