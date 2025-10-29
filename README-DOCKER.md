# Executor Balancer - Docker Setup

## 🐳 Запуск с Docker Compose

### Быстрый старт

```bash
# Клонирование репозитория
git clone <repository-url>
cd executor-balancers

# Запуск всех сервисов
docker-compose up --build -d

# Проверка статуса
docker-compose ps
```

### Доступные сервисы

- **Executor Balancer API**: http://localhost:8006/
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Структура сервисов

```yaml
services:
  postgres:     # База данных PostgreSQL
  redis:        # Кэш Redis
  executor-balancer:  # Основное приложение
  nginx:        # Reverse proxy (опционально)
```

## 🔧 Настройка

### Переменные окружения

Создайте файл `.env` в корне проекта:

```env
DATABASE_URL=postgresql://postgres:password@postgres:5432/executor_balancer
REDIS_URL=redis://redis:6379
USE_DATABASE=true
DEBUG=true
```

### Порты

- **8006** - Основное приложение
- **5432** - PostgreSQL
- **6379** - Redis
- **80/443** - Nginx (если включен)

## 📋 Команды управления

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f executor-balancer

# Перезапуск приложения
docker-compose restart executor-balancer

# Остановка всех сервисов
docker-compose down

# Остановка с удалением данных
docker-compose down -v

# Сборка без кэша
docker-compose build --no-cache
```

## 🗄️ База данных

### Подключение к PostgreSQL

```bash
# Через Docker
docker-compose exec postgres psql -U postgres -d executor_balancer

# Локально (если порт проброшен)
psql -h localhost -p 5432 -U postgres -d executor_balancer
```

### Подключение к Redis

```bash
# Через Docker
docker-compose exec redis redis-cli

# Локально
redis-cli -h localhost -p 6379
```

## 🔍 Мониторинг

### Проверка здоровья

```bash
# Статус всех сервисов
docker-compose ps

# Проверка здоровья приложения
curl http://localhost:8006/health

# Логи приложения
docker-compose logs executor-balancer
```

### Метрики

- **API документация**: http://localhost:8006/docs
- **Дашборд**: http://localhost:8006/dashboard
- **Статистика**: http://localhost:8006/api/stats

## 🚀 Production

### С Nginx

```bash
# Запуск с Nginx
docker-compose --profile production up -d
```

### Масштабирование

```bash
# Запуск нескольких экземпляров приложения
docker-compose up --scale executor-balancer=3 -d
```

## 🛠️ Разработка

### Горячая перезагрузка

```bash
# Запуск в режиме разработки
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Отладка

```bash
# Подключение к контейнеру
docker-compose exec executor-balancer bash

# Просмотр переменных окружения
docker-compose exec executor-balancer env
```

## 📁 Структура проекта

```
executor-balancers/
├── docker-compose.yml      # Основной compose файл
├── Dockerfile             # Dockerfile для приложения
├── executor_balancer_api.py  # Основной файл приложения
├── app/                   # Модули приложения
├── static/               # Статические файлы
├── templates/            # HTML шаблоны
├── requirements.txt      # Python зависимости
└── start-docker.sh       # Скрипт запуска
```

## ❗ Устранение проблем

### Проблемы с подключением к БД

```bash
# Проверка статуса PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Перезапуск БД
docker-compose restart postgres
```

### Проблемы с Redis

```bash
# Проверка Redis
docker-compose exec redis redis-cli ping

# Очистка кэша
docker-compose exec redis redis-cli FLUSHALL
```

### Очистка данных

```bash
# Полная очистка (ВНИМАНИЕ: удалит все данные!)
docker-compose down -v
docker system prune -a
```