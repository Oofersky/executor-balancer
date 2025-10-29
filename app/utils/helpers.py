"""
Utility functions and helpers for Executor Balancer
Утилиты и вспомогательные функции для системы распределения исполнителей
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from models.schemas import Executor, Request, DistributionRule, RuleCondition
from core.config import settings

def generate_id() -> str:
    """Генерировать уникальный ID"""
    return str(uuid.uuid4())

def get_current_timestamp() -> datetime:
    """Получить текущую временную метку"""
    return datetime.now()

def validate_executor_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Валидация данных исполнителя"""
    errors = []
    
    # Обязательные поля
    required_fields = ["name", "email", "role"]
    for field in required_fields:
        if not data.get(field):
            errors.append(f"Field '{field}' is required")
    
    # Валидация email
    email = data.get("email", "")
    if email and "@" not in email:
        errors.append("Invalid email format")
    
    # Валидация роли
    role = data.get("role", "")
    if role and role not in settings.EXECUTOR_ROLES:
        errors.append(f"Invalid role. Must be one of: {settings.EXECUTOR_ROLES}")
    
    # Валидация веса
    weight = data.get("weight", 0.5)
    if not isinstance(weight, (int, float)) or not (0 <= weight <= 1):
        errors.append("Weight must be a number between 0 and 1")
    
    # Валидация статуса
    status = data.get("status", "active")
    if status not in settings.EXECUTOR_STATUSES:
        errors.append(f"Invalid status. Must be one of: {settings.EXECUTOR_STATUSES}")
    
    return {"valid": len(errors) == 0, "errors": errors}

