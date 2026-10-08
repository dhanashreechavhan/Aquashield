"""Assign VVN locations and severity from titles. Run from the project root."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.social.locations import OUTSIDE, PLACES

SRC = ROOT / "aquashield_handoff" / "backend" / "data" / "flood_reports.json"
INSTA = ROOT / "data" / "social" / "instagram_manual.json"
OUT = ROOT / "data" / "social" / "flood_reports.json"

HIGH_WORDS = (
    "flood", "flooded", "submerged", "waterlog", "water logging", "jalbharav",
    "जलभराव", "डूबा", "underpass", "wade", "knee", "inundat", "doob", "waterlogging",
    "station", "roads flooded", "vehicles submerged",
)
MED_WORDS = ("rain", "बारिश", "heavy rain", "downpour", "संततधार", "shower", "monsoon")
OUTSIDE_WORDS = (
    ("khar", "Khar, Mumbai"),
    ("airport", "Mumbai Airport"),
    ("dahanu", "Dahanu"),
    ("palghar", "Palghar"),
)


def _blob(text: str) -> str:
    return (text or "").lower()


def _jitter(video_id: str, lat: float, lon: float) -> tuple[float, float]:
    digest = hashlib.md5(video_id.encode("utf-8")).hexdigest()
    dx = (int(digest[:4], 16) / 65535.0 - 0.5) * 0.012
    dy = (int(digest[4:8], 16) / 65535.0 - 0.5) * 0.012
    return round(lat + dx, 5), round(lon + dy, 5)


def infer_place(title: str, channel: str) -> tuple[str, tuple[float, float], bool, str]:
    blob = _blob(f"{title} {channel}")
    for word, place in OUTSIDE_WORDS:
        if word in blob and "vasai" not in blob and "virar" not in blob and "nalasopara" not in blob:
            return place, OUTSIDE[place], False, "Title points outside Vasai–Virar–Nalasopara."
    checks = (
        ("nalasopara west", "Nalasopara West"),
        ("nalasopara east", "Nalasopara East"),
        ("नालासोपारा", "Nalasopara"),
        ("nalasopara", "Nalasopara"),
        ("virar west", "Virar West"),
        ("virar east", "Virar East"),
        ("विरार", "Virar"),
        ("virar", "Virar"),
        ("vasai west", "Vasai West"),
        ("वसई वेस्ट", "Vasai West"),
        ("vasai east", "Vasai East"),
        ("वसई", "Vasai"),
        ("vasai", "Vasai"),
        ("naigaon", "Naigaon"),
        ("नायगाव", "Naigaon"),
        ("pelhar", "Pelhar"),
    )
    for needle, place in checks:
        if needle in blob:
            return place, PLACES[place], True, "Place inferred from title/hashtags (approximate pin)."
    return "Vasai-Virar", PLACES["Vasai-Virar"], True, "No specific locality in title; pinned to VVN centre with jitter."


def infer_severity(title: str) -> str:
    blob = _blob(title)
    if any(w in blob for w in HIGH_WORDS):
        return "high"
    if any(w in blob for w in MED_WORDS):
        return "medium"
    return "low"


def enrich_one(row: dict) -> dict:
    out = dict(row)
    place, (lat, lon), relevant, note = infer_place(row.get("title", ""), row.get("channel", ""))
    lat, lon = _jitter(str(row.get("video_id") or row.get("id")), lat, lon)
    out["location"] = place
    out["lat"] = lat
    out["lng"] = lon
    out["severity"] = infer_severity(row.get("title", ""))
    out["relevant"] = relevant
    out["geo_note"] = note
    out["source_layer"] = "public_social_video"
    out["verification_status"] = "Unverified"
    return out


def main() -> None:
    reports = json.loads(SRC.read_text(encoding="utf-8"))
    cleaned = [enrich_one(r) for r in reports]
    if INSTA.exists():
        insta = json.loads(INSTA.read_text(encoding="utf-8"))
        cleaned.extend(insta)
    # Keep generated output repeatable if a platform entry appears in both inputs.
    unique = {}
    for row in cleaned:
        key = (row.get("platform"), row.get("video_id") or row.get("id"))
        unique[key] = row
    cleaned = list(unique.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")
    n_yt = sum(1 for r in cleaned if r.get("platform") == "youtube")
    n_ig = sum(1 for r in cleaned if r.get("platform") == "instagram")
    n_rel = sum(1 for r in cleaned if r.get("relevant"))
    print(f"Wrote {len(cleaned)} reports ({n_yt} YouTube, {n_ig} Instagram, {n_rel} marked relevant) -> {OUT}")


if __name__ == "__main__":
    main()
