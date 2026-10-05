"""The 10-pillar data quality model.

Each pillar returns a 0-100 score plus the evidence behind it. Several
pillars (Timeliness, Accuracy, Integrity, Traceability) cannot be measured
with full certainty from a single flat file with no ground truth or related
tables — for those we compute a transparent, documented proxy and set
`limitation` on the result instead of silently presenting it as a direct
measurement. See docs/METHODOLOGY.md for the exact formulas.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from dqi_core.models import PillarResult

_TRACE_NAME_HINTS = ("created_at", "updated_at", "created_by", "updated_by",
                     "source", "source_system", "record_id", "id", "audit")


def _severity_label(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 55:
        return "Needs Attention"
    if score >= 35:
        return "Poor"
    return "Critical"


def _issues_for_pillar(issues, pillar_name):
    return [i for i in issues if i.pillar == pillar_name]


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def _weighted_deduction(pillar_issues, denom: int) -> float:
    """Deduct severity-weighted frequency from 100. Each issue's contribution
    is capped so one extreme issue cannot swing the whole pillar to zero."""
    if denom <= 0:
        return 100.0
    deduction = 0.0
    for issue in pillar_issues:
        weight = issue.severity / 5.0
        contribution = min(40.0, weight * issue.frequency_pct)
        deduction += contribution
    return _clamp(100.0 - deduction)


def assess_completeness(df, profile, issues) -> PillarResult:
    pillar_issues = _issues_for_pillar(issues, "Completeness")
    score = _clamp(100.0 - profile.missing_pct * 1.5)
    affected_cols = [c for c, cp in profile.column_profiles.items() if cp.null_pct > 0]
    return PillarResult(
        name="Completeness", score=round(score, 2), affected_records=profile.missing_cells,
        affected_columns=affected_cols,
        explanation=f"{profile.missing_cells} missing cells across {len(affected_cols)} column(s) "
                    f"({profile.missing_pct}% of all cells).",
        detected_issues=[i.issue_id for i in pillar_issues], severity=_severity_label(score),
        recommendations=["Impute or drop based on criticality.", "Enforce NOT NULL at ingestion for critical fields."],
    )


def assess_uniqueness(df, profile, issues) -> PillarResult:
    pillar_issues = _issues_for_pillar(issues, "Uniqueness")
    n = len(df)
    dup_total = sum(i.affected_records for i in pillar_issues)
    score = _weighted_deduction(pillar_issues, n)
    affected_cols = sorted({i.column for i in pillar_issues if i.column})
    return PillarResult(
        name="Uniqueness", score=round(score, 2), affected_records=dup_total, affected_columns=affected_cols,
        explanation=f"{profile.duplicate_rows} duplicate row(s); "
                    f"{len(profile.identifier_columns)} identifier column(s) checked for duplicate keys.",
        detected_issues=[i.issue_id for i in pillar_issues], severity=_severity_label(score),
        recommendations=["Deduplicate exact row duplicates.", "Enforce primary-key uniqueness constraints."],
    )


def assess_validity(df, profile, issues) -> PillarResult:
    pillar_issues = _issues_for_pillar(issues, "Validity")
    n = len(df)
    score = _weighted_deduction(pillar_issues, n)
    affected_cols = sorted({i.column for i in pillar_issues if i.column})
    affected = sum(i.affected_records for i in pillar_issues)
    return PillarResult(
        name="Validity", score=round(score, 2), affected_records=affected, affected_columns=affected_cols,
        explanation=f"{len(pillar_issues)} validity rule violation group(s) detected "
                    f"(out-of-range numerics, unparseable dates, future dates).",
        detected_issues=[i.issue_id for i in pillar_issues], severity=_severity_label(score),
        recommendations=["Apply range/format checks at ingestion.", "Quarantine records failing validity rules."],
    )


def assess_consistency(df, profile, issues) -> PillarResult:
    pillar_issues = _issues_for_pillar(issues, "Consistency")
    n = len(df)
    score = _weighted_deduction(pillar_issues, n)
    affected_cols = sorted({i.column for i in pillar_issues if i.column})
    affected = sum(i.affected_records for i in pillar_issues)
    return PillarResult(
        name="Consistency", score=round(score, 2), affected_records=affected, affected_columns=affected_cols,
        explanation=f"{len(pillar_issues)} column(s) have inconsistent label formatting "
                    f"(casing/whitespace variants of the same value).",
        detected_issues=[i.issue_id for i in pillar_issues], severity=_severity_label(score),
        recommendations=["Normalize categorical values (trim + case-fold) during ingestion."],
    )


def assess_conformity(df, profile, issues) -> PillarResult:
    pillar_issues = _issues_for_pillar(issues, "Conformity")
    n = len(df)
    score = _weighted_deduction(pillar_issues, n)
    affected_cols = sorted({i.column for i in pillar_issues if i.column})
    affected = sum(i.affected_records for i in pillar_issues)
    return PillarResult(
        name="Conformity", score=round(score, 2), affected_records=affected, affected_columns=affected_cols,
        explanation=f"{len(pillar_issues)} column(s) show values that don't conform to the "
                    f"column's inferred type/format.",
        detected_issues=[i.issue_id for i in pillar_issues], severity=_severity_label(score),
        recommendations=["Define and enforce a formal schema/data contract (see Governance)."],
    )


def assess_timeliness(df, profile, issues) -> PillarResult:
    pillar_issues = [i for i in issues if i.issue_type == "future_date"]
    n = len(df)
    score = _weighted_deduction(pillar_issues, n) if profile.datetime_columns else 100.0
    limitation = None
    if not profile.datetime_columns:
        limitation = ("No datetime columns detected. Timeliness cannot be measured directly; "
                       "defaulting to a neutral 100 rather than inventing a result.")
    return PillarResult(
        name="Timeliness", score=round(score, 2),
        affected_records=sum(i.affected_records for i in pillar_issues),
        affected_columns=sorted({i.column for i in pillar_issues if i.column}),
        explanation="Proxy measure: fraction of date values that fall outside an expected "
                    "(non-future) time window." if profile.datetime_columns else "No temporal columns to assess.",
        detected_issues=[i.issue_id for i in pillar_issues], severity=_severity_label(score),
        recommendations=["Capture event timestamps with timezone discipline to enable true timeliness SLAs."],
        limitation=limitation,
    )


def assess_accuracy(df, profile, issues) -> PillarResult:
    pillar_issues = _issues_for_pillar(issues, "Accuracy")
    n = len(df)
    score = _weighted_deduction(pillar_issues, n)
    return PillarResult(
        name="Accuracy", score=round(score, 2),
        affected_records=sum(i.affected_records for i in pillar_issues),
        affected_columns=sorted({i.column for i in pillar_issues if i.column}),
        explanation="Proxy measure based on statistical outlier rate (1.5x IQR). True accuracy "
                    "requires a ground-truth reference this dataset alone cannot provide.",
        detected_issues=[i.issue_id for i in pillar_issues], severity=_severity_label(score),
        recommendations=["Cross-check against a trusted source-of-truth where available."],
        limitation="Outlier rate is a proxy for accuracy, not a direct measurement against ground truth.",
    )


def assess_integrity(df, profile, issues) -> PillarResult:
    pk_issues = [i for i in issues if i.issue_type == "duplicate_primary_key"]
    n = len(df)
    score = _weighted_deduction(pk_issues, n) if profile.identifier_columns else 100.0
    limitation = ("No cross-table relationships are available in a single-file upload, so only "
                   "key-uniqueness (a necessary condition for referential integrity) is checked here.")
    return PillarResult(
        name="Integrity", score=round(score, 2),
        affected_records=sum(i.affected_records for i in pk_issues), affected_columns=profile.identifier_columns,
        explanation="Proxy measure: uniqueness of identifier/key columns.",
        detected_issues=[i.issue_id for i in pk_issues], severity=_severity_label(score),
        recommendations=["Validate foreign keys against related tables once a multi-table workspace is available."],
        limitation=limitation,
    )


def assess_freshness(df, profile, issues) -> PillarResult:
    pillar_issues = [i for i in issues if i.issue_type == "stale_record"]
    n = len(df)
    has_freshness_cols = any(i.issue_type == "stale_record" for i in issues) or len(profile.datetime_columns) > 0
    score = _weighted_deduction(pillar_issues, n) if pillar_issues else 100.0
    limitation = None
    if not profile.datetime_columns:
        limitation = "No datetime columns detected; freshness defaulted to 100 rather than inventing a result."
    return PillarResult(
        name="Freshness", score=round(score, 2),
        affected_records=sum(i.affected_records for i in pillar_issues),
        affected_columns=sorted({i.column for i in pillar_issues if i.column}),
        explanation="Share of records whose last-touched timestamp is older than a 180-day threshold.",
        detected_issues=[i.issue_id for i in pillar_issues], severity=_severity_label(score),
        recommendations=["Define a freshness SLA per dataset and alert when breached."],
        limitation=limitation,
    )


def assess_traceability(df, profile, issues) -> PillarResult:
    cols_lower = {c.lower() for c in df.columns}
    hints_present = [h for h in _TRACE_NAME_HINTS if any(h in c for c in cols_lower)]
    score = _clamp(100.0 * len(hints_present) / len(_TRACE_NAME_HINTS) * 2.2)  # scale since few hints needed
    score = min(score, 100.0)
    return PillarResult(
        name="Traceability", score=round(score, 2), affected_records=0,
        affected_columns=[c for c in df.columns if any(h in c.lower() for h in hints_present)],
        explanation=f"{len(hints_present)}/{len(_TRACE_NAME_HINTS)} audit-friendly column patterns "
                    f"found (e.g. id, created_at, source).",
        detected_issues=[], severity=_severity_label(score),
        recommendations=["Add created_at/updated_at/source_system columns to support lineage tracing."],
        limitation="Structural proxy based on column naming, not a check of actual lineage metadata.",
    )


PILLAR_FUNCTIONS = [
    assess_completeness, assess_uniqueness, assess_validity, assess_consistency,
    assess_timeliness, assess_accuracy, assess_integrity, assess_conformity,
    assess_freshness, assess_traceability,
]


def assess_all_pillars(df: pd.DataFrame, profile, issues) -> dict:
    return {fn.__name__.replace("assess_", ""): fn(df, profile, issues) for fn in PILLAR_FUNCTIONS}
