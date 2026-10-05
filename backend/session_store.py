"""In-memory per-session state for the FastAPI backend.

A browser tab gets a session_id (generated client-side, sent as the
X-Session-Id header). Everything here is process-memory only — restarting
the server drops all sessions, same tradeoff the Streamlit build made with
st.session_state. This is a demo/single-process backend, not a durable store.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from dqi_core.profiling import profile_dataset
from dqi_core.issues.detection import detect_all_issues
from dqi_core.quality.pillars import assess_all_pillars
from dqi_core.health import compute_health_index
from dqi_core.impact.scoring import score_issues
from dqi_core.impact.ranking import build_rankings
from dqi_core.impact.stats import compute_rank_correlation
from dqi_core.governance.audit import AuditLog
from dqi_core.remediation.engine import RemediationSession


class DatasetState:
    def __init__(self, filename: str, df: pd.DataFrame):
        self.filename = filename
        self.original_df = df
        self.current_df = df
        self.remediation_session: Optional[RemediationSession] = None
        self.critical_columns: List[str] = []
        self.revenue_per_record: float = 0.0
        self.operational_cost_per_record: float = 0.0
        self.pii_results = None
        self.contract_result = None
        self.validation_report = None
        self.health_weights: Optional[Dict[str, float]] = None  # user-tuned pillar weights; None = configs/weights.yaml
        self.created_at = time.time()
        self.updated_at = time.time()
        self.recompute()

    def recompute(self):
        self.profile = profile_dataset(self.current_df, self.filename)
        self.issues = detect_all_issues(self.current_df, self.profile)
        self.pillars = assess_all_pillars(self.current_df, self.profile, self.issues)
        self.health = compute_health_index(self.pillars, weights=self.health_weights)
        self.issues = score_issues(
            self.issues, total_rows=len(self.current_df),
            critical_columns=self.critical_columns, revenue_per_record=self.revenue_per_record,
        )
        self.ranking_df = build_rankings(self.issues)
        self.rank_corr = compute_rank_correlation(self.ranking_df)
        self.updated_at = time.time()


@dataclass
class Session:
    session_id: str
    datasets: Dict[str, DatasetState] = field(default_factory=dict)
    active_dataset: Optional[str] = None
    audit_log: AuditLog = field(default_factory=AuditLog)
    last_seen: float = field(default_factory=time.time)
    history: Dict[str, list] = field(default_factory=dict)

    def record_snapshot(self, state: DatasetState):
        from datetime import datetime, timezone
        self.history.setdefault(state.filename, []).append({
            "at": datetime.now(timezone.utc).isoformat(),
            "rows": state.profile.rows,
            "health": state.health.overall,
            "band": state.health.band,
            "issues": len(state.issues),
            "critical": sum(1 for i in state.issues if i.severity >= 4),
        })

    def get_active(self) -> Optional[DatasetState]:
        if self.active_dataset is None:
            return None
        return self.datasets.get(self.active_dataset)

    def require(self, filename: Optional[str] = None) -> DatasetState:
        name = filename or self.active_dataset
        if name is None or name not in self.datasets:
            raise KeyError("No active dataset for this session.")
        return self.datasets[name]


class SessionStore:
    """Thread-safe registry of Session objects, keyed by session_id."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> Session:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = Session(session_id=session_id)
            session = self._sessions[session_id]
            session.last_seen = time.time()
            return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)


store = SessionStore()
