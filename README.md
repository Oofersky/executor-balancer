# Executor Balancer 🚀

Система распределения заявок между исполнителями с веб-интерфейсом, дашбордом аналитики и API.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)

## 📋 Описание

Executor Balancer - это интеллектуальная система для автоматического распределения заявок между исполнителями на основе их навыков, загруженности и соответствия требованиям. Система включает веб-интерфейс, дашборд аналитики и REST API.

## ✨ Основные возможности

- 🎯 **Умное распределение** - Алгоритм подбора исполнителей на основе навыков и загруженности
- 📊 **Дашборд аналитики** - Визуализация метрик и статистики в реальном времени
- 🌐 **Веб-интерфейс** - Удобный интерфейс для управления исполнителями и заявками
- 🔌 **REST API** - Полнофункциональное API для интеграции с внешними системами
- 📈 **Метрики** - Сбор и анализ производительности системы
- 🔄 **WebSocket** - Обновления в реальном времени

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.8+
- pip

### Установка и запуск

#### Вариант 1: Быстрый запуск (Windows)
```bash
# Клонируйте репозиторий
git clone https://github.com/Oofersky/executor-balancer.git
cd executor-balancer

# Установка зависимостей
pip install fastapi uvicorn pydantic pydantic-settings jinja2 python-multipart
```

#### Вариант 2: Полный запуск с Dashboard
```bash
# Установите полные зависимости
pip install -r requirements-full.txt

# Запустите приложение
python -m app.main
```

#### Вариант 3: Минимальная установка
```bash
# Установите минимальные зависимости
pip install -r requirements-minimal.txt

# Запустите приложение
python -m app.main
```

### Доступ к приложению

После запуска откройте браузер и перейдите по адресам:

- **http://localhost:8006** - Главная страница
- **http://localhost:8006/app** - Основное приложение
- **http://localhost:8006/dashboard** - Дашборд аналитики
- **http://localhost:8006/docs** - API документация (Swagger UI)

## 📚 API Эндпоинты

### 🎯 Исполнители (Executors)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/executors` | Получить список всех исполнителей |
| `POST` | `/api/executors` | Создать нового исполнителя |
| `GET` | `/api/executors/{id}` | Получить исполнителя по ID |
| `PUT` | `/api/executors/{id}` | Обновить исполнителя |
| `DELETE` | `/api/executors/{id}` | Удалить исполнителя |
| `POST` | `/api/executors/search` | Поиск исполнителей по критериям |

### 📋 Заявки (Requests)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/requests` | Получить список всех заявок |
| `POST` | `/api/requests` | Создать новую заявку |
| `GET` | `/api/requests/{id}` | Получить заявку по ID |
| `PUT` | `/api/requests/{id}` | Обновить заявку |
| `DELETE` | `/api/requests/{id}` | Удалить заявку |

### 🔗 Назначения (Assignments)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/assignments` | Получить список всех назначений |
| `POST` | `/api/assignments` | Создать новое назначение |
| `GET` | `/api/assignments/{id}` | Получить назначение по ID |
| `PUT` | `/api/assignments/{id}` | Обновить назначение |
| `DELETE` | `/api/assignments/{id}` | Удалить назначение |

### ⚙️ Правила распределения (Rules)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/rules` | Получить список правил |
| `POST` | `/api/rules` | Создать новое правило |
| `GET` | `/api/rules/{id}` | Получить правило по ID |
| `PUT` | `/api/rules/{id}` | Обновить правило |
| `DELETE` | `/api/rules/{id}` | Удалить правило |

