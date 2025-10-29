#!/usr/bin/env python3
"""
Комплексный тест всех эндпоинтов
"""

import requests
import json

def test_endpoint(method, url, data=None):
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=5)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=5)
        
        print(f"{method} {url} - {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"  Response type: {type(result)}")
                if isinstance(result, dict):
                    print(f"  Keys: {list(result.keys())}")
                    if "results" in result:
                        print(f"  Results type: {type(result['results'])}")
                        print(f"  Results length: {len(result['results']) if isinstance(result['results'], list) else 'not list'}")
                return True
            except:
                print(f"  Response: {response.text[:100]}...")
                return True
        else:
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False

def main():
    print("=== КОМПЛЕКСНЫЙ ТЕСТ ЭНДПОИНТОВ ===")
    print()
    
    base_url = "http://localhost:8006"
    
    # Тест GET эндпоинтов
    print("1. Тестирование GET эндпоинтов:")
    get_endpoints = [
        f"{base_url}/health",
        f"{base_url}/stats", 
        f"{base_url}/executors",
        f"{base_url}/requests",
        f"{base_url}/rules",
        f"{base_url}/debug/executors"
    ]
    
    for url in get_endpoints:
        test_endpoint("GET", url)
    
    print()
    
    # Тест POST эндпоинтов
    print("2. Тестирование POST эндпоинтов:")
    
    # Тест поиска исполнителей
    search_data = {
        "title": "Test",
        "priority": "medium",
        "weight": 0.5,
        "category": "technical",
        "required_skills": [],
        "technology_stack": []
    }
    
    print("2.1. Поиск исполнителей:")
    test_endpoint("POST", f"{base_url}/search-executors", search_data)
    
    # Тест создания исполнителя
    executor_data = {
        "name": "Тест Тестович",
        "role": "middle",
        "status": "active",
        "skills": ["Python", "JavaScript"],
        "daily_limit": 10,
        "success_rate": 0.85
    }
    
    print("2.2. Создание исполнителя:")
    test_endpoint("POST", f"{base_url}/executors", executor_data)
    test_endpoint("POST", f"{base_url}/api/executor", executor_data)
    
    # Тест справедливого распределения
    assignment_data = {
        "title": "Тестовая заявка",
        "description": "Описание тестовой заявки",
        "priority": "medium",
        "category": "technical",
        "required_skills": "Python"
    }
    
    print("2.3. Справедливое распределение:")
    test_endpoint("POST", f"{base_url}/api/assign-fair", assignment_data)
    
    print()
    print("=== ТЕСТ ЗАВЕРШЕН ===")

if __name__ == "__main__":
    main()
