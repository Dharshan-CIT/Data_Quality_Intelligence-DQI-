"""Central design system for the DQI Streamlit UI.

Light by default, with a sidebar toggle that flips a `dark_mode` flag in
session_state and re-injects CSS for the dark palette. Colors are taken from
the validated reference palette (categorical / status / chart-chrome roles)
so every chart and badge in the app draws from the same, colorblind-safe set.
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Palette (validated reference instance — see docs/METHODOLOGY.md for source)
# ---------------------------------------------------------------------------
LIGHT = {
    "page": "#f9f9f7",
    "surface": "#ffffff",
    "surface_raised": "#fcfcfb",
    "sidebar": "#f4f5f7",
    "text": "#0b0b0b",
    "text_secondary": "#52514e",
    "muted": "#898781",
    "gridline": "#e1e0d9",
    "baseline": "#c3c2b7",
    "border": "rgba(11,11,11,0.10)",
}
DARK = {
    "page": "#0d0d0d",
    "surface": "#17171a",
    "surface_raised": "#1a1a19",
    "sidebar": "#141416",
    "text": "#ffffff",
    "text_secondary": "#c3c2b7",
    "muted": "#898781",
    "gridline": "#2c2c2a",
    "baseline": "#383835",
    "border": "rgba(255,255,255,0.10)",
}

CATEGORICAL = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    "dark":  ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
}
STATUS = {
    "good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b",
}
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]
PRIMARY = "#2a78d6"

_BAND_TO_STATUS = {
    "Excellent": "good", "Good": "good", "Needs Attention": "warning",
    "Poor": "serious", "Critical": "critical",
}


def _tokens() -> dict:
    return DARK if st.session_state.get("dark_mode") else LIGHT


def _cat() -> list:
    return CATEGORICAL["dark"] if st.session_state.get("dark_mode") else CATEGORICAL["light"]


def init_theme():
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False


def inject_css():
    t = _tokens()
    st.markdown(f"""
<style>
:root {{
  --dqi-page: {t['page']};
  --dqi-surface: {t['surface']};
  --dqi-surface-raised: {t['surface_raised']};
  --dqi-text: {t['text']};
  --dqi-text-secondary: {t['text_secondary']};
  --dqi-muted: {t['muted']};
  --dqi-gridline: {t['gridline']};
  --dqi-border: {t['border']};
  --dqi-primary: {PRIMARY};
}}

html, body, [data-testid="stAppViewContainer"], .stApp {{
  background-color: var(--dqi-page) !important;
  color: var(--dqi-text) !important;
  font-family: -apple-system, system-ui, "Segoe UI", sans-serif !important;
}}
[data-testid="stHeader"] {{
  background-color: var(--dqi-page) !important;
}}
section[data-testid="stSidebar"] {{
  background-color: {t['sidebar']} !important;
  border-right: 1px solid var(--dqi-border);
}}
section[data-testid="stSidebar"] * {{
  color: var(--dqi-text) !important;
}}
[data-testid="stSidebarNav"] a {{
  border-radius: 8px;
  margin: 1px 8px;
}}
[data-testid="stSidebarNav"] a:hover {{
  background-color: var(--dqi-border);
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
  background-color: var(--dqi-primary) !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{
  color: #ffffff !important;
}}

h1, h2, h3, h4, h5, p, span, label, div, li {{
  color: var(--dqi-text);
}}
.stMarkdown, .stCaption, [data-testid="stCaptionContainer"] {{
  color: var(--dqi-text-secondary) !important;
}}

/* Cards / bordered containers */
[data-testid="stVerticalBlockBorderWrapper"] {{
  background-color: var(--dqi-surface);
  border: 1px solid var(--dqi-border) !important;
  border-radius: 12px !important;
}}

/* Native st.metric */
[data-testid="stMetric"] {{
  background-color: var(--dqi-surface);
  border: 1px solid var(--dqi-border);
  border-radius: 12px;
  padding: 14px 16px;
}}
[data-testid="stMetricLabel"] {{ color: var(--dqi-text-secondary) !important; }}
[data-testid="stMetricValue"] {{ color: var(--dqi-text) !important; }}

/* DataFrame / table */
[data-testid="stDataFrame"] {{
  border: 1px solid var(--dqi-border);
  border-radius: 10px;
  overflow: hidden;
}}

/* Buttons */
.stButton>button, .stDownloadButton>button {{
  border-radius: 8px;
  border: 1px solid var(--dqi-border);
  font-weight: 600;
}}
.stButton>button[kind="primary"] {{
  background-color: var(--dqi-primary);
  border-color: var(--dqi-primary);
}}

/* Tabs */
[data-baseweb="tab-list"] {{
  gap: 4px;
  border-bottom: 1px solid var(--dqi-border);
}}
[data-baseweb="tab"] {{
  border-radius: 8px 8px 0 0;
}}

/* Expander */
[data-testid="stExpander"] {{
  background-color: var(--dqi-surface);
  border: 1px solid var(--dqi-border) !important;
  border-radius: 10px !important;
}}

/* Inputs */
[data-baseweb="input"], [data-baseweb="select"]>div, [data-baseweb="base-input"] {{
  background-color: var(--dqi-surface) !important;
  border-color: var(--dqi-border) !important;
}}

/* File uploader */
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section {{
  background-color: var(--dqi-surface-raised) !important;
  border: 1px dashed var(--dqi-border) !important;
}}
[data-testid="stFileUploaderDropzone"] *, [data-testid="stFileUploader"] section * {{
  color: var(--dqi-text) !important;
}}
[data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploader"] button {{
  background-color: var(--dqi-surface) !important;
  border: 1px solid var(--dqi-border) !important;
  color: var(--dqi-text) !important;
}}
[data-testid="stFileUploaderFile"] {{
  background-color: var(--dqi-surface-raised) !important;
  color: var(--dqi-text) !important;
}}

