import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.state import init_session, require_active_dataset
from app.theme import init_page, page_header, kpi_card_html, kpi_row, apply_chart_theme, status_color, badge_html
from dqi_core.config import load_config
from dqi_core.health import compute_health_index

init_page("Quality Pillars", icon="🧭")
init_session()
state = require_active_dataset()

page_header(f"10-Pillar Quality Assessment — {state.filename}", icon="🧭")

kpi_row([kpi_card_html("Dataset Health Index", f"{state.health.overall}/100", state.health.band, state.health.band)])

with st.expander("Pillar weights (editable — recomputes the Health Index live)"):
    cfg = load_config()["health_index"]["weights"]
    cols = st.columns(5)
    new_weights = {}
    for idx, (pillar, w) in enumerate(cfg.items()):
        with cols[idx % 5]:
            new_weights[pillar] = st.slider(pillar.title(), 0.0, 0.3, float(w), 0.01, key=f"w_{pillar}")
    if st.button("Recompute Health Index with these weights", type="primary"):
        state.health = compute_health_index(state.pillars, weights=new_weights)
        st.success(f"New Health Index: {state.health.overall}/100 ({state.health.band})")

with st.container(border=True):
    names = list(state.pillars.keys())
    scores = [state.pillars[n].score for n in names]
    colors = [status_color(state.pillars[n].severity) for n in names]
    fig = go.Figure(data=[go.Bar(x=[n.title() for n in names], y=scores, marker_color=colors,
                                  text=[f"{s:.0f}" for s in scores], textposition="outside")])
    fig.update_layout(yaxis=dict(range=[0, 105], title="Score"), height=380)
    apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Pillar detail")
for name, result in state.pillars.items():
    header_badge = badge_html(result.severity, result.severity)
    with st.expander(f"{name.title()} — {result.score}/100"):
        st.markdown(header_badge, unsafe_allow_html=True)
        st.write(result.explanation)
        if result.limitation:
            st.warning(f"Limitation: {result.limitation}")
        cols2 = st.columns(3)
        cols2[0].metric("Affected records", result.affected_records)
        cols2[1].metric("Affected columns", len(result.affected_columns))
        cols2[2].metric("Linked issues", len(result.detected_issues))
        if result.affected_columns:
            st.write("Columns:", ", ".join(result.affected_columns))
        if result.recommendations:
            st.write("**Recommendations:**")
            for r in result.recommendations:
                st.write(f"- {r}")
