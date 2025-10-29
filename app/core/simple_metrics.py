"""
Simple Metrics System
Простая система метрик без Prometheus
"""

from typing import Dict, Any, List
from datetime import datetime
import json
import asyncio
from collections import defaultdict, deque

class SimpleMetrics:
    """Простая система метрик для отслеживания статистики"""
    
    def __init__(self):
        # Счетчики
        self.counters = defaultdict(int)
        
        # Gauges (текущие значения)
        self.gauges = defaultdict(float)
        
        # История метрик для графиков
        self.history = defaultdict(lambda: deque(maxlen=100))
        
        # Статистика по времени
        self.timestamps = deque(maxlen=100)
        
    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        """Увеличить счетчик"""
        key = self._make_key(name, labels)
        self.counters[key] += value
        
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Установить значение gauge"""
        key = self._make_key(name, labels)
        self.gauges[key] = value
        
    def record_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Записать метрику в историю"""
        key = self._make_key(name, labels)
        self.history[key].append({
            'value': value,
            'timestamp': datetime.now().isoformat()
        })
        
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Создать ключ для метрики"""
        if labels:
            label_str = ','.join([f"{k}={v}" for k, v in sorted(labels.items())])
            return f"{name}{{{label_str}}}"
        return name
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Получить сводку всех метрик"""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'timestamp': datetime.now().isoformat()
        }
        
    def get_metric_history(self, name: str, labels: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Получить историю метрики"""
        key = self._make_key(name, labels)
        return list(self.history[key])
        
    def clear_old_data(self, hours: int = 24):
        """Очистить старые данные"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        for key, history in self.history.items():
            # Фильтруем старые записи
            filtered_history = deque(maxlen=100)
            for record in history:
                record_time = datetime.fromisoformat(record['timestamp']).timestamp()
                if record_time > cutoff_time:
                    filtered_history.append(record)
            self.history[key] = filtered_history

# Глобальный экземпляр метрик
metrics = SimpleMetrics()

class RealtimeMetricsCollector:
    """Сборщик метрик в реальном времени"""
    
    def __init__(self):
        self.metrics = metrics
        
    def collect_executor_metrics(self, executors: List[Any]) -> Dict[str, Any]:
        """Сбор метрик исполнителей"""
        stats = {
            'total_executors': len(executors),
            'active_executors': 0,
            'inactive_executors': 0,
            'executors_by_role': defaultdict(int),
            'executors_by_status': defaultdict(int),
            'total_workload': 0,
            'average_success_rate': 0.0
        }
        
        if not executors:
            return stats
            
        success_rates = []
        
        for executor in executors:
            # Обработка как Pydantic модели, так и словарей
            if hasattr(executor, 'dict'):
                executor_data = executor.dict()
            elif hasattr(executor, '__dict__'):
                executor_data = executor.__dict__
            else:
                executor_data = executor
                
            status = executor_data.get('status', 'unknown')
            role = executor_data.get('role', 'unknown')
            active_requests = executor_data.get('active_requests_count', 0)
            success_rate = executor_data.get('success_rate', 0.0)
            
            stats['executors_by_status'][status] += 1
            stats['executors_by_role'][role] += 1
            stats['total_workload'] += active_requests
            
            if success_rate > 0:
                success_rates.append(success_rate)
                
            if status == 'active':
                stats['active_executors'] += 1
            else:
                stats['inactive_executors'] += 1
                
        if success_rates:
            stats['average_success_rate'] = sum(success_rates) / len(success_rates)
            
        return stats
        
    def collect_request_metrics(self, requests: List[Any]) -> Dict[str, Any]:
        """Сбор метрик заявок"""
        stats = {
            'total_requests': len(requests),
            'pending_requests': 0,
            'assigned_requests': 0,
            'completed_requests': 0,
            'requests_by_status': defaultdict(int),
            'requests_by_priority': defaultdict(int),
            'requests_by_category': defaultdict(int)
        }
        
        if not requests:
            return stats
            
        for request in requests:
            # Обработка как Pydantic модели, так и словарей
            if hasattr(request, 'dict'):
                request_data = request.dict()
            elif hasattr(request, '__dict__'):
                request_data = request.__dict__
            else:
                request_data = request
                
            status = request_data.get('status', 'unknown')
            priority = request_data.get('priority', 'unknown')
            category = request_data.get('category', 'unknown')
            
            stats['requests_by_status'][status] += 1
            stats['requests_by_priority'][priority] += 1
            stats['requests_by_category'][category] += 1
            
            if status == 'pending':
                stats['pending_requests'] += 1
            elif status == 'assigned':
                stats['assigned_requests'] += 1
            elif status == 'completed':
                stats['completed_requests'] += 1
                
        return stats
        
    def collect_assignment_metrics(self, assignments: List[Any]) -> Dict[str, Any]:
        """Сбор метрик назначений"""
        stats = {
            'total_assignments': len(assignments),
            'assignments_by_status': defaultdict(int),
            'assignments_by_executor_role': defaultdict(int)
        }
        
        if not assignments:
            return stats
            
        for assignment in assignments:
            # Обработка как Pydantic модели, так и словарей
            if hasattr(assignment, 'dict'):
                assignment_data = assignment.dict()
            elif hasattr(assignment, '__dict__'):
                assignment_data = assignment.__dict__
            else:
                assignment_data = assignment
                
            status = assignment_data.get('status', 'unknown')
            executor_role = assignment_data.get('executor_role', 'unknown')
            
            stats['assignments_by_status'][status] += 1
            stats['assignments_by_executor_role'][executor_role] += 1
            
        return stats
        
    def collect_system_metrics(self, executors: List[Any], requests: List[Any], assignments: List[Any]) -> Dict[str, Any]:
        """Сбор системных метрик"""
        executor_stats = self.collect_executor_metrics(executors)
        request_stats = self.collect_request_metrics(requests)
        assignment_stats = self.collect_assignment_metrics(assignments)
        
        # Расчет системной загрузки
        total_capacity = executor_stats['total_executors'] * 10  # Предполагаем лимит 10 заявок на исполнителя
        current_load = executor_stats['total_workload']
        system_load = (current_load / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            'system_load_percent': min(system_load, 100),
            'efficiency_score': self._calculate_efficiency(executor_stats, request_stats),
            'response_time_avg': self._calculate_avg_response_time(assignments),
            'throughput_per_hour': self._calculate_throughput(requests),
            'executor_stats': executor_stats,
            'request_stats': request_stats,
            'assignment_stats': assignment_stats
        }
        
    def _calculate_efficiency(self, executor_stats: Dict, request_stats: Dict) -> float:
        """Расчет эффективности системы"""
        if executor_stats['active_executors'] == 0:
            return 0.0
            
        # Простая формула эффективности
        utilization = executor_stats['total_workload'] / executor_stats['active_executors']
        success_rate = executor_stats['average_success_rate']
        
        return min((utilization * success_rate) / 10 * 100, 100)
        
    def _calculate_avg_response_time(self, assignments: List[Any]) -> float:
        """Расчет среднего времени ответа"""
        if not assignments:
            return 0.0
            
        total_time = 0
        count = 0
        
        for assignment in assignments:
            if hasattr(assignment, 'dict'):
                assignment_data = assignment.dict()
            elif hasattr(assignment, '__dict__'):
                assignment_data = assignment.__dict__
            else:
                assignment_data = assignment
                
            # Предполагаем, что есть поле с временем обработки
            processing_time = assignment_data.get('processing_time', 0)
            if processing_time > 0:
                total_time += processing_time
                count += 1
                
        return total_time / count if count > 0 else 0.0
        
    def _calculate_throughput(self, requests: List[Any]) -> float:
        """Расчет пропускной способности (заявок в час)"""
        if not requests:
            return 0.0
            
        # Подсчитываем завершенные заявки за последний час
        now = datetime.now()
        hour_ago = now.timestamp() - 3600
        
        completed_count = 0
        for request in requests:
            if hasattr(request, 'dict'):
                request_data = request.dict()
            elif hasattr(request, '__dict__'):
                request_data = request.__dict__
            else:
                request_data = request
                
            if request_data.get('status') == 'completed':
                # Предполагаем, что есть поле с временем завершения
                completed_at = request_data.get('completed_at')
                if completed_at:
                    try:
                        if isinstance(completed_at, str):
                            completed_time = datetime.fromisoformat(completed_at).timestamp()
                        else:
                            completed_time = completed_at.timestamp()
                            
                        if completed_time > hour_ago:
                            completed_count += 1
                    except:
                        pass
                        
        return completed_count

# Глобальный экземпляр сборщика метрик
metrics_collector = RealtimeMetricsCollector()
