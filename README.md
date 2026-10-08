# AquaShield application — presentation copy

Urban flood intelligence demo for **Vasai–Virar–Nalasopara (VVN)**. This copy includes the Streamlit app, processed datasets, saved ML models, and project notes.

## What to say tomorrow (simple)

AquaShield is a flood-intelligence **application** (not a static website). It shows rainfall and flood risk, a map, an ML model, safer roads, a simulated IoT water sensor, citizen photo/video reports, and public YouTube/Instagram clips as extra dummy/real media.

| Layer | Honest label |
|---|---|
| Rainfall, elevation, roads | Source-derived files (Open-Meteo / OpenStreetMap); some derived grid values are approximations |
| Flood High/Medium/Low labels | Rule-based proxy formula, not a surveyed flood map |
| ML metrics | Measured hold-out scores on rule-generated labels; not proof of real-world flood prediction |
| IoT page | **Simulation** until ESP32 + Firebase exist |
| Community uploads | Four synthetic demo posts are labelled; new uploads are user-submitted and unverified |
| YouTube Shorts | Saved catalog of public Shorts links (65 records at this snapshot); not a live feed; pins are approximate/unverified |
| Instagram | Six manually written hashtag demo cards; no live Instagram feed and no Instagram video embeds |

## Run on Windows

Easiest: double-click `start_aquashield.bat`. The first run creates a Python virtual environment and installs requirements; it needs internet and may take several minutes. If the browser does not open automatically, visit http://localhost:8501.

Or open PowerShell in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

Browser opens at http://localhost:8501

Click the sidebar pages in this order for the viva:

1. Home Dashboard  
2. Flood Risk Map (tick the YouTube/Instagram pins)  
3. Analytics  
4. ML Model (show spatial Macro-F1, not accuracy)  
5. Road Risk Map  
6. Safe Routes (pick two different places)  
7. IoT Sensor Monitoring (say “simulated”)  
8. Community Reports (upload a phone photo)  
9. Social Videos (play a Short)

## Public web deployment (GitHub + Streamlit Community Cloud)

1. Create a GitHub repository. A **private** repository keeps the source code private; the deployed app can separately be made public.
2. In VS Code, open this project root. If Source Control says there is no repository, choose **Initialize Repository**. Stage the project files, enter a commit message, and commit. Then choose **Publish to GitHub** and make the repository private. The `models/*.joblib` files are included because the prediction page needs them. The larger model is under GitHub's 100 MB per-file limit; do not upload it or the ZIP through GitHub's browser file uploader.
3. Sign in at https://share.streamlit.io with GitHub. If the repository is private, authorize Community Cloud to access your private repositories, then choose **Create app**.
4. Select the repository, its active branch (often `main` or `master`), and entrypoint `src/dashboard/app.py`, then deploy. Streamlit installs dependencies from `requirements.txt` in its own environment.
5. In App settings → Sharing, set **Who can view this app** to public, then share the `*.streamlit.app` URL. Anyone with the URL can use it; no local Python setup is needed.
6. Optional moderation: configure a strong `moderator_password = "..."` value in App settings → Secrets. Without it, report verification controls stay locked. Never commit secrets to GitHub.

This is a student demo, not an operational flood-warning service. Public users can submit unverified community reports. The sample app stores reports/uploads locally; cloud restarts may clear them. Do not collect sensitive information or rely on this storage for a real service.

## Guide checklist

- Route indication → Safe Routes  
- Application instead of website → Streamlit app chrome, phone-friendly layout  
- IoT planning → labelled simulator  
- UI/UX → maps, charts, risk chips  
- Photo/video → Community Reports  
- Dummy data from IG / social → Social Videos + Facebook-style demo posts  

