#!/usr/bin/env python3
"""
Executor Balancer - Single File API
Система распределения заявок между исполнителями с метриками в реальном времени
"""

import asyncio
import json
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict, deque
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты для работы с БД
import asyncpg
import redis.asyncio as redis

# Попытка импорта модулей БД (с fallback)
try:
    from app.core.database import DatabaseManager, RedisManager
    from app.services.database_service import DatabaseService
    from app.models.schemas import Executor as DBExecutor, Request as DBRequest, Assignment as DBAssignment
    DB_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Модули БД недоступны: {e}")
    DB_MODULES_AVAILABLE = False
    # Заглушки для случаев когда модули недоступны
    DatabaseManager = None
    RedisManager = None
    DatabaseService = None
    DBExecutor = None
    DBRequest = None
    DBAssignment = None

# =============================================================================
# PYDANTIC МОДЕЛИ
# =============================================================================

class Executor(BaseModel):
    id: Optional[str] = None
    name: str
    email: Optional[str] = None
    role: str
    status: str = "active"
    active_requests_count: int = 0
    daily_limit: int = 10
    success_rate: float = 0.0
    weight: float = 1.0
    skills: List[str] = []
    created_at: Optional[datetime] = None

class Request(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    priority: str = "medium"
    category: str = "general"
    status: str = "pending"
    assigned_executor_id: Optional[str] = None
    weight: float = 1.0
    created_at: Optional[datetime] = None

class Assignment(BaseModel):
    id: Optional[str] = None
    request_id: str
    executor_id: str
    assigned_at: Optional[datetime] = None
    status: str = "active"

class StatsResponse(BaseModel):
    total_executors: int
    active_executors: int
    total_requests: int
    pending_requests: int
    assigned_requests: int
    total_assignments: int

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    cors_enabled: bool = True
    version: str = "1.0.0"

# =============================================================================
# СИСТЕМА МЕТРИК
# =============================================================================

class SimpleMetrics:
    """Простая система метрик для отслеживания статистики"""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.history = defaultdict(lambda: deque(maxlen=100))
        
    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        key = self._make_key(name, labels)
        self.counters[key] += value
        
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        key = self._make_key(name, labels)
        self.gauges[key] = value
        
    def record_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        key = self._make_key(name, labels)
        self.history[key].append({
            'value': value,
            'timestamp': datetime.now().isoformat()
        })
        
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        if labels:
            label_str = ','.join([f"{k}={v}" for k, v in sorted(labels.items())])
            return f"{name}{{{label_str}}}"
        return name
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'timestamp': datetime.now().isoformat()
        }
        
    def get_metric_history(self, name: str, labels: Dict[str, str] = None) -> List[Dict[str, Any]]:
        key = self._make_key(name, labels)
        return list(self.history[key])

class RealtimeMetricsCollector:
    """Сборщик метрик в реальном времени"""
    
    def __init__(self):
        self.metrics = SimpleMetrics()
        
    def collect_executor_metrics(self, executors: List[Executor]) -> Dict[str, Any]:
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
            stats['executors_by_status'][executor.status] += 1
            stats['executors_by_role'][executor.role] += 1
            stats['total_workload'] += executor.active_requests_count
            
            if executor.success_rate > 0:
                success_rates.append(executor.success_rate)
                
            if executor.status == 'active':
                stats['active_executors'] += 1
            else:
                stats['inactive_executors'] += 1
                
        if success_rates:
            stats['average_success_rate'] = sum(success_rates) / len(success_rates)
            
        return stats
        
    def collect_request_metrics(self, requests: List[Request]) -> Dict[str, Any]:
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
            stats['requests_by_status'][request.status] += 1
            stats['requests_by_priority'][request.priority] += 1
            stats['requests_by_category'][request.category] += 1
            
            if request.status == 'pending':
                stats['pending_requests'] += 1
            elif request.status == 'assigned':
                stats['assigned_requests'] += 1
            elif request.status == 'completed':
                stats['completed_requests'] += 1
                
        return stats
        
    def collect_assignment_metrics(self, assignments: List[Assignment]) -> Dict[str, Any]:
        stats = {
            'total_assignments': len(assignments),
            'assignments_by_status': defaultdict(int)
        }
        
        if not assignments:
            return stats
            
        for assignment in assignments:
            stats['assignments_by_status'][assignment.status] += 1
            
        return stats
        
    def collect_system_metrics(self, executors: List[Executor], requests: List[Request], assignments: List[Assignment]) -> Dict[str, Any]:
        executor_stats = self.collect_executor_metrics(executors)
        request_stats = self.collect_request_metrics(requests)
        assignment_stats = self.collect_assignment_metrics(assignments)
        
        # Расчет системной загрузки
        total_capacity = executor_stats['total_executors'] * 10
        current_load = executor_stats['total_workload']
        system_load = (current_load / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            'system_load_percent': min(system_load, 100),
            'efficiency_score': self._calculate_efficiency(executor_stats, request_stats),
            'executor_stats': executor_stats,
            'request_stats': request_stats,
            'assignment_stats': assignment_stats
        }
        
    def _calculate_efficiency(self, executor_stats: Dict, request_stats: Dict) -> float:
        if executor_stats['active_executors'] == 0:
            return 0.0
            
        utilization = executor_stats['total_workload'] / executor_stats['active_executors']
        success_rate = executor_stats['average_success_rate']
        
        return min((utilization * success_rate) / 10 * 100, 100)

# =============================================================================
# WEBSOCKET МЕНЕДЖЕР
# =============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

# =============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# =============================================================================

# Базы данных в памяти (fallback)
executors_db: List[Executor] = []
requests_db: List[Request] = []
assignments_db: List[Assignment] = []

# Сервисы
metrics_collector = RealtimeMetricsCollector()
manager = ConnectionManager()

# База данных
db_manager: Optional[DatabaseManager] = None
redis_manager: Optional[RedisManager] = None
db_service: Optional[DatabaseService] = None

# Настройки БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/executor_balancer")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
USE_DATABASE = os.getenv("USE_DATABASE", "true").lower() == "true"

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# =============================================================================

async def init_database():
    """Инициализация базы данных"""
    global db_manager, redis_manager, db_service
    
    if not USE_DATABASE or not DB_MODULES_AVAILABLE:
        logger.info("🗄️ Использование базы данных отключено, работаем в памяти")
        return
    
    try:
        # Инициализация PostgreSQL
        db_manager = DatabaseManager(DATABASE_URL)
        await db_manager.init_pool()
        await db_manager.create_tables()
        logger.info("✅ PostgreSQL подключен успешно")
        
        # Инициализация Redis
        redis_manager = RedisManager(REDIS_URL)
        await redis_manager.init_connection()
        logger.info("✅ Redis подключен успешно")
        
        # Инициализация сервиса БД
        db_service = DatabaseService()
        logger.info("✅ Сервис базы данных инициализирован")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        logger.info("🔄 Переключение на работу в памяти")
        db_manager = None
        redis_manager = None
        db_service = None

async def cleanup_database():
    """Очистка ресурсов базы данных"""
    if db_manager:
        await db_manager.close_pool()
    if redis_manager:
        await redis_manager.close_connection()

# =============================================================================
# FASTAPI ПРИЛОЖЕНИЕ
# =============================================================================

app = FastAPI(
    title="Executor Balancer API",
    description="Система распределения заявок между исполнителями с метриками в реальном времени",
    version="1.0.0"
)

# События запуска и остановки
@app.on_event("startup")
async def startup_event():
    """Событие запуска приложения"""
    await init_database()

@app.on_event("shutdown")
async def shutdown_event():
    """Событие остановки приложения"""
    await cleanup_database()

# Настройка шаблонов и статических файлов
templates = Jinja2Templates(directory="templates")

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# HTML СТРАНИЦЫ (загружаются из папки templates)
# =============================================================================

# Функции для загрузки HTML шаблонов
async def load_template(template_name: str, context: dict = None) -> str:
    """Загрузка HTML шаблона из папки templates"""
    try:
        template_path = os.path.join("templates", template_name)
        if os.path.exists(template_path):
            logger.info(f"Загружаем шаблон: {template_name}")
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Простая замена переменных в шаблоне
                if context:
                    for key, value in context.items():
                        content = content.replace(f"{{{{{key}}}}}", str(value))
                logger.info(f"Шаблон {template_name} успешно загружен")
                return content
        else:
            logger.warning(f"Шаблон {template_name} не найден в {template_path}, используется fallback")
            return get_fallback_html(template_name)
    except Exception as e:
        logger.error(f"Ошибка загрузки шаблона {template_name}: {e}")
        return get_fallback_html(template_name)

