"""
Fetch flood-related YouTube Shorts and save them as flood_reports.json.

Setup:
  pip install requests
  export YOUTUBE_API_KEY="your_key"      (Windows: set YOUTUBE_API_KEY=your_key)
Run:
  python fetch_flood_shorts.py

Quota: each search = 100 units, each videos lookup = 1 unit (free limit 10,000/day).
Instagram Reels have no public search API, so add them by hand in
instagram_manual.json (same fields as the output) and they get merged in.
"""
import json
import os
import re
import sys
from pathlib import Path

import requests

API_KEY = os.environ.get("YOUTUBE_API_KEY")
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

QUERIES = [
    "Vasai flood",
    "Virar waterlogging",
    "Nalasopara flood",
    "Vasai Virar rain waterlogging",
]
PUBLISHED_AFTER = "2025-01-01T00:00:00Z"
MAX_SECONDS = 60          # Shorts length filter (Shorts can now be up to 180)
RESULTS_PER_QUERY = 25    # max 50

# Approximate coordinates - correct them per video if you know the exact spot
PLACES = {
    "virar": (19.4559, 72.8112),
    "nalasopara": (19.4150, 72.8200),
    "nallasopara": (19.4150, 72.8200),
    "vasai": (19.3919, 72.8397),
    "evershine": (19.4000, 72.8500),
    "naigaon": (19.3500, 72.8500),
}
SEVERITY_WORDS = {
    "high": ["rescue", "ndrf", "red alert", "submerged", "stranded", "boat", "trapped"],
    "medium": ["waterlogging", "flooded", "flood", "inundated", "traffic"],
}


def parse_duration(iso):
    """PT1M5S -> 65 seconds."""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def guess_location(text):
    text = text.lower()
    for name, (lat, lng) in PLACES.items():
        if name in text:
            return name.title(), lat, lng
    return "Vasai-Virar", 19.4200, 72.8200


def guess_severity(text):
    text = text.lower()
    for level in ("high", "medium"):
        if any(w in text for w in SEVERITY_WORDS[level]):
            return level
    return "low"


def search_ids(query):
    params = {
        "part": "id",
        "q": query,
        "type": "video",
        "videoDuration": "short",
        "regionCode": "IN",
        "order": "date",
        "publishedAfter": PUBLISHED_AFTER,
        "maxResults": RESULTS_PER_QUERY,
        "key": API_KEY,
    }
    r = requests.get(SEARCH_URL, params=params, timeout=20)
    r.raise_for_status()
    return [item["id"]["videoId"] for item in r.json().get("items", [])]


def video_details(ids):
    out = []
    for i in range(0, len(ids), 50):  # API accepts 50 ids per call
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(ids[i:i + 50]),
            "key": API_KEY,
        }
        r = requests.get(VIDEOS_URL, params=params, timeout=20)
        r.raise_for_status()
        out.extend(r.json().get("items", []))
    return out


def main():
    if not API_KEY:
        sys.exit("Set the YOUTUBE_API_KEY environment variable first.")

    ids = []
    for q in QUERIES:
        ids.extend(search_ids(q))
    ids = list(dict.fromkeys(ids))  # de-duplicate, keep order

    reports = []
    for v in video_details(ids):
        seconds = parse_duration(v["contentDetails"]["duration"])
        if seconds == 0 or seconds > MAX_SECONDS:
            continue
        sn = v["snippet"]
        text = f"{sn['title']} {sn.get('description', '')}"
        place, lat, lng = guess_location(text)
        reports.append({
            "id": f"yt_{v['id']}",
            "platform": "youtube",
            "video_id": v["id"],
            "title": sn["title"],
            "channel": sn["channelTitle"],
            "published_at": sn["publishedAt"],
            "duration_sec": seconds,
            "views": int(v.get("statistics", {}).get("viewCount", 0)),
            "location": place,
            "lat": lat,
            "lng": lng,
            "severity": guess_severity(text),
            "source_url": f"https://www.youtube.com/shorts/{v['id']}",
            "embed_url": f"https://www.youtube.com/embed/{v['id']}",
        })

    # Merge hand-collected Instagram reels, if the file exists
    manual = Path("instagram_manual.json")
    if manual.exists():
        reports.extend(json.loads(manual.read_text(encoding="utf-8")))

    Path("flood_reports.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Saved {len(reports)} reports to flood_reports.json")


if __name__ == "__main__":
    main()
