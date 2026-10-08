from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from src.paths import FORECAST_CSV, VVN_CENTER


def fetch_live_forecast(lat: float | None = None, lon: float | None = None, days: int = 7) -> pd.DataFrame:
    lat = VVN_CENTER[0] if lat is None else lat
    lon = VVN_CENTER[1] if lon is None else lon
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum,rain_sum,precipitation_probability_max",
        "forecast_days": days,
        "timezone": "Asia/Kolkata",
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(
        {
            "date": data["daily"]["time"],
            "precipitation_mm": data["daily"]["precipitation_sum"],
            "rain_mm": data["daily"]["rain_sum"],
            "rain_probability_pct": data["daily"]["precipitation_probability_max"],
        }
    )
    df["latitude"] = lat
    df["longitude"] = lon
    df["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
    df["source"] = "open_meteo_forecast"
    return df


def load_forecast_with_fallback(thresholds: dict) -> tuple[pd.DataFrame, str]:
    try:
        df = fetch_live_forecast()
        note = "Live Open-Meteo forecast (network)."
    except Exception as exc:
        if FORECAST_CSV.exists():
            df = pd.read_csv(FORECAST_CSV)
            dates = pd.to_datetime(df["date"], errors="coerce").dropna()
            last_date = dates.max().date() if not dates.empty else None
            today = pd.Timestamp.now(tz="Asia/Kolkata").date()
            if last_date is None or last_date < today:
                last_label = last_date.isoformat() if last_date else "unknown date"
                note = (
                    f"Live forecast unavailable and the saved fallback is stale (last date {last_label}); "
                    "do not interpret it as a current forecast."
                )
            else:
                note = f"Using saved forecast fallback through {last_date.isoformat()} (live API unavailable)."
        else:
            raise
    df = df.copy()
    df["flood_risk_forecast"] = df["precipitation_mm"].apply(
        lambda mm: "Low" if mm < thresholds["low"] else ("Medium" if mm < thresholds["medium"] else "High")
    )
    return df, note


def simulate_iot_series(hours: int = 48, now: datetime | None = None) -> pd.DataFrame:
    """Seeded, time-varying stand-in for ESP32 + Firebase. Not real hardware."""
    now = now or datetime.now()
    seed = int(now.strftime("%Y%m%d%H%M"))
    rng = np.random.default_rng(seed)
    index = pd.date_range(end=now, periods=hours, freq="h")
    t = np.arange(hours)
    diurnal = 0.5 + 0.5 * np.sin((t / 24.0) * 2 * np.pi)
    rain_rate = np.clip(rng.gamma(1.2, 1.8, hours) * (0.4 + diurnal), 0, 25)
    # monsoon-ish boost in Jun-Sep
    if now.month in (6, 7, 8, 9):
        rain_rate *= 1.6
    water_level_cm = np.clip(18 + np.cumsum(rain_rate * 0.15 - 0.35) + rng.normal(0, 1.2, hours), 5, 180)
    soil = np.clip(35 + rain_rate * 2.2 + rng.normal(0, 3, hours), 10, 95)
    temp = 27 + 4 * np.sin((t / 24.0) * 2 * np.pi + 1.2) + rng.normal(0, 0.4, hours)
    df = pd.DataFrame(
        {
            "timestamp": index,
            "water_level_cm": water_level_cm,
            "rain_rate_mm_hr": rain_rate,
            "soil_moisture_pct": soil,
            "temperature_c": temp,
        }
    )
    df["source"] = "simulation"
    return df