def get_fallback_html(template_name: str) -> str:
    """Fallback HTML если шаблон не найден"""
    if template_name == "dashboard.html":
        return DASHBOARD_HTML_FALLBACK
    elif template_name == "guide.html":
        return GUIDE_HTML_FALLBACK
    elif template_name == "demo.html":
        return DEMO_HTML_FALLBACK
    elif template_name == "index.html":
        return MAIN_PAGE_HTML_FALLBACK
    else:
        return "<html><body><h1>Страница не найдена</h1></body></html>"

# Fallback HTML шаблоны (если внешние файлы недоступны)
DASHBOARD_HTML_FALLBACK = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executor Balancer - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="/static/js/app.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-align: center;
        }

        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 15px;
        }

        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .status-online { background-color: #27ae60; }
        .status-offline { background-color: #e74c3c; }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }

        .card h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.3em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }

        .stat-item {
            text-align: center;
            padding: 15px;
            background: rgba(52, 152, 219, 0.1);
            border-radius: 10px;
            border: 1px solid rgba(52, 152, 219, 0.2);
        }

        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #3498db;
        }

        .stat-label {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 5px;
        }

        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 15px;
        }

        .realtime-indicator {
            position: absolute;
            top: 10px;
            right: 10px;
            background: #27ae60;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0.5; }
        }

        .refresh-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            transition: background 0.3s ease;
        }

        .refresh-btn:hover {
            background: #2980b9;
        }

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .status-bar {
                flex-direction: column;
                gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Executor Balancer Dashboard</h1>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-indicator status-online" id="connectionStatus"></div>
                    <span id="connectionText">Подключено</span>
                </div>
                <div class="status-item">
                    <span>Последнее обновление: <strong id="lastUpdate">--</strong></span>
                </div>
                <button class="refresh-btn" onclick="refreshData()">🔄 Обновить</button>
            </div>
        </div>

        <div class="dashboard-grid">
            <!-- Общая статистика -->
            <div class="card">
                <h3>📊 Общая статистика</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="totalExecutors">0</div>
                        <div class="stat-label">Исполнителей</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="totalRequests">0</div>
                        <div class="stat-label">Заявок</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="totalAssignments">0</div>
                        <div class="stat-label">Назначений</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="systemLoad">0%</div>
                        <div class="stat-label">Загрузка системы</div>
                    </div>
                </div>
            </div>

            <!-- Статус исполнителей -->
            <div class="card">
                <h3>👥 Исполнители по статусам</h3>
                <div class="chart-container">
                    <div class="realtime-indicator">LIVE</div>
                    <canvas id="executorsChart"></canvas>
                </div>
            </div>

            <!-- Статус заявок -->
            <div class="card">
                <h3>📋 Заявки по статусам</h3>
                <div class="chart-container">
                    <div class="realtime-indicator">LIVE</div>
                    <canvas id="requestsChart"></canvas>
                </div>
            </div>

            <!-- Приоритеты заявок -->
            <div class="card">
                <h3>⚡ Приоритеты заявок</h3>
                <div class="chart-container">
                    <div class="realtime-indicator">LIVE</div>
                    <canvas id="priorityChart"></canvas>
                </div>
            </div>

            <!-- График в реальном времени -->
            <div class="card" style="grid-column: 1 / -1;">
                <h3>📈 Заявки в реальном времени</h3>
                <div class="chart-container">
                    <div class="realtime-indicator">LIVE</div>
                    <canvas id="realtimeChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket подключение
        let ws;
        let charts = {};
        let realtimeData = {
            labels: [],
            datasets: [{
                label: 'Заявки',
                data: [],
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                tension: 0.4
            }]
        };

        // Подключение к WebSocket
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                document.getElementById('connectionStatus').className = 'status-indicator status-online';
                document.getElementById('connectionText').textContent = 'Подключено';
                console.log('WebSocket подключен');
            };
            
            ws.onclose = function() {
                document.getElementById('connectionStatus').className = 'status-indicator status-offline';
                document.getElementById('connectionText').textContent = 'Отключено';
                console.log('WebSocket отключен');
                
                // Переподключение через 3 секунды
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('Ошибка WebSocket:', error);
                document.getElementById('connectionStatus').className = 'status-indicator status-offline';
                document.getElementById('connectionText').textContent = 'Ошибка подключения';
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'dashboard_update') {
                        updateDashboard(data.data);
                    }
                } catch (error) {
                    console.error('Ошибка парсинга данных:', error);
                }
            };
        }

        // Инициализация графиков
        function initCharts() {
            // График исполнителей
            charts.executors = new Chart(document.getElementById('executorsChart'), {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: ['#27ae60', '#e74c3c', '#f39c12', '#9b59b6']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });

            // График заявок
            charts.requests = new Chart(document.getElementById('requestsChart'), {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: ['#3498db', '#e67e22', '#95a5a6', '#1abc9c']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });

            // График приоритетов
            charts.priority = new Chart(document.getElementById('priorityChart'), {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Количество',
                        data: [],
                        backgroundColor: ['#e74c3c', '#f39c12', '#27ae60']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });

            // График в реальном времени
            charts.realtime = new Chart(document.getElementById('realtimeChart'), {
                type: 'line',
                data: realtimeData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    animation: {
                        duration: 750
                    }
                }
            });
        }

        // Обновление дашборда
        function updateDashboard(data) {
            // Обновление общих метрик
            document.getElementById('totalExecutors').textContent = data.total_executors || 0;
            document.getElementById('totalRequests').textContent = data.total_requests || 0;
            document.getElementById('totalAssignments').textContent = data.total_assignments || 0;
            document.getElementById('systemLoad').textContent = Math.round(data.system_load_percent || 0) + '%';

            // Обновление времени
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();

            // Обновление графиков
            if (data.executors_by_status) {
                charts.executors.data.labels = Object.keys(data.executors_by_status);
                charts.executors.data.datasets[0].data = Object.values(data.executors_by_status);
                charts.executors.update();
            }

            if (data.requests_by_status) {
                charts.requests.data.labels = Object.keys(data.requests_by_status);
                charts.requests.data.datasets[0].data = Object.values(data.requests_by_status);
                charts.requests.update();
            }

            if (data.requests_by_priority) {
                charts.priority.data.labels = Object.keys(data.requests_by_priority);
                charts.priority.data.datasets[0].data = Object.values(data.requests_by_priority);
                charts.priority.update();
            }

            // Обновление графика в реальном времени
            const now = new Date().toLocaleTimeString();
            realtimeData.labels.push(now);
            realtimeData.datasets[0].data.push(data.total_requests || 0);

            // Ограничиваем количество точек
            if (realtimeData.labels.length > 20) {
                realtimeData.labels.shift();
                realtimeData.datasets[0].data.shift();
            }

            charts.realtime.update();
        }

        // Загрузка данных
        async function loadData() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Ошибка загрузки данных:', error);
            }
        }

        // Обновление данных
        function refreshData() {
            loadData();
        }

        // Автоматическое обновление каждые 5 секунд
        setInterval(loadData, 5000);

        // Инициализация при загрузке страницы
        document.addEventListener('DOMContentLoaded', () => {
            initCharts();
            connectWebSocket();
            loadData();
        });
    </script>
