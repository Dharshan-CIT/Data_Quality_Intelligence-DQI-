import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import streamlit as st

from app.state import init_session, require_active_dataset
from app.theme import init_page, page_header, kpi_row, kpi_card_html
from dqi_core.governance.pii import detect_pii, tokenize_column
from dqi_core.governance.contracts import load_contract, validate_against_contract
from dqi_core.integrations.streaming import LocalSimulator, get_kafka_status
from dqi_core.integrations.external_trackers import create_jira_ticket, trigger_pagerduty_alert

init_page("Governance", icon="🛡️")
init_session()
state = require_active_dataset()

page_header(f"Governance — {state.filename}",
            "PII detection, data contracts, streaming telemetry, and the audit trail.", icon="🛡️")

tab_pii, tab_contract, tab_stream, tab_audit, tab_ext = st.tabs(
    ["PII Detection", "Data Contracts", "Streaming / Kafka", "Audit Log", "Jira / PagerDuty"]
)

with tab_pii:
    st.subheader("Heuristic PII detection")
    st.caption("Regex pattern matching only — this is NOT a legal compliance determination.")
    if st.button("Scan for PII"):
        results = detect_pii(state.current_df)
        st.session_state[f"pii_{state.filename}"] = results
        st.session_state.audit_log.log("pii_scan", state.filename, "dataset", f"{len(results)} pattern(s) found.")
    results = st.session_state.get(f"pii_{state.filename}", [])
    if results:
        rows = [{"Column": r.column, "Pattern": r.pattern, "Matches": r.match_count,
                 "Match %": r.match_pct, "Sample (masked)": r.sample_masked, "Method": r.detection_method}
                for r in results]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("**SHA-256 tokenization** (referentially consistent — same input always maps to the same token)")
        pii_cols = sorted({r.column for r in results})
        col = st.selectbox("Column to tokenize", pii_cols)
        if st.button("Tokenize column (applies to the working copy)"):
            state.current_df = tokenize_column(state.current_df, col)
            st.session_state.audit_log.log("tokenization", state.filename, col, "SHA-256 tokenized.")
            st.success(f"Column '{col}' tokenized.")
    else:
        st.caption("No scan run yet, or no PII-like patterns found.")

with tab_contract:
    st.subheader("Data contract validation")
    uploaded_contract = st.file_uploader("Upload a contract (YAML)", type=["yaml", "yml"])
    use_example = st.checkbox("Use the bundled example contract (contracts/retail_sample_contract.yaml)")
    contract = None
    contract_name = "contract"
    if uploaded_contract is not None:
        import yaml
        contract = yaml.safe_load(uploaded_contract)
        contract_name = uploaded_contract.name
    elif use_example:
        example_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                     "contracts", "retail_sample_contract.yaml")
        if os.path.exists(example_path):
            contract = load_contract(example_path)
            contract_name = "retail_sample_contract.yaml"
        else:
            st.warning("Example contract not found — only ships alongside the sample retail dataset.")

    if contract and st.button("Validate against contract"):
        result = validate_against_contract(state.current_df, contract, contract_name)
        st.session_state[f"contract_{state.filename}"] = result
        st.session_state.audit_log.log("contract_validation", state.filename, contract_name,
                                        f"{result.deployment_status}: {len(result.violations)} violation(s).")

    result = st.session_state.get(f"contract_{state.filename}")
    if result:
        status_color = {"PASS": "success", "WARN": "warning", "BLOCKED": "error"}[result.deployment_status]
        getattr(st, status_color)(f"Deployment status: {result.deployment_status}")
        if result.violations:
            rows = [{"Column": v.column, "Rule": v.rule, "Severity": v.severity,
                     "Affected Rows": v.affected_rows, "Message": v.message, "Blocking": v.blocking}
                    for v in result.violations]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.success("No contract violations.")

with tab_stream:
    st.subheader("Real-time / streaming pipeline")
    kafka_status = get_kafka_status(os.environ.get("KAFKA_BOOTSTRAP_SERVERS"))
    if kafka_status["available"]:
        st.success(f"Kafka: {kafka_status['reason']}")
    else:
        st.warning(f"Kafka unavailable: {kafka_status['reason']}")

    st.markdown("**Simulation Mode** — synthetic events, clearly not a live broker.")
    if "simulator" not in st.session_state:
        st.session_state.simulator = LocalSimulator()
    if st.button("Generate a batch of 500 simulated events"):
        metrics = st.session_state.simulator.tick(500)
        st.session_state.stream_metrics = metrics
    metrics = st.session_state.get("stream_metrics")
    if metrics:
        st.caption(metrics.status)
        kpi_row([
            kpi_card_html("Throughput (events/sec)", str(metrics.throughput_eps)),
            kpi_card_html("Valid events", str(metrics.valid_events), None, "good"),
            kpi_card_html("Malformed", str(metrics.malformed_events), None, "serious" if metrics.malformed_events else "good"),
            kpi_card_html("Schema violations", str(metrics.schema_violations), None, "warning" if metrics.schema_violations else "good"),
            kpi_card_html("Quarantined", str(metrics.quarantined_events)),
        ])
        st.caption("Circuit breaker: malformed/invalid events are quarantined and never propagated downstream.")

with tab_audit:
    st.subheader("Audit log")
    audit_df = st.session_state.audit_log.as_dataframe()
    st.dataframe(audit_df, use_container_width=True, hide_index=True)
    if st.button("Export audit log to reports/audit_log.json"):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                             "reports", "audit_log.json")
        st.session_state.audit_log.export_json(path)
        st.success(f"Exported to {path}")

with tab_ext:
    st.subheader("Jira / PagerDuty (optional integrations)")
    st.caption("These never fake success. Without credentials configured, they return an honest "
               "'integration unavailable' result.")
    summary = st.text_input("Ticket/alert summary", value="DQI: critical data quality issue detected")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Create Jira ticket"):
            result = create_jira_ticket(summary, "Created from the DQI Governance page.")
            (st.success if result.ok else st.error)(result.message)
    with c2:
        if st.button("Trigger PagerDuty alert"):
            result = trigger_pagerduty_alert(summary)
            (st.success if result.ok else st.error)(result.message)
