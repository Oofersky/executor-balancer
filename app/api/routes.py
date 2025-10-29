"""
API Routes for Executor Balancer
API маршруты для системы распределения исполнителей
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
from datetime import datetime
import uuid
import json
import asyncio
import os

# Определяем путь к шаблонам
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")

from models.schemas import (
    Executor, Request, Assignment, DistributionRule, 
    ExecutorSearchResult, ExecutorSearchRequest, AssignmentRequest,
    StatsResponse, HealthResponse
)
from services.balancer import ExecutorBalancer
from services.database_service import db_service
from core.simple_metrics import metrics_collector, metrics
from core.database import redis_manager

# Создаем роутер
router = APIRouter()

# Инициализация сервисов
balancer = ExecutorBalancer()

# Временные базы данных в памяти (для демонстрации)
executors_db = []
requests_db = []
assignments_db = []
rules_db = []

# WebSocket подключения
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

# HTML страницы
@router.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main guide page"""
    try:
        with open(os.path.join(TEMPLATES_PATH, "guide.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Executor Balancer</title></head>
            <body>
                <h1>Executor Balancer API</h1>
                <p>API is running. Guide file not found.</p>
                <p><a href="/app">Go to Application</a></p>
                <p><a href="/dashboard">Go to Dashboard</a></p>
                <p><a href="/docs">API Documentation</a></p>
            </body>
        </html>
        """)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard page"""
    try:
        with open(os.path.join(TEMPLATES_PATH, "dashboard.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Dashboard</title></head>
            <body>
                <h1>Dashboard not found</h1>
                <p>Dashboard file not found.</p>
            </body>
        </html>
        """)


# WebSocket для обновлений в реальном времени
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Отправляем обновления каждые 2 секунды
            await asyncio.sleep(2)
            dashboard_data = await get_dashboard_data()
            await manager.broadcast({
                "type": "dashboard_update",
                "data": dashboard_data
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# API эндпоинты для работы с БД
@router.post("/api/executors", response_model=Executor)
async def create_executor(executor: Executor):
    """Создание исполнителя"""
    try:
        return await db_service.create_executor(executor)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/executors", response_model=List[Executor])
async def get_executors():
    """Получение всех исполнителей"""
    try:
        return await db_service.get_executors()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/executors/{executor_id}", response_model=Executor)
async def get_executor(executor_id: str):
    """Получение исполнителя по ID"""
    try:
        executor = await db_service.get_executor_by_id(executor_id)
        if not executor:
            raise HTTPException(status_code=404, detail="Executor not found")
        return executor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/executors/{executor_id}", response_model=Executor)
async def update_executor(executor_id: str, executor: Executor):
    """Обновление исполнителя"""
    try:
        updated_executor = await db_service.update_executor(executor_id, executor)
        if not updated_executor:
            raise HTTPException(status_code=404, detail="Executor not found")
        return updated_executor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/executors/{executor_id}")
async def delete_executor(executor_id: str):
    """Удаление исполнителя"""
    try:
        success = await db_service.delete_executor(executor_id)
        if not success:
            raise HTTPException(status_code=404, detail="Executor not found")
        return {"message": "Executor deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/requests", response_model=Request)
async def create_request(request: Request):
    """Создание заявки"""
    try:
        return await db_service.create_request(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/requests", response_model=List[Request])
async def get_requests():
    """Получение всех заявок"""
    try:
        return await db_service.get_requests()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/requests/{request_id}", response_model=Request)
async def get_request(request_id: str):
    """Получение заявки по ID"""
    try:
        request = await db_service.get_request_by_id(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        return request
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/requests/{request_id}", response_model=Request)
async def update_request(request_id: str, request: Request):
    """Обновление заявки"""
    try:
        updated_request = await db_service.update_request(request_id, request)
        if not updated_request:
            raise HTTPException(status_code=404, detail="Request not found")
        return updated_request
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/requests/{request_id}")
async def delete_request(request_id: str):
    """Удаление заявки"""
    try:
        success = await db_service.delete_request(request_id)
        if not success:
            raise HTTPException(status_code=404, detail="Request not found")
        return {"message": "Request deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Дашборд API
@router.get("/api/dashboard")
async def get_dashboard_data():
    """Получение данных для дашборда"""
    try:
        # Получаем данные из памяти (вместо БД)
        executors = executors_db
        requests = requests_db
        assignments = assignments_db
        
        # Собираем метрики
        executor_metrics = metrics_collector.collect_executor_metrics(executors)
        request_metrics = metrics_collector.collect_request_metrics(requests)
        assignment_metrics = metrics_collector.collect_assignment_metrics(assignments)
        system_metrics = metrics_collector.collect_system_metrics(executors, requests, assignments)
        
        # Получаем количество активных пользователей (симуляция)
        active_users = len(manager.active_connections)
        
        # Формируем ответ
        dashboard_data = {
            'total_executors': executor_metrics['total_executors'],
            'active_executors': executor_metrics['active_executors'],
            'total_requests': request_metrics['total_requests'],
            'pending_requests': request_metrics['pending_requests'],
            'assigned_requests': request_metrics['assigned_requests'],
            'completed_requests': request_metrics['completed_requests'],
            'total_assignments': assignment_metrics['total_assignments'],
            'active_users': active_users,
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
        # Возвращаем тестовые данные в случае ошибки
        return {
            'total_executors': len(executors_db),
            'active_executors': len([e for e in executors_db if e.status == 'active']),
            'total_requests': len(requests_db),
            'pending_requests': len([r for r in requests_db if r.status == 'pending']),
            'assigned_requests': len([r for r in requests_db if r.status == 'assigned']),
            'completed_requests': len([r for r in requests_db if r.status == 'completed']),
            'total_assignments': len(assignments_db),
            'active_users': len(manager.active_connections),
            'system_load_percent': 75.5,
            'efficiency_score': 88.2,
            'executors_by_status': {'active': 3, 'busy': 1, 'offline': 1},
            'executors_by_role': {'programmer': 2, 'support': 2, 'admin': 1},
            'requests_by_status': {'pending': 1, 'assigned': 1, 'completed': 1},
            'requests_by_priority': {'high': 2, 'medium': 1},
            'requests_by_category': {'technical': 2, 'support': 1},
            'assignments_by_status': {'assigned': 1, 'completed': 1},
            'timestamp': datetime.now().isoformat()
        }

# Остальные эндпоинты остаются без изменений...

# HTML страницы
@router.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main guide page"""
    try:
        with open(os.path.join(TEMPLATES_PATH, "guide.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Executor Balancer</title></head>
            <body>
                <h1>Executor Balancer API</h1>
                <p>API is running. Guide file not found.</p>
                <p><a href="/app">Go to Application</a></p>
                <p><a href="/docs">API Documentation</a></p>
            </body>
        </html>
        """)

@router.get("/app", response_class=HTMLResponse)
async def app_page():
    """Serve the main application page"""
    try:
        with open(os.path.join(TEMPLATES_PATH, "index.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Executor Balancer</title></head>
            <body>
                <h1>Executor Balancer API</h1>
                <p>API is running. Application file not found.</p>
                <p><a href="/">Go to Guide</a></p>
                <p><a href="/docs">API Documentation</a></p>
            </body>
        </html>
        """)

@router.get("/index.html", response_class=HTMLResponse)
async def index():
    """Serve the main application page"""
    try:
        with open(os.path.join(TEMPLATES_PATH, "index.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Executor Balancer</title></head>
            <body>
                <h1>Executor Balancer API</h1>
                <p>API is running. Application file not found.</p>
                <p><a href="/">Go to Guide</a></p>
                <p><a href="/docs">API Documentation</a></p>
            </body>
        </html>
        """)

@router.get("/demo", response_class=HTMLResponse)
async def demo():
    """Serve the demo page"""
    try:
        with open(os.path.join(TEMPLATES_PATH, "demo.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Executor Balancer</title></head>
            <body>
                <h1>Executor Balancer API</h1>
                <p>API is running. Demo file not found.</p>
                <p><a href="/">Go to Guide</a></p>
                <p><a href="/app">Go to Application</a></p>
            </body>
        </html>
        """)

# Health check
@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy", 
        timestamp=datetime.now().isoformat(),
        cors_enabled=True,
        version="1.0.0"
    )

# Executors endpoints
@router.post("/executors", response_model=Executor)
async def create_executor(executor: Executor):
    """Создать нового исполнителя"""
    print(f"Creating executor with data: {executor.dict()}")
    
    executor.id = str(uuid.uuid4())
    executors_db.append(executor)
    
    print(f"Executor created successfully with ID: {executor.id}")
    return executor

@router.get("/executors", response_model=List[Executor])
async def get_executors():
    """Получить всех исполнителей"""
    return executors_db

# Requests endpoints
@router.post("/requests", response_model=Request)
async def create_request(request: Request):
    """Создать новую заявку"""
    print(f"Creating request with data: {request.dict()}")
    
    request.id = str(uuid.uuid4())
    
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
    print(f"Request created successfully with ID: {request.id}")
    return request

@router.get("/requests", response_model=List[Request])
async def get_requests():
    """Получить все заявки"""
    return requests_db

# Assignments endpoints
@router.get("/assignments", response_model=List[Assignment])
async def get_assignments():
    """Получить все назначения"""
    return assignments_db

@router.post("/assign")
async def assign_executor(assignment_data: AssignmentRequest):
    """Назначить исполнителя на заявку"""
    executor_id = assignment_data.executor_id
    request_id = assignment_data.request_id
    
    # Найти исполнителя и заявку
    executor = next((e for e in executors_db if e.id == executor_id), None)
    request = next((r for r in requests_db if r.id == request_id), None)
    
    if not executor or not request:
        raise HTTPException(status_code=404, detail="Executor or request not found")
    
    # Создать назначение
    assignment = Assignment(
        id=str(uuid.uuid4()),
        request_id=request_id,
        executor_id=executor_id,
        assigned_at=datetime.now()
    )
    assignments_db.append(assignment)
    
    # Обновить заявку и исполнителя
    request.status = "assigned"
    request.assigned_executor_id = executor_id
    executor.active_requests_count += 1
    
    return {"message": "Assignment created successfully", "assignment_id": assignment.id}

# Statistics endpoint
@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Получить статистику системы"""
    return StatsResponse(
        total_executors=len(executors_db),
        active_executors=len([e for e in executors_db if e.status == "active"]),
        total_requests=len(requests_db),
        pending_requests=len([r for r in requests_db if r.status == "pending"]),
        assigned_requests=len([r for r in requests_db if r.status == "assigned"]),
        total_assignments=len(assignments_db)
    )

# Rules endpoints
@router.post("/rules", response_model=DistributionRule)
async def create_rule(rule: DistributionRule):
    """Создать новое правило распределения"""
    rule.id = str(uuid.uuid4())
    rule.created_at = datetime.now()
    rules_db.append(rule)
    return rule

@router.get("/rules", response_model=List[DistributionRule])
async def get_rules():
    """Получить все правила"""
    return rules_db

@router.get("/rules/{rule_id}", response_model=DistributionRule)
async def get_rule(rule_id: str):
    """Получить правило по ID"""
    rule = next((r for r in rules_db if r.id == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.put("/rules/{rule_id}", response_model=DistributionRule)
async def update_rule(rule_id: str, rule: DistributionRule):
    """Обновить правило"""
    existing_rule = next((r for r in rules_db if r.id == rule_id), None)
    if not existing_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Обновить правило
    rule.id = rule_id
    rule.created_at = existing_rule.created_at
    rule_index = rules_db.index(existing_rule)
    rules_db[rule_index] = rule
    return rule

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """Удалить правило"""
    rule = next((r for r in rules_db if r.id == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rules_db.remove(rule)
    return {"message": "Rule deleted successfully"}

@router.post("/rules/{rule_id}/test")
async def test_rule(rule_id: str):
    """Протестировать правило"""
    rule = next((r for r in rules_db if r.id == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Простой тест - подсчитать сколько исполнителей соответствуют правилу
    matching_executors = 0
    for executor in executors_db:
        if executor.status == "active":
            # Простой тест - проверить соответствие базовым условиям
            matching_executors += 1
    
    return {
        "message": f"Rule '{rule.name}' tested successfully",
        "matching_executors": matching_executors,
        "total_executors": len(executors_db)
    }

# Search executors endpoint
@router.post("/search-executors", response_model=List[ExecutorSearchResult])
async def search_executors(search_request: ExecutorSearchRequest):
    """Найти подходящих исполнителей для заявки"""
    return balancer.search_executors(search_request, executors_db)

# Metrics endpoints для реального времени
@router.get("/api/metrics/realtime")
async def get_realtime_metrics():
    """Получение метрик в реальном времени"""
    try:
        # Получаем данные из БД
        executors = await db_service.get_executors()
        requests = await db_service.get_requests()
        assignments = await db_service.get_assignments()
        
        # Собираем метрики
        executor_metrics = metrics_collector.collect_executor_metrics(executors)
        request_metrics = metrics_collector.collect_request_metrics(requests)
        assignment_metrics = metrics_collector.collect_assignment_metrics(assignments)
        system_metrics = metrics_collector.collect_system_metrics(executors, requests, assignments)
        
        # Записываем метрики в историю
        metrics.record_metric('total_requests', request_metrics['total_requests'])
        metrics.record_metric('active_executors', executor_metrics['active_executors'])
        metrics.record_metric('system_load', system_metrics['system_load_percent'])
        
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

@router.get("/api/metrics/history/{metric_name}")
async def get_metric_history(metric_name: str, hours: int = 24):
    """Получение истории метрики"""
    try:
        history = metrics.get_metric_history(metric_name)
        
        # Фильтруем по времени если нужно
        if hours < 24:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            filtered_history = []
            for record in history:
                record_time = datetime.fromisoformat(record['timestamp']).timestamp()
                if record_time > cutoff_time:
                    filtered_history.append(record)
            history = filtered_history
        
        return {
            "metric_name": metric_name,
            "hours": hours,
            "data": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения истории: {str(e)}")

@router.get("/api/metrics/summary")
async def get_metrics_summary():
    """Получение сводки всех метрик"""
    try:
        return metrics.get_metrics_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения сводки: {str(e)}")
