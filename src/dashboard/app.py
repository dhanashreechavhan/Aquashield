import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import os

# ─── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="AquaShield — VVN Flood Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a6eb5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #888;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f0f4f9;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        border-left: 4px solid #1a6eb5;
    }
    .risk-high   { color: #c0392b; font-weight: 700; }
    .risk-medium { color: #e67e22; font-weight: 700; }
    .risk-low    { color: #27ae60; font-weight: 700; }
    div[data-testid="stSidebar"] { background-color: #0d1b2a; }
    div[data-testid="stSidebar"] * { color: #e0e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Data loading ────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "..", "..", "data", "processed")

@st.cache_data
def load_flood():
    path = os.path.join(DATA_DIR, "flood_risk_dataset.csv")
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["year"]  = df["date"].dt.year
        df["month"] = df["date"].dt.month
    return df

@st.cache_data
def load_roads():
    path = os.path.join(DATA_DIR, "road_risk_dataset.csv")
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

# Detect risk column name (handles slight naming differences)
def get_risk_col(df):
    for column in ["flood_risk", "infra_risk"]:
        if column in df.columns:
            return column

    for column in df.columns:
        if "risk" in column and "score" not in column:
            return column

    return None

def get_score_col(df):
    for c in df.columns:
        if "score" in c:
            return c
    return None

try:
    flood_df = load_flood()
    roads_df = load_roads()
    data_ok = True
except Exception as e:
    data_ok = False
    err_msg = str(e)

# ─── Sidebar nav ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌊 AquaShield")
    st.markdown("**Urban Flood Intelligence**")
    st.markdown("*Vasai-Virar-Nalasopara*")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🏠 Home", "🗺️ Flood Risk Map", "📊 Analytics", "🛣️ Road Risk Map",
         "🛡️ Safe Routes", "📡 IoT Sensor"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("**Team AquaShield**")
    st.caption("Harshita • Mufis • Vidhan • Dhana")

if not data_ok:
    st.error(f"❌ Data load karne mein error: {err_msg}")
    st.info("Check karo ki `data/processed/` folder mein dono CSV files hain.")
    st.stop()

# ════════════════════════════════════════════════════════════════
# PAGE 1 — HOME
# ════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    st.markdown('<p class="main-header">🌊 AquaShield</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Urban Flood Intelligence System — Vasai-Virar-Nalasopara, Maharashtra</p>',
                unsafe_allow_html=True)

    risk_col = get_risk_col(flood_df)
    score_col = get_score_col(flood_df)

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    total = len(flood_df)
    if risk_col:
        high   = (flood_df[risk_col].str.lower() == "high").sum()
        medium = (flood_df[risk_col].str.lower() == "medium").sum()
        low    = (flood_df[risk_col].str.lower() == "low").sum()
    else:
        high = medium = low = 0

    c1.metric("📍 Total records", f"{total:,}", "12 locations × 5 yrs")
    c2.metric("🔴 High-risk days", f"{high:,}", f"{high/total*100:.1f}% of total", delta_color="inverse")
    c3.metric("🟡 Medium-risk days", f"{medium:,}", f"{medium/total*100:.1f}%")
    c4.metric("🟢 Low-risk days", f"{low:,}", f"{low/total*100:.1f}%")

    st.markdown("---")

    col_a, col_b = st.columns([1.2, 1])

    with col_a:
        st.subheader("📅 Risk distribution over time")
        if risk_col and "year" in flood_df.columns:
            yearly = flood_df.groupby(["year", risk_col]).size().reset_index(name="count")
            fig = px.bar(yearly, x="year", y="count", color=risk_col,
                         color_discrete_map={"Low": "#27ae60", "Medium": "#e67e22", "High": "#c0392b"},
                         barmode="stack", height=320)
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), legend_title="Risk level")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Date/risk column nahi mila CSV mein.")

    with col_b:
        st.subheader("⚠️ About VVN")
        st.info("""
**Vasai-Virar-Nalasopara** is one of the most flood-prone
urban regions near Mumbai.

- Area: ~310–380 sq. km
- Floods almost every monsoon
- Verified flood event: **18 July 2021**
- Low elevation + blocked drainage + rapid construction
        """)
        st.subheader("📋 Project phases")
        st.success("✅ Phase 0-1-2: Data collection & preprocessing")
        st.warning("🔄 Phase 3: ML model training (Mufis)")
        st.warning("🔄 Phase 4: Route engine (Vidhan)")
        st.info("🚧 Phase 5: Dashboard (Dhana — this!)")
        st.info("⏳ Phase 6: IoT sensor integration")

    st.markdown("---")
    st.subheader("🗂️ Raw data preview")
    tab1, tab2 = st.tabs(["Flood risk dataset", "Road risk dataset"])
    with tab1:
        st.dataframe(flood_df.head(20), use_container_width=True)
        st.caption(f"Total rows: {len(flood_df):,} | Columns: {list(flood_df.columns)}")
    with tab2:
        st.dataframe(roads_df.head(20), use_container_width=True)
        st.caption(f"Total rows: {len(roads_df):,} | Columns: {list(roads_df.columns)}")


# ════════════════════════════════════════════════════════════════
# PAGE 2 — FLOOD RISK MAP
# ════════════════════════════════════════════════════════════════
elif page == "🗺️ Flood Risk Map":
    st.markdown('<p class="main-header">🗺️ Flood Risk Map</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Location-wise flood risk across Vasai-Virar-Nalasopara</p>',
                unsafe_allow_html=True)

    risk_col  = get_risk_col(flood_df)
    score_col = get_score_col(flood_df)

    # Find lat/lon columns
    lat_col = next((c for c in flood_df.columns if "lat" in c), None)
    lon_col = next((c for c in flood_df.columns if "lon" in c or "lng" in c), None)

    col_filter, col_info = st.columns([1, 3])
    with col_filter:
        if "year" in flood_df.columns:
            years = sorted(flood_df["year"].dropna().unique().astype(int).tolist())
            sel_year = st.selectbox("Select year", years, index=len(years)-1)
            filtered = flood_df[flood_df["year"] == sel_year]
        else:
            filtered = flood_df
            st.info("No date column found.")

        if risk_col:
            levels = ["All"] + sorted(flood_df[risk_col].dropna().unique().tolist())
            sel_risk = st.selectbox("Filter by risk", levels)
            if sel_risk != "All":
                filtered = filtered[filtered[risk_col].str.lower() == sel_risk.lower()]

        st.metric("Showing records", f"{len(filtered):,}")

    with col_info:
        st.markdown("""
        **Color coding:**
        🟢 **Green** = Low risk &nbsp;&nbsp; 🟡 **Orange** = Medium risk &nbsp;&nbsp; 🔴 **Red** = High risk

        Each dot = one monitoring location on one day. Click any dot for details.
        """)

    # Map
    if lat_col and lon_col:
        map_data = filtered[[lat_col, lon_col, risk_col, score_col]].dropna().copy() if (risk_col and score_col) else filtered[[lat_col, lon_col]].dropna().copy()

        # Sample for performance (max 2000 points)
        if len(map_data) > 2000:
            map_data = map_data.sample(2000, random_state=42)

        m = folium.Map(location=[19.45, 72.82], zoom_start=12,
                       tiles="CartoDB positron")

        color_map = {"low": "green", "medium": "orange", "high": "red"}

        for _, row in map_data.iterrows():
            try:
                risk_val = str(row[risk_col]).lower() if risk_col else "low"
                color    = color_map.get(risk_val, "blue")
                score_val = f"Score: {row[score_col]:.1f}" if score_col and pd.notna(row[score_col]) else ""
                folium.CircleMarker(
                    location=[row[lat_col], row[lon_col]],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    popup=folium.Popup(
                        f"<b>Risk: {risk_val.title()}</b><br>{score_val}<br>"
                        f"Lat: {row[lat_col]:.4f}, Lon: {row[lon_col]:.4f}",
                        max_width=200
                    )
                ).add_to(m)
            except Exception:
                continue

        st_folium(m, width=None, height=520, returned_objects=[])
    else:
        st.warning("CSV mein latitude/longitude columns nahi mile. Column names check karo.")
        st.write("Available columns:", list(flood_df.columns))


# ════════════════════════════════════════════════════════════════
# PAGE 3 — ANALYTICS
# ════════════════════════════════════════════════════════════════
elif page == "📊 Analytics":
    st.markdown('<p class="main-header">📊 Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Historical flood data analysis — VVN 2019–2023</p>',
                unsafe_allow_html=True)

    risk_col  = get_risk_col(flood_df)
    score_col = get_score_col(flood_df)

    # KPI row
    c1, c2, c3 = st.columns(3)
    c1.metric("Total data points", f"{len(flood_df):,}", "12 locations × 5 years daily")
    if risk_col:
        high = (flood_df[risk_col].str.lower() == "high").sum()
        c2.metric("High-risk records", f"{high:,}", f"{high/len(flood_df)*100:.1f}% of all data",
                  delta_color="inverse")
    road_risk_col = get_risk_col(roads_df)
    if road_risk_col:
        road_high = (roads_df[road_risk_col].str.lower() == "high").sum()
        c3.metric("High-risk roads", f"{road_high:,}",
                  f"{road_high/len(roads_df)*100:.0f}% of {len(roads_df):,} roads",
                  delta_color="inverse")

    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Monthly rainfall", "🎯 Risk distribution",
                                       "📈 Year trend", "🏘️ Area hotspots"])

    # Tab 1: Monthly rainfall
    with tab1:
        rain_col = next((c for c in flood_df.columns if "rain" in c), None)
        if rain_col and "month" in flood_df.columns:
            monthly = flood_df.groupby("month")[rain_col].mean().reset_index()
            month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                           7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
            monthly["month_name"] = monthly["month"].map(month_names)
            monthly["is_monsoon"] = monthly["month"].isin([6,7,8,9])
            fig = px.bar(monthly, x="month_name", y=rain_col,
                         color="is_monsoon",
                         color_discrete_map={True: "#1a6eb5", False: "#b0c4de"},
                         labels={rain_col: "Avg rainfall (mm)", "month_name": "Month"},
                         title="Average monthly rainfall — VVN (2019–2023)",
                         height=380)
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Blue bars = monsoon months (Jun–Sep). July is consistently the highest-risk month.")
        else:
            st.info("Rainfall ya month column nahi mila CSV mein.")

    # Tab 2: Risk distribution
    with tab2:
        if risk_col:
            col_pie, col_bar = st.columns(2)
            with col_pie:
                counts = flood_df[risk_col].value_counts().reset_index()
                counts.columns = ["Risk level", "Count"]
                fig = px.pie(counts, names="Risk level", values="Count",
                             color="Risk level",
                             color_discrete_map={"Low":"#27ae60","Medium":"#e67e22","High":"#c0392b"},
                             title="Flood risk zone distribution",
                             hole=0.4, height=340)
                fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig, use_container_width=True)
            with col_bar:
                if road_risk_col:
                    road_counts = roads_df[road_risk_col].value_counts().reset_index()
                    road_counts.columns = ["Risk level", "Count"]
                    fig2 = px.bar(road_counts, x="Risk level", y="Count",
                                  color="Risk level",
                                  color_discrete_map={"Low":"#27ae60","Medium":"#e67e22","High":"#c0392b"},
                                  title="Road infrastructure risk",
                                  height=340)
                    fig2.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Risk label column nahi mila.")

    # Tab 3: Year trend
    with tab3:
        if risk_col and "year" in flood_df.columns:
            trend = flood_df[flood_df[risk_col].str.lower() == "high"].groupby("year").size().reset_index(name="high_risk_days")
            fig = px.line(trend, x="year", y="high_risk_days",
                          markers=True,
                          labels={"high_risk_days": "High-risk day count", "year": "Year"},
                          title="High-risk days per year (2019–2023)",
                          height=360)
            fig.add_vline(x=2021, line_dash="dash", line_color="red",
                          annotation_text="18 Jul 2021 flood", annotation_position="top right")
            fig.update_traces(line_color="#1a6eb5", marker_size=10)
            fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("2021 ka spike real flood event ke saath match karta hai — model validation!")
        else:
            st.info("Year ya risk column nahi mila.")

    # Tab 4: Area hotspots
    with tab4:
        lat_col = next((c for c in flood_df.columns if "lat" in c), None)
        lon_col = next((c for c in flood_df.columns if "lon" in c or "lng" in c), None)
        if score_col and lat_col and lon_col:
            hotspots = (flood_df.groupby([lat_col, lon_col])[score_col]
                        .mean()
                        .reset_index()
                        .sort_values(score_col, ascending=False)
                        .head(12))
            hotspots.columns = ["Latitude", "Longitude", "Avg risk score"]
            hotspots["Avg risk score"] = hotspots["Avg risk score"].round(1)
            hotspots["Risk level"] = hotspots["Avg risk score"].apply(
                lambda x: "🔴 High" if x >= 60 else ("🟡 Medium" if x >= 30 else "🟢 Low"))
            hotspots.insert(0, "Rank", range(1, len(hotspots)+1))
            st.dataframe(hotspots, use_container_width=True, hide_index=True)
            st.caption("Locations ranked by average flood risk score (0–100). Higher = more dangerous.")
        else:
            st.info("Score ya lat/lon columns nahi mile.")


