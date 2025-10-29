#!/usr/bin/env python3
"""
Тест POST эндпоинта для поиска исполнителей
"""

import requests
import json

def test_search_executors():
    url = "http://localhost:8006/search-executors"
    
    # Тестовые данные для поиска
    search_data = {
        "skills": ["Python"],
        "status": "active",
        "available_only": True
    }
    
    try:
        response = requests.post(url, json=search_data, timeout=5)
        print(f"POST {url} - {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data.get('total', 0)} executors")
            print(f"   Message: {data.get('message', 'No message')}")
            
            executors = data.get('executors', [])
            for executor in executors[:3]:  # Показываем первых 3
                print(f"   - {executor['name']} ({executor['role']}) - Skills: {executor['skills']}")
            
            return True
        else:
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR {url} - {e}")
        return False

def main():
    print("Testing search executors endpoint")
    print("=" * 50)
    
    if test_search_executors():
        print("\nSearch executors endpoint works!")
    else:
        print("\nSearch executors endpoint has issues")

if __name__ == "__main__":
    main()
