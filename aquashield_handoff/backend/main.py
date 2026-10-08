"""
AquaShield backend - serves flood video reports (YouTube Shorts / Instagram Reels).

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload
Docs (auto-generated, try the endpoints here):
    http://127.0.0.1:8000/docs
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DATA_FILE = Path(__file__).parent / "data" / "flood_reports.json"

app = FastAPI(title="AquaShield Flood Reports API")

# Allow the Streamlit app / any frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_reports():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_reports(reports):
    DATA_FILE.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")


@app.get("/api/health")
def health():
    return {"status": "ok", "reports": len(load_reports())}


@app.get("/api/flood-reports")
def list_reports(
    platform: Optional[str] = Query(None, description="youtube or instagram"),
    severity: Optional[str] = Query(None, description="low, medium or high"),
    location: Optional[str] = Query(None, description="text match, e.g. Virar"),
    limit: int = Query(100, ge=1, le=500),
):
    reports = load_reports()
    if platform:
        reports = [r for r in reports if r.get("platform") == platform.lower()]
    if severity:
        reports = [r for r in reports if r.get("severity") == severity.lower()]
    if location:
        reports = [r for r in reports if location.lower() in r.get("location", "").lower()]
    reports.sort(key=lambda r: r.get("published_at", ""), reverse=True)
    return reports[:limit]


@app.get("/api/flood-reports/{report_id}")
def get_report(report_id: str):
    for r in load_reports():
        if r.get("id") == report_id:
            return r
    raise HTTPException(status_code=404, detail="Report not found")


@app.post("/api/flood-reports")
def add_report(report: dict):
    """Add one report (same fields as flood_reports.json). Skips duplicates by id."""
    required = {"id", "platform", "video_id", "location", "lat", "lng", "severity", "source_url"}
    missing = required - report.keys()
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing fields: {sorted(missing)}")
    reports = load_reports()
    if any(r.get("id") == report["id"] for r in reports):
        raise HTTPException(status_code=409, detail="Report with this id already exists")
    reports.append(report)
    save_reports(reports)
    return {"saved": True, "total": len(reports)}


@app.get("/api/stats")
def stats():
    reports = load_reports()
    by_severity, by_location = {}, {}
    for r in reports:
        by_severity[r.get("severity", "unknown")] = by_severity.get(r.get("severity", "unknown"), 0) + 1
        by_location[r.get("location", "unknown")] = by_location.get(r.get("location", "unknown"), 0) + 1
    return {"total": len(reports), "by_severity": by_severity, "by_location": by_location}
