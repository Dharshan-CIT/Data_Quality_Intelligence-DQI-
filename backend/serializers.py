"""Converts dqi_core result objects into plain JSON-serializable dicts."""
from __future__ import annotations

import math

from backend.session_store import DatasetState
from dqi_core.config import load_config


def _clean(obj):
    """Recursively replace NaN/Inf (invalid JSON) with None."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def dataset_summary(state: DatasetState) -> dict:
    critical = sum(1 for i in state.issues if i.severity >= 4)
    top_impact = max((i.impact_score for i in state.issues if i.impact_score is not None), default=0.0)
    return _clean({
        "filename": state.filename,
        "rows": state.profile.rows,
        "columns": state.profile.columns,
        "health": state.health.overall,
        "band": state.health.band,
        "issue_count": len(state.issues),
        "critical_count": critical,
        "top_impact_score": round(top_impact, 2),
        "remediated": bool(state.remediation_session and state.remediation_session.audit_trail),
        "updated_at": state.updated_at,
    })


def profile_dict(state: DatasetState) -> dict:
    return _clean(state.profile.to_dict())


def pillars_dict(state: DatasetState) -> dict:
    return _clean({name: p.to_dict() for name, p in state.pillars.items()})


def health_dict(state: DatasetState) -> dict:
    # default_weights are the configs/weights.yaml baseline, so the UI can offer "reset" even after a custom recompute.
    return _clean({**state.health.to_dict(), "default_weights": load_config()["health_index"]["weights"]})


def issues_list(state: DatasetState) -> list:
    return _clean([i.to_dict() for i in state.issues])


def ranking_list(state: DatasetState) -> list:
    if state.ranking_df.empty:
        return []
    return _clean(state.ranking_df.to_dict(orient="records"))


def rank_corr_dict(state: DatasetState) -> dict:
    c = state.rank_corr
    return _clean({
        "spearman_rs": c.spearman_rs, "spearman_p": c.spearman_p,
        "kendall_tau": c.kendall_tau, "kendall_p": c.kendall_p,
        "n": c.n, "interpretation": c.interpretation,
    })


def audit_log_list(state_session) -> list:
    return _clean([e.to_dict() for e in state_session.audit_log.entries])
