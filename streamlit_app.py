#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Energy Optimizer Dashboard
Auto-adjusts AC & lighting based on occupancy, real-time weather & live sensor feed
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import datetime
import os
import math
import csv
from pathlib import Path
from zoneinfo import ZoneInfo

# ─── 1) PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Walmart Project",
    page_icon="",
    layout="wide",
)

# ─── 0) REMOVE TOP BLANK ─────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      /* remove that big top‐margin above the first header */
      .block-container {
        padding-top: 0rem;
      }
      .metric-card { border: 1px solid rgba(200,200,200,0.15); border-radius: 10px; padding: 12px; }
      .metric-label { color: #9aa4b2; font-size: 12px; }
      .metric-value { font-size: 22px; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── 2) AUTO-REFRESH EVERY 5s ────────────────────────────────────────────────────
st_autorefresh(interval=5_000, limit=None, key="sensor_refresh")

# ─── 3) WEATHER API KEY ──────────────────────────────────────────────────────────
# Read key each call: prefer env var, else st.secrets if available

def _get_owm_api_key() -> str | None:
    key = os.getenv("OWM_API_KEY")
    if key:
        return key
    try:
        return st.secrets["weather"]["OWM_API_KEY"]
    except Exception:
        return None

# ─── THEME CONTROLS ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Appearance")
    theme = st.radio("Theme", ["Dark", "Light"], index=0, horizontal=True)
    accent = st.selectbox("Accent color", ["Teal", "Blue", "Green", "Orange"], index=0)

accent_map = {
    "Teal": "#14b8a6",
    "Blue": "#3b82f6",
    "Green": "#22c55e",
    "Orange": "#f59e0b",
}
accent_hex = accent_map.get(accent, "#14b8a6")

if theme == "Dark":
    st.markdown(
        f"""
        <style>
          body, .stApp {{ background: #0b1220; color: #e6edf6; }}
          .metric-card {{ border-color: rgba(255,255,255,0.12); }}
          a, .st-emotion-cache-16idsys a {{ color: {accent_hex}; }}
          .stButton>button {{ background:{accent_hex}; color:white; border:none; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"""
        <style>
          /* Light theme: enforce high-contrast readable text */
          body, .stApp {{ background: #ffffff; color: #0b1220; }}
          /* General text elements */
          .stApp, .stApp div, .stApp span, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{ color: #0b1220 !important; }}
          /* Sidebar */
          [data-testid="stSidebar"], [data-testid="stSidebar"] * {{ background: #f8fafc; color:#0b1220 !important; }}
          /* Inputs */
          input, textarea, select {{ color:#0b1220 !important; background:#ffffff !important; }}
          /* Metrics */
          .metric-card {{ background:#ffffff; border-color: rgba(0,0,0,0.1); }}
          .metric-label {{ color:#334155 !important; }}
          .metric-value {{ color:#0b1220 !important; }}
          /* Links & buttons */
          a, .st-emotion-cache-16idsys a {{ color: {accent_hex} !important; }}
          .stButton>button {{ background:{accent_hex}; color:white; border:none; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ─── 4) FETCH REAL-TIME WEATHER ─────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_weather(city_or_coords: str, nonce: int) -> dict:
    api_key = _get_owm_api_key()
    if not api_key:
        return {"error": True, "msg": "OWM_API_KEY not set"}

    base = "https://api.openweathermap.org/data/2.5/weather"

    # Accept either "City" or "lat,lon"
    lat = lon = None
    if "," in city_or_coords:
        parts = [p.strip() for p in city_or_coords.split(",", 1)]
        try:
            lat = float(parts[0])
            lon = float(parts[1])
        except Exception:
            lat = lon = None

    if lat is not None and lon is not None:
        params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    else:
        params = {"q": city_or_coords, "appid": api_key, "units": "metric"}

    r = requests.get(base, params=params)
    d = r.json()
    if r.status_code != 200 or "main" not in d or "weather" not in d:
        return {"error": True, "msg": d.get("message", "Unknown error")}
    return {
        "error": False,
        "temp" : d["main"]["temp"],
        "desc" : d["weather"][0]["description"].title(),
        "icon" : d["weather"][0]["icon"],
        "city" : d.get("name") or city_or_coords,
    }

# ─── 5) FETCH LIVE SENSOR STATUS ────────────────────────────────────────────────
@st.cache_data(ttl=5)
def fetch_sensor() -> dict:
    try:
        resp = requests.get("http://127.0.0.1:5000/current_status", timeout=1)
        resp.raise_for_status()
        data = resp.json()
        power = float(data.get("power_kW") or 0.0)
        occ   = int(data.get("occupancy") or 0)
        return {"occupancy": occ, "power_kW": power}
    except Exception:
        return {"occupancy": 0, "power_kW": 0.0}

# ─── SIDEBAR CONTROLS ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ☀️ Real-Time Weather")
    if "weather_nonce" not in st.session_state:
        st.session_state.weather_nonce = 0
    city_input = st.text_input("City or 'Lat-Lon'", "Darbhanga")
    if st.button("Refresh weather", type="secondary"):
        st.session_state.weather_nonce += 1
        # Clear local weather cache
        fetch_weather.clear()
        # Inform backend so sensor_feed uses the same city
        try:
            requests.post(
                "http://127.0.0.1:5000/set_city",
                json={"city": city_input},
                timeout=2,
            )
        except Exception:
            # Fail silently; dashboard will still use direct API
            pass
    weather = fetch_weather(city_input, st.session_state.weather_nonce)
    if weather.get("error"):
        msg = weather.get("msg", "Weather fetch failed")
        st.warning(f"Weather unavailable: {msg}. Using defaults.")
        weather = {"temp": 25.0, "desc": "Clear", "icon": "01d", "city": city_input}
    st.markdown(
        f"""
        <div style=\"display:flex; align-items:center; gap:6px; margin-bottom:12px;\">
          <img src=\"http://openweathermap.org/img/wn/{weather['icon']}@2x.png\"
               width=\"28\" height=\"28\" />
          <span style=\"font-size:14px; line-height:1.2;\">
            {weather['temp']:.1f}°C, {weather['desc']}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("###  Live Sensor Feed")
    sensor        = fetch_sensor()
    occupancy_raw = sensor["occupancy"]
    current_usage = sensor["power_kW"]

    # Time awareness controls
    st.markdown("###  Time (IST)")
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    st.caption(f"Current IST: {now_ist.strftime('%Y-%m-%d %H:%M')} (UTC+5:30)")
    use_custom_time = st.checkbox("Use custom time of day", value=False)
    custom_hour = st.slider("Hour of day (IST)", 0, 23, value=now_ist.hour, disabled=not use_custom_time)

    st.markdown("###  Time-aware occupancy")
    occ_blend = st.slider("Blend with IST profile", 0.0, 1.0, value=0.4, help="0 uses sensor only, 1 uses profile only")

    st.markdown("###  ROI Settings")
    cost_per_kwh = st.number_input("Cost per kWh (₹)", 0.1, 20.0, 7.0)
    num_stores   = st.slider("No. of identical stores", 1, 50, 1)

    st.write(f"**Sensor occupancy:** {occupancy_raw} people")
    st.write(f"**Power draw:** {current_usage:.1f} kW")

# Safety defaults in case of rerun ordering
if 'cost_per_kwh' not in locals():
    cost_per_kwh = 7.0
if 'num_stores' not in locals():
    num_stores = 1

# ─── 7) TIME, OCCUPANCY PROFILE & FEATURES ──────────────────────────────────────
# Use IST hour (or custom) to better reflect India operations
hour_source = custom_hour if use_custom_time else datetime.datetime.now(ZoneInfo("Asia/Kolkata")).hour
now         = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
hour        = int(hour_source)

def occupancy_profile_0_1(hour_local: int, weekend: bool) -> float:
    # Peak during 11:00–19:00, low overnight; weekend slightly lower
    base = 0.15 + 0.55 * max(0.0, math.sin((hour_local - 8) / 24 * math.pi))  # 0.15..0.70
    weekend_factor = 0.85 if weekend else 1.0
    return max(0.05, min(0.95, base * weekend_factor))

temperature = weather["temp"]
max_occ     = 200
ideal_temp  = 22.0

# Determine weekend from IST date
is_weekend = now.weekday() >= 5
profile_occ = int(occupancy_profile_0_1(hour, is_weekend) * max_occ)
occupancy   = int((1 - occ_blend) * occupancy_raw + occ_blend * profile_occ)

occ_factor  = occupancy / max_occ
if max_occ == 0:
    occ_factor = 0.0

temp_factor = min(max((temperature - ideal_temp) / 28, 0), 1)

ac_bump     = round(min(1 + occ_factor*2 + temp_factor*2, 5), 1)
dim_pct     = round(min(10 + occ_factor*30 + temp_factor*20, 60), 0)

# ─── 8) PREDICTION VIA BACKEND ML MODEL ─────────────────────────────────────────────
def get_backend_prediction(hour, temperature, occupancy, is_weekend):
    """Call the backend /predict endpoint to use the trained RandomForest model."""
    try:
        payload = {
            "hour": int(hour),
            "temperature": float(temperature),
            "occupancy": int(occupancy),
            "is_weekend": int(is_weekend)
        }
        resp = requests.post("http://127.0.0.1:5000/predict", json=payload, timeout=2)
        resp.raise_for_status()
        data = resp.json()
        return float(data.get("predicted_usage_kW", 0.0)), data.get("model_type", "unknown"), data.get("temperature_used", temperature)
    except Exception as e:
        # Fallback to a simple rule if backend is down
        print(f"Backend prediction failed: {e}")
        base = 200.0
        temp_component = 5.0 * float(temperature)
        occ_component = 2.0 * float(occupancy)
        weekend_component = 20.0 * (1 if int(is_weekend) else 0)
        hour_component = 10.0 * math.sin(2 * math.pi * (float(hour) - 12.0) / 24.0)
        pred = base + temp_component + occ_component + weekend_component + hour_component
        return float(pred), "fallback", temperature

pred_usage, model_type_used, temp_used = get_backend_prediction(hour, temperature, occupancy, int(is_weekend))

# ─── DYNAMIC SAFETY BUFFER ───────────────────────────────────────────────────────
# Cap predicted usage to maintain a dynamic safety margin (15% of current, 10–60 kW)
buffer_kW = max(10.0, min(60.0, round(0.15 * max(current_usage, 0.0), 1)))
max_allowed = max(current_usage - buffer_kW, 0.0)
if pred_usage > max_allowed:
    pred_usage = max_allowed

# ─── 9) OVERVIEW METRICS ────────────────────────────────────────────────────────
st.markdown(
	f"""
	<div class="metric-card" style="margin-bottom: 1rem;">
	  <div class="metric-label">Live Store Overview</div>
	  <div class="metric-value">
	    {weather['city']} • {temperature:.1f}°C • {occupancy} people • {current_usage:.1f} kW
	  </div>
	</div>
	""",
	unsafe_allow_html=True,
)

st.markdown("##  Overview", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4, gap="large")

# 1) Current
c1.metric("Current Usage (kW)", f"{current_usage:.2f}")

# 2) Predicted (with delta always ≤ 0)
delta = pred_usage - current_usage
c2.metric("Predicted Usage (kW)", f"{pred_usage:.2f}", delta=f"{delta:+.2f}")

# 3) Savings %
if current_usage:
	savings_pct = max(0.0, (current_usage - pred_usage) / current_usage * 100)
else:
	savings_pct = 0.0
c3.metric("Savings %", f"{savings_pct:.0f}%")

# 4) Monthly ₹
monthly_savings = (savings_pct/100) * current_usage * 24 * 30 * cost_per_kwh * num_stores
c4.metric("Monthly Savings (₹)", f"{monthly_savings:,.0f}")

# ─── 10) AI RECOMMENDATIONS ─────────────────────────────────────────────────────
st.markdown("##  AI Recommendations")
if occupancy == 0:
	st.info("No occupancy detected: dim lights by 60% and set AC to energy-saver mode.")
else:
	st.success(f"Increase AC setpoint by +{ac_bump}°C to reduce cooling load.")
	st.success(f"Dim ambient lighting by {dim_pct}% while maintaining aisle task lighting.")

# ─── 11) TRENDS CHART (REAL DATA SAMPLE) ────────────────────────────────────────
try:
	import pandas as pd
	import altair as alt
	csv_path = (Path(__file__).resolve().parent / "real_walmart_energy.csv").as_posix()
	df = pd.read_csv(csv_path)
	if "timestamp" not in df.columns:
		# Fallback: create a synthetic hourly index if missing
		n = len(df)
		end = now
		start = end - datetime.timedelta(hours=n-1)
		df["timestamp"] = pd.date_range(start, periods=n, freq="h")
	df["timestamp"] = pd.to_datetime(df["timestamp"])

	st.markdown("##  Energy & Temperature Trends (24h sample)")
	latest = df.tail(24)
	base = alt.Chart(latest).encode(x="timestamp:T")
	usage_line = base.mark_line(color=accent_hex, strokeWidth=2).encode(
		y=alt.Y("energy_kW:Q", axis=alt.Axis(title="kW")),
		tooltip=["timestamp", "energy_kW", "temperature"],
	)
	temp_line = base.mark_line(color="#9AA4B2", strokeDash=[4,3]).encode(
		y=alt.Y(
			"temperature:Q",
			axis=alt.Axis(title="°C"),
			scale=alt.Scale(zero=False),
		),
		tooltip=["timestamp", "temperature"],
	)
	chart = alt.layer(usage_line, temp_line).resolve_scale(y="independent")
	st.altair_chart(chart, use_container_width=True)
except Exception:
	st.info("Trend chart unavailable (install pandas/altair and ensure real_walmart_energy.csv exists).")

# ─── 13) FOOTER ──────────────────────────────────────────────────────────────────
st.markdown(
	"<hr><small> • Sustainable Energy Optimizer for Walmart • 2025</small>",
	unsafe_allow_html=True,
)