"""
Executor Balancer Service
Сервис для распределения заявок между исполнителями
"""

from typing import List, Dict, Any, Tuple
from models.schemas import Executor, ExecutorSearchRequest, ExecutorSearchResult

class ExecutorBalancer:
    """Сервис для распределения заявок между исполнителями"""
    
    def __init__(self):
        self.role_scores = {
            "admin": {"technical": 15, "support": 20, "development": 10, "testing": 5, "design": 5, "marketing": 10},
            "programmer": {"technical": 20, "support": 10, "development": 20, "testing": 15, "design": 5, "marketing": 5},
            "moderator": {"technical": 10, "support": 20, "development": 5, "testing": 10, "design": 5, "marketing": 15},
            "support": {"technical": 15, "support": 20, "development": 5, "testing": 10, "design": 5, "marketing": 10},
            "tester": {"technical": 15, "support": 10, "development": 10, "testing": 20, "design": 5, "marketing": 5},
            "designer": {"technical": 5, "support": 5, "development": 10, "testing": 5, "design": 20, "marketing": 15},
            "analyst": {"technical": 15, "support": 15, "development": 15, "testing": 15, "design": 10, "marketing": 15},
            "manager": {"technical": 10, "support": 15, "development": 15, "testing": 10, "design": 10, "marketing": 20}
        }
        
        self.complexity_requirements = {
            "low": 1,
            "medium": 3,
            "high": 5,
            "expert": 8
        }
        
        self.priority_scores = {"critical": 10, "high": 8, "medium": 5, "low": 2}
    
    def search_executors(self, search_request: ExecutorSearchRequest, executors_db: List[Executor]) -> List[ExecutorSearchResult]:
        """Найти подходящих исполнителей для заявки"""
        suitable_executors = []
        
        for executor in executors_db:
            if executor.status != "active":
                continue
                
            # Проверить, соответствует ли исполнитель базовым требованиям
            if executor.active_requests_count >= executor.daily_limit:
                continue
                
            # Рассчитать оценку соответствия на основе правил и параметров
            match_score, reasons = self.calculate_executor_match(executor, search_request)
            
            if match_score > 0:  # Включить только исполнителей с некоторым соответствием
                final_score = self.calculate_final_score(executor, search_request, match_score)
                suitable_executors.append(ExecutorSearchResult(
                    executor=executor,
                    match_score=match_score,
                    final_score=final_score,
                    reasons=reasons
                ))
        
        # Сортировать по итоговой оценке (по убыванию)
        suitable_executors.sort(key=lambda x: x.final_score, reverse=True)
        
        return suitable_executors[:10]  # Вернуть топ-10 совпадений
    
    def calculate_executor_match(self, executor: Executor, request: ExecutorSearchRequest) -> Tuple[float, List[str]]:
        """Рассчитать, насколько хорошо исполнитель соответствует заявке"""
        match_score = 0.0
        reasons = []
        
        # Соответствие роли (20 баллов)
        role_score = self.role_scores.get(executor.role, {}).get(request.category, 5)
        match_score += role_score
        reasons.append(f"Соответствие роли и категории: +{role_score}")
        
        # Соответствие опыта (15 баллов)
        required_experience = self.complexity_requirements.get(request.complexity, 3)
        if executor.experience_years >= required_experience:
            exp_score = min(15, executor.experience_years * 2)
            match_score += exp_score
            reasons.append(f"Опыт работы: +{exp_score}")
        
        # Соответствие языка (10 баллов)
        if request.language_requirement == "both" or request.language_requirement in executor.language_skills:
            match_score += 10
            reasons.append("Соответствие языковым требованиям: +10")
        
        # Соответствие часового пояса (5 баллов)
        if request.timezone_requirement == "any" or request.timezone_requirement == executor.timezone:
            match_score += 5
            reasons.append("Соответствие часовому поясу: +5")
        
        # Соответствие навыков (20 баллов)
        if request.required_skills:
            executor_skills = executor.specialization.lower().split(",") if executor.specialization else []
            matched_skills = 0
            for skill in request.required_skills:
                if any(skill.lower().strip() in exec_skill.strip() for exec_skill in executor_skills):
                    matched_skills += 1
            
            if matched_skills > 0:
                skills_score = (matched_skills / len(request.required_skills)) * 20
                match_score += skills_score
                reasons.append(f"Соответствие навыкам: +{skills_score:.1f}")
        
        # Соответствие приоритету (10 баллов)
        priority_score = self.priority_scores.get(request.priority, 5)
        match_score += priority_score
        reasons.append(f"Приоритет заявки: +{priority_score}")
        
        # Преобразовать в проценты
        match_score = min(100, match_score)
        
        return match_score, reasons
    
    def calculate_final_score(self, executor: Executor, request: ExecutorSearchRequest, match_score: float) -> float:
        """Рассчитать итоговую оценку с учетом справедливости и балансировки нагрузки"""
        final_score = 0.0
        
        # Базовая оценка соответствия (0-100 баллов)
        final_score += match_score
        
        # Бонус веса исполнителя (0-20 баллов)
        weight_bonus = executor.weight * 20
        final_score += weight_bonus
        
        # Бонус процента успешности (0-15 баллов)
        success_bonus = executor.success_rate * 15
        final_score += success_bonus
        
        # Штраф за балансировку нагрузки (поощрить справедливое распределение)
        load_penalty = executor.active_requests_count * 5
        final_score -= load_penalty
        
        # Бонус опыта (0-10 баллов)
        exp_bonus = min(10, executor.experience_years)
        final_score += exp_bonus
        
        # Обеспечить неотрицательную оценку
        final_score = max(0, final_score)
        
        return final_score
    
    def assign_executor(self, executor_id: str, request_id: str, executors_db: List[Executor], requests_db: List[Any]) -> Dict[str, Any]:
        """Назначить исполнителя на заявку"""
        # Найти исполнителя и заявку
        executor = next((e for e in executors_db if e.id == executor_id), None)
        request = next((r for r in requests_db if r.id == request_id), None)
        
        if not executor or not request:
            return {"success": False, "error": "Executor or request not found"}
        
        # Проверить доступность исполнителя
        if executor.active_requests_count >= executor.daily_limit:
            return {"success": False, "error": "Executor has reached daily limit"}
        
        if executor.status != "active":
            return {"success": False, "error": "Executor is not active"}
        
        # Обновить заявку и исполнителя
        request.status = "assigned"
        request.assigned_executor_id = executor_id
        executor.active_requests_count += 1
        
        return {
            "success": True,
            "executor_id": executor_id,
            "request_id": request_id,
            "message": "Assignment successful"
        }
    
    def get_executor_stats(self, executor: Executor) -> Dict[str, Any]:
        """Получить статистику исполнителя"""
        return {
            "id": executor.id,
            "name": executor.name,
            "role": executor.role,
            "active_requests": executor.active_requests_count,
            "daily_limit": executor.daily_limit,
            "workload_percentage": (executor.active_requests_count / executor.daily_limit) * 100,
            "success_rate": executor.success_rate,
            "experience_years": executor.experience_years,
            "weight": executor.weight,
            "status": executor.status
        }
    
    def get_system_load(self, executors_db: List[Executor]) -> Dict[str, Any]:
        """Получить загрузку системы"""
        total_executors = len(executors_db)
        active_executors = len([e for e in executors_db if e.status == "active"])
        total_capacity = sum(e.daily_limit for e in executors_db if e.status == "active")
        total_active_requests = sum(e.active_requests_count for e in executors_db)
        
        system_load = (total_active_requests / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            "total_executors": total_executors,
            "active_executors": active_executors,
            "total_capacity": total_capacity,
            "total_active_requests": total_active_requests,
            "system_load_percentage": round(system_load, 2),
            "average_workload": round(total_active_requests / active_executors, 2) if active_executors > 0 else 0
        }
