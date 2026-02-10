#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for weather integration
"""

import requests
import json
import time

def test_weather_service():
    """Test the weather service directly"""
    print("🌡️  Testing weather service...")
    try:
        from backend.weather_service import get_current_temperature, get_weather_info
        
        temp = get_current_temperature()
        print(f"   Current temperature: {temp}°C")
        
        weather = get_weather_info()
        print(f"   Weather info: {weather}")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_backend_api():
    """Test the backend API endpoints"""
    print("\n🔌 Testing backend API...")
    
    base_url = "http://127.0.0.1:5000"
    
    # Test weather endpoint
    try:
        response = requests.get(f"{base_url}/weather", timeout=5)
        if response.status_code == 200:
            weather = response.json()
            print(f"   ✅ Weather endpoint: {weather['temperature']:.1f}°C in {weather['city']}")
        else:
            print(f"   ❌ Weather endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Weather endpoint error: {e}")
        return False
    
    # Test prediction without temperature (should use real weather)
    try:
        payload = {
            "hour": 14,
            "occupancy": 150,
            "is_weekend": 0
            # Note: no temperature provided
        }
        
        response = requests.post(f"{base_url}/predict", json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Prediction (auto-temp): {result['predicted_usage_kW']} kW using {result['temperature_used']}°C")
            print(f"   📊 Model type: {result['model_type']}")
        else:
            print(f"   ❌ Prediction failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Prediction error: {e}")
        return False
    
    # Test prediction with explicit temperature
    try:
        payload = {
            "hour": 14,
            "temperature": 25.0,
            "occupancy": 150,
            "is_weekend": 0
        }
        
        response = requests.post(f"{base_url}/predict", json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Prediction (manual-temp): {result['predicted_usage_kW']} kW using {result['temperature_used']}°C")
        else:
            print(f"   ❌ Manual prediction failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Manual prediction error: {e}")
        return False
    
    return True

def test_sensor_feed():
    """Test that sensor feed includes temperature"""
    print("\n📡 Testing sensor feed...")
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        response = requests.get(f"{base_url}/current_status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            if "temperature" in status:
                print(f"   ✅ Sensor data includes temperature: {status.get('temperature', 'N/A')}°C")
                print(f"   📊 Current status: {status}")
                return True
            else:
                print(f"   ⚠️  Sensor data missing temperature field")
                return False
        else:
            print(f"   ❌ Status endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Status endpoint error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Weather Integration")
    print("=" * 50)
    
    # Test components
    weather_ok = test_weather_service()
    api_ok = test_backend_api()
    sensor_ok = test_sensor_feed()
    
    print("\n📋 Test Results:")
    print(f"   Weather Service: {'✅ PASS' if weather_ok else '❌ FAIL'}")
    print(f"   Backend API:     {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"   Sensor Feed:     {'✅ PASS' if sensor_ok else '❌ FAIL'}")
    
    if all([weather_ok, api_ok, sensor_ok]):
        print("\n🎉 All tests passed! Weather integration is working.")
    else:
        print("\n⚠️  Some tests failed. Check the backend and sensor feed are running.")