</body>
</html>
"""

GUIDE_HTML_FALLBACK = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executor Balancer - Руководство пользователя</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .hero-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 80px 0;
        }
        .feature-card {
            transition: transform 0.3s;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }
        .step-number {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 15px;
        }
        .algorithm-step {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }
        .code-example {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            margin: 10px 0;
        }
        .metric-highlight {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .nav-link.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-balance-scale"></i> Executor Balancer
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/">Главная</a>
                <a class="nav-link" href="/app">Приложение</a>
                <a class="nav-link" href="/demo">Демо</a>
                <a class="nav-link" href="/docs">API Документация</a>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <div class="hero-section">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-lg-8">
                    <h1 class="display-4 fw-bold mb-4">
                        <i class="fas fa-balance-scale"></i> Executor Balancer
                    </h1>
                    <p class="lead mb-4">
                        Интеллектуальная система справедливого распределения заявок между исполнителями 
                        с поддержкой динамических правил и точного поиска
                    </p>
                    <div class="d-flex gap-3">
                        <a href="/app" class="btn btn-light btn-lg">
                            <i class="fas fa-rocket"></i> Запустить приложение
                        </a>
                        <a href="#features" class="btn btn-outline-light btn-lg">
                            <i class="fas fa-info-circle"></i> Узнать больше
                        </a>
                    </div>
                </div>
                <div class="col-lg-4 text-center">
                    <div class="metric-highlight">
                        <h3>4000+</h3>
                        <p>заявок в час</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Features Section -->
    <section id="features" class="py-5">
        <div class="container">
            <div class="text-center mb-5">
                <h2 class="display-5 fw-bold">Ключевые возможности</h2>
                <p class="lead text-muted">Современное решение для автоматизации распределения задач</p>
            </div>
            
            <div class="row g-4">
                <div class="col-md-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <div class="mb-3">
                                <i class="fas fa-cogs fa-3x text-primary"></i>
                            </div>
                            <h5 class="card-title">Конструктор правил</h5>
                            <p class="card-text">
                                Создавайте гибкие правила распределения с 20+ параметрами исполнителей 
                                и заявок. Поддержка всех операторов сравнения.
                            </p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <div class="mb-3">
                                <i class="fas fa-search fa-3x text-success"></i>
                            </div>
                            <h5 class="card-title">Точный поиск</h5>
                            <p class="card-text">
                                Интеллектуальный алгоритм поиска исполнителей с рейтинговой системой, 
                                учитывающий навыки, опыт и справедливое распределение.
                            </p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <div class="mb-3">
                                <i class="fas fa-chart-line fa-3x text-warning"></i>
                            </div>
                            <h5 class="card-title">Аналитика и мониторинг</h5>
                            <p class="card-text">
                                Дашборд в реальном времени с метриками эффективности, 
                                статистикой распределения и KPI исполнителей.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- How to Use Section -->
    <section class="py-5 bg-light">
        <div class="container">
            <div class="text-center mb-5">
                <h2 class="display-5 fw-bold">Как использовать сервис</h2>
                <p class="lead text-muted">Пошаговое руководство по работе с системой</p>
            </div>

            <div class="row">
                <div class="col-lg-8 mx-auto">
                    <!-- Step 1 -->
                    <div class="d-flex align-items-start mb-4">
                        <div class="step-number">1</div>
                        <div>
                            <h4>Добавление исполнителей</h4>
                            <p>Создайте профили исполнителей с указанием роли, навыков, опыта и других параметров.</p>
                            <div class="code-example">
                                Роль: Программист<br>
                                Навыки: Python, JavaScript, React<br>
                                Опыт: 5 лет<br>
                                Вес: 0.9
                            </div>
                        </div>
                    </div>

                    <!-- Step 2 -->
                    <div class="d-flex align-items-start mb-4">
                        <div class="step-number">2</div>
                        <div>
                            <h4>Создание правил распределения</h4>
                            <p>Настройте правила с помощью конструктора. Определите условия для автоматического назначения.</p>
                            <div class="code-example">
                                Условие: роль == "программист" И вес > 0.7<br>
                                Приоритет: Высокий<br>
                                Активность: Включено
                            </div>
                        </div>
                    </div>

                    <!-- Step 3 -->
                    <div class="d-flex align-items-start mb-4">
                        <div class="step-number">3</div>
                        <div>
                            <h4>Создание заявки</h4>
                            <p>Опишите заявку с указанием требований, навыков, приоритета и других параметров.</p>
                            <div class="code-example">
                                Название: Разработка веб-приложения<br>
                                Категория: Разработка<br>
                                Навыки: Python, React<br>
                                Приоритет: Высокий
                            </div>
                        </div>
                    </div>

                    <!-- Step 4 -->
                    <div class="d-flex align-items-start mb-4">
                        <div class="step-number">4</div>
                        <div>
                            <h4>Поиск исполнителей</h4>
                            <p>Система автоматически найдет подходящих исполнителей с объяснением выбора.</p>
                            <div class="code-example">
                                Результат поиска:<br>
                                1. Алексей Петров - 95% соответствие<br>
                                2. Мария Сидорова - 87% соответствие<br>
                                3. Дмитрий Козлов - 82% соответствие
                            </div>
                        </div>
                    </div>

                    <!-- Step 5 -->
                    <div class="d-flex align-items-start mb-4">
                        <div class="step-number">5</div>
                        <div>
                            <h4>Назначение и мониторинг</h4>
                            <p>Назначьте исполнителя и отслеживайте прогресс через дашборд.</p>
                            <div class="code-example">
                                Статус: Назначен<br>
                                Исполнитель: Алексей Петров<br>
                                Время назначения: 2025-10-28 23:15:00
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Algorithm Explanation -->
    <section class="py-5">
        <div class="container">
            <div class="text-center mb-5">
                <h2 class="display-5 fw-bold">Алгоритм поиска исполнителей</h2>
                <p class="lead text-muted">Как система выбирает лучшего исполнителя для заявки</p>
            </div>

            <div class="row">
                <div class="col-lg-10 mx-auto">
                    <div class="algorithm-step">
                        <h5><i class="fas fa-filter"></i> Этап 1: Фильтрация</h5>
                        <p>Система отбирает только активных исполнителей, не превысивших дневной лимит заявок.</p>
                    </div>

                    <div class="algorithm-step">
                        <h5><i class="fas fa-calculator"></i> Этап 2: Оценка соответствия</h5>
                        <p>Для каждого исполнителя рассчитывается балл соответствия по 6 критериям:</p>
                        <ul>
                            <li><strong>Роль-категория:</strong> до 20 баллов</li>
                            <li><strong>Опыт работы:</strong> до 15 баллов</li>
                            <li><strong>Языковые навыки:</strong> до 10 баллов</li>
                            <li><strong>Часовой пояс:</strong> до 5 баллов</li>
                            <li><strong>Технические навыки:</strong> до 20 баллов</li>
                            <li><strong>Приоритет заявки:</strong> до 10 баллов</li>
                        </ul>
                    </div>

                    <div class="algorithm-step">
                        <h5><i class="fas fa-balance-scale"></i> Этап 3: Справедливое распределение</h5>
                        <p>К базовому баллу добавляются бонусы и штрафы:</p>
                        <ul>
                            <li><strong>Бонус за вес исполнителя:</strong> до 20 баллов</li>
                            <li><strong>Бонус за успешность:</strong> до 15 баллов</li>
                            <li><strong>Бонус за опыт:</strong> до 10 баллов</li>
                            <li><strong>Штраф за перегрузку:</strong> -5 баллов за каждую активную заявку</li>
                        </ul>
                    </div>

                    <div class="algorithm-step">
                        <h5><i class="fas fa-trophy"></i> Этап 4: Выбор лучшего</h5>
                        <p>Исполнители сортируются по финальному баллу. Система возвращает топ-10 кандидатов с объяснением выбора.</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- API Documentation -->
    <section class="py-5 bg-light">
        <div class="container">
            <div class="text-center mb-5">
                <h2 class="display-5 fw-bold">API Endpoints</h2>
                <p class="lead text-muted">Интеграция с внешними системами</p>
            </div>

            <div class="row">
                <div class="col-lg-8 mx-auto">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Метод</th>
                                    <th>Endpoint</th>
                                    <th>Описание</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><span class="badge bg-success">POST</span></td>
                                    <td><code>/api/executors</code></td>
                                    <td>Создание исполнителя</td>
                                </tr>
                                <tr>
                                    <td><span class="badge bg-primary">GET</span></td>
                                    <td><code>/api/executors</code></td>
                                    <td>Получение списка исполнителей</td>
                                </tr>
                                <tr>
                                    <td><span class="badge bg-success">POST</span></td>
                                    <td><code>/api/requests</code></td>
                                    <td>Создание заявки</td>
                                </tr>
                                <tr>
                                    <td><span class="badge bg-primary">GET</span></td>
                                    <td><code>/api/dashboard</code></td>
                                    <td>Получение данных дашборда</td>
                                </tr>
                                <tr>
                                    <td><span class="badge bg-primary">GET</span></td>
                                    <td><code>/api/stats</code></td>
                                    <td>Получение статистики системы</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="text-center mt-4">
                        <a href="/docs" class="btn btn-primary btn-lg">
                            <i class="fas fa-book"></i> Полная документация API
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Performance Metrics -->
    <section class="py-5">
        <div class="container">
            <div class="text-center mb-5">
                <h2 class="display-5 fw-bold">Производительность системы</h2>
                <p class="lead text-muted">Ключевые показатели эффективности</p>
            </div>

            <div class="row g-4">
                <div class="col-md-3">
                    <div class="text-center">
                        <div class="metric-highlight">
                            <h3>4000+</h3>
                            <p>заявок в час</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <div class="metric-highlight">
                            <h3>±1-2%</h3>
                            <p>погрешность распределения</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <div class="metric-highlight">
                            <h3>20+</h3>
                            <p>параметров исполнителя</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <div class="metric-highlight">
                            <h3>2-10 сек</h3>
                            <p>время назначения</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Call to Action -->
    <section class="py-5 bg-primary text-white">
        <div class="container text-center">
            <h2 class="display-5 fw-bold mb-4">Готовы начать?</h2>
            <p class="lead mb-4">
                Запустите Executor Balancer и начните справедливо распределять заявки между исполнителями
            </p>
            <a href="/app" class="btn btn-light btn-lg me-3">
                <i class="fas fa-rocket"></i> Запустить приложение
            </a>
            <a href="/docs" class="btn btn-outline-light btn-lg">
                <i class="fas fa-book"></i> API Документация
            </a>
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-dark text-white py-4">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <h5><i class="fas fa-balance-scale"></i> Executor Balancer</h5>
                    <p class="text-muted">Система справедливого распределения заявок между исполнителями</p>
                </div>
                <div class="col-md-6 text-end">
                    <p class="text-muted mb-0">
                        © 2025 Executor Balancer. Создано для хакатона Цунами.
                    </p>
                </div>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

DEMO_HTML_FALLBACK = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executor Balancer - Демо</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .demo-card {
            transition: transform 0.3s;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .demo-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }
        .executor-card {
            border-left: 4px solid #28a745;
            margin: 10px 0;
        }
        .request-card {
            border-left: 4px solid #007bff;
            margin: 10px 0;
        }
        .rule-card {
            border-left: 4px solid #ffc107;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-balance-scale"></i> Executor Balancer
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/">Главная</a>
                <a class="nav-link" href="/app">Приложение</a>
                <a class="nav-link" href="/demo">Демо</a>
                <a class="nav-link" href="/docs">API Документация</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <h1 class="display-4 text-center mb-5">
                    <i class="fas fa-play-circle"></i> Демонстрация системы
                </h1>
            </div>
        </div>

        <!-- Metrics -->
        <div class="row mb-5">
            <div class="col-md-3">
                <div class="metric-card">
                    <h3>5</h3>
                    <p>Исполнителей</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <h3>5</h3>
                    <p>Заявок</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <h3>3</h3>
                    <p>Назначений</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <h3>95%</h3>
                    <p>Точность</p>
                </div>
            </div>
        </div>

        <!-- Executors -->
        <div class="row mb-5">
            <div class="col-12">
                <h3><i class="fas fa-users"></i> Исполнители</h3>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card executor-card">
                            <div class="card-body">
                                <h5 class="card-title">Алексей Иванов</h5>
                                <p class="card-text text-muted">Senior Developer</p>
                                <div class="mb-2">
                                    <span class="badge bg-primary">Senior</span>
                                    <span class="badge bg-success">Активный</span>
                                    <span class="badge bg-info">Заявок: 2</span>
                                </div>
                                <small class="text-muted">
                                    Навыки: Python, FastAPI, PostgreSQL | Успешность: 95%
                                </small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card executor-card">
                            <div class="card-body">
                                <h5 class="card-title">Мария Петрова</h5>
                                <p class="card-text text-muted">Middle Developer</p>
                                <div class="mb-2">
                                    <span class="badge bg-warning">Middle</span>
                                    <span class="badge bg-success">Активный</span>
                                    <span class="badge bg-info">Заявок: 1</span>
                                </div>
                                <small class="text-muted">
                                    Навыки: JavaScript, React, Node.js | Успешность: 88%
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-md-6">
                        <div class="card executor-card">
                            <div class="card-body">
                                <h5 class="card-title">Дмитрий Сидоров</h5>
                                <p class="card-text text-muted">Junior Developer</p>
                                <div class="mb-2">
                                    <span class="badge bg-secondary">Junior</span>
                                    <span class="badge bg-success">Активный</span>
                                    <span class="badge bg-info">Заявок: 0</span>
                                </div>
                                <small class="text-muted">
                                    Навыки: HTML, CSS, JavaScript | Успешность: 75%
                                </small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card executor-card">
                            <div class="card-body">
                                <h5 class="card-title">Елена Козлова</h5>
                                <p class="card-text text-muted">DevOps Engineer</p>
                                <div class="mb-2">
                                    <span class="badge bg-danger">DevOps</span>
                                    <span class="badge bg-secondary">Неактивный</span>
                                    <span class="badge bg-info">Заявок: 0</span>
                                </div>
                                <small class="text-muted">
                                    Навыки: Docker, Kubernetes, AWS | Успешность: 92%
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Requests -->
        <div class="row mb-5">
            <div class="col-12">
                <h3><i class="fas fa-tasks"></i> Заявки</h3>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card request-card">
                            <div class="card-body">
                                <h5 class="card-title">Разработка API для мобильного приложения</h5>
                                <p class="card-text">Необходимо создать REST API для мобильного приложения с аутентификацией</p>
                                <div class="mb-2">
                                    <span class="badge bg-danger">Высокий</span>
                                    <span class="badge bg-success">Назначен</span>
                                    <span class="badge bg-info">Разработка</span>
                                </div>
                                <small class="text-muted">
                                    Назначен: Алексей Иванов | Создано: 2025-10-29
                                </small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card request-card">
                            <div class="card-body">
                                <h5 class="card-title">Оптимизация базы данных</h5>
                                <p class="card-text">Требуется оптимизировать производительность PostgreSQL</p>
                                <div class="mb-2">
                                    <span class="badge bg-warning">Средний</span>
                                    <span class="badge bg-secondary">Ожидает</span>
                                    <span class="badge bg-info">Оптимизация</span>
                                </div>
                                <small class="text-muted">
                                    Статус: Ожидает назначения | Создано: 2025-10-29
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Algorithm Demo -->
        <div class="row mb-5">
            <div class="col-12">
                <h3><i class="fas fa-brain"></i> Пример работы алгоритма</h3>
                <div class="card">
                    <div class="card-body">
                        <h5>Заявка: "Разработка API для мобильного приложения"</h5>
                        <p><strong>Параметры:</strong> Категория: development, Навыки: Python, FastAPI, Приоритет: high</p>
                        
                        <div class="row mt-4">
                            <div class="col-md-6">
                                <h6>Результат поиска:</h6>
                                <div class="list-group">
                                    <div class="list-group-item">
                                        <div class="d-flex w-100 justify-content-between">
                                            <h6 class="mb-1">1. Алексей Иванов</h6>
                                            <small class="text-success">95% соответствие</small>
                                        </div>
                                        <p class="mb-1">Senior Developer | Совпадение навыков: 100%</p>
                                        <small>Причины: Опыт (+15), Навыки (+20), Успешность (+15), Вес (+20)</small>
                                    </div>
                                    <div class="list-group-item">
                                        <div class="d-flex w-100 justify-content-between">
                                            <h6 class="mb-1">2. Мария Петрова</h6>
                                            <small class="text-primary">87% соответствие</small>
                                        </div>
                                        <p class="mb-1">Middle Developer | Совпадение навыков: 60%</p>
                                        <small>Причины: Опыт (+10), Навыки (+12), Успешность (+12), Вес (+15)</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h6>Почему Алексей первый?</h6>
                                <ul class="list-unstyled">
                                    <li><i class="fas fa-check text-success"></i> <strong>Полное соответствие навыков:</strong> Python, FastAPI</li>
                                    <li><i class="fas fa-check text-success"></i> <strong>Высокий опыт:</strong> Senior уровень</li>
                                    <li><i class="fas fa-check text-success"></i> <strong>Отличная успешность:</strong> 95%</li>
                                    <li><i class="fas fa-check text-success"></i> <strong>Справедливое распределение:</strong> 2 активные заявки</li>
                                </ul>
                                <div class="alert alert-info">
                                    <small><strong>Вывод:</strong> Алгоритм учитывает не только соответствие навыкам, но и справедливое распределение нагрузки!</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Call to Action -->
        <div class="row">
            <div class="col-12 text-center">
                <div class="card bg-primary text-white">
                    <div class="card-body">
                        <h3>Готовы попробовать?</h3>
                        <p class="lead">Запустите приложение и создайте свою первую заявку</p>
                        <a href="/app" class="btn btn-light btn-lg me-3">
                            <i class="fas fa-rocket"></i> Запустить приложение
                        </a>
                        <a href="/dashboard" class="btn btn-outline-light btn-lg">
                            <i class="fas fa-chart-line"></i> Дашборд
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer class="bg-dark text-white py-4 mt-5">
        <div class="container text-center">
            <p class="mb-0">© 2025 Executor Balancer. Создано для хакатона Цунами.</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

MAIN_PAGE_HTML_FALLBACK = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executor Balancer</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
            text-align: center;
            max-width: 600px;
        }
        h1 {
            color: #2c3e50;
            font-size: 3em;
            margin-bottom: 20px;
        }
        .subtitle {
            color: #7f8c8d;
            font-size: 1.2em;
            margin-bottom: 40px;
        }
        .nav-links {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .nav-link {
            background: #3498db;
            color: white;
            text-decoration: none;
            padding: 20px;
            border-radius: 15px;
            font-size: 1.1em;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
        }
        .nav-link:hover {
            background: #2980b9;
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(52, 152, 219, 0.4);
        }
        .status {
            background: #27ae60;
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            display: inline-block;
            margin-bottom: 20px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="status">🟢 Система работает</div>
        <h1>🚀 Executor Balancer</h1>
        <p class="subtitle">Система распределения заявок между исполнителями с метриками в реальном времени</p>
        
        <div class="nav-links">
            <a href="/guide" class="nav-link">📖 Руководство</a>
            <a href="/demo" class="nav-link">🎮 Демо</a>
            <a href="/dashboard" class="nav-link">📊 Дашборд</a>
            <a href="/docs" class="nav-link">📚 API Документация</a>
            <a href="/health" class="nav-link">❤️ Статус системы</a>
        </div>
    </div>
</body>
</html>
"""

