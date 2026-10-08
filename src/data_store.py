from __future__ import annotations

import ast
import json
from functools import lru_cache

import pandas as pd
import yaml

from src.paths import CONFIG_PATH, EVENTS_CSV, FLOOD_CSV, FORECAST_CSV, METRICS_JSON, ROAD_CSV


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_maybe_list(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list) and parsed:
                return str(parsed[0])
            if isinstance(parsed, list):
                return ""
        except (ValueError, SyntaxError):
            return value
    return value


@lru_cache(maxsize=1)
def load_flood_dataset() -> pd.DataFrame:
    df = pd.read_csv(FLOOD_CSV, parse_dates=["date"])
    df["flood_risk"] = df["flood_risk"].astype(str)
    df["data_layer"] = "processed_observation"
    return df


@lru_cache(maxsize=1)
def load_road_dataset() -> pd.DataFrame:
    df = pd.read_csv(ROAD_CSV)
    for col in ("name", "highway"):
        if col in df.columns:
            df[col] = df[col].map(_parse_maybe_list)
    df["name"] = df["name"].fillna("Unnamed road")
    df["highway"] = df["highway"].fillna("unknown")
    df["data_layer"] = "osm_derived_infrastructure"
    return df.reset_index(drop=True)


@lru_cache(maxsize=1)
def load_known_events() -> pd.DataFrame:
    if not EVENTS_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(EVENTS_CSV)
    df["source_layer"] = "official_curated"
    return df


def load_metrics() -> dict | None:
    if not METRICS_JSON.exists():
        return None
    return json.loads(METRICS_JSON.read_text(encoding="utf-8"))


def latest_grid_snapshot(flood_df: pd.DataFrame) -> pd.DataFrame:
    latest = flood_df["date"].max()
    snap = flood_df[flood_df["date"] == latest].copy()
    return snap


def monsoon_months() -> set[int]:
    return {6, 7, 8, 9}
