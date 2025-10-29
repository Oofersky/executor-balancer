#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API эндпоинтов Executor Balancer
"""

import requests
import json

BASE_URL = "http://localhost:8006"

def test_endpoint(method, endpoint, data=None):
    """Тестирование эндпоинта"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        
        print(f"✅ {method} {endpoint} - {response.status_code}")
        if response.status_code != 200:
            print(f"   Ошибка: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ {method} {endpoint} - Ошибка: {e}")
        return False

def main():
    print("🧪 Тестирование API эндпоинтов Executor Balancer")
    print("=" * 50)
    
    # Тестируем основные эндпоинты
    endpoints = [
        ("GET", "/health"),
        ("GET", "/stats"),
        ("GET", "/executors"),
        ("GET", "/requests"),
        ("GET", "/api/stats"),
        ("GET", "/api/executors"),
        ("GET", "/api/requests"),
        ("GET", "/api/rules"),
        ("GET", "/api/dashboard"),
    ]
    
    success_count = 0
    total_count = len(endpoints)
    
    for method, endpoint in endpoints:
        if test_endpoint(method, endpoint):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты: {success_count}/{total_count} эндпоинтов работают")
    
    if success_count == total_count:
        print("🎉 Все эндпоинты работают корректно!")
    else:
        print("⚠️ Некоторые эндпоинты требуют внимания")
    
    # Тестируем POST эндпоинты
    print("\n🔍 Тестирование POST эндпоинтов:")
    print("-" * 30)
    
    # Тест поиска исполнителей
    search_data = {
        "skills": ["Python", "FastAPI"],
        "status": "active",
        "available_only": True
    }
    test_endpoint("POST", "/api/executors/search", search_data)
    
    # Тест создания правила
    rule_data = {
        "name": "Test Rule",
        "conditions": [],
        "priority": 1
    }
    test_endpoint("POST", "/api/rules", rule_data)

if __name__ == "__main__":
    main()