def validate_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Валидация данных заявки"""
    errors = []
    
    # Обязательные поля
    required_fields = ["title", "description"]
    for field in required_fields:
        if not data.get(field):
            errors.append(f"Field '{field}' is required")
    
    # Валидация приоритета
    priority = data.get("priority", "medium")
    if priority not in settings.REQUEST_PRIORITIES:
        errors.append(f"Invalid priority. Must be one of: {settings.REQUEST_PRIORITIES}")
    
    # Валидация категории
    category = data.get("category", "technical")
    if category not in settings.REQUEST_CATEGORIES:
        errors.append(f"Invalid category. Must be one of: {settings.REQUEST_CATEGORIES}")
    
    # Валидация сложности
    complexity = data.get("complexity", "medium")
    if complexity not in settings.REQUEST_COMPLEXITY:
        errors.append(f"Invalid complexity. Must be one of: {settings.REQUEST_COMPLEXITY}")
    
    # Валидация часов
    estimated_hours = data.get("estimated_hours", 8)
    if not isinstance(estimated_hours, int) or estimated_hours <= 0:
        errors.append("Estimated hours must be a positive integer")
    
    return {"valid": len(errors) == 0, "errors": errors}

def create_sample_executors() -> List[Executor]:
    """Создать тестовых исполнителей"""
    sample_executors = [
        Executor(
            name="Алексей Петров",
            email="alexey.petrov@company.com",
            role="programmer",
            weight=0.9,
            status="active",
            experience_years=5,
            specialization="Python, JavaScript, React",
            language_skills="ru, en",
            timezone="MSK",
            daily_limit=15,
            success_rate=0.95
        ),
        Executor(
            name="Мария Сидорова",
            email="maria.sidorova@company.com",
            role="designer",
            weight=0.8,
            status="active",
            experience_years=3,
            specialization="UI/UX, Figma, Adobe Creative Suite",
            language_skills="ru, en",
            timezone="MSK",
            daily_limit=12,
            success_rate=0.88
        ),
        Executor(
            name="Дмитрий Козлов",
            email="dmitry.kozlov@company.com",
            role="tester",
            weight=0.7,
            status="active",
            experience_years=4,
            specialization="QA, Selenium, Manual Testing",
            language_skills="ru",
            timezone="MSK",
            daily_limit=10,
            success_rate=0.92
        ),
        Executor(
            name="Анна Волкова",
            email="anna.volkova@company.com",
            role="support",
            weight=0.6,
            status="active",
            experience_years=2,
            specialization="Customer Support, Troubleshooting",
            language_skills="ru, en",
            timezone="MSK",
            daily_limit=20,
            success_rate=0.85
        ),
        Executor(
            name="Сергей Морозов",
            email="sergey.morozov@company.com",
            role="admin",
            weight=0.95,
            status="active",
            experience_years=8,
            specialization="System Administration, DevOps, Linux",
            language_skills="ru, en",
            timezone="MSK",
            daily_limit=8,
            success_rate=0.98
        )
    ]
    
    for executor in sample_executors:
        executor.id = generate_id()
    
    return sample_executors

def create_sample_requests() -> List[Request]:
    """Создать тестовые заявки"""
    sample_requests = [
        Request(
            title="Разработка веб-приложения",
            description="Создание современного веб-приложения с использованием React и Node.js",
            priority="high",
            weight=0.8,
            category="development",
            complexity="high",
            estimated_hours=40,
            required_skills=["React", "Node.js", "JavaScript"],
            language_requirement="ru",
            client_type="business",
            urgency="high",
            budget=50000,
            technology_stack=["React", "Node.js", "MongoDB"],
            timezone_requirement="MSK"
        ),
        Request(
            title="Дизайн мобильного приложения",
            description="Создание UI/UX дизайна для мобильного приложения",
            priority="medium",
            weight=0.6,
            category="design",
            complexity="medium",
            estimated_hours=24,
            required_skills=["UI/UX", "Figma", "Mobile Design"],
            language_requirement="ru",
            client_type="individual",
            urgency="medium",
            budget=25000,
            technology_stack=["Figma", "Adobe XD"],
            timezone_requirement="MSK"
        ),
        Request(
            title="Тестирование API",
            description="Проведение комплексного тестирования REST API",
            priority="medium",
            weight=0.5,
            category="testing",
            complexity="medium",
            estimated_hours=16,
            required_skills=["API Testing", "Postman", "Automation"],
            language_requirement="ru",
            client_type="business",
            urgency="medium",
            budget=20000,
            technology_stack=["Postman", "Selenium", "Python"],
            timezone_requirement="MSK"
        )
    ]
    
    for request in sample_requests:
        request.id = generate_id()
    
    return sample_requests

def create_sample_rules() -> List[DistributionRule]:
    """Создать тестовые правила распределения"""
    sample_rules = [
        DistributionRule(
            name="Высокоприоритетные заявки для программистов",
            description="Назначать программистов на высокоприоритетные технические заявки",
            priority=1,
            conditions=[
                RuleCondition(field="role", operator="equals", value="programmer"),
                RuleCondition(field="weight", operator="greater_than", value="0.7"),
                RuleCondition(field="status", operator="equals", value="active")
            ],
            is_active=True,
            created_at=get_current_timestamp()
        ),
        DistributionRule(
            name="Дизайнеры для дизайн-заявок",
            description="Назначать дизайнеров на заявки категории дизайн",
            priority=2,
            conditions=[
                RuleCondition(field="role", operator="equals", value="designer"),
                RuleCondition(field="category", operator="equals", value="design"),
                RuleCondition(field="active_requests_count", operator="less_than", value="5")
            ],
            is_active=True,
            created_at=get_current_timestamp()
        ),
        DistributionRule(
            name="Опытные исполнители для сложных задач",
            description="Назначать опытных исполнителей на сложные заявки",
            priority=2,
            conditions=[
                RuleCondition(field="experience_years", operator="greater_than", value="3"),
                RuleCondition(field="complexity", operator="equals", value="high"),
                RuleCondition(field="success_rate", operator="greater_than", value="0.8")
            ],
            is_active=True,
            created_at=get_current_timestamp()
        )
    ]
    
    for rule in sample_rules:
        rule.id = generate_id()
    
    return sample_rules

def format_executor_summary(executor: Executor) -> Dict[str, Any]:
    """Форматировать краткую информацию об исполнителе"""
    return {
        "id": executor.id,
        "name": executor.name,
        "role": executor.role,
        "status": executor.status,
        "workload": f"{executor.active_requests_count}/{executor.daily_limit}",
        "success_rate": f"{executor.success_rate * 100:.1f}%",
        "experience": f"{executor.experience_years} лет"
    }

def format_request_summary(request: Request) -> Dict[str, Any]:
    """Форматировать краткую информацию о заявке"""
    return {
        "id": request.id,
        "title": request.title,
        "priority": request.priority,
        "category": request.category,
        "status": request.status,
        "estimated_hours": request.estimated_hours,
        "assigned_to": request.assigned_executor_id
    }

def calculate_workload_percentage(active_requests: int, daily_limit: int) -> float:
    """Рассчитать процент загрузки исполнителя"""
    if daily_limit == 0:
        return 0.0
    return min(100.0, (active_requests / daily_limit) * 100)

def get_workload_status(percentage: float) -> str:
    """Получить статус загрузки на основе процента"""
    if percentage >= 90:
        return "critical"
    elif percentage >= 70:
        return "high"
    elif percentage >= 50:
        return "medium"
    else:
        return "low"

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Очистить и обрезать пользовательский ввод"""
    if not text:
        return ""
    
    # Удалить потенциально опасные символы
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    # Обрезать до максимальной длины
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text.strip()

def format_duration(seconds: float) -> str:
    """Форматировать продолжительность в читаемый вид"""
    if seconds < 60:
        return f"{seconds:.1f} сек"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} мин"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} ч"

def calculate_priority_score(priority: str) -> int:
    """Рассчитать числовой приоритет"""
    return settings.PRIORITY_SCORES.get(priority, 5)

def calculate_complexity_score(complexity: str) -> int:
    """Рассчитать числовую сложность"""
    return settings.COMPLEXITY_REQUIREMENTS.get(complexity, 3)

def is_executor_available(executor: Executor) -> bool:
    """Проверить доступность исполнителя"""
    return (
        executor.status == "active" and 
        executor.active_requests_count < executor.daily_limit
    )

def get_executor_efficiency_score(executor: Executor) -> float:
    """Рассчитать оценку эффективности исполнителя"""
    # Базовые факторы
    success_rate_score = executor.success_rate * 40  # 0-40 баллов
    experience_score = min(executor.experience_years * 2, 20)  # 0-20 баллов
    weight_score = executor.weight * 20  # 0-20 баллов
    
    # Штраф за перегрузку
    workload_penalty = 0
    if executor.active_requests_count > executor.daily_limit * 0.8:
        workload_penalty = (executor.active_requests_count - executor.daily_limit * 0.8) * 5
    
    efficiency = success_rate_score + experience_score + weight_score - workload_penalty
    return max(0, min(100, efficiency))
