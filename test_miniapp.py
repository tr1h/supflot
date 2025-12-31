#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Быстрый тест Mini App"""

import requests
import sys

def test_miniapp():
    base_url = "http://localhost:5000"
    
    print("🔍 Тестирование Mini App...\n")
    
    # Тест главной страницы
    try:
        response = requests.get(f"{base_url}/miniapp/", timeout=5)
        if response.status_code == 200:
            print("✅ Главная страница Mini App работает!")
        else:
            print(f"❌ Ошибка: статус {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("   Убедитесь, что сайт запущен на порту 5000")
        return False
    
    # Тест API локаций
    try:
        response = requests.get(f"{base_url}/miniapp/api/locations", timeout=5)
        if response.status_code == 200:
            locations = response.json()
            print(f"✅ API локаций работает! Найдено локаций: {len(locations)}")
        else:
            print(f"⚠️  API локаций: статус {response.status_code}")
    except Exception as e:
        print(f"⚠️  API локаций: {e}")
    
    print("\n🎉 Тест завершен!")
    return True

if __name__ == "__main__":
    test_miniapp()

