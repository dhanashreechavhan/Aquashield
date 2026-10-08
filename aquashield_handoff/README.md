# AquaShield - Flood Video Reports (handoff pack)

Dummy/real flood videos from YouTube Shorts and Instagram Reels (Vasai-Virar-Nalasopara)
to show on the AquaShield site: a map of reports plus embedded videos.

Frontend (already live): https://aquashield-flood-intelligence.streamlit.app/
Backend (to build/deploy): the FastAPI app in `backend/`.

## Folder map
```
backend/
  main.py                  FastAPI app (the API)
  requirements.txt
  data/flood_reports.json  THE DATA (merged + de-duplicated from raw_searches/)
raw_searches/              The 4 original YouTube search downloads (kept as-is)
frontend_streamlit/
  flood_reports_page.py    Streamlit page: filters + map + embedded videos
data_tools/
  flood_shorts_test.html   Browser tool to fetch fresh YouTube Shorts -> JSON
  fetch_flood_shorts.py    Same thing as a Python script
  instagram_manual.template.json   Template for Instagram reels (added by hand)
```

## 0. About the data
`backend/data/flood_reports.json` = the 4 searches in `raw_searches/` merged, duplicates removed
(same video found by several searches). Searches used: "Vasai Virar flood" (x2), "Virar rain",
"Nalasopara waterlogging". Sept 2026 backward to July 2026 videos.

TODO for the team (data cleaning):
- `location`, `lat`, `lng` and `severity` are PLACEHOLDERS for every entry (Vasai-Virar, 19.42/72.82, medium).
  Set them properly per video (title/hashtags often name the place: Nalasopara, Virar, Vasai West...).
- Remove or mark videos that are not really floods (e.g. light drizzle, airport waterlogging far from
  Vasai-Virar, a house collapse, Dahanu bus). Suggestion: add a `relevant: true/false` field.
- Add Instagram reels by hand.

## 1. Run the backend (2 minutes)
```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs and try the endpoints:

| Endpoint | What it does |
|---|---|
| GET /api/health | Check it is running |
| GET /api/flood-reports | List reports. Optional: ?platform=youtube&severity=high&location=Virar&limit=50 |
| GET /api/flood-reports/{id} | One report |
| POST /api/flood-reports | Add a report (JSON body, same fields as below) |
| GET /api/stats | Counts by severity and location |

## 2. Show it in Streamlit
Copy `frontend_streamlit/flood_reports_page.py` into the Streamlit repo (as `pages/flood_reports.py`,
or import `show_flood_reports()` into the main app).

Set the backend address in Streamlit Cloud: App settings -> Secrets:
```
BACKEND_URL = "https://your-backend-url"
```
Until the backend is deployed, the page reads `backend/data/flood_reports.json` directly,
so the frontend can be built and tested right away.

## 3. Data format (one report)
| Field | Meaning |
|---|---|
| id | unique, e.g. yt_<videoId> or ig_<reelCode> |
| platform | youtube or instagram |
| video_id | YouTube video ID / Instagram reel code |
| title, channel | from the video |
| published_at | ISO date |
| duration_sec, views | numbers (0 if unknown) |
| location | place name (Vasai, Virar, Nalasopara...) |
| lat, lng | coordinates - APPROXIMATE, fix them per video |
| severity | low / medium / high |
| source_url | original link |
| embed_url | used to embed: https://www.youtube.com/embed/<id> or https://www.instagram.com/reel/<code>/embed |

## 4. Getting more data
**YouTube (automatic):** open `data_tools/flood_shorts_test.html` in a browser, paste YOUR OWN
YouTube Data API v3 key, search (e.g. "Nalasopara waterlogging"), press Fetch, then
Download flood_reports.json. Merge into `backend/data/flood_reports.json`.
Get a free key: console.cloud.google.com -> new project -> enable "YouTube Data API v3"
-> Credentials -> Create API key. Free limit is 10,000 units/day (each search = 100).

**Instagram (manual):** Instagram has no public search API and scraping breaks its terms.
Search hashtags in the app (#vasaivirarrain, #virarflood, #nalasoparaflood), open a public reel,
copy the link, and add an entry using `data_tools/instagram_manual.template.json`.
The reel code is the part after /reel/ in the URL.

**Cleaning tip:** the fetch tool guesses nothing about location. Set `location`, `lat`, `lng`
and `severity` by watching the video (or from the title/hashtags).

## 5. Rules
- NEVER commit an API key to GitHub. Each person uses their own key.
- Keep `.streamlit/secrets.toml` and `.env` out of git (see .gitignore).
- These are public videos shown by embed/link only - do not download or re-upload them.
- The data is dummy/demo data for the project, not an official flood record.

## 6. Suggested split of work
1. Backend: run it, deploy it (Render / Railway free tier), share the URL.
2. Frontend: add the Streamlit page, wire BACKEND_URL, style it.
3. Data: collect 30-50 reports (YouTube tool + Instagram by hand), fix lat/lng and severity.
4. Stretch: show the nearest videos on the flood-risk map; add a "report a flood" form that POSTs to the backend.
