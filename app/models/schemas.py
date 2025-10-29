"""
Data Models and Schemas for Executor Balancer
Модели данных и схемы для системы распределения исполнителей
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class Executor(BaseModel):
    """Модель исполнителя"""
    id: str = None
    name: str
    email: str
    role: str
    weight: float = 0.5
    status: str = "active"
    active_requests_count: int = 0
    success_rate: float = 0.0
    experience_years: int = 0
    specialization: str = ""
    language_skills: str = ""
    timezone: str = "MSK"
    daily_limit: int = 10
    parameters: Dict[str, Any] = {}

class Request(BaseModel):
    """Модель заявки"""
    id: str = None
    title: str
    description: str
    priority: str = "medium"
    weight: float = 0.5
    status: str = "pending"
    assigned_executor_id: Optional[str] = None
    category: str = "technical"
    complexity: str = "medium"
    estimated_hours: int = 8
    required_skills: List[str] = []
    language_requirement: str = "ru"
    client_type: str = "individual"
    urgency: str = "medium"
    budget: Optional[int] = None
    technology_stack: List[str] = []
    timezone_requirement: str = "any"
    security_clearance: str = "public"
    compliance_requirements: List[str] = []
    parameters: Dict[str, Any] = {}

class Assignment(BaseModel):
    """Модель назначения"""
    id: str = None
    request_id: str
    executor_id: str
    assigned_at: datetime = None
    status: str = "assigned"

class RuleCondition(BaseModel):
    """Условие правила распределения"""
    field: str
    operator: str
    value: Any

class DistributionRule(BaseModel):
    """Правило распределения заявок"""
    id: str = None
    name: str
    description: str
    priority: int = 3
    conditions: List[RuleCondition]
    is_active: bool = True
    created_at: datetime = None

class ExecutorSearchResult(BaseModel):
    """Результат поиска исполнителя"""
    executor: Executor
    match_score: float
    final_score: float
    reasons: List[str]

class ExecutorSearchRequest(BaseModel):
    """Запрос на поиск исполнителя"""
    title: str
    priority: str
    weight: float
    category: str
    complexity: str
    estimated_hours: int
    required_skills: List[str]
    language_requirement: str
    client_type: str
    urgency: str
    budget: Optional[int] = None
    technology_stack: List[str]
    timezone_requirement: str
    security_clearance: str
    compliance_requirements: List[str]

class AssignmentRequest(BaseModel):
    """Запрос на назначение исполнителя"""
    executor_id: str
    request_id: str

class StatsResponse(BaseModel):
    """Ответ со статистикой"""
    total_executors: int
    active_executors: int
    total_requests: int
    pending_requests: int
    assigned_requests: int
    total_assignments: int

class HealthResponse(BaseModel):
    """Ответ проверки здоровья"""
    status: str
    timestamp: str
    cors_enabled: bool
    version: str