# =============================================================================
# API ЭНДПОИНТЫ
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница"""
    try:
        return HTMLResponse(content=await load_template("guide.html"))
    except Exception as e:
        logger.error(f"Ошибка загрузки главной страницы: {e}")
        return HTMLResponse(content=GUIDE_HTML_FALLBACK)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Дашборд с метриками в реальном времени"""
    try:
        return HTMLResponse(content=await load_template("dashboard.html"))
    except Exception as e:
        logger.error(f"Ошибка загрузки дашборда: {e}")
        return HTMLResponse(content=DASHBOARD_HTML_FALLBACK)

@app.get("/guide", response_class=HTMLResponse)
async def guide():
    """Руководство пользователя"""
    try:
        return HTMLResponse(content=await load_template("guide.html"))
    except Exception as e:
        logger.error(f"Ошибка загрузки руководства: {e}")
        return HTMLResponse(content=GUIDE_HTML_FALLBACK)

@app.get("/demo", response_class=HTMLResponse)
async def demo():
    """Демонстрация системы"""
    try:
        return HTMLResponse(content=await load_template("demo.html"))
    except Exception as e:
        logger.error(f"Ошибка загрузки демо: {e}")
        return HTMLResponse(content=DEMO_HTML_FALLBACK)

@app.get("/favicon.ico")
async def favicon():
    """Favicon"""
    try:
        favicon_path = os.path.join("static", "favicon.ico")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path)
        else:
            # Возвращаем пустой ответ вместо ошибки
            return HTMLResponse(content="", status_code=404)
    except:
        return HTMLResponse(content="", status_code=404)

