#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for OpenWeatherMap API key
"""

import os
import sys

def setup_weather_api():
    print("🌤️  OpenWeatherMap API Setup")
    print("=" * 40)
    print()
    print("1. Get your free API key from: https://openweathermap.org/api")
    print("2. Sign up for a free account")
    print("3. Go to 'API keys' tab and copy your key")
    print()
    
    api_key = input("Enter your OpenWeatherMap API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("⚠️  No API key provided. Weather features will use default values.")
        return False
    
    # Set environment variable for current session
    os.environ["OWM_API_KEY"] = api_key
    
    # Add to .env file for persistence
    env_file = ".env"
    try:
        with open(env_file, "w") as f:
            f.write(f"OWM_API_KEY={api_key}\n")
        print(f"✅ API key saved to {env_file}")
    except Exception as e:
        print(f"⚠️  Could not save to .env file: {e}")
    
    print(f"✅ API key set for current session")
    print("💡 To make it permanent, add this to your system environment variables:")
    print(f"   OWM_API_KEY={api_key}")
    print()
    
    return True

def test_weather_api():
    """Test the weather API connection"""
    try:
        from backend.weather_service import get_weather_info
        weather = get_weather_info()
        
        if weather.get("error"):
            print(f"❌ Weather API test failed: {weather['error']}")
            return False
        
        print(f"✅ Weather API working!")
        print(f"   Location: {weather['city']}")
        print(f"   Temperature: {weather['temperature']:.1f}°C")
        print(f"   Conditions: {weather['description']}")
        return True
        
    except Exception as e:
        print(f"❌ Weather API test failed: {e}")
        return False

if __name__ == "__main__":
    if setup_weather_api():
        test_weather_api()
    else:
        print("⚠️  Skipping weather API test (no key provided)")