# ════════════════════════════════════════════════════════════════
# PAGE 4 — ROAD RISK MAP
# ════════════════════════════════════════════════════════════════
elif page == "🛣️ Road Risk Map":
    st.markdown('<p class="main-header">🛣️ Road Risk Map</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Infrastructure risk — which roads flood first</p>',
                unsafe_allow_html=True)

    road_risk_col = get_risk_col(roads_df)
    lat_col = next((c for c in roads_df.columns if "lat" in c), None)
    lon_col = next((c for c in roads_df.columns if "lon" in c or "lng" in c), None)

    col_f, col_i = st.columns([1, 3])
    with col_f:
        if road_risk_col:
            levels = ["All"] + sorted(roads_df[road_risk_col].dropna().unique().tolist())
            sel = st.selectbox("Filter roads by risk", levels)
            road_filtered = roads_df if sel == "All" else roads_df[roads_df[road_risk_col].str.lower() == sel.lower()]
        else:
            road_filtered = roads_df
        st.metric("Roads shown", f"{len(road_filtered):,}")

    with col_i:
        st.markdown("🟢 Low-risk roads = safe to use &nbsp;&nbsp; 🟡 Medium = caution &nbsp;&nbsp; 🔴 High = avoid during floods")

    if lat_col and lon_col:
        sample = road_filtered.sample(min(2000, len(road_filtered)), random_state=42)
        m = folium.Map(location=[19.45, 72.82], zoom_start=12, tiles="CartoDB positron")
        color_map = {"low": "green", "medium": "orange", "high": "red"}
        for _, row in sample.iterrows():
            try:
                risk_val = str(row[road_risk_col]).lower() if road_risk_col else "low"
                color    = color_map.get(risk_val, "blue")
                folium.CircleMarker(
                    location=[row[lat_col], row[lon_col]],
                    radius=4,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.6,
                    popup=f"Road risk: {risk_val.title()}"
                ).add_to(m)
            except Exception:
                continue
        st_folium(m, width=None, height=500, returned_objects=[])
    else:
        st.warning("Latitude/longitude columns roads dataset mein nahi mile.")
        st.write("Available columns:", list(roads_df.columns))