@app.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    """Обслуживание статических файлов"""
    try:
        static_file_path = os.path.join("static", file_path)
        if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
            return FileResponse(static_file_path)
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Ошибка обслуживания статического файла {file_path}: {e}")
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/app", response_class=HTMLResponse)
async def app_page():
    """Страница приложения"""
    try:
        return HTMLResponse(content=await load_template("index.html"))
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы приложения: {e}")
        return HTMLResponse(content=MAIN_PAGE_HTML_FALLBACK)

@app.get("/health", response_model=HealthResponse)
async def health():
    """Проверка состояния системы"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        cors_enabled=True,
        version="1.0.0"
    )

# WebSocket для обновлений в реальном времени
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                await asyncio.sleep(2)
                dashboard_data = await get_dashboard_data()
                await manager.broadcast({
                    "type": "dashboard_update",
                    "data": dashboard_data
                })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

# API для получения данных дашборда
@app.get("/api/dashboard")
async def get_dashboard_data():
    """Получение данных для дашборда"""
    try:
        # Собираем метрики
        executor_metrics = metrics_collector.collect_executor_metrics(executors_db)
        request_metrics = metrics_collector.collect_request_metrics(requests_db)
        assignment_metrics = metrics_collector.collect_assignment_metrics(assignments_db)
        system_metrics = metrics_collector.collect_system_metrics(executors_db, requests_db, assignments_db)
        
        # Формируем ответ
        dashboard_data = {
            'total_executors': executor_metrics['total_executors'],
            'active_executors': executor_metrics['active_executors'],
            'total_requests': request_metrics['total_requests'],
            'pending_requests': request_metrics['pending_requests'],
            'assigned_requests': request_metrics['assigned_requests'],
            'completed_requests': request_metrics['completed_requests'],
            'total_assignments': assignment_metrics['total_assignments'],
            'system_load_percent': system_metrics['system_load_percent'],
            'efficiency_score': system_metrics['efficiency_score'],
            'executors_by_status': dict(executor_metrics['executors_by_status']),
            'executors_by_role': dict(executor_metrics['executors_by_role']),
            'requests_by_status': dict(request_metrics['requests_by_status']),
            'requests_by_priority': dict(request_metrics['requests_by_priority']),
            'requests_by_category': dict(request_metrics['requests_by_category']),
            'assignments_by_status': dict(assignment_metrics['assignments_by_status']),
            'timestamp': datetime.now().isoformat()
        }
        
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CRUD операции для исполнителей
# Эндпоинты для создания исполнителей (разные URL)
@app.post("/api/executors", response_model=Executor)
async def create_executor(executor: Executor):
    """Создание исполнителя"""
    if db_service and db_manager:
        try:
            # Конвертируем в модель БД
            db_executor = DBExecutor(
                name=executor.name,
                email=f"{executor.name.lower().replace(' ', '.')}@example.com",  # Генерируем email
                role=executor.role,
                weight=0.8,  # По умолчанию
                status=executor.status,
                active_requests_count=executor.active_requests_count,
                success_rate=executor.success_rate,
                experience_years=3,  # По умолчанию
                specialization="",  # Будет заполнено из skills
                language_skills="ru",
                timezone="MSK",
                daily_limit=executor.daily_limit,
                parameters={"skills": executor.skills}
            )
            
            created_executor = await db_service.create_executor(db_executor)
            
            # Конвертируем обратно в простую модель
            executor.id = created_executor.id
            executor.created_at = datetime.now()
            
            logger.info(f"✅ Исполнитель {executor.name} создан в БД")
            return executor
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания исполнителя в БД: {e}")
            # Fallback на работу в памяти
            pass
    
    # Fallback: работа в памяти
    executor.id = str(uuid.uuid4())
    executor.created_at = datetime.now()
    executors_db.append(executor)
    logger.info(f"✅ Исполнитель {executor.name} создан в памяти")
    return executor

# Дополнительные эндпоинты для создания исполнителей
@app.post("/executors")
async def create_executor_short(executor: Executor):
    """Создание исполнителя (короткий URL)"""
    return await create_executor(executor)

@app.post("/api/executor")
async def create_executor_single(executor: Executor):
    """Создание исполнителя (альтернативный URL)"""
    return await create_executor(executor)

@app.get("/api/executors", response_model=List[Executor])
async def get_executors():
    """Получение всех исполнителей"""
    if db_service and db_manager:
        try:
            db_executors = await db_service.get_executors()
            
            # Конвертируем в простые модели
            executors = []
            for db_executor in db_executors:
                executor = Executor(
                    id=db_executor.id,
                    name=db_executor.name,
                    role=db_executor.role,
                    status=db_executor.status,
                    active_requests_count=db_executor.active_requests_count,
                    daily_limit=db_executor.daily_limit,
                    success_rate=db_executor.success_rate,
                    skills=db_executor.parameters.get("skills", []) if db_executor.parameters else [],
                    created_at=datetime.now()
                )
                executors.append(executor)
            
            logger.info(f"✅ Получено {len(executors)} исполнителей из БД")
            return executors
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения исполнителей из БД: {e}")
            # Fallback на работу в памяти
            pass
    
    # Fallback: работа в памяти
    logger.info(f"✅ Получено {len(executors_db)} исполнителей из памяти")
    return executors_db

@app.get("/api/executors/{executor_id}", response_model=Executor)
async def get_executor(executor_id: str):
    """Получение исполнителя по ID"""
    executor = next((e for e in executors_db if e.id == executor_id), None)
    if not executor:
        raise HTTPException(status_code=404, detail="Executor not found")
    return executor

@app.put("/api/executors/{executor_id}", response_model=Executor)
async def update_executor(executor_id: str, executor: Executor):
    """Обновление исполнителя"""
    existing_executor = next((e for e in executors_db if e.id == executor_id), None)
    if not existing_executor:
        raise HTTPException(status_code=404, detail="Executor not found")
    
    executor.id = executor_id
    executor.created_at = existing_executor.created_at
    index = executors_db.index(existing_executor)
    executors_db[index] = executor
    return executor

@app.delete("/api/executors/{executor_id}")
async def delete_executor(executor_id: str):
    """Удаление исполнителя"""
    executor = next((e for e in executors_db if e.id == executor_id), None)
    if not executor:
        raise HTTPException(status_code=404, detail="Executor not found")
    
    executors_db.remove(executor)
    return {"message": "Executor deleted successfully"}

# CRUD операции для заявок
@app.post("/api/requests", response_model=Request)
async def create_request(request: Request):
    """Создание заявки"""
    if db_service and db_manager:
        try:
            # Конвертируем в модель БД
            db_request = DBRequest(
                title=request.title,
                description=request.description,
                priority=request.priority,
                weight=0.5,  # По умолчанию
                status=request.status,
                assigned_executor_id=request.assigned_executor_id,
                category=request.category,
                complexity="medium",  # По умолчанию
                estimated_hours=8,  # По умолчанию
                required_skills=[],  # Будет заполнено из параметров
                language_requirement="ru",
                client_type="individual",
                urgency="medium",
                budget=None,
                technology_stack=[],
                timezone_requirement="any",
                security_clearance="public",
                compliance_requirements=[],
                parameters={}
            )
            
            created_request = await db_service.create_request(db_request)
            
            # Конвертируем обратно в простую модель
            request.id = created_request.id
            request.created_at = datetime.now()
            
            # Простая логика назначения
            suitable_executors = await db_service.get_executors()
            suitable_executors = [
                e for e in suitable_executors 
                if e.status == "active" and e.active_requests_count < e.daily_limit
            ]
            
            if suitable_executors:
                # Найти исполнителя с наименьшей нагрузкой
                best_executor = min(suitable_executors, key=lambda e: e.active_requests_count)
                
                # Создать назначение
                assignment = DBAssignment(
                    request_id=request.id,
                    executor_id=best_executor.id,
                    assigned_at=datetime.now()
                )
                await db_service.create_assignment(assignment)
                
                # Обновить заявку и исполнителя
                request.status = "assigned"
                request.assigned_executor_id = best_executor.id
                
                # Обновить исполнителя
                best_executor.active_requests_count += 1
                await db_service.update_executor(best_executor.id, best_executor)
            
            logger.info(f"✅ Заявка '{request.title}' создана в БД")
            return request
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания заявки в БД: {e}")
            # Fallback на работу в памяти
            pass
    
    # Fallback: работа в памяти
    request.id = str(uuid.uuid4())
    request.created_at = datetime.now()
    
    # Простая логика назначения
    suitable_executors = [
        e for e in executors_db 
        if e.status == "active" and e.active_requests_count < e.daily_limit
    ]
    
    if suitable_executors:
        # Найти исполнителя с наименьшей нагрузкой
        best_executor = min(suitable_executors, key=lambda e: e.active_requests_count)
        
        # Создать назначение
        assignment = Assignment(
            id=str(uuid.uuid4()),
            request_id=request.id,
            executor_id=best_executor.id,
            assigned_at=datetime.now()
        )
        assignments_db.append(assignment)
        
        # Обновить заявку и исполнителя
        request.status = "assigned"
        request.assigned_executor_id = best_executor.id
        best_executor.active_requests_count += 1
    
    requests_db.append(request)
    logger.info(f"✅ Заявка '{request.title}' создана в памяти")
    return request

@app.get("/api/requests", response_model=List[Request])
async def get_requests():
    """Получение всех заявок"""
    if db_service and db_manager:
        try:
            db_requests = await db_service.get_requests()
            
            # Конвертируем в простые модели
            requests = []
            for db_request in db_requests:
                request = Request(
                    id=db_request.id,
                    title=db_request.title,
                    description=db_request.description,
                    priority=db_request.priority,
                    category=db_request.category,
                    status=db_request.status,
                    assigned_executor_id=db_request.assigned_executor_id,
                    created_at=datetime.now()
                )
                requests.append(request)
            
            logger.info(f"✅ Получено {len(requests)} заявок из БД")
            return requests
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения заявок из БД: {e}")
            # Fallback на работу в памяти
            pass
    
    # Fallback: работа в памяти
    logger.info(f"✅ Получено {len(requests_db)} заявок из памяти")
    return requests_db

@app.get("/api/requests/{request_id}", response_model=Request)
async def get_request(request_id: str):
    """Получение заявки по ID"""
    request = next((r for r in requests_db if r.id == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request

@app.put("/api/requests/{request_id}", response_model=Request)
async def update_request(request_id: str, request: Request):
    """Обновление заявки"""
    existing_request = next((r for r in requests_db if r.id == request_id), None)
    if not existing_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request.id = request_id
    request.created_at = existing_request.created_at
    index = requests_db.index(existing_request)
    requests_db[index] = request
    return request

@app.delete("/api/requests/{request_id}")
async def delete_request(request_id: str):
    """Удаление заявки"""
    request = next((r for r in requests_db if r.id == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    requests_db.remove(request)
    return {"message": "Request deleted successfully"}

# CRUD операции для назначений
@app.get("/api/assignments", response_model=List[Assignment])
async def get_assignments():
    """Получение всех назначений"""
    if db_service and db_manager:
        try:
            db_assignments = await db_service.get_assignments()
            
            # Конвертируем в простые модели
            assignments = []
            for db_assignment in db_assignments:
                assignment = Assignment(
                    id=db_assignment.id,
                    request_id=db_assignment.request_id,
                    executor_id=db_assignment.executor_id,
                    assigned_at=db_assignment.assigned_at,
                    status=db_assignment.status
                )
                assignments.append(assignment)
            
            logger.info(f"✅ Получено {len(assignments)} назначений из БД")
            return assignments
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения назначений из БД: {e}")
            # Fallback на работу в памяти
            pass
    
    # Fallback: работа в памяти
    logger.info(f"✅ Получено {len(assignments_db)} назначений из памяти")
    return assignments_db

@app.post("/api/assignments", response_model=Assignment)
async def create_assignment(assignment: Assignment):
    """Создание назначения"""
    assignment.id = str(uuid.uuid4())
    assignment.assigned_at = datetime.now()
    assignments_db.append(assignment)
    return assignment

# Статистика
# Дополнительные маршруты для фронтенда
@app.get("/stats", response_model=StatsResponse)
async def get_stats_short():
    """Получение статистики системы (короткий URL)"""
    return await get_stats()

@app.get("/executors", response_model=List[Executor])
async def get_executors_short():
    """Получение всех исполнителей (короткий URL)"""
    return await get_executors()

@app.get("/requests", response_model=List[Request])
async def get_requests_short():
    """Получение всех заявок (короткий URL)"""
    return await get_requests()

# Эндпоинты для правил распределения
@app.get("/api/rules")
async def get_rules():
    """Получение правил распределения"""
    # Возвращаем пустой список правил (можно расширить в будущем)
    return []

@app.get("/rules")
async def get_rules_short():
    """Получение правил распределения (короткий URL)"""
    return await get_rules()

@app.post("/api/rules")
async def create_rule(rule: dict):
    """Создание правила распределения"""
    try:
        logger.info(f"Создание правила: {rule}")
        
        # Простая валидация
        if not rule.get("name"):
            raise HTTPException(status_code=400, detail="Название правила обязательно")
        
        # Создаем правило с ID
        rule_id = str(uuid.uuid4())
        rule["id"] = rule_id
        rule["created_at"] = datetime.now().isoformat()
        rule["active"] = True
        
        # В реальном приложении здесь была бы запись в БД
        logger.info(f"Правило {rule_id} создано успешно")
        
        return {
            "id": rule_id,
            "message": "Правило успешно создано",
            "rule": rule
        }
    except Exception as e:
        logger.error(f"Ошибка создания правила: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rules")
async def create_rule_short(rule: dict):
    """Создание правила распределения (короткий URL)"""
    return await create_rule(rule)

# Эндпоинт для поиска исполнителей
@app.post("/api/executors/search")
async def search_executors(search_data: dict):
    """Поиск исполнителей по критериям"""
    try:
        logger.info(f"Получен запрос поиска: {search_data}")
        
        # Получаем всех исполнителей
        all_executors = await get_executors()
        logger.info(f"Всего исполнителей в системе: {len(all_executors)}")
        
        # Начинаем с всех исполнителей
        executors = all_executors.copy()
        
        # Обработка навыков из разных полей
        required_skills = []
        
        # Проверяем поле required_skills
        if "required_skills" in search_data:
            skills_data = search_data["required_skills"]
            if isinstance(skills_data, str) and skills_data.strip():
                required_skills = [skill.strip() for skill in skills_data.split(",") if skill.strip()]
            elif isinstance(skills_data, list) and skills_data:
                required_skills = [skill for skill in skills_data if skill.strip()]
        
        # Проверяем поле technology_stack как альтернативу
        if not required_skills and "technology_stack" in search_data:
            tech_data = search_data["technology_stack"]
            if isinstance(tech_data, str) and tech_data.strip():
                required_skills = [skill.strip() for skill in tech_data.split(",") if skill.strip()]
            elif isinstance(tech_data, list) and tech_data:
                required_skills = [skill for skill in tech_data if skill.strip()]
        
        logger.info(f"Требуемые навыки: {required_skills}")
        
        # Фильтрация по навыкам (если есть навыки)
        if required_skills:
            filtered_executors = []
            for executor in executors:
                executor_skills = [skill.lower() for skill in executor.skills]
                required_skills_lower = [skill.lower() for skill in required_skills]
                
                # Проверяем пересечение навыков
                if any(skill in executor_skills for skill in required_skills_lower):
                    filtered_executors.append(executor)
            executors = filtered_executors
            logger.info(f"После фильтрации по навыкам: {len(executors)} исполнителей")
        
        # Фильтр по статусу (по умолчанию только активные)
        if "status" in search_data:
            executors = [e for e in executors if e.status == search_data["status"]]
        else:
            # По умолчанию показываем только активных
            executors = [e for e in executors if e.status == "active"]
        
        logger.info(f"После фильтрации по статусу: {len(executors)} исполнителей")
        
        # Фильтр по доступности (опционально)
        if "available_only" in search_data and search_data["available_only"]:
            executors = [e for e in executors if e.active_requests_count < e.daily_limit]
            logger.info(f"После фильтрации по доступности: {len(executors)} исполнителей")
        
        # Сортируем по рейтингу успешности (лучшие сначала)
        executors.sort(key=lambda x: x.success_rate, reverse=True)
        
        # Логируем финальный результат
        logger.info(f"Финальный результат: {len(executors)} исполнителей")
        
        # Возвращаем в формате, ожидаемом фронтендом
        result = {
            "results": executors,  # Фронтенд ожидает поле "results"
            "executors": executors,  # Дублируем для совместимости
            "total": len(executors),
            "message": f"Найдено {len(executors)} исполнителей"
        }
        
        logger.info(f"Возвращаем результат: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Ошибка поиска исполнителей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-executors")
async def search_executors_short(search_data: dict):
    """Поиск исполнителей по критериям (короткий URL)"""
    try:
        result = await search_executors(search_data)
        logger.info(f"Короткий URL возвращает: {type(result)} с ключами: {result.keys() if isinstance(result, dict) else 'не dict'}")
        return result
    except Exception as e:
        logger.error(f"Ошибка в коротком URL: {e}")
        raise

# Отладочный эндпоинт для проверки формата
@app.get("/debug/executors")
async def debug_executors():
    """Отладочный эндпоинт для проверки формата данных"""
    executors = await get_executors()
    return {
        "type": "array",
        "length": len(executors),
        "sample": executors[0] if executors else None,
        "all_executors": executors
    }

# Эндпоинт для справедливого распределения заявки
@app.post("/api/assign-fair")
async def assign_request_fairly(request_data: dict):
    """Справедливое распределение заявки между исполнителями"""
    try:
        logger.info(f"Запрос на справедливое распределение: {request_data}")
        
        # Получаем всех активных исполнителей
        all_executors = await get_executors()
        active_executors = [e for e in all_executors if e.status == "active"]
        
        if not active_executors:
            return {
                "success": False,
                "message": "Нет доступных исполнителей",
                "assigned_executor": None
            }
        
        # Алгоритм справедливого распределения
        # 1. Фильтруем по навыкам (если указаны)
        suitable_executors = active_executors.copy()
        
        if "required_skills" in request_data and request_data["required_skills"]:
            skills_data = request_data["required_skills"]
            if isinstance(skills_data, str) and skills_data.strip():
                required_skills = [skill.strip().lower() for skill in skills_data.split(",") if skill.strip()]
                
                suitable_executors = []
                for executor in active_executors:
                    executor_skills = [skill.lower() for skill in executor.skills]
                    if any(skill in executor_skills for skill in required_skills):
                        suitable_executors.append(executor)
        
        if not suitable_executors:
            suitable_executors = active_executors  # Если никто не подходит по навыкам, берем всех
        
        # 2. Сортируем по справедливости:
        # - Сначала по загруженности (меньше заявок = выше приоритет)
        # - Затем по рейтингу успешности
        # - Затем по дневному лимиту (больше лимит = больше возможностей)
        
        def fairness_score(executor):
            # Обратная загруженность (меньше заявок = лучше)
            load_score = executor.daily_limit - executor.active_requests_count
            
            # Рейтинг успешности
            success_score = executor.success_rate
            
            # Комбинированный балл
            return (load_score * 0.5) + (success_score * 0.3) + (executor.daily_limit * 0.2)
        
        suitable_executors.sort(key=fairness_score, reverse=True)
        
        # 3. Выбираем лучшего исполнителя
        best_executor = suitable_executors[0]
        
        # 4. Создаем заявку
        request_obj = Request(
            id=str(uuid.uuid4()),
            title=request_data.get("title", "Новая заявка"),
            description=request_data.get("description", ""),
            priority=request_data.get("priority", "medium"),
            category=request_data.get("category", "general"),
            status="assigned",
            assigned_executor_id=best_executor.id,
            created_at=datetime.now()
        )
        
        # Добавляем в базу
        requests_db.append(request_obj)
        
        # 5. Создаем назначение
        assignment = Assignment(
            id=str(uuid.uuid4()),
            request_id=request_obj.id,
            executor_id=best_executor.id,
            assigned_at=datetime.now(),
            status="active"
        )
        assignments_db.append(assignment)
        
        # 6. Обновляем счетчик заявок исполнителя
        best_executor.active_requests_count += 1
        
        logger.info(f"Заявка {request_obj.id} назначена исполнителю {best_executor.name}")
        
        return {
            "success": True,
            "message": f"Заявка справедливо назначена исполнителю {best_executor.name}",
            "assigned_executor": {
                "id": best_executor.id,
                "name": best_executor.name,
                "role": best_executor.role,
                "skills": best_executor.skills,
                "success_rate": best_executor.success_rate,
                "active_requests": best_executor.active_requests_count,
                "daily_limit": best_executor.daily_limit
            },
            "request": {
                "id": request_obj.id,
                "title": request_obj.title,
                "priority": request_obj.priority,
                "category": request_obj.category
            },
            "assignment": {
                "id": assignment.id,
                "assigned_at": assignment.assigned_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка справедливого распределения: {e}")
        return {
            "success": False,
            "message": f"Ошибка при распределении: {str(e)}",
            "assigned_executor": None
        }

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Получение статистики системы"""
    if db_service and db_manager:
        try:
            stats = await db_service.get_statistics()
            
            response = StatsResponse(
                total_executors=stats.get('total_executors', 0),
                active_executors=stats.get('executors_by_status', {}).get('active', 0),
                total_requests=stats.get('total_requests', 0),
                pending_requests=stats.get('requests_by_status', {}).get('pending', 0),
                assigned_requests=stats.get('requests_by_status', {}).get('assigned', 0),
                total_assignments=stats.get('total_assignments', 0)
            )
            
            logger.info("✅ Статистика получена из БД")
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики из БД: {e}")
            # Fallback на работу в памяти
            pass
    
    # Fallback: работа в памяти
    response = StatsResponse(
        total_executors=len(executors_db),
        active_executors=len([e for e in executors_db if e.status == "active"]),
        total_requests=len(requests_db),
        pending_requests=len([r for r in requests_db if r.status == "pending"]),
        assigned_requests=len([r for r in requests_db if r.status == "assigned"]),
        total_assignments=len(assignments_db)
    )
    
    logger.info("✅ Статистика получена из памяти")
    return response

