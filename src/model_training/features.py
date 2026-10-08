from __future__ import annotations

import pandas as pd


FEATURE_COLUMNS = [
    "precipitation_mm",
    "elevation_m",
    "building_count",
    "drainage_dist_km",
    "rain_3d",
    "rain_7d",
    "rain_delta",
    "is_monsoon",
    "rain_elev_interact",
]

LABEL_ORDER = ["Low", "Medium", "High"]


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Time-aware features the original rule-based label does not use."""
    out = df.copy()
    out = out.sort_values(["latitude", "longitude", "date"])
    grouped = out.groupby(["latitude", "longitude"], sort=False)["precipitation_mm"]
    out["rain_3d"] = grouped.transform(lambda s: s.rolling(3, min_periods=1).sum())
    out["rain_7d"] = grouped.transform(lambda s: s.rolling(7, min_periods=1).sum())
    out["rain_delta"] = grouped.transform(lambda s: s.diff().fillna(0))
    out["is_monsoon"] = out["date"].dt.month.isin([6, 7, 8, 9]).astype(int)
    out["rain_elev_interact"] = out["precipitation_mm"] / (out["elevation_m"].clip(lower=0) + 1.0)
    return out


def features_from_manual(
    precipitation_mm: float,
    elevation_m: float,
    building_count: float,
    drainage_dist_km: float,
    rain_3d: float | None = None,
    rain_7d: float | None = None,
    rain_delta: float = 0.0,
    is_monsoon: int = 1,
) -> dict:
    rain_3d = precipitation_mm if rain_3d is None else rain_3d
    rain_7d = precipitation_mm if rain_7d is None else rain_7d
    return {
        "precipitation_mm": precipitation_mm,
        "elevation_m": elevation_m,
        "building_count": building_count,
        "drainage_dist_km": drainage_dist_km,
        "rain_3d": rain_3d,
        "rain_7d": rain_7d,
        "rain_delta": rain_delta,
        "is_monsoon": is_monsoon,
        "rain_elev_interact": precipitation_mm / (max(elevation_m, 0) + 1.0),
    }
