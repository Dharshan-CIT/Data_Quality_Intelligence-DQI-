import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import streamlit as st

from app.state import init_session, require_active_dataset
from app.theme import init_page, page_header, kpi_card_html, kpi_row
from dqi_core.remediation.engine import RemediationSession
from dqi_core.remediation.validation import build_validation_report
from dqi_core.profiling import profile_dataset
from dqi_core.issues.detection import detect_all_issues
from dqi_core.quality.pillars import assess_all_pillars
from dqi_core.health import compute_health_index

init_page("Remediation", icon="🛠️")
init_session()
state = require_active_dataset()

page_header(f"Remediation — {state.filename}",
            "Before → Detected Issues → Selected Repairs → After. The original upload is never mutated; "
            "every operation is logged with a before/after summary.", icon="🛠️")

if state.remediation_session is None:
    state.remediation_session = RemediationSession(state.original_df)
session = state.remediation_session

kpi_row([
    kpi_card_html("Rows", f"{len(session.current_df):,}"),
    kpi_card_html("Health (current)", f"{state.health.overall}/100", state.health.band, state.health.band),
    kpi_card_html("Open issues", str(len(state.issues))),
])

st.subheader("Apply a repair")
op = st.selectbox("Operation", [
    "Remove exact duplicate rows", "Handle missing values", "Handle invalid numeric values",
    "Normalize text formatting", "Normalize dates",
])

with st.container(border=True):
    if op == "Remove exact duplicate rows":
        if st.button("Apply", key="dup"):
            action = session.remove_duplicate_rows()
            st.session_state.audit_log.log("remediation", state.filename, "duplicate_rows",
                                            f"Removed {action.rows_affected} duplicate rows.")
            st.success(f"Removed {action.rows_affected} duplicate rows.")

    elif op == "Handle missing values":
        col = st.selectbox("Column", list(session.current_df.columns))
        strategy = st.selectbox("Strategy", ["drop", "mean", "median", "mode", "constant", "ffill"])
        constant = st.text_input("Constant value (only for 'constant' strategy)") if strategy == "constant" else None
        if st.button("Apply", key="missing"):
            try:
                action = session.handle_missing(col, strategy, constant=constant)
                st.session_state.audit_log.log("remediation", state.filename, col,
                                                f"{strategy} applied to missing values ({action.rows_affected} rows).")
                st.success(f"Applied '{strategy}' to {action.rows_affected} missing values in '{col}'.")
            except Exception as e:
                st.error(str(e))

    elif op == "Handle invalid numeric values":
        numeric_cols = state.profile.numeric_columns
        if not numeric_cols:
            st.info("No numeric columns in this dataset.")
        else:
            col = st.selectbox("Column", numeric_cols)
            condition = st.selectbox("Condition", ["negative", "zero"])
            strategy = st.selectbox("Strategy", ["replace", "remove", "quarantine"])
            replacement = st.number_input("Replacement value (only for 'replace')", value=0.0) if strategy == "replace" else None
            if st.button("Apply", key="invalid_numeric"):
                try:
                    action = session.handle_invalid_numeric(col, condition, strategy, replacement=replacement)
                    st.session_state.audit_log.log("remediation", state.filename, col,
                                                    f"{strategy} applied to {condition} values ({action.rows_affected} rows).")
                    st.success(f"Applied '{strategy}' to {action.rows_affected} {condition} values in '{col}'.")
                except Exception as e:
                    st.error(str(e))

    elif op == "Normalize text formatting":
        col = st.selectbox("Column", state.profile.categorical_columns or list(session.current_df.columns))
        if st.button("Apply", key="format"):
            action = session.normalize_formatting(col)
            st.session_state.audit_log.log("remediation", state.filename, col,
                                            f"Formatting normalized ({action.rows_affected} rows changed).")
            st.success(f"Normalized formatting in '{col}' ({action.rows_affected} rows changed).")

    elif op == "Normalize dates":
        col = st.selectbox("Column", state.profile.datetime_columns or list(session.current_df.columns))
        if st.button("Apply", key="dates"):
            action = session.normalize_dates(col)
            st.session_state.audit_log.log("remediation", state.filename, col,
                                            f"Dates normalized ({action.rows_affected} rows changed).")
            st.success(f"Normalized dates in '{col}' ({action.rows_affected} rows changed).")

st.subheader("Audit trail")
if session.audit_trail:
    audit_rows = [{"Operation": a.operation, "Column": a.column, "Rows Affected": a.rows_affected,
                   "Reason": a.reason, "Before": a.before_summary, "After": a.after_summary,
                   "Timestamp": a.timestamp} for a in session.audit_trail]
    st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
else:
    st.caption("No remediation actions applied yet.")

st.subheader("Quarantine")
st.caption(f"{len(session.quarantine_df)} record(s) quarantined (could not be safely auto-repaired).")
if len(session.quarantine_df):
    st.dataframe(session.quarantine_df, use_container_width=True)

st.divider()
st.subheader("Commit & validate")
st.warning("Committing recomputes health/issues on the current remediated data and locks in the 'before' "
           "snapshot for comparison. This does not affect your original uploaded file.")
if st.button("Commit remediation and run validation", type="primary"):
    before_df = state.original_df
    before_health = state.health.overall
    before_issue_count = len(state.issues)

    state.current_df = session.current_df
    profile_after = profile_dataset(state.current_df, state.filename)
    issues_after = detect_all_issues(state.current_df, profile_after)
    pillars_after = assess_all_pillars(state.current_df, profile_after, issues_after)
    health_after = compute_health_index(pillars_after)

    state.profile, state.issues, state.pillars, state.health = profile_after, issues_after, pillars_after, health_after
    state.recompute()  # re-score impact on the new issue set

    report = build_validation_report(before_df, state.current_df, before_health, state.health.overall,
                                      before_issue_count, len(state.issues), profile_after.numeric_columns)
    st.session_state[f"validation_report_{state.filename}"] = report
    st.session_state.audit_log.log("remediation_commit", state.filename, "dataset",
                                    f"Health {before_health} -> {state.health.overall}.")
    st.success("Committed. See the validation report below.")

report = st.session_state.get(f"validation_report_{state.filename}")
if report:
    st.subheader("Before / After validation")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", report.rows_after, delta=report.rows_after - report.rows_before)
    c2.metric("Missing cells", report.missing_cells_after, delta=report.missing_cells_after - report.missing_cells_before)
    c3.metric("Health", report.health_after, delta=round(report.health_after - report.health_before, 2))
    c4.metric("Issue count", report.issue_count_after, delta=report.issue_count_after - report.issue_count_before)

    if report.ks_results:
        st.markdown("**Kolmogorov–Smirnov test (numeric distribution shift check)**")
        ks_rows = [{"Column": r.column, "KS statistic": r.statistic, "p-value": r.p_value,
                    "Interpretation": r.interpretation} for r in report.ks_results]
        st.dataframe(pd.DataFrame(ks_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No numeric columns available for a KS test.")
