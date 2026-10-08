"""
Streamlit page: flood video reports (map + embedded videos).

Use it as its own page (pages/flood_reports.py) or copy the function into the
existing AquaShield app and call show_flood_reports().

Config (pick one):
  - Streamlit secrets:  BACKEND_URL = "https://your-backend.onrender.com"
  - env variable:       BACKEND_URL
  - neither set -> falls back to the local JSON file (handy before the backend is live)
"""
import json
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

LOCAL_FALLBACK = Path(__file__).parent.parent / "backend" / "data" / "flood_reports.json"


def get_backend_url():
    try:
        return st.secrets["BACKEND_URL"]
    except Exception:
        return os.environ.get("BACKEND_URL")


@st.cache_data(ttl=300)
def load_reports(backend_url):
    if backend_url:
        r = requests.get(f"{backend_url.rstrip('/')}/api/flood-reports", params={"limit": 500}, timeout=15)
        r.raise_for_status()
        return r.json()
    return json.loads(LOCAL_FALLBACK.read_text(encoding="utf-8"))


def show_flood_reports():
    st.header("Flood video reports")
    try:
        reports = load_reports(get_backend_url())
    except Exception as e:
        st.error(f"Could not load reports: {e}")
        return
    if not reports:
        st.info("No reports yet.")
        return

    df = pd.DataFrame(reports)

    # Filters
    col1, col2 = st.columns(2)
    sev = col1.multiselect("Severity", ["low", "medium", "high"], default=["low", "medium", "high"])
    plat = col2.multiselect("Platform", ["youtube", "instagram"], default=["youtube", "instagram"])
    df = df[df["severity"].isin(sev) & df["platform"].isin(plat)]
    st.caption(f"{len(df)} reports")

    # Map (st.map needs columns named lat / lon)
    if not df.empty:
        st.map(df.rename(columns={"lng": "lon"})[["lat", "lon"]])

    # Videos
    for _, r in df.iterrows():
        st.subheader(r["title"])
        st.caption(f"{r['location']} | severity: {r['severity']} | {str(r['published_at'])[:10]} | {r['platform']}")
        if r["platform"] == "youtube":
            components.iframe(r["embed_url"], height=420)
        else:
            components.iframe(r["embed_url"], height=640)
        st.link_button("Open original", r["source_url"])


if __name__ == "__main__":
    show_flood_reports()
