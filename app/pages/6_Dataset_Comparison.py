import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.state import init_session
from app.theme import init_page, page_header, apply_chart_theme, categorical_colors, status_color

init_page("Dataset Comparison", icon="📊")
init_session()

page_header("Dataset Comparison", "Compare health, pillars, and impact across every loaded dataset.", icon="📊")

datasets = st.session_state.datasets
if len(datasets) < 2:
    st.info("Load at least two datasets on the Home page to compare them.")
    st.stop()

selected = st.multiselect("Datasets to compare", list(datasets.keys()), default=list(datasets.keys()))
if not selected:
    st.stop()

rows = []
for name in selected:
    s = datasets[name]
    critical = sum(1 for i in s.issues if i.severity >= 4)
    rows.append({
        "Dataset": name, "Health": s.health.overall, "Band": s.health.band, "Rows": s.profile.rows,
        "Issues": len(s.issues), "Critical Issues": critical,
        "Completeness": s.pillars["completeness"].score, "Uniqueness": s.pillars["uniqueness"].score,
        "Validity": s.pillars["validity"].score, "Consistency": s.pillars["consistency"].score,
        "Top Impact": max((i.impact_score for i in s.issues if i.impact_score is not None), default=0.0),
    })
df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("Health comparison")
with st.container(border=True):
    colors = [status_color(b) for b in df["Band"]]
    fig = go.Figure(data=[go.Bar(x=df["Dataset"], y=df["Health"], text=df["Health"], textposition="outside",
                                  marker_color=colors)])
    fig.update_layout(yaxis=dict(range=[0, 105], title="Health Index"), height=360)
    apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Pillar comparison (radar)")
with st.container(border=True):
    pillar_names = [n.title() for n in datasets[selected[0]].health.pillar_scores.keys()]
    colors = categorical_colors(len(selected))
    fig2 = go.Figure()
    for idx, name in enumerate(selected):
        scores = list(datasets[name].health.pillar_scores.values())
        fig2.add_trace(go.Scatterpolar(r=scores + [scores[0]], theta=pillar_names + [pillar_names[0]],
                                        fill="toself", name=name,
                                        line=dict(color=colors[idx % len(colors)])))
    fig2.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=480)
    apply_chart_theme(fig2)
    st.plotly_chart(fig2, use_container_width=True)
