#!/usr/bin/env python3
"""
Простой тест эндпоинта поиска
"""

import requests
import json

def test_search():
    url = "http://localhost:8006/search-executors"
    
    # Простые тестовые данные
    data = {
        "title": "Test",
        "priority": "medium",
        "weight": 0.5,
        "category": "technical",
        "required_skills": [],
        "technology_stack": []
    }
    
    try:
        response = requests.post(url, json=data, timeout=5)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response type: {type(result)}")
            print(f"Keys: {result.keys()}")
            
            if "results" in result:
                results = result["results"]
                print(f"Results type: {type(results)}")
                print(f"Results length: {len(results)}")
                
                if isinstance(results, list):
                    print("SUCCESS: results is a list!")
                    for i, executor in enumerate(results[:2]):
                        print(f"  {i+1}. {executor['name']} - {executor['skills']}")
                else:
                    print(f"ERROR: results is not a list, it's {type(results)}")
            else:
                print("ERROR: no 'results' field in response")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_search()
