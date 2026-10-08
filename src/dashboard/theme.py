BRAND_CSS = """
<style>
html, body, [class*="css"] {
  font-family: "Segoe UI", Arial, sans-serif;
}
.block-container { padding-top: 1.2rem; max-width: 1280px; }

.as-header {
  background: linear-gradient(120deg, #102B33 0%, #123F46 55%, #1B3552 100%);
  color: #F0FDFA;
  padding: 1.15rem 1.4rem 1.05rem 1.4rem;
  border-radius: 14px;
  margin-bottom: 1rem;
  border: 1px solid #24535A;
}
.as-header h1 {
  font-family: Georgia, serif;
  font-size: 1.75rem;
  margin: 0 0 0.2rem 0;
  letter-spacing: 0.01em;
}
.as-header p { margin: 0; opacity: 0.92; font-size: 0.95rem; }
.as-kicker {
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.8;
  margin-bottom: 0.25rem;
}

.as-banner {
  padding: 0.85rem 1rem;
  border-radius: 10px;
  margin: 0.4rem 0 1rem 0;
  border-left: 6px solid;
}
.as-banner.high { background: #351D22; border-color: #F87171; color: #FECACA; }
.as-banner.medium { background: #352B18; border-color: #FBBF24; color: #FDE68A; }
.as-banner.low { background: #173126; border-color: #34D399; color: #A7F3D0; }
.as-banner.sim { background: #1B293B; border-color: #60A5FA; color: #BFDBFE; }

.as-chip {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-right: 0.35rem;
}
.chip-low { background: #17432F; color: #A7F3D0; }
.chip-medium { background: #493719; color: #FDE68A; }
.chip-high { background: #4A2428; color: #FECACA; }
.chip-unverified { background: #493719; color: #FDE68A; }
.chip-verified { background: #17432F; color: #A7F3D0; }
.chip-synthetic { background: #193B52; color: #BAE6FD; }
.chip-user { background: #3C2850; color: #E9D5FF; }
.chip-official { background: #4A2428; color: #FECACA; }

div[data-testid="stMetric"] {
  background: #131D26;
  border: 1px solid #293945;
  padding: 0.6rem 0.8rem;
  border-radius: 12px;
}
section[data-testid="stSidebar"] {
  background: #101922;
}
.as-footnote { font-size: 0.82rem; color: #A8BAC6; }

.as-appbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 0.6rem;
}
.as-app-badge {
  background: #153A3E;
  color: #CCFBF1;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 0.28rem 0.6rem;
  border-radius: 999px;
}

@media (max-width: 900px) {
  .block-container { padding: 0.6rem 0.7rem 2rem 0.7rem; }
  .as-header h1 { font-size: 1.35rem; }
  .as-header { padding: 0.9rem 1rem; }
}


footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
"""


def inject_theme(st):
    st.markdown(BRAND_CSS, unsafe_allow_html=True)


def header(st, subtitle: str):
    st.markdown(
        f"""
        <div class="as-header">
          <div class="as-kicker">AquaShield · Vasai–Virar–Nalasopara</div>
          <h1>Urban flood intelligence</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_chip(label: str) -> str:
    key = (label or "Low").lower()
    cls = "chip-low" if key == "low" else "chip-medium" if key == "medium" else "chip-high"
    return f'<span class="as-chip {cls}">{label}</span>'


def banner(st, level: str, html: str):
    st.markdown(f'<div class="as-banner {level}">{html}</div>', unsafe_allow_html=True)
