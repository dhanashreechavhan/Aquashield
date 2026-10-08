from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.paths import COMMUNITY_DB, DATA_SYNTHETIC, UPLOADS

ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO = {".mp4", ".mov", ".webm", ".m4v"}


def _connect() -> sqlite3.Connection:
    UPLOADS.mkdir(parents=True, exist_ok=True)
    COMMUNITY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(COMMUNITY_DB)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            caption TEXT NOT NULL,
            created_at TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            location_label TEXT,
            media_path TEXT,
            media_kind TEXT,
            verification_status TEXT NOT NULL,
            source_layer TEXT NOT NULL,
            notes TEXT
        )
        """
    )
    conn.commit()
    return conn


def seed_synthetic_demo_posts() -> None:
    DATA_SYNTHETIC.mkdir(parents=True, exist_ok=True)
    existing = {row["caption"] for row in list_reports()}
    demos = [
        {
            "caption": "Standing water near Nalasopara station underpass after evening rain (demo).",
            "latitude": 19.419,
            "longitude": 72.814,
            "location_label": "Nalasopara West",
            "verification_status": "Unverified",
            "source_layer": "synthetic_demo",
            "notes": "Synthetic demonstration post — not a real citizen upload.",
        },
        {
            "caption": "Virar East lane clear; drainage flowing (demo).",
            "latitude": 19.455,
            "longitude": 72.841,
            "location_label": "Virar East",
            "verification_status": "Verified",
            "source_layer": "synthetic_demo",
            "notes": "Synthetic demonstration post — verified only to show UI states.",
        },
        {
            "caption": "[Facebook-style demo] Vasai West residents sharing photos of standing water near the market after afternoon rain.",
            "latitude": 19.361,
            "longitude": 72.805,
            "location_label": "Vasai West",
            "verification_status": "Unverified",
            "source_layer": "synthetic_demo",
            "notes": "Synthetic Facebook-style community post. Not a live Facebook API feed.",
        },
        {
            "caption": "[Facebook-style demo] Naigaon commuters reporting slow traffic near the underpass; water receding.",
            "latitude": 19.351,
            "longitude": 72.846,
            "location_label": "Naigaon",
            "verification_status": "Unverified",
            "source_layer": "synthetic_demo",
            "notes": "Synthetic Facebook-style community post. Not a live Facebook API feed.",
        },
    ]
    for item in demos:
        if item["caption"] in existing:
            continue
        add_report(media_bytes=None, filename=None, **item)
    marker = DATA_SYNTHETIC / "demo_seeded.json"
    marker.write_text(json.dumps({"seeded": True}), encoding="utf-8")


def add_report(
    caption: str,
    latitude: float | None,
    longitude: float | None,
    location_label: str | None,
    verification_status: str = "Unverified",
    source_layer: str = "user_report",
    notes: str | None = None,
    media_bytes: bytes | None = None,
    filename: str | None = None,
) -> str:
    conn = _connect()
    report_id = str(uuid.uuid4())
    media_path = None
    media_kind = "none"
    if media_bytes and filename:
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_IMAGE:
            media_kind = "image"
        elif ext in ALLOWED_VIDEO:
            media_kind = "video"
        else:
            raise ValueError("Unsupported media type. Use an image or short video.")
        dest = UPLOADS / f"{report_id}{ext}"
        dest.write_bytes(media_bytes)
        media_path = str(dest)
    created = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO reports (
            id, caption, created_at, latitude, longitude, location_label,
            media_path, media_kind, verification_status, source_layer, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_id,
            caption.strip(),
            created,
            latitude,
            longitude,
            location_label,
            media_path,
            media_kind,
            verification_status,
            source_layer,
            notes,
        ),
    )
    conn.commit()
    conn.close()
    return report_id


def list_reports() -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_verification(report_id: str, status: str) -> None:
    if status not in {"Unverified", "Verified", "Rejected"}:
        raise ValueError("Invalid status")
    conn = _connect()
    conn.execute("UPDATE reports SET verification_status = ? WHERE id = ?", (status, report_id))
    conn.commit()
    conn.close()
