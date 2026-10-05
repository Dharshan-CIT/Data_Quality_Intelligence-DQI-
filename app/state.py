"""Shared Streamlit session-state helpers.

Each uploaded/loaded dataset gets one DatasetState entry. Running the
pipeline (profile -> issues -> pillars -> health -> impact -> ranking) is
idempotent and cheap enough to call eagerly on upload, then re-run on demand
after remediation so "before" and "after" are always two distinct,
independently computed DatasetState snapshots.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from dqi_core.profiling import profile_dataset
from dqi_core.issues.detection import detect_all_issues
from dqi_core.quality.pillars import assess_all_pillars
from dqi_core.health import compute_health_index
from dqi_core.impact.scoring import score_issues
from dqi_core.impact.ranking import build_rankings
from dqi_core.impact.stats import compute_rank_correlation
from dqi_core.governance.audit import AuditLog


class DatasetState:
    def __init__(self, filename: str, df):
        self.filename = filename
        self.original_df = df
        self.current_df = df
        self.remediation_session = None
        self.quarantine_df = df.iloc[0:0]
        self.critical_columns: list = []
        self.revenue_per_record: float = 0.0
        self.operational_cost_per_record: float = 0.0
        self.recompute()

    def recompute(self):
        self.profile = profile_dataset(self.current_df, self.filename)
        self.issues = detect_all_issues(self.current_df, self.profile)
        self.pillars = assess_all_pillars(self.current_df, self.profile, self.issues)
        self.health = compute_health_index(self.pillars)
        self.issues = score_issues(
            self.issues, total_rows=len(self.current_df),
            critical_columns=self.critical_columns, revenue_per_record=self.revenue_per_record,
        )
        self.ranking_df = build_rankings(self.issues)
        self.rank_corr = compute_rank_correlation(self.ranking_df)


def init_session():
    if "datasets" not in st.session_state:
        st.session_state.datasets = {}  # filename -> DatasetState
    if "active_dataset" not in st.session_state:
        st.session_state.active_dataset = None
    if "audit_log" not in st.session_state:
        st.session_state.audit_log = AuditLog()
    if "before_remediation" not in st.session_state:
        st.session_state.before_remediation = {}  # filename -> snapshot DatasetState


def get_active() -> DatasetState | None:
    init_session()
    name = st.session_state.active_dataset
    if name is None:
        return None
    return st.session_state.datasets.get(name)


def add_dataset(filename: str, df) -> DatasetState:
    init_session()
    state = DatasetState(filename, df)
    st.session_state.datasets[filename] = state
    st.session_state.active_dataset = filename
    st.session_state.audit_log.log("dataset_upload", filename, filename,
                                    f"Loaded {df.shape[0]} rows x {df.shape[1]} columns.")
    return state


def require_active_dataset():
    state = get_active()
    if state is None:
        st.info("Upload or load a dataset on the Home page first.")
        st.stop()
    return state
