from __future__ import annotations

import sys
import hmac
import os
from html import escape
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.community.store import add_report, list_reports, seed_synthetic_demo_posts, update_verification
from src.dashboard.maps import add_flood_grid, add_path, add_reports, add_roads, add_social_videos, base_map
from src.dashboard.theme import banner, header, inject_theme, risk_chip
from src.social.loader import load_social_reports
from src.data_store import (
    latest_grid_snapshot,
    load_config,
    load_flood_dataset,
    load_known_events,
    load_metrics,
    load_road_dataset,
)
from src.iot.simulator import load_forecast_with_fallback, simulate_iot_series
from src.model_training.predict import predict_from_manual
from src.paths import NAMED_PLACES
from src.routing.graph import apply_community_penalties, build_route_graph, nearest_node, shortest_path


def _plotly_layout(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#131D26",
        font=dict(family="Segoe UI, Arial, sans-serif", color="#E6EDF3"),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h"),
    )
    return fig


def page_home(flood, events, forecast, forecast_note):
    header(st, "Rainfall forecast when available, rule-based risk, curated events, and model-ready context.")
    snap = latest_grid_snapshot(flood)
    high_n = int((snap.flood_risk == "High").sum())
    med_n = int((snap.flood_risk == "Medium").sum())
    mean_rain = float(snap.precipitation_mm.mean())
    next3 = float(forecast.head(3)["precipitation_mm"].sum()) if len(forecast) else 0
    peak = forecast.loc[forecast["precipitation_mm"].idxmax()] if len(forecast) else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grid cells (latest historical day)", f"{len(snap)}", help="12 Open-Meteo sample points covering VVN.")
    c2.metric("Mean rainfall on that day", f"{mean_rain:.1f} mm")
    c3.metric("High / Medium cells", f"{high_n} / {med_n}")
    stale_forecast = "stale" in forecast_note.lower()
    c4.metric("Last 3 cached days rain" if stale_forecast else "Next 3-day forecast rain", f"{next3:.1f} mm")

    if stale_forecast:
        banner(st, "medium", f"<b>Current forecast unavailable.</b> {escape(forecast_note)}")
    elif peak is not None and peak["flood_risk_forecast"] == "High":
        banner(st, "high", f"<b>High-rainfall threshold reached (demo).</b> Forecast peak {peak['precipitation_mm']} mm on {peak['date']}. {escape(forecast_note)}")
    elif peak is not None and peak["flood_risk_forecast"] == "Medium":
        banner(st, "medium", f"<b>Rainfall threshold watch (demo).</b> Forecast peak {peak['precipitation_mm']} mm on {peak['date']}. {escape(forecast_note)}")
    else:
        banner(st, "low", f"<b>No high-rain forecast in the downloaded window.</b> {escape(forecast_note)}")

    st.markdown("**Data layers on this page are labelled.** Historical grid risk uses a rule-based formula, not surveyed flood extents.")
    left, right = st.columns((1.2, 1))
    with left:
        st.subheader("7-day rainfall history / forecast window")
        fig = px.bar(forecast, x="date", y="precipitation_mm", color="flood_risk_forecast",
                     color_discrete_map={"Low": "#1e8449", "Medium": "#d68910", "High": "#c0392b"})
        st.plotly_chart(_plotly_layout(fig), use_container_width=True)
    with right:
        st.subheader("Official / curated historical events")
        st.caption("Separated from user community reports and from synthetic demo posts.")
        st.dataframe(events, hide_index=True, use_container_width=True)

    st.subheader("Latest processed grid snapshot")
    show = snap[["latitude", "longitude", "precipitation_mm", "elevation_m", "drainage_dist_km",
                 "building_count", "flood_risk", "flood_risk_score"]].sort_values("flood_risk_score", ascending=False)
    st.dataframe(show, hide_index=True, use_container_width=True)


def page_flood_map(flood):
    header(st, "Interactive map of grid flood-risk scores. Sparse 12-point sample — not a hydraulic inundation map.")
    min_d = flood["date"].min().date()
    max_d = flood["date"].max().date()
    pick = st.date_input("Historical date (processed rainfall grid)", value=max_d, min_value=min_d, max_value=max_d)
    snap = flood[flood["date"].dt.date == pick]
    show_videos = st.checkbox("Show public YouTube/Instagram pins (unverified crowd signal)", value=True)
    m = add_flood_grid(base_map(), snap)
    if show_videos:
        add_social_videos(m, load_social_reports())
    st_folium(m, height=520, use_container_width=True, returned_objects=[])
    banner(st, "sim", "Labels are rule-based (60% rainfall, 25% elevation, 15% drainage distance). Heat is interpolated between 12 sample locations. Video pins are not official flood proof.")


