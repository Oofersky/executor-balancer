#!/usr/bin/env python3
"""
Тест с точно такими же данными как в фронтенде
"""

import requests
import json

def test_search_with_frontend_data():
    url = "http://localhost:8006/search-executors"
    
    # Точные данные как в фронтенде
    search_data = {
        "budget": None,
        "category": "technical",
        "client_type": "individual",
        "complexity": "medium",
        "compliance_requirements": [],
        "estimated_hours": 8,
        "language_requirement": "ru",
        "priority": "medium",
        "required_skills": [],  # Пустой массив как в фронтенде
        "security_clearance": "public",
        "technology_stack": [],  # Пустой массив как в фронтенде
        "timezone_requirement": "any",
        "title": "",
        "urgency": "medium",
        "weight": 0.5
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
            
            if results:
                print("   Top 3 executors:")
                for i, executor in enumerate(results[:3]):
                    print(f"   {i+1}. {executor['name']} ({executor['role']})")
                    print(f"      Skills: {executor['skills']}")
                    print(f"      Success Rate: {executor['success_rate']}")
                    print(f"      Active Requests: {executor['active_requests_count']}/{executor['daily_limit']}")
                    print(f"      Status: {executor['status']}")
            else:
                print("   No executors found!")
            
            return True
        else:
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR {url} - {e}")
        return False

def main():
    print("Testing with exact frontend data")
    print("=" * 50)
    
    if test_search_with_frontend_data():
        print("\nSearch works with frontend data!")
    else:
        print("\nSearch still has issues")

if __name__ == "__main__":
    main()