# Метрики в реальном времени
@app.get("/api/metrics/realtime")
async def get_realtime_metrics():
    """Получение метрик в реальном времени"""
    try:
        executor_metrics = metrics_collector.collect_executor_metrics(executors_db)
        request_metrics = metrics_collector.collect_request_metrics(requests_db)
        assignment_metrics = metrics_collector.collect_assignment_metrics(assignments_db)
        system_metrics = metrics_collector.collect_system_metrics(executors_db, requests_db, assignments_db)
        
        # Записываем метрики в историю
        metrics_collector.metrics.record_metric('total_requests', request_metrics['total_requests'])
        metrics_collector.metrics.record_metric('active_executors', executor_metrics['active_executors'])
        metrics_collector.metrics.record_metric('system_load', system_metrics['system_load_percent'])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "executor_metrics": executor_metrics,
            "request_metrics": request_metrics,
            "assignment_metrics": assignment_metrics,
            "system_metrics": system_metrics,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения метрик: {str(e)}")

@app.get("/api/metrics/summary")
async def get_metrics_summary():
    """Получение сводки всех метрик"""
    try:
        return metrics_collector.metrics.get_metrics_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения сводки: {str(e)}")

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ ДАННЫХ
# =============================================================================

def create_sample_data():
    """Создание тестовых данных"""
    global executors_db, requests_db, assignments_db
    
    # Очищаем существующие данные
    executors_db.clear()
    requests_db.clear()
    assignments_db.clear()
    
    # Создаем исполнителей
    sample_executors = [
        Executor(
            id=str(uuid.uuid4()),
            name="Алексей Иванов",
            email="alexey.ivanov@company.com",
            role="senior",
            status="active",
            active_requests_count=2,
            daily_limit=15,
            success_rate=0.95,
            weight=1.0,
            skills=["Python", "FastAPI", "PostgreSQL"],
            created_at=datetime.now()
        ),
        Executor(
            id=str(uuid.uuid4()),
            name="Мария Петрова",
            email="maria.petrova@company.com",
            role="middle",
            status="active",
            active_requests_count=1,
            daily_limit=10,
            success_rate=0.88,
            weight=0.9,
            skills=["JavaScript", "React", "Node.js"],
            created_at=datetime.now()
        ),
        Executor(
            id=str(uuid.uuid4()),
            name="Дмитрий Сидоров",
            email="dmitry.sidorov@company.com",
            role="junior",
            status="active",
            active_requests_count=0,
            daily_limit=8,
            success_rate=0.75,
            weight=0.7,
            skills=["HTML", "CSS", "JavaScript"],
            created_at=datetime.now()
        ),
        Executor(
            id=str(uuid.uuid4()),
            name="Елена Козлова",
            email="elena.kozlova@company.com",
            role="senior",
            status="inactive",
            active_requests_count=0,
            daily_limit=12,
            success_rate=0.92,
            weight=0.95,
            skills=["Docker", "Kubernetes", "AWS"],
            created_at=datetime.now()
        ),
        Executor(
            id=str(uuid.uuid4()),
            name="Игорь Волков",
            email="igor.volkov@company.com",
            role="middle",
            status="active",
            active_requests_count=3,
            daily_limit=10,
            success_rate=0.85,
            weight=0.85,
            skills=["Python", "Django", "Redis"],
            created_at=datetime.now()
        )
    ]
    
    # Создаем заявки
    sample_requests = [
        Request(
            id=str(uuid.uuid4()),
            title="Разработка API для мобильного приложения",
            description="Необходимо создать REST API для мобильного приложения с аутентификацией",
            priority="high",
            category="development",
            status="assigned",
            weight=1.0,
            created_at=datetime.now()
        ),
        Request(
            id=str(uuid.uuid4()),
            title="Оптимизация базы данных",
            description="Требуется оптимизировать производительность PostgreSQL",
            priority="medium",
            category="optimization",
            status="pending",
            weight=0.8,
            created_at=datetime.now()
        ),
        Request(
            id=str(uuid.uuid4()),
            title="Настройка CI/CD пайплайна",
            description="Настроить автоматическое развертывание приложения",
            priority="low",
            category="devops",
            status="assigned",
            weight=0.6,
            created_at=datetime.now()
        ),
        Request(
            id=str(uuid.uuid4()),
            title="Создание дашборда аналитики",
            description="Разработать веб-дашборд для отображения метрик",
            priority="high",
            category="development",
            status="assigned",
            weight=1.2,
            created_at=datetime.now()
        ),
        Request(
            id=str(uuid.uuid4()),
            title="Рефакторинг legacy кода",
            description="Улучшить архитектуру существующего кода",
            priority="medium",
            category="refactoring",
            status="pending",
            weight=0.9,
            created_at=datetime.now()
        )
    ]
    
    # Добавляем данные в базы
    executors_db.extend(sample_executors)
    requests_db.extend(sample_requests)
    
    # Создаем назначения
    if sample_executors and sample_requests:
        assignments = [
            Assignment(
                id=str(uuid.uuid4()),
                request_id=sample_requests[0].id,
                executor_id=sample_executors[0].id,
                assigned_at=datetime.now(),
                status="active"
            ),
            Assignment(
                id=str(uuid.uuid4()),
                request_id=sample_requests[2].id,
                executor_id=sample_executors[1].id,
                assigned_at=datetime.now(),
                status="active"
            ),
            Assignment(
                id=str(uuid.uuid4()),
                request_id=sample_requests[3].id,
                executor_id=sample_executors[4].id,
                assigned_at=datetime.now(),
                status="active"
            )
        ]
        assignments_db.extend(assignments)
    
    logger.info(f"Создано {len(sample_executors)} исполнителей, {len(sample_requests)} заявок, {len(assignments)} назначений")

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================