def page_analytics(flood, events):
    header(st, "Rainfall trends, risk mix, and the 18 July 2021 curated event window.")
    daily = flood.groupby("date", as_index=False).agg(
        precipitation_mm=("precipitation_mm", "mean"),
        flood_risk_score=("flood_risk_score", "mean"),
    )
    fig = px.line(daily, x="date", y="precipitation_mm", title="Basin-mean daily rainfall (processed Open-Meteo grid)")
    for _, ev in events.iterrows():
        fig.add_vline(x=pd.Timestamp(ev["date"]), line_dash="dot", line_color="#c0392b")
    st.plotly_chart(_plotly_layout(fig), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        counts = flood["flood_risk"].value_counts().rename_axis("risk").reset_index(name="rows")
        fig2 = px.pie(counts, names="risk", values="rows", title="Rule-based label mix (all years)",
                      color="risk", color_discrete_map={"Low": "#1e8449", "Medium": "#d68910", "High": "#c0392b"})
        st.plotly_chart(_plotly_layout(fig2), use_container_width=True)
    with col2:
        flood = flood.copy()
        flood["month"] = flood["date"].dt.month
        mon = flood.groupby("month")["precipitation_mm"].mean().reset_index()
        fig3 = px.bar(mon, x="month", y="precipitation_mm", title="Mean rainfall by month")
        st.plotly_chart(_plotly_layout(fig3), use_container_width=True)

    st.markdown("High-risk rows are rare (~1.4% in the processed file). That is why model training reports Macro-F1 and High-risk recall instead of accuracy.")


def page_ml(flood):
    header(st, "Flood-risk model: genuine hold-out metrics, what-if inference, and proxy-label caveats.")
    metrics = load_metrics()
    if metrics is None:
        st.error("Models are not trained yet. From the project root run: `python src/model_training/train_flood_risk_model.py`")
        return
    st.warning(
        "Near-perfect temporal accuracy is **not** a claim of operational skill. "
        "The target labels are generated from rainfall, elevation and drainage — the same family of inputs. "
        "The spatial hold-out (~0.91 Macro-F1) is the more honest check. These scores were measured, not hardcoded."
    )

    st.subheader("Temporal split (train 2019–2022 / test 2023)")
    rows = []
    for name, m in metrics["temporal_split"]["models"].items():
        rows.append({
            "model": name,
            "accuracy": round(m["accuracy"], 3),
            "macro_f1": round(m["macro_f1"], 3),
            "high_risk_recall": round(m["high_risk_recall"], 3),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.write(f"Selected classifier: **{metrics['best_classifier']}** (Macro-F1 and High-risk recall, not accuracy).")
    st.write(f"Selected regressor: **{metrics['best_regressor']}** · temporal RMSE shown below.")
    st.json(metrics.get("regression_temporal", {}))

    st.subheader("Spatial split (held-out grid locations)")
    sm = metrics["spatial_split"]["metrics"]
    st.write(
        f"Macro-F1 {sm['macro_f1']:.3f} · High-risk recall {sm['high_risk_recall']:.3f} · "
        f"Accuracy {sm['accuracy']:.3f} (accuracy is not the headline metric)."
    )
    with st.expander("Classification report (spatial hold-out)"):
        st.text(sm.get("classification_report", ""))

    st.subheader("What-if prediction")
    c1, c2, c3, c4 = st.columns(4)
    rain = c1.slider("Precipitation (mm)", 0.0, 250.0, 45.0)
    elev = c2.slider("Elevation (m)", 0.0, 80.0, 8.0)
    drain = c3.slider("Distance to drainage (km)", 0.0, 5.0, 0.8)
    bld = c4.slider("Building count (proxy)", 0, 400, 80)
    monsoon = st.checkbox("Monsoon season flag", value=datetime.now().month in (6, 7, 8, 9))
    if st.button("Run model"):
        result = predict_from_manual(
            precipitation_mm=rain,
            elevation_m=elev,
            building_count=bld,
            drainage_dist_km=drain,
            is_monsoon=int(monsoon),
        )
        if "error" in result:
            st.error(result["error"])
        else:
            st.markdown(
                f"Predicted class {risk_chip(result['label'])} · vulnerability score "
                f"**{result['vulnerability_score']:.1f}** · model `{result['model_name']}`",
                unsafe_allow_html=True,
            )
            if result.get("probabilities"):
                st.write(result["probabilities"])


def page_roads(roads):
    header(st, "Road-segment infrastructure risk from elevation and drainage proximity (OSM-derived).")
    mix = roads["infra_risk"].value_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("Segments", f"{len(roads):,}")
    c2.metric("High infra-risk", int(mix.get("High", 0)))
    c3.metric("Medium infra-risk", int(mix.get("Medium", 0)))
    m = add_roads(base_map(12), roads)
    st_folium(m, height=540, use_container_width=True, returned_objects=[])
    st.caption("Sampled markers for speed. Scores are static infrastructure susceptibility, not live water depth.")


def page_routes(roads):
    header(st, "Risk-weighted Dijkstra on the road-midpoint graph, plus a geographic-distance alternative.")
    st.caption("Demo approximation: nearby road-segment midpoints are connected by straight-line links; this is not a verified street-by-street or turn-by-turn route. Check actual road conditions before travelling.")
    banner(
        st,
        "sim",
        "Unverified community reports never prove a road is flooded. Only <b>Verified</b> reports younger than 48 hours "
        "add a local penalty. Infrastructure risk still comes from the processed road table.",
    )
    places = list(NAMED_PLACES.keys())
    c1, c2 = st.columns(2)
    origin_name = c1.selectbox("Origin", places, index=0)
    dest_name = c2.selectbox("Destination", places, index=4)
    use_community = st.checkbox("Apply verified recent community penalties", value=True)
    if origin_name == dest_name:
        st.warning("Choose two different places.")
        return

    @st.cache_resource
    def _graph():
        return build_route_graph()

    G = _graph()
    reports = list_reports()
    if use_community:
        G_use = apply_community_penalties(G, reports)
    else:
        G_use = G
    o = NAMED_PLACES[origin_name]
    d = NAMED_PLACES[dest_name]
    s = nearest_node(G_use, o[0], o[1])
    e = nearest_node(G_use, d[0], d[1])
    try:
        risk_path = shortest_path(G_use, s, e, weight="risk_weight")
        geo_path = shortest_path(G_use, s, e, weight="dist_km")
    except Exception as exc:
        st.error(f"No path in the connected road graph: {exc}")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Risk-aware distance", f"{risk_path['distance_km']:.2f} km")
    m2.metric("Geographic-shortest distance", f"{geo_path['distance_km']:.2f} km")
    m3.metric("High-infra edges on risk path", int(risk_path["high_risk_edges"]))

    m = base_map(12)
    add_path(m, geo_path["coords"], "#7f8c8d", "Geographic shortest", weight=4)
    add_path(m, risk_path["coords"], "#0b6e6a", "Risk-weighted", weight=7)
    add_reports(m, [r for r in reports if r.get("latitude") is not None])
    st_folium(m, height=540, use_container_width=True, returned_objects=[])
    st.caption("Teal = risk-weighted route. Grey = shortest geographic distance on the same graph.")


def page_iot():
    header(st, "Canal-side telemetry placeholder until ESP32 + Firebase nodes are installed.")
    banner(st, "sim", "<b>SIMULATION</b> — water level, rain rate, soil moisture and temperature are generated from a time-seeded model. No hardware is connected.")
    hours = st.slider("Hours of simulated history", 12, 72, 48)
    df = simulate_iot_series(hours=hours)
    warn_cm, alert_cm = 80, 120
    latest = df.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Water level", f"{latest.water_level_cm:.0f} cm")
    c2.metric("Rain rate", f"{latest.rain_rate_mm_hr:.1f} mm/h")
    c3.metric("Soil moisture", f"{latest.soil_moisture_pct:.0f} %")
    c4.metric("Temperature", f"{latest.temperature_c:.1f} °C")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.water_level_cm, name="Water level (cm)", line=dict(color="#1c4e7a", width=2)))
    fig.add_hline(y=warn_cm, line_dash="dash", line_color="#d68910", annotation_text="Warning 80 cm")
    fig.add_hline(y=alert_cm, line_dash="dash", line_color="#c0392b", annotation_text="Alert 120 cm")
    st.plotly_chart(_plotly_layout(fig), use_container_width=True)
    fig2 = px.line(df, x="timestamp", y=["rain_rate_mm_hr", "soil_moisture_pct"], title="Rain rate and soil moisture (simulated)")
    st.plotly_chart(_plotly_layout(fig2), use_container_width=True)
    st.dataframe(df.tail(12), hide_index=True, use_container_width=True)


def page_social():
    header(st, "Public YouTube Shorts and manually catalogued Instagram posts. Separate from official alerts and citizen uploads.")
    banner(
        st,
        "sim",
        "These clips are <b>crowd / news media</b>, not sensor readings. Location and severity were inferred from titles "
        "and then jittered so pins are not stacked on one dummy coordinate. An unverified video does not prove a road is flooded.",
    )
    reports = load_social_reports()
    if not reports:
        st.error("Social report JSON is missing. Run `python src/social/enrich_reports.py` from the project folder.")
        return

    df = pd.DataFrame(reports)
    c1, c2, c3, c4 = st.columns(4)
    only_relevant = c1.checkbox("VVN-relevant only", value=True)
    plat = c2.multiselect("Platform", sorted(df["platform"].dropna().unique()), default=list(df["platform"].dropna().unique()))
    sev = c3.multiselect("Severity", ["low", "medium", "high"], default=["low", "medium", "high"])
    loc_options = ["All"] + sorted(df["location"].dropna().unique().tolist())
    loc = c4.selectbox("Locality", loc_options)

    view = df.copy()
    if only_relevant and "relevant" in view.columns:
        view = view[view["relevant"] != False]
    view = view[view["platform"].isin(plat) & view["severity"].isin(sev)]
    if loc != "All":
        view = view[view["location"] == loc]

    k1, k2, k3 = st.columns(3)
    k1.metric("Videos shown", len(view))
    k2.metric("YouTube", int((view["platform"] == "youtube").sum()))
    k3.metric("Instagram (manual catalog)", int((view["platform"] == "instagram").sum()))

    m = add_social_videos(base_map(12), view.to_dict("records"))
    st_folium(m, height=460, use_container_width=True, returned_objects=[])

    st.subheader("Watch a clip")
    if view.empty:
        st.info("No videos match these filters.")
        return
    labels = [f"{r['location']} · {r['severity']} · {str(r.get('title') or '')[:70]}" for _, r in view.iterrows()]
    choice = st.selectbox("Pick a video", range(len(labels)), format_func=lambda i: labels[i])
    row = view.iloc[int(choice)]
    st.write(str(row["title"]))
    st.caption(
        f"{escape(str(row['platform']))} · {escape(str(row['location']))} · severity {escape(str(row['severity']))} · "
        f"{escape(str(row.get('published_at') or '')[:10])} · {escape(str(row.get('geo_note', '')))}"
    )
    import streamlit.components.v1 as components

    embed = str(row.get("embed_url") or "")
    if row["platform"] == "youtube" and embed:
        components.iframe(embed, height=420)
    elif row["platform"] == "instagram" and embed:
        components.iframe(embed, height=640)
    else:
        st.info("Instagram has no public search API. This row is a manual hashtag catalog card (no embed).")
    if row.get("source_url"):
        st.link_button("Open original / hashtag page", row["source_url"])


def page_community():
    header(st, "Citizen photo/video reports. Kept separate from official alerts and from synthetic demo posts.")
    st.caption("Do not submit private or sensitive information. Reports are unverified by default; hosted demo storage may reset.")
    seed_synthetic_demo_posts()
    banner(
        st,
        "medium",
        "An <b>unverified</b> report is a crowd signal only. It does not prove a road is flooded and is not used as a hard barrier in routing.",
    )
    with st.form("report_form", clear_on_submit=True):
        caption = st.text_area("Caption")
        place = st.selectbox("Optional named location", ["(none)"] + list(NAMED_PLACES.keys()))
        custom = st.text_input("Or location label (optional)")
        col_a, col_b = st.columns(2)
        lat = col_a.number_input("Latitude (optional, 0 = skip)", value=0.0, format="%.6f")
        lon = col_b.number_input("Longitude (optional, 0 = skip)", value=0.0, format="%.6f")
        media = st.file_uploader("Photo or video", type=["jpg", "jpeg", "png", "webp", "gif", "mp4", "mov", "webm"])
        submitted = st.form_submit_button("Submit report")
        if submitted:
            if not caption.strip():
                st.error("Caption is required.")
            elif bool(lat) != bool(lon):
                st.error("Enter both latitude and longitude, or leave both as 0.")
            elif lat and not (-90 <= lat <= 90 and -180 <= lon <= 180):
                st.error("Coordinates must be valid latitude (−90 to 90) and longitude (−180 to 180).")
            else:
                chosen_lat = lat if lat else None
                chosen_lon = lon if lon else None
                label = None if place == "(none)" else place
                if label and (not chosen_lat):
                    chosen_lat, chosen_lon = NAMED_PLACES[label]
                if custom:
                    label = custom
                add_report(
                    caption=caption,
                    latitude=chosen_lat,
                    longitude=chosen_lon,
                    location_label=label,
                    media_bytes=media.getvalue() if media else None,
                    filename=media.name if media else None,
                    source_layer="user_report",
                    verification_status="Unverified",
                )
                st.success("Saved as an unverified user report.")

    reports = list_reports()
    user_n = sum(1 for r in reports if r["source_layer"] == "user_report")
    syn_n = sum(1 for r in reports if r["source_layer"] == "synthetic_demo")
    st.write(f"User reports: **{user_n}** · Synthetic demo posts: **{syn_n}** · Official events live on Home, not here.")

    m = add_reports(base_map(12), reports)
    st_folium(m, height=420, use_container_width=True, returned_objects=[])
    show_moderation = False
    if show_moderation:
        st.subheader("Moderation (demonstration)")
        try:
            moderator_password = st.secrets.get("moderator_password", os.environ.get("AQUASHIELD_MODERATOR_PASSWORD", ""))
        except Exception:
            moderator_password = os.environ.get("AQUASHIELD_MODERATOR_PASSWORD", "")
        can_moderate = False
        if moderator_password:
            entered_password = st.text_input("Moderator password", type="password", key="moderator_password")
            can_moderate = hmac.compare_digest(entered_password, str(moderator_password)) if entered_password else False
            if not can_moderate:
                st.caption("Verification controls unlock only with the moderator password.")
        else:
            st.info("Moderation controls are locked. Set `moderator_password` in Streamlit Cloud → App settings → Secrets to enable them.")
        for rep in reports:
            cols = st.columns((3, 1, 1, 1)) if can_moderate else [st.container()]
            cols[0].write(rep["caption"])
            layer_cls = "chip-user" if rep["source_layer"] == "user_report" else "chip-synthetic"
            status_cls = "chip-verified" if rep["verification_status"] == "Verified" else "chip-unverified"
            cols[0].markdown(
                f"<span class='as-chip {layer_cls}'>{escape(str(rep['source_layer']))}</span>"
                f"<span class='as-chip {status_cls}'>{escape(str(rep['verification_status']))}</span><br>"
                f"<span class='as-footnote'>{escape(str(rep['created_at'])[:19])} UTC"
                f"{' · ' + escape(str(rep['location_label'])) if rep.get('location_label') else ''}</span>",
                unsafe_allow_html=True,
            )
            if rep.get("media_path") and rep.get("media_kind") == "image":
                cols[0].image(rep["media_path"], width=280)
            elif rep.get("media_kind") == "video" and rep.get("media_path"):
                cols[0].video(rep["media_path"])
            if can_moderate:
                if cols[1].button("Verify", key=f"v{rep['id']}"):
                    update_verification(rep["id"], "Verified")
                    st.rerun()
                if cols[2].button("Reject", key=f"r{rep['id']}"):
                    update_verification(rep["id"], "Rejected")
                    st.rerun()
                if cols[3].button("Unverify", key=f"u{rep['id']}"):
                    update_verification(rep["id"], "Unverified")
                    st.rerun()


def main():
    st.set_page_config(
    page_title="AquaShield",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)
    inject_theme(st)
    st.markdown(
        '<div class="as-appbar"><span class="as-app-badge">AquaShield application</span>'
        "<span class='as-footnote'>Vasai–Virar–Nalasopara flood intelligence</span></div>",
        unsafe_allow_html=True,
    )
    config = load_config()

    @st.cache_data(ttl=600)
    def _forecast(low, medium):
        return load_forecast_with_fallback({"low": low, "medium": medium, "high": medium})

    flood = load_flood_dataset()
    roads = load_road_dataset()
    events = load_known_events()
    th = config["flood_risk_thresholds"]
    forecast, forecast_note = _forecast(th["low"], th["medium"])

    st.sidebar.markdown("### AquaShield")
    st.sidebar.caption("VVN flood intelligence")
    page = st.sidebar.radio(
        "Navigate",
        [
            "Home Dashboard",
            "Flood Risk Map",
            "Analytics",
            "ML Model",
            "Road Risk Map",
            "Safe Routes",
            "IoT Sensor Monitoring",
            "Community Reports",
            "Social Videos (YT / IG)",
        ],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Observations, synthetic IoT, demo posts, and user uploads are stored in separate layers.")

    if page == "Home Dashboard":
        page_home(flood, events, forecast, forecast_note)
    elif page == "Flood Risk Map":
        page_flood_map(flood)
    elif page == "Analytics":
        page_analytics(flood, events)
    elif page == "ML Model":
        page_ml(flood)
    elif page == "Road Risk Map":
        page_roads(roads)
    elif page == "Safe Routes":
        page_routes(roads)
    elif page == "IoT Sensor Monitoring":
        page_iot()
    elif page == "Community Reports":
        page_community()
    else:
        page_social()


if __name__ == "__main__":
    main()