### 📊 Аналитика и метрики

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/dashboard` | Получить данные для дашборда |
| `GET` | `/api/stats` | Получить общую статистику |
| `GET` | `/api/metrics` | Получить метрики системы |
| `GET` | `/api/health` | Проверка состояния системы |

### 🔄 WebSocket

| Эндпоинт | Описание |
|----------|----------|
| `/ws` | WebSocket подключение для обновлений в реальном времени |

## 📁 Структура проекта

```
executor-balancer/
├── app/                           # Основной код приложения
│   ├── main.py                   # Точка входа приложения
│   ├── api/                      # API маршруты
│   │   └── routes.py             # Все API эндпоинты
│   ├── core/                     # Ядро системы
│   │   ├── config.py             # Конфигурация
│   │   ├── database.py           # Работа с БД
│   │   ├── simple_metrics.py     # Простые метрики
│   │   ├── metrics.py            # Расширенные метрики
│   │   └── prometheus_metrics.py # Prometheus метрики
│   ├── models/                   # Модели данных
│   │   └── schemas.py            # Pydantic схемы
│   ├── services/                 # Бизнес-логика
│   │   ├── balancer.py           # Алгоритм распределения
│   │   └── database_service.py   # Сервис БД
│   └── utils/                    # Вспомогательные функции
│       └── helpers.py             # Утилиты
├── templates/                    # HTML шаблоны
│   ├── index.html                # Главная страница приложения
│   ├── dashboard.html            # Дашборд аналитики
│   ├── guide.html                # Руководство пользователя
│   └── demo.html                 # Демо страница
├── static/                       # Статические файлы
│   └── js/
│       └── app.js                # JavaScript для фронтенда
├── requirements-minimal.txt      # Минимальные зависимости
├── requirements-full.txt         # Полные зависимости
├── quick-start.bat               # Быстрый запуск (Windows)
├── start-full.bat                # Полный запуск с Dashboard
└── README.md                     # Этот файл
```

## 🔧 Конфигурация

### Основные настройки (app/core/config.py)

```python
# Сервер
HOST = "0.0.0.0"
PORT = 8006

# База данных (опционально)
DATABASE_URL = "sqlite:///./executor_balancer.db"

# Redis (опционально)
REDIS_URL = "redis://localhost:6379"

# Метрики
PROMETHEUS_ENABLED = True
LOAD_SAMPLE_DATA = True
```

### Переменные окружения

```bash
# Отключить базу данных (работа в памяти)
USE_DATABASE=false

# Настройки сервера
HOST=0.0.0.0
PORT=8006

# Уровень логирования
LOG_LEVEL=INFO
```

## 📊 Модели данных

### Исполнитель (Executor)
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "role": "programmer|support|admin|...",
  "skills": ["skill1", "skill2"],
  "languages": ["ru", "en"],
  "timezone": "MSK|UTC|...",
  "experience_years": 5,
  "status": "active|busy|offline",
  "daily_limit": 10,
  "current_load": 3,
  "success_rate": 0.95,
  "weight": 0.8
}
```

### Заявка (Request)
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "category": "technical|support|development|...",
  "priority": "critical|high|medium|low",
  "complexity": "low|medium|high|expert",
  "required_skills": ["skill1", "skill2"],
  "required_languages": ["ru", "en"],
  "timezone_preference": "MSK|UTC|...",
  "status": "pending|assigned|in_progress|completed",
  "created_at": "datetime",
  "deadline": "datetime"
}
```

## 🎯 Алгоритм распределения

Система использует интеллектуальный алгоритм подбора исполнителей:

1. **Соответствие роли** - Проверка соответствия роли исполнителя категории заявки
2. **Навыки** - Оценка соответствия навыков требованиям заявки
3. **Языки** - Проверка языковых требований
4. **Часовой пояс** - Учет временных зон
5. **Загруженность** - Анализ текущей нагрузки исполнителя
6. **Успешность** - Учет истории успешных выполнений
7. **Приоритет** - Учет приоритета заявки

## 🚀 Развертывание

### Docker (рекомендуется)

```bash
# Сборка и запуск
docker-compose up -d

# Доступ к приложению
http://localhost:8006
```

### Локальное развертывание

```bash
# Клонирование
git clone https://github.com/Oofersky/executor-balancer.git
cd executor-balancer

# Установка зависимостей
pip install -r requirements-full.txt

# Запуск
python -m app.main
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 👥 Авторы

- **Oofersky** - *Основной разработчик* - [GitHub](https://github.com/Oofersky)

## 🙏 Благодарности

- FastAPI за отличный веб-фреймворк
- Chart.js за интерактивные графики
- Pydantic за валидацию данных

## 📞 Поддержка

Если у вас есть вопросы или проблемы:

1. Проверьте [Issues](https://github.com/Oofersky/executor-balancer/issues)
2. Создайте новый Issue с подробным описанием
3. Обратитесь к документации API: http://localhost:8006/docs

---

⭐ Если проект вам понравился, поставьте звезду!
