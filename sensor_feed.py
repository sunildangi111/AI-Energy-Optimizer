#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  9 12:12:23 2025

@author: ashwanthelangovan
"""

# sensor_feed.py
import time, random, requests
import sys
import os
import datetime

# Add backend to path to import weather service
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

API = "http://127.0.0.1:5000"

def get_backend_temperature() -> float:
	"""Fetch current temperature from the backend /weather endpoint.
	This ensures the sensor feed uses the same city as configured by the dashboard.
	"""
	try:
		resp = requests.get(f"{API}/weather", timeout=2)
		resp.raise_for_status()
		data = resp.json()
		return float(data.get("temperature", 22.0))
	except Exception as e:
		print(f"Weather fallback (sensor_feed): {e}")
		return 22.0

print("🌡️  Starting sensor feed with backend weather integration...")

while True:
    # Get real temperature from backend weather API
    current_temp = get_backend_temperature()
    
    # Generate realistic occupancy based on time and temperature
    current_hour = datetime.datetime.now().hour
    
    # Base occupancy patterns for Walmart
    if 6 <= current_hour <= 23:  # Store hours
        if 8 <= current_hour <= 11:  # Morning peak
            base_occupancy = 120 + random.randint(-30, 30)
        elif 13 <= current_hour <= 16:  # Afternoon peak
            base_occupancy = 100 + random.randint(-25, 25)
        elif 18 <= current_hour <= 21:  # Evening peak
            base_occupancy = 160 + random.randint(-40, 40)
        else:  # Regular hours
            base_occupancy = 60 + random.randint(-20, 20)
    else:  # Closed
        base_occupancy = 0
    
    # Temperature affects occupancy (extreme weather reduces foot traffic)
    if current_temp < 5 or current_temp > 35:
        occupancy_factor = 0.7  # 30% reduction in extreme weather
    elif 15 <= current_temp <= 25:
        occupancy_factor = 1.2  # 20% increase in pleasant weather
    else:
        occupancy_factor = 1.0
    
    occupancy = max(0, int(base_occupancy * occupancy_factor + random.randint(-10, 10)))
    
    # Power draw correlates with occupancy and temperature (HVAC load)
    base_power = 250  # Base load for large store
    
    # HVAC power based on temperature deviation from ideal (22°C)
    temp_deviation = abs(current_temp - 22)
    hvac_power = min(temp_deviation * 15, 200)  # Max 200kW for HVAC
    
    # Occupancy power (lighting, equipment)
    occupancy_power = occupancy * 1.2
    
    # Total power with some randomness
    power_kW = round(base_power + hvac_power + occupancy_power + random.randint(-20, 20), 2)
    power_kW = max(200, min(800, power_kW))  # Keep within realistic bounds
    
    data = {
        "occupancy": occupancy,
        "power_kW": power_kW,
        "temperature": round(current_temp, 1),
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    try:
       resp = requests.post(f"{API}/sensor_update", json=data, timeout=2)
       print(f"→ sensor_update: {resp.status_code} - Occupancy: {occupancy}, Power: {power_kW}kW, Temp: {current_temp:.1f}°C")
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(5)