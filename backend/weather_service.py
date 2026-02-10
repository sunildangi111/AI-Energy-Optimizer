#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weather service for real-time temperature data
"""

import requests
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict

class WeatherService:
    def __init__(self, api_key: Optional[str] = None, city: str = "Darbhanga"):
        self.api_key = api_key or os.getenv("OWM_API_KEY")
        self.city = city
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.cache_timeout = 300  # 5 minutes
        self._last_fetch = 0
        self._cached_data = None
    
    def get_current_temperature(self) -> float:
        """Get current temperature in Celsius"""
        if not self.api_key:
            print("⚠️  No OWM_API_KEY found, using default temperature (22°C)")
            return 22.0
        
        current_time = time.time()
        
        # Use cached data if still valid
        if self._cached_data and (current_time - self._last_fetch) < self.cache_timeout:
            return self._cached_data
        
        try:
            params = {
                "q": self.city,
                "appid": self.api_key,
                "units": "metric"  # Get temperature in Celsius
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if "main" in data and "temp" in data["main"]:
                temp_celsius = data["main"]["temp"]
                self._cached_data = temp_celsius
                self._last_fetch = current_time
                
                print(f"🌡️  Current temperature in {self.city}: {temp_celsius:.1f}°C")
                return temp_celsius
            else:
                print("⚠️  Invalid weather API response format")
                return 22.0
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Weather API error: {e}")
            return 22.0
        except Exception as e:
            print(f"⚠️  Unexpected weather error: {e}")
            return 22.0
    
    def get_weather_info(self) -> Dict:
        """Get full weather information"""
        if not self.api_key:
            return {
                "temperature": 22.0,
                "description": "Clear",
                "city": self.city,
                "error": "No API key"
            }
        
        try:
            params = {
                "q": self.city,
                "appid": self.api_key,
                "units": "metric"
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"].title(),
                "city": data.get("name", self.city),
                "humidity": data["main"].get("humidity", 0),
                "feels_like": data["main"].get("feels_like", data["main"]["temp"]),
                "error": None
            }
            
        except Exception as e:
            return {
                "temperature": 22.0,
                "description": "Unknown",
                "city": self.city,
                "error": str(e)
            }

# Global weather service instance
weather_service = WeatherService()

def get_current_temperature() -> float:
    """Convenience function to get current temperature"""
    return weather_service.get_current_temperature()

def get_weather_info() -> Dict:
    """Convenience function to get weather info"""
    return weather_service.get_weather_info()

if __name__ == "__main__":
    # Test the weather service
    print("Testing weather service...")
    
    temp = get_current_temperature()
    print(f"Current temperature: {temp}°C")
    
    info = get_weather_info()
    print(f"Weather info: {info}")
