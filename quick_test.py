#!/usr/bin/env python3
"""
Быстрый тест API эндпоинтов
"""

import requests
import json

def test_endpoint(url):
    try:
        response = requests.get(url, timeout=5)
        print(f"OK {url} - {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Data: {data}")
            except:
                print(f"   Response: {response.text[:100]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR {url} - {e}")
        return False

def main():
    print("Testing critical endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8006"
    
    # Тестируем основные эндпоинты
    endpoints = [
        f"{base_url}/health",
        f"{base_url}/rules",
        f"{base_url}/stats",
        f"{base_url}/executors",
        f"{base_url}/requests",
    ]
    
    success_count = 0
    for url in endpoints:
        if test_endpoint(url):
            success_count += 1
    
    print(f"\nResult: {success_count}/{len(endpoints)} endpoints work")
    
    if success_count == len(endpoints):
        print("All main endpoints work!")
    else:
        print("Some endpoints don't work")

if __name__ == "__main__":
    main()