if __name__ == "__main__":
    # Создаем тестовые данные
    create_sample_data()
    
    # Проверяем наличие папок templates и static
    templates_dir = "templates"
    static_dir = "static"
    
    logger.info("🔍 Проверка подключенных файлов...")
    
    if os.path.exists(templates_dir):
        template_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
        logger.info(f"📁 Найдено {len(template_files)} HTML шаблонов в папке templates: {template_files}")
    else:
        logger.warning(f"⚠️ Папка {templates_dir} не найдена, будут использоваться встроенные шаблоны")
    
    if os.path.exists(static_dir):
        static_files = []
        for root, dirs, files in os.walk(static_dir):
            for file in files:
                static_files.append(os.path.relpath(os.path.join(root, file), static_dir))
        logger.info(f"📁 Найдено {len(static_files)} статических файлов в папке static: {static_files}")
    else:
        logger.warning(f"⚠️ Папка {static_dir} не найдена")
    
    logger.info("🚀 Запуск Executor Balancer API...")
    logger.info("📊 Дашборд: http://localhost:8006/dashboard")
    logger.info("📚 API Документация: http://localhost:8006/docs")
    logger.info("❤️ Статус системы: http://localhost:8006/health")
    logger.info("📖 Руководство: http://localhost:8006/guide")
    logger.info("🎮 Демо: http://localhost:8006/demo")
    logger.info("🏠 Главная: http://localhost:8006/")
    logger.info("📱 Приложение: http://localhost:8006/app")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8006,
        reload=False,
        workers=1
    )
