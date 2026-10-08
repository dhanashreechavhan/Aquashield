from __future__ import annotations

from html import escape

import folium
from folium.plugins import HeatMap, MarkerCluster
import pandas as pd

from src.paths import VVN_CENTER


RISK_COLOR = {"Low": "#1e8449", "Medium": "#d68910", "High": "#c0392b"}


def base_map(zoom: int = 12) -> folium.Map:
    m = folium.Map(
        location=list(VVN_CENTER),
        zoom_start=zoom,
        tiles="OpenStreetMap",
        control_scale=True,
    )
    return m

def add_flood_grid(m: folium.Map, snap: pd.DataFrame) -> folium.Map:
    heat = []
    for _, row in snap.iterrows():
        weight = max(row.flood_risk_score / 100.0, 0.05)
        heat.append([row.latitude, row.longitude, weight])
        folium.CircleMarker(
            location=[row.latitude, row.longitude],
            radius=8 + row.flood_risk_score / 12,
            color=RISK_COLOR.get(row.flood_risk, "#555"),
            fill=True,
            fill_opacity=0.75,
            popup=folium.Popup(
                f"Grid {row.latitude:.3f}, {row.longitude:.3f}<br>"
                f"Risk: {row.flood_risk} ({row.flood_risk_score})<br>"
                f"Rain: {row.precipitation_mm} mm<br>"
                f"Elev: {row.elevation_m} m · Drain {row.drainage_dist_km:.2f} km<br>"
                f"<i>Processed observation + rule-based label</i>",
                max_width=280,
            ),
        ).add_to(m)
    if heat:
        HeatMap(heat, radius=28, blur=18, min_opacity=0.25).add_to(m)
    return m


def add_roads(m: folium.Map, roads: pd.DataFrame, sample: int = 2800) -> folium.Map:
    if len(roads) > sample:
        roads = roads.sample(sample, random_state=42)
    for _, row in roads.iterrows():
        folium.CircleMarker(
            location=[row.mid_lat, row.mid_lon],
            radius=2.4,
            color=RISK_COLOR.get(row.infra_risk, "#888"),
            fill=True,
            fill_opacity=0.65,
            popup=f"{escape(str(row.name))}<br>{escape(str(row.highway))}<br>Infra {escape(str(row.infra_risk))} ({row.infra_risk_score})",
        ).add_to(m)
    return m


def add_path(m: folium.Map, coords, color: str, name: str, weight: int = 6):
    if not coords:
        return
    folium.PolyLine(coords, color=color, weight=weight, opacity=0.9, tooltip=name).add_to(m)
    folium.Marker(coords[0], tooltip="Origin", icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker(coords[-1], tooltip="Destination", icon=folium.Icon(color="red", icon="stop")).add_to(m)


def add_social_videos(m: folium.Map, reports: list[dict]) -> folium.Map:
    cluster = MarkerCluster(name="Public social videos").add_to(m)
    color_for = {"high": "red", "medium": "orange", "low": "green"}
    for row in reports:
        lat, lon = row.get("lat"), row.get("lng")
        if lat is None or lon is None:
            continue
        if row.get("relevant") is False:
            continue
        sev = str(row.get("severity", "medium")).lower()
        folium.Marker(
            [lat, lon],
            tooltip=f"{escape(str(row.get('platform')))} · {escape(str(row.get('location')))} · {escape(sev)}",
            popup=folium.Popup(
                f"<b>{escape(str(row.get('title') or ''))}</b><br>"
                f"{escape(str(row.get('location') or ''))} · {escape(sev)}<br>"
                f"{escape(str(row.get('published_at') or '')[:10])}"
                f"<br><i>Public video pin — not official proof of flooding.</i>",
                max_width=280,
            ),
            icon=folium.Icon(color=color_for.get(sev, "blue"), icon="play"),
        ).add_to(cluster)
    return m


def add_reports(m: folium.Map, reports: list[dict]) -> folium.Map:
    cluster = MarkerCluster(name="Community reports").add_to(m)
    for rep in reports:
        if rep.get("latitude") is None or rep.get("longitude") is None:
            continue
        color = {
            "Verified": "green",
            "Rejected": "gray",
            "Unverified": "orange",
        }.get(rep.get("verification_status"), "orange")
        layer = rep.get("source_layer")
        folium.Marker(
            [rep["latitude"], rep["longitude"]],
            tooltip=f"{escape(str(rep['verification_status']))} · {escape(str(layer))}",
            popup=folium.Popup(
                f"<b>{escape(str(rep['caption']))}</b><br>{escape(str(rep['created_at'])[:19])} UTC"
                f"<br>Status: {escape(str(rep['verification_status']))}"
                f"<br>Layer: {escape(str(layer))}"
                f"<br><i>Unverified reports are not treated as proof of flooding.</i>",
                max_width=280,
            ),
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(cluster)
    return m
