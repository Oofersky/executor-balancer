"""
Database Service for Executor Balancer
Сервис для работы с базой данных
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from core.database import db_manager
from models.schemas import Executor, Request, Assignment, DistributionRule

logger = logging.getLogger(__name__)

class DatabaseService:
    """Сервис для работы с базой данных"""
    
    # Executors
    async def create_executor(self, executor: Executor) -> Executor:
        """Создание исполнителя"""
        if not db_manager or not db_manager.pool:
            raise Exception("Database not initialized")
        
        async with db_manager.pool.acquire() as conn:
            executor_id = str(uuid.uuid4())
            await conn.execute('''
                INSERT INTO executors (id, name, email, role, weight, status, active_requests_count, 
                                    success_rate, experience_years, specialization, language_skills, 
                                    timezone, daily_limit, parameters)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ''', executor_id, executor.name, executor.email, executor.role, executor.weight,
                executor.status, executor.active_requests_count, executor.success_rate,
                executor.experience_years, executor.specialization, executor.language_skills,
                executor.timezone, executor.daily_limit, executor.parameters)
            
            executor.id = executor_id
            return executor
    
    async def get_executors(self) -> List[Executor]:
        """Получение всех исполнителей"""
        if not db_manager or not db_manager.pool:
            return []
        
        async with db_manager.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM executors ORDER BY created_at DESC')
            return [Executor(**dict(row)) for row in rows]
    
    async def get_executor_by_id(self, executor_id: str) -> Optional[Executor]:
        """Получение исполнителя по ID"""
        if not db_manager or not db_manager.pool:
            return None
        
        async with db_manager.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM executors WHERE id = $1', executor_id)
            return Executor(**dict(row)) if row else None
    
    async def update_executor(self, executor_id: str, executor: Executor) -> Optional[Executor]:
        """Обновление исполнителя"""
        if not db_manager or not db_manager.pool:
            return None
        
        async with db_manager.pool.acquire() as conn:
            await conn.execute('''
                UPDATE executors SET 
                    name = $2, email = $3, role = $4, weight = $5, status = $6,
                    active_requests_count = $7, success_rate = $8, experience_years = $9,
                    specialization = $10, language_skills = $11, timezone = $12,
                    daily_limit = $13, parameters = $14, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            ''', executor_id, executor.name, executor.email, executor.role, executor.weight,
                executor.status, executor.active_requests_count, executor.success_rate,
                executor.experience_years, executor.specialization, executor.language_skills,
                executor.timezone, executor.daily_limit, executor.parameters)
            
            return await self.get_executor_by_id(executor_id)
    
    async def delete_executor(self, executor_id: str) -> bool:
        """Удаление исполнителя"""
        if not db_manager or not db_manager.pool:
            return False
        
        async with db_manager.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM executors WHERE id = $1', executor_id)
            return result == "DELETE 1"
    
    # Requests
    async def create_request(self, request: Request) -> Request:
        """Создание заявки"""
        if not db_manager or not db_manager.pool:
            raise Exception("Database not initialized")
        
        async with db_manager.pool.acquire() as conn:
            request_id = str(uuid.uuid4())
            await conn.execute('''
                INSERT INTO requests (id, title, description, priority, weight, status,
                                   assigned_executor_id, category, complexity, estimated_hours,
                                   required_skills, language_requirement, client_type, urgency,
                                   budget, technology_stack, timezone_requirement, security_clearance,
                                   compliance_requirements, parameters)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            ''', request_id, request.title, request.description, request.priority, request.weight,
                request.status, request.assigned_executor_id, request.category, request.complexity,
                request.estimated_hours, request.required_skills, request.language_requirement,
                request.client_type, request.urgency, request.budget, request.technology_stack,
                request.timezone_requirement, request.security_clearance, request.compliance_requirements,
                request.parameters)
            
            request.id = request_id
            return request
    
    async def get_requests(self) -> List[Request]:
        """Получение всех заявок"""
        if not db_manager or not db_manager.pool:
            return []
        
        async with db_manager.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM requests ORDER BY created_at DESC')
            return [Request(**dict(row)) for row in rows]
    
    async def get_request_by_id(self, request_id: str) -> Optional[Request]:
        """Получение заявки по ID"""
        if not db_manager or not db_manager.pool:
            return None
        
        async with db_manager.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM requests WHERE id = $1', request_id)
            return Request(**dict(row)) if row else None
    
    async def update_request(self, request_id: str, request: Request) -> Optional[Request]:
        """Обновление заявки"""
        if not db_manager or not db_manager.pool:
            return None
        
        async with db_manager.pool.acquire() as conn:
            await conn.execute('''
                UPDATE requests SET 
                    title = $2, description = $3, priority = $4, weight = $5, status = $6,
                    assigned_executor_id = $7, category = $8, complexity = $9, estimated_hours = $10,
                    required_skills = $11, language_requirement = $12, client_type = $13, urgency = $14,
                    budget = $15, technology_stack = $16, timezone_requirement = $17, security_clearance = $18,
                    compliance_requirements = $19, parameters = $20, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            ''', request_id, request.title, request.description, request.priority, request.weight,
                request.status, request.assigned_executor_id, request.category, request.complexity,
                request.estimated_hours, request.required_skills, request.language_requirement,
                request.client_type, request.urgency, request.budget, request.technology_stack,
                request.timezone_requirement, request.security_clearance, request.compliance_requirements,
                request.parameters)
            
            return await self.get_request_by_id(request_id)
    
    async def delete_request(self, request_id: str) -> bool:
        """Удаление заявки"""
        if not db_manager or not db_manager.pool:
            return False
        
        async with db_manager.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM requests WHERE id = $1', request_id)
            return result == "DELETE 1"
    
    # Assignments
    async def create_assignment(self, assignment: Assignment) -> Assignment:
        """Создание назначения"""
        if not db_manager or not db_manager.pool:
            raise Exception("Database not initialized")
        
        async with db_manager.pool.acquire() as conn:
            assignment_id = str(uuid.uuid4())
            await conn.execute('''
                INSERT INTO assignments (id, request_id, executor_id, assigned_at, status, 
                                       completed_at, rating, comment)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', assignment_id, assignment.request_id, assignment.executor_id, 
                assignment.assigned_at, assignment.status, assignment.completed_at,
                assignment.rating, assignment.comment)
            
            assignment.id = assignment_id
            return assignment
    
    async def get_assignments(self) -> List[Assignment]:
        """Получение всех назначений"""
        if not db_manager or not db_manager.pool:
            return []
        
        async with db_manager.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM assignments ORDER BY assigned_at DESC')
            return [Assignment(**dict(row)) for row in rows]
    
    # Distribution Rules
    async def create_distribution_rule(self, rule: DistributionRule) -> DistributionRule:
        """Создание правила распределения"""
        if not db_manager or not db_manager.pool:
            raise Exception("Database not initialized")
        
        async with db_manager.pool.acquire() as conn:
            rule_id = str(uuid.uuid4())
            await conn.execute('''
                INSERT INTO distribution_rules (id, name, description, priority, conditions, is_active)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', rule_id, rule.name, rule.description, rule.priority, rule.conditions, rule.is_active)
            
            rule.id = rule_id
            return rule
    
    async def get_distribution_rules(self) -> List[DistributionRule]:
        """Получение всех правил распределения"""
        if not db_manager or not db_manager.pool:
            return []
        
        async with db_manager.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM distribution_rules ORDER BY priority DESC')
            return [DistributionRule(**dict(row)) for row in rows]
    
    # Statistics
    async def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики"""
        if not db_manager or not db_manager.pool:
            return {}
        
        async with db_manager.pool.acquire() as conn:
            # Количество исполнителей по статусам
            executor_stats = await conn.fetch('''
                SELECT status, COUNT(*) as count FROM executors GROUP BY status
            ''')
            
            # Количество заявок по статусам
            request_stats = await conn.fetch('''
                SELECT status, COUNT(*) as count FROM requests GROUP BY status
            ''')
            
            # Количество заявок по приоритетам
            priority_stats = await conn.fetch('''
                SELECT priority, COUNT(*) as count FROM requests GROUP BY priority
            ''')
            
            # Количество назначений по статусам
            assignment_stats = await conn.fetch('''
                SELECT status, COUNT(*) as count FROM assignments GROUP BY status
            ''')
            
            return {
                'executors_by_status': {row['status']: row['count'] for row in executor_stats},
                'requests_by_status': {row['status']: row['count'] for row in request_stats},
                'requests_by_priority': {row['priority']: row['count'] for row in priority_stats},
                'assignments_by_status': {row['status']: row['count'] for row in assignment_stats},
                'total_executors': sum(row['count'] for row in executor_stats),
                'total_requests': sum(row['count'] for row in request_stats),
                'total_assignments': sum(row['count'] for row in assignment_stats)
            }

# Глобальный экземпляр сервиса
db_service = DatabaseService()