/* Radio / checkbox / toggle / slider labels */
[data-testid="stWidgetLabel"] p {{ color: var(--dqi-text) !important; }}
[data-testid="stRadio"] label, [data-testid="stCheckbox"] label {{ color: var(--dqi-text) !important; }}

/* Alerts keep their own tint but inherit readable text */
[data-testid="stAlert"] p {{ color: inherit !important; }}

/* Plain containers (non-bordered) that still carry Streamlit's own white block bg */
[data-testid="stVerticalBlock"] {{ background-color: transparent; }}

/* Scrollbar polish */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: var(--dqi-baseline, #c3c2b7); border-radius: 6px; }}

/* DQI custom components */
.dqi-header {{
  display: flex; align-items: center; gap: 12px; margin-bottom: 4px;
}}
.dqi-logo {{
  width: 36px; height: 36px; border-radius: 9px;
  background: linear-gradient(135deg, {PRIMARY}, {CATEGORICAL['light'][2]});
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}}
.dqi-title {{ font-size: 1.6rem; font-weight: 800; line-height: 1.1; margin: 0; }}
.dqi-subtitle {{ color: var(--dqi-text-secondary); font-size: 0.92rem; margin: 2px 0 0 0; }}

.dqi-kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0 18px 0; }}
.dqi-kpi-card {{
  flex: 1 1 150px; min-width: 150px;
  background-color: var(--dqi-surface);
  border: 1px solid var(--dqi-border);
  border-radius: 12px; padding: 14px 16px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}}
.dqi-kpi-label {{
  font-size: 0.74rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--dqi-text-secondary); margin-bottom: 6px;
}}
.dqi-kpi-value {{ font-size: 1.55rem; font-weight: 800; color: var(--dqi-text); line-height: 1.1; }}
.dqi-kpi-sub {{ font-size: 0.78rem; margin-top: 4px; font-weight: 600; }}

.dqi-badge {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 700;
}}
.dqi-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
</style>
""", unsafe_allow_html=True)


def render_sidebar_header():
    with st.sidebar:
        st.markdown(
            '<div class="dqi-header"><div class="dqi-logo">📊</div>'
            '<div><p class="dqi-title" style="font-size:1.15rem;">DQI</p>'
            '<p class="dqi-subtitle" style="margin:0;">Data Quality Intelligence</p></div></div>',
            unsafe_allow_html=True,
        )
        st.toggle("Dark mode", key="dark_mode")
        st.divider()


def page_header(title: str, subtitle: str = "", icon: str = "📊"):
    st.markdown(f"""
<div class="dqi-header">
  <div class="dqi-logo">{icon}</div>
  <div>
    <p class="dqi-title">{title}</p>
    {f'<p class="dqi-subtitle">{subtitle}</p>' if subtitle else ''}
  </div>
</div>
""", unsafe_allow_html=True)


def status_color(band_or_status: str) -> str:
    key = _BAND_TO_STATUS.get(band_or_status, band_or_status)
    return STATUS.get(key, _tokens()["muted"])


def badge_html(label: str, status: str) -> str:
    color = status_color(status)
    return (f'<span class="dqi-badge" style="background-color:{color}1a; color:{color};">'
            f'<span class="dqi-dot" style="background-color:{color};"></span>{label}</span>')


def kpi_card_html(label: str, value: str, sub: str | None = None, sub_status: str | None = None) -> str:
    sub_html = ""
    if sub:
        color = status_color(sub_status) if sub_status else _tokens()["text_secondary"]
        sub_html = f'<div class="dqi-kpi-sub" style="color:{color};">{sub}</div>'
    return (f'<div class="dqi-kpi-card"><div class="dqi-kpi-label">{label}</div>'
            f'<div class="dqi-kpi-value">{value}</div>{sub_html}</div>')


def kpi_row(cards: list):
    st.markdown(f'<div class="dqi-kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)


def apply_chart_theme(fig):
    """Applies the DQI chrome (surface, gridlines, ink, font) to a Plotly figure in place."""
    t = _tokens()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text_secondary"], family="-apple-system, system-ui, Segoe UI, sans-serif"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=30, b=20),
    )
    fig.update_xaxes(gridcolor=t["gridline"], zerolinecolor=t["baseline"], linecolor=t["baseline"])
    fig.update_yaxes(gridcolor=t["gridline"], zerolinecolor=t["baseline"], linecolor=t["baseline"])
    # Polar charts (radar) don't inherit plot_bgcolor — theme them explicitly.
    if fig.layout.polar is not None:
        fig.update_layout(polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(gridcolor=t["gridline"], linecolor=t["baseline"], color=t["text_secondary"]),
            angularaxis=dict(gridcolor=t["gridline"], linecolor=t["baseline"], color=t["text"]),
        ))
    return fig


def categorical_colors(n: int | None = None) -> list:
    colors = _cat()
    return colors[:n] if n else colors


def sequential_scale() -> list:
    return SEQUENTIAL_BLUE


def init_page(title: str, icon: str = "📊", layout: str = "wide"):
    """One call at the top of every page: config + theme + sidebar branding."""
    st.set_page_config(page_title=f"{title} — DQI", page_icon=icon, layout=layout)
    init_theme()
    inject_css()
    render_sidebar_header()
