import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

from app.state import init_session, require_active_dataset
from app.theme import init_page, page_header
from dqi_core.reporting import build_report, export_json, export_csv, export_pdf
from dqi_core.business_impact import estimate_exposure, total_exposure
from dqi_core.governance.pii import detect_pii
from dqi_core.assistant import answer_question, llm_available

init_page("Reports & Assistant", icon="📄")
init_session()
state = require_active_dataset()

page_header(f"Reports & Assistant — {state.filename}", icon="📄")
tab_report, tab_assistant = st.tabs(["Report Export", "Assistant"])

with tab_report:
    st.caption("Every export (JSON/CSV/PDF) is built from the same report dict — the numbers always match.")

    exposures = estimate_exposure(state.issues, total_rows=len(state.current_df),
                                   revenue_per_record=state.revenue_per_record,
                                   operational_cost_per_record=state.operational_cost_per_record)
    exposure_summary = total_exposure(exposures)
    pii_results = st.session_state.get(f"pii_{state.filename}", [])
    contract_result = st.session_state.get(f"contract_{state.filename}")
    validation_report = st.session_state.get(f"validation_report_{state.filename}")

    report = build_report(
        state.profile, state.health, state.pillars, state.ranking_df, state.rank_corr,
        validation_report=validation_report, exposure_summary=exposure_summary,
        contract_result=contract_result, pii_results=pii_results,
    )

    st.json(report["executive_summary"])

    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports")
    base_name = os.path.splitext(state.filename)[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Export JSON"):
            path = export_json(report, os.path.join(reports_dir, f"{base_name}_report.json"))
            st.success(f"Written to {path}")
            st.session_state.audit_log.log("export", state.filename, "report.json", path)
    with c2:
        if st.button("Export ranking CSV"):
            path = export_csv(state.ranking_df, os.path.join(reports_dir, f"{base_name}_ranking.csv"))
            st.success(f"Written to {path}")
            st.session_state.audit_log.log("export", state.filename, "ranking.csv", path)
    with c3:
        if st.button("Export PDF"):
            try:
                path = export_pdf(report, os.path.join(reports_dir, f"{base_name}_report.pdf"))
                st.success(f"Written to {path}")
                st.session_state.audit_log.log("export", state.filename, "report.pdf", path)
            except Exception as e:
                st.error(f"PDF export failed: {e}")

with tab_assistant:
    st.title("DQI Assistant")
    if llm_available():
        st.caption("An LLM (ANTHROPIC_API_KEY detected) could be wired in here; this build answers "
                   "deterministically from computed results either way, so numbers are never invented.")
    else:
        st.caption("Deterministic local assistant — answers are generated only from already-computed "
                   "results for this dataset, never invented. Set ANTHROPIC_API_KEY to enable an LLM-backed version.")

    for suggestion in ["Why is this dataset unhealthy?", "What is the highest-impact issue?",
                        "Which column needs attention first?", "What remediation would you recommend?"]:
        if st.button(suggestion):
            st.session_state["assistant_question"] = suggestion

    question = st.text_input("Ask a question about this dataset", value=st.session_state.get("assistant_question", ""))
    if question:
        answer = answer_question(question, state.health, state.issues, state.ranking_df)
        st.markdown(f"**Answer:** {answer}")
