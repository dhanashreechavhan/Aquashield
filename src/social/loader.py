from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from src.paths import SOCIAL_REPORTS

_HANDOFF = Path(__file__).resolve().parents[2] / "aquashield_handoff" / "backend" / "data" / "flood_reports.json"


def load_social_reports() -> list[dict]:
    backend = os.environ.get("BACKEND_URL")
    if backend:
        try:
            response = requests.get(f"{backend.rstrip('/')}/api/flood-reports", params={"limit": 500}, timeout=12)
            response.raise_for_status()
            return response.json()
        except Exception:
            pass
    for path in (SOCIAL_REPORTS, _HANDOFF):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return []
