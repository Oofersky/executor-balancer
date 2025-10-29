"""
Metrics and Analytics Module
Модуль для работы с метриками, аналитикой и экспортом данных
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from io import BytesIO
import sqlite3
import os

class MetricsCollector:
    """Сборщик метрик системы"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных для метрик"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица для агрегированных метрик
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aggregated_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metric_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для метрик исполнителей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executor_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                executor_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                active_requests INTEGER DEFAULT 0,
                completed_requests INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                response_time REAL DEFAULT 0.0,
                workload_score REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для метрик заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                assignment_time REAL DEFAULT 0.0,
                completion_time REAL DEFAULT 0.0,
                priority_score REAL DEFAULT 0.0,
                complexity_score REAL DEFAULT 0.0,
                satisfaction_score REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для системных метрик
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_executors INTEGER DEFAULT 0,
                active_executors INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                pending_requests INTEGER DEFAULT 0,
                completed_requests INTEGER DEFAULT 0,
                average_response_time REAL DEFAULT 0.0,
                system_load REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def collect_executor_metrics(self, executors: List[Dict]) -> Dict[str, Any]:
        """Сбор метрик исполнителей"""
        if not executors:
            return {}
        
        total_executors = len(executors)
        active_executors = len([e for e in executors if e.get('status') == 'active'])
        total_active_requests = sum(e.get('active_requests_count', 0) for e in executors)
        avg_success_rate = sum(e.get('success_rate', 0) for e in executors) / total_executors if total_executors > 0 else 0
        avg_experience = sum(e.get('experience_years', 0) for e in executors) / total_executors if total_executors > 0 else 0
        
        # Распределение по ролям
        role_distribution = {}
        for executor in executors:
            role = executor.get('role', 'unknown')
            role_distribution[role] = role_distribution.get(role, 0) + 1
        
        # Распределение по нагрузке
        workload_distribution = {
            'low': len([e for e in executors if e.get('active_requests_count', 0) <= 2]),
            'medium': len([e for e in executors if 2 < e.get('active_requests_count', 0) <= 5]),
            'high': len([e for e in executors if e.get('active_requests_count', 0) > 5])
        }
        
        return {
            'total_executors': total_executors,
            'active_executors': active_executors,
            'total_active_requests': total_active_requests,
            'avg_success_rate': round(avg_success_rate, 2),
            'avg_experience': round(avg_experience, 1),
            'role_distribution': role_distribution,
            'workload_distribution': workload_distribution,
            'timestamp': datetime.now().isoformat()
        }
    
    def collect_request_metrics(self, requests: List[Dict]) -> Dict[str, Any]:
        """Сбор метрик заявок"""
        if not requests:
            return {}
        
        total_requests = len(requests)
        pending_requests = len([r for r in requests if r.get('status') == 'pending'])
        assigned_requests = len([r for r in requests if r.get('status') == 'assigned'])
        completed_requests = len([r for r in requests if r.get('status') == 'completed'])
        
        # Распределение по приоритету
        priority_distribution = {}
        for request in requests:
            priority = request.get('priority', 'unknown')
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        # Распределение по категории
        category_distribution = {}
        for request in requests:
            category = request.get('category', 'unknown')
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        # Средняя сложность
        complexity_scores = {'low': 1, 'medium': 2, 'high': 3, 'expert': 4}
        avg_complexity = sum(complexity_scores.get(r.get('complexity', 'medium'), 2) for r in requests) / total_requests if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'pending_requests': pending_requests,
            'assigned_requests': assigned_requests,
            'completed_requests': completed_requests,
            'priority_distribution': priority_distribution,
            'category_distribution': category_distribution,
            'avg_complexity': round(avg_complexity, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def collect_system_metrics(self, executors: List[Dict], requests: List[Dict], assignments: List[Dict]) -> Dict[str, Any]:
        """Сбор системных метрик"""
        executor_metrics = self.collect_executor_metrics(executors)
        request_metrics = self.collect_request_metrics(requests)
        
        # Метрики производительности
        total_assignments = len(assignments)
        successful_assignments = len([a for a in assignments if a.get('status') == 'completed'])
        success_rate = (successful_assignments / total_assignments * 100) if total_assignments > 0 else 0
        
        # Среднее время назначения (симуляция)
        avg_assignment_time = 3.5  # секунды
        
        # Загрузка системы
        system_load = (executor_metrics.get('total_active_requests', 0) / 
                     (executor_metrics.get('active_executors', 1) * 10)) * 100
        
        return {
            'total_executors': executor_metrics.get('total_executors', 0),
            'active_executors': executor_metrics.get('active_executors', 0),
            'total_requests': request_metrics.get('total_requests', 0),
            'pending_requests': request_metrics.get('pending_requests', 0),
            'completed_requests': request_metrics.get('completed_requests', 0),
            'total_assignments': total_assignments,
            'success_rate': round(success_rate, 2),
            'avg_assignment_time': round(avg_assignment_time, 2),
            'system_load': round(min(system_load, 100), 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def save_metrics(self, metrics: Dict[str, Any], metric_type: str):
        """Сохранение метрик в базу данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                cursor.execute('''
                    INSERT INTO aggregated_metrics (timestamp, metric_type, metric_name, metric_value)
                    VALUES (?, ?, ?, ?)
                ''', (timestamp, metric_type, metric_name, metric_value))
        
        conn.commit()
        conn.close()
    
    def get_metrics_history(self, metric_type: str, hours: int = 24) -> List[Dict]:
        """Получение истории метрик"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        
        cursor.execute('''
            SELECT timestamp, metric_name, metric_value, metadata
            FROM aggregated_metrics
            WHERE metric_type = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (metric_type, since))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'timestamp': row[0],
                'metric_name': row[1],
                'metric_value': row[2],
                'metadata': row[3]
            })
        
        conn.close()
        return results

class ExcelExporter:
    """Экспортер метрик в Excel"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
    
    def export_dashboard_metrics(self, executors: List[Dict], requests: List[Dict], 
                               assignments: List[Dict], rules: List[Dict]) -> BytesIO:
        """Экспорт всех метрик дашборда в Excel"""
        
        # Сбор всех метрик
        executor_metrics = self.metrics_collector.collect_executor_metrics(executors)
        request_metrics = self.metrics_collector.collect_request_metrics(requests)
        system_metrics = self.metrics_collector.collect_system_metrics(executors, requests, assignments)
        
        # Создание Excel файла в памяти
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: Общие метрики системы
            system_df = pd.DataFrame([
                {'Метрика': 'Всего исполнителей', 'Значение': system_metrics.get('total_executors', 0)},
                {'Метрика': 'Активных исполнителей', 'Значение': system_metrics.get('active_executors', 0)},
                {'Метрика': 'Всего заявок', 'Значение': system_metrics.get('total_requests', 0)},
                {'Метрика': 'Ожидающих заявок', 'Значение': system_metrics.get('pending_requests', 0)},
                {'Метрика': 'Завершенных заявок', 'Значение': system_metrics.get('completed_requests', 0)},
                {'Метрика': 'Всего назначений', 'Значение': system_metrics.get('total_assignments', 0)},
                {'Метрика': 'Процент успешности', 'Значение': f"{system_metrics.get('success_rate', 0)}%"},
                {'Метрика': 'Среднее время назначения', 'Значение': f"{system_metrics.get('avg_assignment_time', 0)} сек"},
                {'Метрика': 'Загрузка системы', 'Значение': f"{system_metrics.get('system_load', 0)}%"},
            ])
            system_df.to_excel(writer, sheet_name='Системные метрики', index=False)
            
            # Лист 2: Метрики исполнителей
            executor_data = []
            for executor in executors:
                executor_data.append({
                    'ID': executor.get('id', ''),
                    'Имя': executor.get('name', ''),
                    'Email': executor.get('email', ''),
                    'Роль': executor.get('role', ''),
                    'Статус': executor.get('status', ''),
                    'Опыт (лет)': executor.get('experience_years', 0),
                    'Вес': executor.get('weight', 0),
                    'Успешность (%)': executor.get('success_rate', 0) * 100,
                    'Активных заявок': executor.get('active_requests_count', 0),
                    'Дневной лимит': executor.get('daily_limit', 0),
                    'Часовой пояс': executor.get('timezone', ''),
                    'Навыки': ', '.join(executor.get('specialization', '').split(',')[:3]) if executor.get('specialization') else ''
                })
            
            executor_df = pd.DataFrame(executor_data)
            executor_df.to_excel(writer, sheet_name='Исполнители', index=False)
            
            # Лист 3: Метрики заявок
            request_data = []
            for request in requests:
                request_data.append({
                    'ID': request.get('id', ''),
                    'Название': request.get('title', ''),
                    'Описание': request.get('description', '')[:50] + '...' if len(request.get('description', '')) > 50 else request.get('description', ''),
                    'Приоритет': request.get('priority', ''),
                    'Категория': request.get('category', ''),
                    'Сложность': request.get('complexity', ''),
                    'Статус': request.get('status', ''),
                    'Вес': request.get('weight', 0),
                    'Часы': request.get('estimated_hours', 0),
                    'Бюджет': request.get('budget', 0),
                    'Язык': request.get('language_requirement', ''),
                    'Часовой пояс': request.get('timezone_requirement', ''),
                    'Навыки': ', '.join(request.get('required_skills', [])[:3])
                })
            
            request_df = pd.DataFrame(request_data)
            request_df.to_excel(writer, sheet_name='Заявки', index=False)
            
            # Лист 4: Назначения
            assignment_data = []
            for assignment in assignments:
                assignment_data.append({
                    'ID': assignment.get('id', ''),
                    'Заявка ID': assignment.get('request_id', ''),
                    'Исполнитель ID': assignment.get('executor_id', ''),
                    'Статус': assignment.get('status', ''),
                    'Время назначения': assignment.get('assigned_at', ''),
                    'Время завершения': assignment.get('completed_at', ''),
                    'Оценка': assignment.get('rating', ''),
                    'Комментарий': assignment.get('comment', '')[:50] + '...' if len(assignment.get('comment', '')) > 50 else assignment.get('comment', '')
                })
            
            assignment_df = pd.DataFrame(assignment_data)
            assignment_df.to_excel(writer, sheet_name='Назначения', index=False)
            
            # Лист 5: Правила
            rule_data = []
            for rule in rules:
                rule_data.append({
                    'ID': rule.get('id', ''),
                    'Название': rule.get('name', ''),
                    'Описание': rule.get('description', ''),
                    'Приоритет': rule.get('priority', ''),
                    'Активно': rule.get('is_active', False),
                    'Условия': str(rule.get('conditions', [])),
                    'Создано': rule.get('created_at', ''),
                    'Обновлено': rule.get('updated_at', '')
                })
            
            rule_df = pd.DataFrame(rule_data)
            rule_df.to_excel(writer, sheet_name='Правила', index=False)
            
            # Лист 6: Аналитика
            analytics_data = []
            
            # Распределение по ролям
            role_dist = executor_metrics.get('role_distribution', {})
            for role, count in role_dist.items():
                analytics_data.append({
                    'Тип анализа': 'Распределение по ролям',
                    'Категория': role,
                    'Количество': count,
                    'Процент': round(count / executor_metrics.get('total_executors', 1) * 100, 2)
                })
            
            # Распределение по приоритету заявок
            priority_dist = request_metrics.get('priority_distribution', {})
            for priority, count in priority_dist.items():
                analytics_data.append({
                    'Тип анализа': 'Распределение по приоритету',
                    'Категория': priority,
                    'Количество': count,
                    'Процент': round(count / request_metrics.get('total_requests', 1) * 100, 2)
                })
            
            # Распределение по категориям заявок
            category_dist = request_metrics.get('category_distribution', {})
            for category, count in category_dist.items():
                analytics_data.append({
                    'Тип анализа': 'Распределение по категориям',
                    'Категория': category,
                    'Количество': count,
                    'Процент': round(count / request_metrics.get('total_requests', 1) * 100, 2)
                })
            
            analytics_df = pd.DataFrame(analytics_data)
            analytics_df.to_excel(writer, sheet_name='Аналитика', index=False)
        
        output.seek(0)
        return output
    
    def export_executor_performance(self, executors: List[Dict], hours: int = 24) -> BytesIO:
        """Экспорт производительности исполнителей"""
        output = BytesIO()
        
        # Получение истории метрик исполнителей
        history = self.metrics_collector.get_metrics_history('executor', hours)
        
        executor_data = []
        for executor in executors:
            executor_data.append({
                'ID': executor.get('id', ''),
                'Имя': executor.get('name', ''),
                'Роль': executor.get('role', ''),
                'Опыт (лет)': executor.get('experience_years', 0),
                'Успешность (%)': executor.get('success_rate', 0) * 100,
                'Активных заявок': executor.get('active_requests_count', 0),
                'Вес': executor.get('weight', 0),
                'Статус': executor.get('status', ''),
                'Последняя активность': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(executor_data)
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Производительность исполнителей', index=False)
        
        output.seek(0)
        return output
