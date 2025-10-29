#!/usr/bin/env python3
"""
Тест исправленного эндпоинта поиска исполнителей
"""

import requests
import json

def test_search_executors():
    url = "http://localhost:8006/search-executors"
    
    # Тестовые данные как в фронтенде
    search_data = {
        "title": "Тестовая заявка",
        "priority": "medium",
        "weight": 0.5,
        "category": "technical",
        "complexity": "medium",
        "estimated_hours": 8,
        "required_skills": "Python, JavaScript, SQL",  # Строка как в фронтенде
        "language_requirement": "ru",
        "client_type": "individual",
        "urgency": "medium",
        "budget": None,
        "technology_stack": "React, Node.js, MongoDB",
        "timezone_requirement": "any",
        "security_clearance": "public",
        "compliance_requirements": []
    }
    
    try:
        response = requests.post(url, json=search_data, timeout=5)
        print(f"POST {url} - {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data.get('total', 0)} executors")
            print(f"   Message: {data.get('message', 'No message')}")
            
            # Проверяем наличие поля results
            results = data.get('results', [])
            print(f"   Results field exists: {len(results)} items")
            
            for i, executor in enumerate(results[:3]):  # Показываем первых 3
                print(f"   {i+1}. {executor['name']} ({executor['role']})")
                print(f"      Skills: {executor['skills']}")
                print(f"      Success Rate: {executor['success_rate']}")
                print(f"      Active Requests: {executor['active_requests_count']}/{executor['daily_limit']}")
            
            return True
        else:
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR {url} - {e}")
        return False

def main():
    print("Testing fixed search executors endpoint")
    print("=" * 50)
    
    if test_search_executors():
        print("\nSearch executors endpoint works correctly!")
    else:
        print("\nSearch executors endpoint still has issues")

if __name__ == "__main__":
    main()
