import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dqi_core.ingestion import load_file
from app.state import init_session, add_dataset, get_active
from app.theme import (
    init_page, page_header, kpi_card_html, kpi_row, badge_html, status_color,
    apply_chart_theme, categorical_colors, sequential_scale,
)

init_page("Home", icon="📊")
init_session()

page_header("Data Quality Intelligence", "An impact-aware framework for assessing and prioritizing data quality issues.")

with st.expander("What makes DQI different", expanded=False):
    st.markdown(
        "Most data-quality tools prioritize the **most frequent** issue. DQI prioritizes by "
        "**Impact Score = Severity × Downstream Sensitivity × Business Exposure**, with frequency "
        "applied only as a small, capped contextual modifier. See the **Impact Analysis** page to "
        "see where frequency-based and impact-aware prioritization disagree on this dataset."
    )

st.subheader("1. Load a dataset")
with st.container(border=True):
    col_a, col_b = st.columns([2, 1])
    with col_a:
        uploaded = st.file_uploader("Upload CSV, Parquet or Excel", type=["csv", "parquet", "xlsx", "xls"],
                                     accept_multiple_files=True)
        if uploaded:
            for f in uploaded:
                if f.name in st.session_state.datasets:
                    continue
                result = load_file(f, f.name)
                if result.ok:
                    add_dataset(result.filename, result.dataframe)
                    if result.warnings:
                        st.warning(f"{result.filename}: " + "; ".join(result.warnings))
                    st.success(f"Loaded {result.filename}: {result.dataframe.shape[0]} rows x "
                               f"{result.dataframe.shape[1]} columns.")
                else:
                    st.error(f"{result.filename}: {result.error}")
    with col_b:
        st.write("No file handy?")
        if st.button("Load sample retail dataset", use_container_width=True, type="primary"):
            sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                        "data", "sample", "retail_sample.csv")
            result = load_file(sample_path, "retail_sample.csv")
            if result.ok:
                add_dataset(result.filename, result.dataframe)
                st.success(f"Loaded sample dataset: {result.dataframe.shape[0]} rows.")
            else:
                st.error(result.error)

if not st.session_state.datasets:
    st.info("Upload a file or load the sample dataset to begin.")
    st.stop()

st.subheader("2. Workspace")
names = list(st.session_state.datasets.keys())
active = st.selectbox("Active dataset", names, index=names.index(st.session_state.active_dataset)
                       if st.session_state.active_dataset in names else 0)
st.session_state.active_dataset = active

comparison_rows = []
for name, s in st.session_state.datasets.items():
    critical = sum(1 for i in s.issues if i.severity >= 4)
    top_impact = max((i.impact_score for i in s.issues if i.impact_score is not None), default=0.0)
    comparison_rows.append({
        "Dataset": name, "Health": s.health.overall, "Band": s.health.band,
        "Rows": s.profile.rows, "Issues": len(s.issues), "Critical Issues": critical,
        "Top Impact Score": round(top_impact, 2),
        "Remediated": "Yes" if s.remediation_session and s.remediation_session.audit_trail else "No",
    })
st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

st.divider()

state = get_active()
page_header(f"Dashboard — {state.filename}", icon="🧭")

critical_count = sum(1 for i in state.issues if i.severity >= 4)
top_impact = max((i.impact_score for i in state.issues if i.impact_score is not None), default=0.0)
remediated = bool(state.remediation_session and state.remediation_session.audit_trail)

kpi_row([
    kpi_card_html("Dataset Health", f"{state.health.overall}/100", state.health.band, state.health.band),
    kpi_card_html("Quality Issues", str(len(state.issues))),
    kpi_card_html("Critical Issues", str(critical_count), "needs action" if critical_count else "none", "critical" if critical_count else "good"),
    kpi_card_html("Top Impact Score", f"{top_impact:.1f}"),
    kpi_card_html("Rows Analyzed", f"{state.profile.rows:,}"),
    kpi_card_html("Remediation", "Applied" if remediated else "Not yet run", None, "good" if remediated else "warning"),
])

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.markdown("**Quality pillar scores**")
        names10 = list(state.health.pillar_scores.keys())
        scores = list(state.health.pillar_scores.values())
        fig = go.Figure(data=go.Scatterpolar(
            r=scores + [scores[0]], theta=[n.title() for n in names10] + [names10[0].title()],
            fill="toself", line=dict(color=categorical_colors(1)[0]),
            fillcolor=categorical_colors(1)[0] + "33",
        ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=380)
        apply_chart_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

with c2:
    with st.container(border=True):
        st.markdown("**Top critical issues (by impact score)**")
        if not state.ranking_df.empty:
            top = state.ranking_df.sort_values("impact_score", ascending=False).head(8)
            st.dataframe(top[["issue_type", "column", "severity", "impact_score", "affected_records"]],
                         use_container_width=True, hide_index=True)
        else:
            st.success("No issues detected.")

with st.container(border=True):
    st.markdown("**Impact-aware vs frequency-based priority (this dataset)**")
    if not state.ranking_df.empty:
        colors = categorical_colors(2)
        fig2 = go.Figure()
        labels = state.ranking_df["issue_type"] + " · " + state.ranking_df["column"].astype(str)
        fig2.add_trace(go.Bar(name="Frequency rank", x=labels, y=state.ranking_df["frequency_rank"],
                               marker_color=colors[0]))
        fig2.add_trace(go.Bar(name="Impact rank", x=labels, y=state.ranking_df["impact_rank"],
                               marker_color=colors[1]))
        fig2.update_layout(barmode="group", yaxis_title="Rank (1 = most urgent)", height=380)
        apply_chart_theme(fig2)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(f"Spearman rs = {state.rank_corr.spearman_rs}, Kendall τ = {state.rank_corr.kendall_tau} "
                   f"— see the **Impact Analysis** page for the full breakdown.")

st.caption("Use the pages in the left sidebar to walk the full workflow: Profiling → Quality Pillars → "
           "Issue Explorer → Impact Analysis → Remediation → Dataset Comparison → Governance → Reports & Assistant.")
