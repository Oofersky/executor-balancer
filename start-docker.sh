#!/bin/bash
# Скрипт запуска Executor Balancer в Docker

echo "🚀 Запуск Executor Balancer с базой данных..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "💡 Попробуйте запустить: start-dev.bat"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен!"
    echo "💡 Попробуйте запустить: start-dev.bat"
    exit 1
fi

# Проверка Docker Desktop
if ! docker info &> /dev/null; then
    echo "❌ Docker Desktop не запущен!"
    echo "💡 Запустите Docker Desktop или используйте: start-dev.bat"
    exit 1
fi

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
docker-compose down

# Сборка и запуск
echo "🔨 Сборка и запуск контейнеров..."
docker-compose up --build -d

# Ожидание готовности сервисов
echo "⏳ Ожидание готовности сервисов..."
sleep 30

# Проверка статуса
echo "📊 Статус сервисов:"
docker-compose ps

# Проверка здоровья
echo "🏥 Проверка здоровья приложения..."
curl -f http://localhost:8006/health || echo "❌ Приложение не отвечает"

echo ""
echo "✅ Executor Balancer запущен!"
echo "🌐 Главная страница: http://localhost:8006/"
echo "📊 Дашборд: http://localhost:8006/dashboard"
echo "📚 API документация: http://localhost:8006/docs"
echo "❤️ Статус системы: http://localhost:8006/health"
echo ""
echo "📋 Полезные команды:"
echo "  docker-compose logs -f executor-balancer  # Просмотр логов"
echo "  docker-compose down                      # Остановка"
echo "  docker-compose restart executor-balancer # Перезапуск приложения"
