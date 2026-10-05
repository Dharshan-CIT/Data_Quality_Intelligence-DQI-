import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.state import init_session, require_active_dataset
from app.theme import init_page, page_header, kpi_card_html, kpi_row, apply_chart_theme, sequential_scale
from dqi_core.impact.scoring import score_issues
from dqi_core.impact.ranking import build_rankings
from dqi_core.impact.stats import compute_rank_correlation
from dqi_core.business_impact import estimate_exposure, total_exposure

init_page("Impact Analysis", icon="🎯")
init_session()
state = require_active_dataset()

page_header(f"Impact Analysis — {state.filename}",
            "The central DQI contribution: frequency-based vs. impact-aware prioritization, "
            "compared on this dataset's actual detected issues.", icon="🎯")

with st.container(border=True):
    st.markdown("**Scoring configuration**")
    c1, c2, c3 = st.columns(3)
    with c1:
        critical_cols = st.multiselect(
            "Critical columns (downstream sensitivity = 1.0)",
            options=list(state.profile.column_profiles.keys()), default=state.critical_columns,
        )
    with c2:
        revenue = st.number_input("Revenue per affected record ($) — 0 = unconfigured",
                                   min_value=0.0, value=state.revenue_per_record, step=1.0)
    with c3:
        op_cost = st.number_input("Operational cost per affected record ($)",
                                   min_value=0.0, value=state.operational_cost_per_record, step=1.0)

    if st.button("Recompute impact scores with these assumptions", type="primary"):
        state.critical_columns = critical_cols
        state.revenue_per_record = revenue
        state.operational_cost_per_record = op_cost
        state.issues = score_issues(state.issues, total_rows=len(state.current_df),
                                     critical_columns=critical_cols, revenue_per_record=revenue)
        state.ranking_df = build_rankings(state.issues)
        state.rank_corr = compute_rank_correlation(state.ranking_df)
        st.success("Impact scores recomputed.")

if state.ranking_df.empty:
    st.success("No issues detected — nothing to rank.")
    st.stop()

st.subheader("Frequency rank vs. Impact-aware rank")
with st.container(border=True):
    df = state.ranking_df.copy()
    df["label"] = df["issue_type"] + " · " + df["column"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["frequency_rank"], y=df["impact_rank"], mode="markers+text",
        text=df["label"], textposition="top center",
        marker=dict(size=12, color=df["impact_score"], colorscale=[[i / 6, c] for i, c in enumerate(sequential_scale())],
                    showscale=True, colorbar=dict(title="Impact"), line=dict(width=1, color="rgba(0,0,0,0.15)")),
        name="Issues",
    ))
    max_rank = max(df["frequency_rank"].max(), df["impact_rank"].max())
    fig.add_trace(go.Scatter(x=[1, max_rank], y=[1, max_rank], mode="lines", name="Perfect agreement",
                              line=dict(dash="dash", color="#898781")))
    fig.update_layout(xaxis_title="Frequency rank (1 = most frequent)",
                       yaxis_title="Impact rank (1 = highest impact)", height=480)
    apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Points on the dashed line: frequency and impact agree. Points far off it: this is exactly "
               "where frequency-based prioritization would have picked the wrong thing to fix first.")

st.subheader("Statistical validation of the ranking comparison")
corr = state.rank_corr
kpi_row([
    kpi_card_html("Spearman's rs", f"{corr.spearman_rs}", f"p = {corr.spearman_p}"),
    kpi_card_html("Kendall's τ", f"{corr.kendall_tau}", f"p = {corr.kendall_p}"),
    kpi_card_html("Issues compared (n)", str(corr.n)),
])
st.info(corr.interpretation)
st.caption("These are computed live from this dataset's current issues — not hard-coded reference values. "
           "The historical DQI project reported rs≈0.5175, τ≈0.4242 on its own benchmark dataset; your "
           "numbers will differ unless you reproduce that exact dataset and configuration.")

st.subheader("Full ranking comparison")
display_cols = ["issue_id", "issue_type", "pillar", "column", "affected_records", "frequency_pct",
                 "severity", "downstream_sensitivity", "business_exposure", "impact_score",
                 "frequency_rank", "impact_rank", "rank_change"]
st.dataframe(df[display_cols].sort_values("impact_rank"), use_container_width=True, hide_index=True)

st.subheader("Business impact estimation")
if revenue == 0 and op_cost == 0:
    st.warning("UNCONFIGURED: set a revenue/operational-cost assumption above to get a real $ exposure "
               "estimate. Showing $0 would otherwise look like a measurement rather than an unset input.")
exposures = estimate_exposure(state.issues, total_rows=len(state.current_df),
                               revenue_per_record=revenue, operational_cost_per_record=op_cost)
summary = total_exposure(exposures)
kpi_row([kpi_card_html("Total estimated exposure", f"${summary['total_estimated_exposure']:,.2f}", summary["label"])])
exp_df = pd.DataFrame([{"Issue ID": e.issue_id, "Affected Records": e.affected_records,
                        "Estimated Exposure ($)": e.estimated_exposure, "Risk Category": e.risk_category}
                       for e in exposures])
st.dataframe(exp_df, use_container_width=True, hide_index=True)
