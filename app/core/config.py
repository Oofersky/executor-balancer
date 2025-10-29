"""
Configuration settings for Executor Balancer
Настройки конфигурации для системы распределения исполнителей
"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    APP_NAME: str = "Executor Balancer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Сервер
    HOST: str = "0.0.0.0"
    PORT: int = 8006
    WORKERS: int = 1
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]
    
    # База данных
    DATABASE_URL: str = "sqlite:///./executor_balancer.db"
    POSTGRES_DB: str = "executor_balancer"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Метрики
    METRICS_DB_PATH: str = "metrics.db"
    PROMETHEUS_ENABLED: bool = True
    
    # Бизнес-логика
    DEFAULT_EXECUTOR_WEIGHT: float = 0.5
    DEFAULT_REQUEST_WEIGHT: float = 0.5
    DEFAULT_DAILY_LIMIT: int = 10
    MAX_SEARCH_RESULTS: int = 10
    
    # Баллы для оценки соответствия
    ROLE_MATCH_SCORE: int = 20
    EXPERIENCE_SCORE: int = 15
    LANGUAGE_SCORE: int = 10
    TIMEZONE_SCORE: int = 5
    SKILLS_SCORE: int = 20
    PRIORITY_SCORE: int = 10
    
    # Бонусы для итоговой оценки
    WEIGHT_BONUS_MAX: int = 20
    SUCCESS_BONUS_MAX: int = 15
    EXPERIENCE_BONUS_MAX: int = 10
    LOAD_PENALTY_PER_REQUEST: int = 5
    
    # Тестовые данные
    LOAD_SAMPLE_DATA: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Создаем экземпляр настроек
settings = Settings()

# Дополнительные константы
ROLE_SCORES = {
    "admin": {"technical": 15, "support": 20, "development": 10, "testing": 5, "design": 5, "marketing": 10},
    "programmer": {"technical": 20, "support": 10, "development": 20, "testing": 15, "design": 5, "marketing": 5},
    "moderator": {"technical": 10, "support": 20, "development": 5, "testing": 10, "design": 5, "marketing": 15},
    "support": {"technical": 15, "support": 20, "development": 5, "testing": 10, "design": 5, "marketing": 10},
    "tester": {"technical": 15, "support": 10, "development": 10, "testing": 20, "design": 5, "marketing": 5},
    "designer": {"technical": 5, "support": 5, "development": 10, "testing": 5, "design": 20, "marketing": 15},
    "analyst": {"technical": 15, "support": 15, "development": 15, "testing": 15, "design": 10, "marketing": 15},
    "manager": {"technical": 10, "support": 15, "development": 15, "testing": 10, "design": 10, "marketing": 20}
}

COMPLEXITY_REQUIREMENTS = {
    "low": 1,
    "medium": 3,
    "high": 5,
    "expert": 8
}

PRIORITY_SCORES = {
    "critical": 10,
    "high": 8,
    "medium": 5,
    "low": 2
}

# Статусы
EXECUTOR_STATUSES = ["active", "inactive", "busy", "offline"]
REQUEST_STATUSES = ["pending", "assigned", "in_progress", "completed", "cancelled"]
ASSIGNMENT_STATUSES = ["assigned", "accepted", "in_progress", "completed", "cancelled"]

# Роли исполнителей
EXECUTOR_ROLES = ["admin", "programmer", "moderator", "support", "tester", "designer", "analyst", "manager"]

# Категории заявок
REQUEST_CATEGORIES = ["technical", "support", "development", "testing", "design", "marketing"]

# Сложность заявок
REQUEST_COMPLEXITY = ["low", "medium", "high", "expert"]

# Приоритеты заявок
REQUEST_PRIORITIES = ["critical", "high", "medium", "low"]

# Языки
LANGUAGES = ["ru", "en", "both"]

# Часовые пояса
TIMEZONES = ["MSK", "UTC", "EST", "PST", "any"]
