"""The impact-aware scoring engine — DQI's central contribution.

Impact Score = Severity x Downstream Sensitivity x Business Exposure,
with Frequency applied only as a small, capped contextual modifier so it
can never dominate the ranking the way pure frequency-based prioritization
would. All weights are read from configs/weights.yaml (see docs/METHODOLOGY.md).
"""
from __future__ import annotations

import math
from typing import List, Optional

from dqi_core.config import load_config
from dqi_core.models import Issue


def _downstream_sensitivity(column: Optional[str], critical_columns: set, default: float) -> float:
    if column is None:
        return min(1.0, default + 0.2)  # dataset-wide issues touch more downstream consumers
    return 1.0 if column in critical_columns else default


def score_issues(issues: List[Issue], total_rows: int, critical_columns: Optional[List[str]] = None,
                  revenue_per_record: float = 0.0) -> List[Issue]:
    """Mutates and returns `issues` with downstream_sensitivity, business_exposure
    and impact_score populated. Pure function otherwise — no I/O, no globals."""
    cfg = load_config()["impact"]
    critical_set = set(critical_columns or cfg["downstream_sensitivity"].get("critical_columns") or [])
    default_sensitivity = cfg["downstream_sensitivity"]["default_sensitivity"]
    freq_cap = cfg["frequency_modifier_cap"]

    if not issues:
        return issues

    # Step 1: raw business exposure per issue (before normalization).
    raw_exposure = []
    for issue in issues:
        if revenue_per_record > 0:
            exposure_dollars = issue.affected_records * revenue_per_record
            raw_exposure.append(exposure_dollars)
        else:
            raw_exposure.append(None)  # unconfigured -> use frequency proxy below

    using_dollar_exposure = any(v is not None for v in raw_exposure)
    if using_dollar_exposure:
        max_exposure = max(v for v in raw_exposure if v is not None) or 1.0
    else:
        max_exposure = 1.0

    max_severity_x_sensitivity_x_exposure = 5.0 * 1.0 * 1.0
    max_final = max_severity_x_sensitivity_x_exposure * (1 + freq_cap)

    log_total = math.log1p(max(total_rows, 1))

    for issue, exposure_dollars in zip(issues, raw_exposure):
        sensitivity = _downstream_sensitivity(issue.column, critical_set, default_sensitivity)
        if using_dollar_exposure and exposure_dollars is not None:
            exposure_norm = min(1.0, exposure_dollars / max_exposure) if max_exposure else 0.0
        else:
            # No business-value assumption configured: fall back to a LOG-SCALED
            # share of affected records, not a linear one. Linear frequency would
            # let "affects everything, barely matters" issues dominate severe but
            # rare ones — exactly the frequency-first behavior DQI exists to avoid.
            exposure_norm = min(1.0, math.log1p(issue.affected_records) / log_total) if log_total else 0.0

        severity = issue.severity
        raw = severity * sensitivity * exposure_norm
        freq_norm = min(1.0, issue.frequency_pct / 100.0)
        final = raw * (1 + freq_cap * freq_norm)

        issue.downstream_sensitivity = round(sensitivity, 3)
        issue.business_exposure = round(exposure_norm, 4)
        issue.impact_score = round(min(100.0, (final / max_final) * 100.0), 2) if max_final else 0.0

    return issues
