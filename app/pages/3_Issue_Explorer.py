import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import streamlit as st

from app.state import init_session, require_active_dataset
from app.theme import init_page, page_header, badge_html
from dqi_core.rca import analyze_issue

init_page("Issue Explorer", icon="🗂️")
init_session()
state = require_active_dataset()

page_header(f"Issue Explorer — {state.filename}", "Filter, sort, and drill into every detected issue.", icon="🗂️")

if not state.issues:
    st.success("No issues detected in this dataset.")
    st.stop()

all_pillars = sorted({i.pillar for i in state.issues})
all_columns = sorted({i.column for i in state.issues if i.column})
all_types = sorted({i.issue_type for i in state.issues})

with st.container(border=True):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sev_filter = st.multiselect("Severity", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])
    with c2:
        pillar_filter = st.multiselect("Quality dimension", all_pillars, default=all_pillars)
    with c3:
        column_filter = st.multiselect("Column", all_columns, default=all_columns)
    with c4:
        type_filter = st.multiselect("Issue type", all_types, default=all_types)

sort_by = st.radio("Sort by", ["Impact score", "Frequency (affected records)", "Severity"], horizontal=True)

filtered = [i for i in state.issues
            if i.severity in sev_filter and i.pillar in pillar_filter
            and (i.column in column_filter or i.column is None)
            and i.issue_type in type_filter]

sort_key = {
    "Impact score": lambda i: i.impact_score or 0,
    "Frequency (affected records)": lambda i: i.affected_records,
    "Severity": lambda i: i.severity,
}[sort_by]
filtered = sorted(filtered, key=sort_key, reverse=True)

st.caption(f"Showing {len(filtered)} of {len(state.issues)} issues.")

table_rows = [{
    "Issue ID": i.issue_id, "Type": i.issue_type, "Pillar": i.pillar, "Column": i.column,
    "Affected": i.affected_records, "Freq %": i.frequency_pct, "Severity": i.severity,
    "Impact Score": i.impact_score, "Freq Rank": i.frequency_rank, "Impact Rank": i.impact_rank,
    "Rank Δ": i.rank_change,
} for i in filtered]
st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

st.subheader("Inspect an issue")
options = {f"{i.issue_id} — {i.issue_type} on {i.column}": i for i in filtered}
if options:
    choice = st.selectbox("Select an issue for full detail (explanation, recommendation, root cause)",
                           list(options.keys()))
    issue = options[choice]
    severity_label = {5: "Critical", 4: "Poor", 3: "Needs Attention", 2: "Good", 1: "Excellent"}.get(issue.severity, "Good")
    st.markdown(badge_html(f"Severity {issue.severity}/5", severity_label), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**Evidence**")
            st.markdown(f"**Explanation (detected evidence):** {issue.explanation}")
            st.markdown(f"**Recommended action:** {issue.recommended_action}")
            st.json(issue.evidence)
    with c2:
        with st.container(border=True):
            rca = analyze_issue(issue)
            st.markdown("**Root-cause analysis**")
            st.markdown(f"- Detected evidence: {rca.detected_evidence}")
            st.markdown(f"- Probable source *(inferred, not verified from this dataset)*: {rca.probable_source}")
            if rca.contributing_factors:
                st.markdown("- Contributing factors (inferred):")
                for f in rca.contributing_factors:
                    st.markdown(f"  - {f}")
            st.markdown("**Propagation chain**")
            for step in rca.propagation_chain:
                st.markdown(f"→ {step}")
