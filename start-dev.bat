#!/bin/bash
# Скрипт запуска Executor Balancer без Docker Desktop

echo "🚀 Запуск Executor Balancer в режиме разработки..."

# Проверка Python
if ! command -v python &> /dev/null; then
    echo "❌ Python не установлен!"
    exit 1
fi

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip install -r requirements.txt

# Установка переменных окружения
export USE_DATABASE=false
export DATABASE_URL=""
export REDIS_URL=""

# Остановка существующих процессов
echo "🛑 Остановка существующих процессов..."
taskkill /f /im python.exe 2>/dev/null || true

# Запуск приложения
echo "▶️ Запуск приложения..."
python executor_balancer_api.py