# ════════════════════════════════════════════════════════════════
# PAGE 5 — SAFE ROUTES (Placeholder)
# ════════════════════════════════════════════════════════════════
elif page == "🛡️ Safe Routes":
    st.markdown('<p class="main-header">🛡️ Safe Route Finder</p>', unsafe_allow_html=True)
    st.info("🔄 **Coming soon** — Vidhan ka routing engine integrate karna hai (Phase 4). "
            "NetworkX + Dijkstra/A* algorithm use hoga jo high-risk roads avoid karega.")
    st.markdown("""
    **Yeh feature kya karega:**
    - User start point aur end point enter karega
    - System automatically safest route calculate karega
    - Flooded / high-risk roads automatically avoid honge
    - Map pe blue line mein safe route dikhega
    """)
    m = folium.Map(location=[19.45, 72.82], zoom_start=12, tiles="CartoDB positron")
    folium.Marker([19.45, 72.82], popup="Start point (example)", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([19.50, 72.85], popup="End point (example)",   icon=folium.Icon(color="red")).add_to(m)
    st_folium(m, width=None, height=400, returned_objects=[])


# ════════════════════════════════════════════════════════════════
# PAGE 6 — IoT SENSOR (Placeholder)
# ════════════════════════════════════════════════════════════════
elif page == "📡 IoT Sensor":
    st.markdown('<p class="main-header">📡 Live IoT Sensor</p>', unsafe_allow_html=True)
    st.info("🔄 **Coming soon** — ESP32/Arduino sensor + Firebase integration (Phase 6).")
    c1, c2, c3 = st.columns(3)
    c1.metric("Water level (demo)", "42 cm", "+3 cm", delta_color="inverse")
    c2.metric("Buzzer status (demo)", "SAFE", "Below threshold")
    c3.metric("Last updated (demo)", "2:30 PM", "Live feed paused")
    st.markdown("""
    **Yeh feature kya karega:**
    - ESP32 sensor se real-time water level data aayega
    - Firebase se live data dashboard mein stream hoga
    - Threshold cross hone pe buzzer + dashboard alert
    - Last 1 ghante ka water level graph
    """)
    import plotly.graph_objects as go
    import random
    demo_y = [30, 32, 35, 38, 40, 42, 41, 43, 42, 40, 39, 38]
    demo_x = list(range(len(demo_y)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=demo_x, y=demo_y, mode="lines+markers",
                             line=dict(color="#1a6eb5", width=2),
                             name="Water level (cm)"))
    fig.add_hline(y=50, line_dash="dash", line_color="red",
                  annotation_text="Alert threshold (50 cm)")
    fig.update_layout(title="Demo: water level over time",
                      xaxis_title="Time (minutes ago)",
                      yaxis_title="Water level (cm)",
                      height=320, margin=dict(l=0,r=0,t=40,b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Above is demo data. Real sensor data will appear here after Phase 6 integration.")

