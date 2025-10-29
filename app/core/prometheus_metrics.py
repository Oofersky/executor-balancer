"""
Prometheus Metrics Integration
Интеграция с Prometheus для сбора метрик системы
"""

from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
import time
from typing import Dict, Any

class PrometheusMetrics:
    """Класс для работы с метриками Prometheus"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Счетчики
        self.requests_total = Counter(
            'executor_balancer_requests_total',
            'Total number of requests processed',
            ['status', 'priority', 'category'],
            registry=self.registry
        )
        
        self.assignments_total = Counter(
            'executor_balancer_assignments_total',
            'Total number of assignments made',
            ['status', 'executor_role'],
            registry=self.registry
        )
        
        self.executors_total = Counter(
            'executor_balancer_executors_total',
            'Total number of executors',
            ['role', 'status'],
            registry=self.registry
        )
        
        # Гистограммы
        self.request_processing_time = Histogram(
            'executor_balancer_request_processing_seconds',
            'Time spent processing requests',
            ['priority', 'complexity'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        self.assignment_time = Histogram(
            'executor_balancer_assignment_seconds',
            'Time spent assigning executors to requests',
            ['executor_role'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )
        
        # Gauges (текущие значения)
        self.active_executors = Gauge(
            'executor_balancer_active_executors',
            'Number of active executors',
            registry=self.registry
        )
        
        self.pending_requests = Gauge(
            'executor_balancer_pending_requests',
            'Number of pending requests',
            registry=self.registry
        )
        
        self.system_load = Gauge(
            'executor_balancer_system_load_percent',
            'System load percentage',
            registry=self.registry
        )
        
        self.executor_workload = Gauge(
            'executor_balancer_executor_workload',
            'Executor workload (active requests)',
            ['executor_id', 'executor_name', 'role'],
            registry=self.registry
        )
        
        self.executor_success_rate = Gauge(
            'executor_balancer_executor_success_rate',
            'Executor success rate',
            ['executor_id', 'executor_name', 'role'],
            registry=self.registry
        )
        
        # Сводки
        self.request_size = Summary(
            'executor_balancer_request_size_bytes',
            'Size of requests',
            registry=self.registry
        )
        
        self.executor_response_time = Summary(
            'executor_balancer_executor_response_seconds',
            'Executor response time',
            ['executor_role'],
            registry=self.registry
        )
    
    def update_executor_metrics(self, executors: list):
        """Обновление метрик исполнителей"""
        active_count = 0
        
        for executor in executors:
            # Обработка как Pydantic модели, так и словарей
            if hasattr(executor, 'dict'):
                executor_data = executor.dict()
            elif hasattr(executor, '__dict__'):
                executor_data = executor.__dict__
            else:
                executor_data = executor
            
            executor_id = str(executor_data.get('id', ''))
            executor_name = executor_data.get('name', 'unknown')
            role = executor_data.get('role', 'unknown')
            status = executor_data.get('status', 'unknown')
            active_requests = executor_data.get('active_requests_count', 0)
            success_rate = executor_data.get('success_rate', 0.0)
            
            # Обновление счетчиков
            self.executors_total.labels(role=role, status=status).inc(0)  # Только обновляем метки
            
            # Обновление gauges
            self.executor_workload.labels(
                executor_id=executor_id,
                executor_name=executor_name,
                role=role
            ).set(active_requests)
            
            self.executor_success_rate.labels(
                executor_id=executor_id,
                executor_name=executor_name,
                role=role
            ).set(success_rate)
            
            if status == 'active':
                active_count += 1
        
        self.active_executors.set(active_count)
    
    def update_request_metrics(self, requests: list):
        """Обновление метрик заявок"""
        pending_count = 0
        
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
            
            # Обновление счетчиков
            self.requests_total.labels(
                status=status,
                priority=priority,
                category=category
            ).inc(0)  # Только обновляем метки
            
            if status == 'pending':
                pending_count += 1
        
        self.pending_requests.set(pending_count)
    
    def update_assignment_metrics(self, assignments: list):
        """Обновление метрик назначений"""
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
            
            # Обновление счетчиков
            self.assignments_total.labels(
                status=status,
                executor_role=executor_role
            ).inc(0)  # Только обновляем метки
    
    def update_system_metrics(self, system_load: float):
        """Обновление системных метрик"""
        self.system_load.set(system_load)
    
    def record_request_processing_time(self, duration: float, priority: str, complexity: str):
        """Запись времени обработки заявки"""
        self.request_processing_time.labels(
            priority=priority,
            complexity=complexity
        ).observe(duration)
    
    def record_assignment_time(self, duration: float, executor_role: str):
        """Запись времени назначения"""
        self.assignment_time.labels(executor_role=executor_role).observe(duration)
    
    def record_request_size(self, size: int):
        """Запись размера заявки"""
        self.request_size.observe(size)
    
    def record_executor_response_time(self, duration: float, executor_role: str):
        """Запись времени ответа исполнителя"""
        self.executor_response_time.labels(executor_role=executor_role).observe(duration)
    
    def get_metrics(self) -> str:
        """Получение метрик в формате Prometheus"""
        return generate_latest(self.registry)
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Получение метрик в виде словаря для API"""
        metrics_data = {}
        
        # Собираем данные из всех метрик
        for metric in self.registry.collect():
            metric_name = metric.name
            metric_type = metric.type
            
            if metric_type == 'counter':
                metrics_data[metric_name] = {
                    'type': 'counter',
                    'help': metric.documentation,
                    'samples': [
                        {
                            'name': sample.name,
                            'labels': sample.labels,
                            'value': sample.value
                        } for sample in metric.samples
                    ]
                }
            elif metric_type == 'gauge':
                metrics_data[metric_name] = {
                    'type': 'gauge',
                    'help': metric.documentation,
                    'samples': [
                        {
                            'name': sample.name,
                            'labels': sample.labels,
                            'value': sample.value
                        } for sample in metric.samples
                    ]
                }
            elif metric_type == 'histogram':
                metrics_data[metric_name] = {
                    'type': 'histogram',
                    'help': metric.documentation,
                    'samples': [
                        {
                            'name': sample.name,
                            'labels': sample.labels,
                            'value': sample.value
                        } for sample in metric.samples
                    ]
                }
            elif metric_type == 'summary':
                metrics_data[metric_name] = {
                    'type': 'summary',
                    'help': metric.documentation,
                    'samples': [
                        {
                            'name': sample.name,
                            'labels': sample.labels,
                            'value': sample.value
                        } for sample in metric.samples
                    ]
                }
        
        return metrics_data

# Глобальный экземпляр метрик
prometheus_metrics = PrometheusMetrics()
