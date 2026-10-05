"""Transparent business-impact / financial exposure estimation.

Every dollar figure here is `affected_records x assumption`, and the
assumptions are either explicit config defaults (0 = "unconfigured") or
values the user types into the UI. Nothing is invented. If assumptions are
left at 0, results are labeled as unconfigured rather than silently
displaying $0 as if it were a real measurement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from dqi_core.config import load_config
from dqi_core.models import Issue


@dataclass
class ExposureEstimate:
    issue_id: str
    affected_records: int
    estimated_exposure: float
    risk_category: str
    is_configured: bool
    assumptions: dict


def _risk_category(exposure: float, revenue_per_record: float, affected_records: int, total_rows: int) -> str:
    if total_rows == 0:
        return "Unknown"
    share = affected_records / total_rows
    if share >= 0.1 or exposure >= 10000:
        return "Critical"
    if share >= 0.03 or exposure >= 1000:
        return "High"
    if share >= 0.01 or exposure >= 100:
        return "Moderate"
    return "Low"


def estimate_exposure(issues: List[Issue], total_rows: int, revenue_per_record: float = 0.0,
                       operational_cost_per_record: float = 0.0) -> List[ExposureEstimate]:
    cfg = load_config()["business_impact"]
    factor_map = cfg["impact_factor_by_severity"]
    is_configured = revenue_per_record > 0 or operational_cost_per_record > 0
    per_record_value = revenue_per_record + operational_cost_per_record

    results = []
    for issue in issues:
        factor = factor_map.get(issue.severity, factor_map.get(str(issue.severity), 0.2))
        exposure = issue.affected_records * per_record_value * factor
        results.append(ExposureEstimate(
            issue_id=issue.issue_id, affected_records=issue.affected_records,
            estimated_exposure=round(exposure, 2),
            risk_category=_risk_category(exposure, per_record_value, issue.affected_records, total_rows),
            is_configured=is_configured,
            assumptions={
                "revenue_per_record": revenue_per_record,
                "operational_cost_per_record": operational_cost_per_record,
                "impact_factor": factor,
            },
        ))
    return results


def total_exposure(estimates: List[ExposureEstimate]) -> dict:
    total = sum(e.estimated_exposure for e in estimates)
    configured = any(e.is_configured for e in estimates)
    return {
        "total_estimated_exposure": round(total, 2),
        "is_configured": configured,
        "label": ("Estimated exposure based on configured business assumptions."
                   if configured else
                   "UNCONFIGURED: set revenue/operational cost per record to produce a real estimate; "
                   "this value is $0 because no assumption has been entered."),
    }
