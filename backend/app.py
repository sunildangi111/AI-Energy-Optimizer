#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 20:23:32 2025

@author: Sunil
"""

from flask import Flask, request, jsonify
import math
import os
import joblib
import numpy as np
from weather_service import get_current_temperature, get_weather_info, weather_service

app = Flask(__name__)

# ─── Load trained model if available ────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "rf_model.pkl")
REAL_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "real_rf_model.pkl")
trained_model = None
model_type = "rule-based"

# Try to load real model first, then synthetic model
for model_path, model_name in [(REAL_MODEL_PATH, "real"), (MODEL_PATH, "synthetic")]:
    if os.path.exists(model_path):
        try:
            trained_model = joblib.load(model_path)
            model_type = model_name
            print(f"✅ Loaded {model_name} trained model from {model_path}")
            break
        except Exception as e:
            print(f"⚠️  Failed to load {model_name} model: {e}")

if trained_model is None:
    print(f"⚠️  No trained model found")
    print(f"   Looking for: {REAL_MODEL_PATH} or {MODEL_PATH}")
    print(f"   Using rule-based predictor. Run 'python backend/train_real_model.py' or 'python backend/train_model.py'")

# ─── Simple rule-based predictor (no ML dependency) ─────────────────────────────
def rule_based_predict(hour, temperature, occupancy, is_weekend):
	# Base load
	base = 200.0
	# Temperature contributes positively
	temp_component = 5.0 * float(temperature)
	# Occupancy contributes positively
	occ_component = 2.0 * float(occupancy)
	# Weekend uplift
	weekend_component = 20.0 * (1 if int(is_weekend) else 0)
	# Mild hour-of-day modulation (peak around afternoon)
	hour_component = 10.0 * math.sin(2 * math.pi * (float(hour) - 12.0) / 24.0)
	return base + temp_component + occ_component + weekend_component + hour_component

# ─── 1) PREDICTION ENDPOINT ─────────────────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
	data = request.get_json()
	hour = data["hour"]
	temperature = data.get("temperature")  # Optional parameter
	occupancy = data["occupancy"]
	is_weekend = data["is_weekend"]
	
	# If temperature not provided, get real-time weather data
	if temperature is None:
		temperature = get_current_temperature()
		print(f"🌡️  Using real-time temperature: {temperature}°C")
	else:
		temperature = float(temperature)
	
	# Use trained model if available, otherwise fall back to rule-based
	if trained_model is not None:
		# Prepare features in the same format as training data
		# Features: [hour, temperature, occupancy, is_weekend_True]
		is_weekend_true = 1 if int(is_weekend) else 0
		features = np.array([[hour, temperature, occupancy, is_weekend_true]])
		pred = trained_model.predict(features)[0]
	else:
		pred = rule_based_predict(hour, temperature, occupancy, is_weekend)
	
	return jsonify({
		"predicted_usage_kW": round(float(pred), 2),
		"model_type": model_type,
		"temperature_used": round(float(temperature), 1)
	})

# ─── 2) IN‐MEMORY SENSOR STATE ───────────────────────────────────────────────────
sensor_data = {
	"occupancy": 0,
	"power_kW": None,
	"temperature": None,
	"timestamp": None
}

# ─── 3) UPDATE ROUTE (called by sensor_feed.py) ────────────────────────────────
@app.route("/sensor_update", methods=["POST"])
def sensor_update():
	global sensor_data
	sensor_data = request.get_json()
	return jsonify({"status": "ok"}), 200

# ─── 4) READ ROUTE (called by streamlit_app.py) ────────────────────────────────
@app.route("/current_status", methods=["GET"])
def current_status():
	return jsonify(sensor_data), 200

# ─── 5) WEATHER ROUTE ────────────────────────────────────────────────────────────
@app.route("/weather", methods=["GET"])
def get_weather():
	"""Get current weather information"""
	weather_info = get_weather_info()
	return jsonify(weather_info), 200

# ─── 5b) SET WEATHER CITY ROUTE ──────────────────────────────────────────────────
@app.route("/set_city", methods=["POST"])
def set_city():
	"""Update the default city used for weather-based calculations"""
	data = request.get_json() or {}
	city = (data.get("city") or "").strip()
	if not city:
		return jsonify({"error": "city is required"}), 400
	weather_service.city = city
	print(f"🌍 Weather city updated to: {city}")
	return jsonify({"status": "ok", "city": city}), 200

# ─── 6) MAIN LAUNCH ────────────────────────────────────────────────────────────
if __name__ == "__main__":
	# Print your routes so you can verify they’re registered
	print("\n>>> Registered routes:")
	for rule in app.url_map.iter_rules():
		methods = ",".join(sorted(rule.methods - {"HEAD","OPTIONS"}))
		print(f"  {methods:10}  {rule}")
	print()
	app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
