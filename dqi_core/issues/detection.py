"""Rule-based quality issue detection.

Every detector takes (df, profile) and returns a list of dqi_core.models.Issue.
Detectors are intentionally independent functions so new ones can be added
without touching existing logic. `detect_all_issues` is the single entry
point the rest of the application calls.

Severity values (1-5) and the "appears non-negative" / "appears monetary"
column-name heuristics are documented, editable assumptions — see
configs/weights.yaml and docs/METHODOLOGY.md. They are heuristics, not
ground truth, and are labeled as such in each issue's explanation.
"""
from __future__ import annotations

import itertools
import re
from datetime import datetime, timezone
from typing import List

import numpy as np
import pandas as pd

from dqi_core.models import Issue

_id_counter = itertools.count(1)

_NONNEGATIVE_NAME_RE = re.compile(
    r"(price|quantity|qty|amount|cost|revenue|age|count|total|balance|weight|duration|score)",
    re.IGNORECASE,
)
_MISSING_MIN_PCT = 1.0  # don't flag noise below this threshold
_FUTURE_DATE_NAME_RE = re.compile(r"(birth|dob|order_date|created|placed|submitted|signed)", re.IGNORECASE)
_STALE_NAME_RE = re.compile(r"(updated|last_|modified|sync|refresh)", re.IGNORECASE)


def _new_id() -> str:
    return f"ISSUE-{next(_id_counter):05d}"


def _pct(count: int, n: int) -> float:
    return round(100 * count / n, 4) if n else 0.0


def detect_missing_values(df: pd.DataFrame, profile) -> List[Issue]:
    issues = []
    n = len(df)
    for col, cp in profile.column_profiles.items():
        if cp.null_pct <= _MISSING_MIN_PCT:
            continue
        severity = 4 if cp.null_pct > 50 else 3 if cp.null_pct > 20 else 2
        issues.append(Issue(
            issue_id=_new_id(), issue_type="missing_values", pillar="Completeness", column=col,
            affected_records=cp.null_count, frequency_pct=cp.null_pct, severity=severity,
            explanation=f"Column '{col}' has {cp.null_count} missing values ({cp.null_pct}% of {n} rows).",
            recommended_action="Impute (mean/median/mode) or drop rows depending on criticality; "
                                "investigate upstream collection gap.",
            evidence={"null_count": cp.null_count, "null_pct": cp.null_pct},
        ))
    return issues


def detect_duplicate_rows(df: pd.DataFrame, profile) -> List[Issue]:
    n = len(df)
    dup = profile.duplicate_rows
    if dup == 0:
        return []
    return [Issue(
        issue_id=_new_id(), issue_type="duplicate_row", pillar="Uniqueness", column=None,
        affected_records=dup, frequency_pct=_pct(dup, n), severity=2,
        explanation=f"{dup} fully duplicated rows found ({_pct(dup, n)}% of {n} rows).",
        recommended_action="Remove exact duplicates, keeping the first (or most recent) occurrence.",
        evidence={"duplicate_rows": dup},
    )]


def detect_duplicate_identifiers(df: pd.DataFrame, profile) -> List[Issue]:
    issues = []
    n = len(df)
    for col in profile.identifier_columns:
        s = df[col].dropna()
        dup_mask = s.duplicated(keep=False)
        dup_count = int(dup_mask.sum())
        if dup_count == 0:
            continue
        issues.append(Issue(
            issue_id=_new_id(), issue_type="duplicate_primary_key", pillar="Uniqueness", column=col,
            affected_records=dup_count, frequency_pct=_pct(dup_count, n), severity=5,
            explanation=f"Identifier column '{col}' has {dup_count} rows sharing a non-unique value "
                        f"({s[dup_mask].nunique()} distinct values repeated).",
            recommended_action="Investigate upstream key-generation logic; deduplicate or re-key affected records.",
            evidence={"duplicate_key_rows": dup_count},
        ))
    return issues


def detect_invalid_numeric_ranges(df: pd.DataFrame, profile) -> List[Issue]:
    issues = []
    n = len(df)
    for col in profile.numeric_columns:
        if not _NONNEGATIVE_NAME_RE.search(col):
            continue
        s = df[col].dropna()
        if s.empty:
            continue
        negative = s < 0
        neg_count = int(negative.sum())
        if neg_count > 0:
            issues.append(Issue(
                issue_id=_new_id(), issue_type="invalid_numeric_range", pillar="Validity", column=col,
                affected_records=neg_count, frequency_pct=_pct(neg_count, n), severity=4,
                explanation=f"Column '{col}' (name suggests it should be non-negative) has {neg_count} "
                            f"negative values ({_pct(neg_count, n)}% of {n} rows).",
                recommended_action="Quarantine or correct negative values at the source; "
                                    "validate upstream input constraints.",
                evidence={"negative_count": neg_count},
            ))
        if re.search(r"(price|cost|amount)", col, re.IGNORECASE):
            zero_count = int((s == 0).sum())
            if zero_count > 0:
                issues.append(Issue(
                    issue_id=_new_id(), issue_type="invalid_numeric_range", pillar="Validity", column=col,
                    affected_records=zero_count, frequency_pct=_pct(zero_count, n), severity=3,
                    explanation=f"Column '{col}' has {zero_count} non-positive (zero) values, "
                                f"which is unusual for a price/cost/amount field.",
                    recommended_action="Confirm whether zero is a legitimate value (e.g. free item) "
                                        "or a data entry defect.",
                    evidence={"zero_count": zero_count},
                ))
    return issues


def detect_outliers(df: pd.DataFrame, profile) -> List[Issue]:
    issues = []
    n = len(df)
    for col in profile.numeric_columns:
        cp = profile.column_profiles[col]
        if not cp.outlier_count:
            continue
        issues.append(Issue(
            issue_id=_new_id(), issue_type="outlier_extreme", pillar="Accuracy", column=col,
            affected_records=cp.outlier_count, frequency_pct=_pct(cp.outlier_count, n), severity=3,
            explanation=f"Column '{col}' has {cp.outlier_count} values outside 1.5x IQR "
                        f"(Q1={cp.q1}, Q3={cp.q3}).",
            recommended_action="Review extreme values for sensor/entry errors; consider winsorizing or flagging.",
            evidence={"outlier_count": cp.outlier_count, "q1": cp.q1, "q3": cp.q3},
        ))
    return issues


def detect_categorical_inconsistency(df: pd.DataFrame, profile) -> List[Issue]:
    """Flags only the MINORITY variant rows within each normalized group — the
    dominant spelling is treated as canonical and not counted as affected, so
    the issue reflects how many records actually need correcting, not the
    whole group they happen to belong to."""
    issues = []
    n = len(df)
    for col in profile.categorical_columns:
        s = df[col].dropna().astype(str)
        if s.empty:
            continue
        normalized = s.str.strip().str.lower()
        example_variants = None
        example_norm = None
        group_count = 0
        affected = 0
        for norm_val, group in s.groupby(normalized):
            variant_counts = group.value_counts()
            if len(variant_counts) <= 1:
                continue
            group_count += 1
            minority_count = int(variant_counts.iloc[1:].sum())
            affected += minority_count
            if example_variants is None:
                example_variants = sorted(variant_counts.index.tolist())
                example_norm = norm_val
        if group_count == 0 or affected == 0:
            continue
        issues.append(Issue(
            issue_id=_new_id(), issue_type="formatting_inconsistency", pillar="Consistency", column=col,
            affected_records=affected, frequency_pct=_pct(affected, n), severity=2,
            explanation=f"Column '{col}' has {group_count} label group(s) with inconsistent "
                        f"casing/whitespace; {affected} record(s) use a non-canonical spelling, "
                        f"e.g. {example_variants}.",
            recommended_action="Normalize categorical labels (trim, consistent case) at ingestion.",
            evidence={"inconsistent_group_count": group_count,
                      "example_normalized": example_norm, "example_variants": example_variants},
        ))
    return issues


def detect_type_conformity(df: pd.DataFrame, profile) -> List[Issue]:
    """Flag text/categorical columns that look like they should be numeric but aren't fully parseable."""
    issues = []
    n = len(df)
    for col, cp in profile.column_profiles.items():
        if cp.inferred_type not in ("categorical", "text"):
            continue
        s = df[col].dropna().astype(str).str.strip()
        if s.empty:
            continue
        coerced = pd.to_numeric(s, errors="coerce")
        parse_rate = coerced.notna().mean()
        if 0.5 <= parse_rate < 0.99:
            bad_count = int(coerced.isna().sum())
            issues.append(Issue(
                issue_id=_new_id(), issue_type="schema_violation", pillar="Conformity", column=col,
                affected_records=bad_count, frequency_pct=_pct(bad_count, n), severity=4,
                explanation=f"Column '{col}' parses as numeric for {round(parse_rate*100,1)}% of non-null "
                            f"values, suggesting {bad_count} values violate the column's expected type.",
                recommended_action="Enforce a type/format constraint in the ingestion schema or data contract.",
                evidence={"parse_rate": round(parse_rate, 4), "non_numeric_count": bad_count},
            ))
    return issues


def detect_temporal_issues(df: pd.DataFrame, profile) -> List[Issue]:
    issues = []
    n = len(df)
    now = pd.Timestamp.now(tz=None)
    for col in profile.datetime_columns:
        parsed = pd.to_datetime(df[col], errors="coerce")
        invalid_mask = parsed.isna() & df[col].notna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            issues.append(Issue(
                issue_id=_new_id(), issue_type="invalid_date", pillar="Validity", column=col,
                affected_records=invalid_count, frequency_pct=_pct(invalid_count, n), severity=4,
                explanation=f"Column '{col}' has {invalid_count} values that could not be parsed as dates.",
                recommended_action="Standardize date format at the source; quarantine unparseable records.",
                evidence={"unparseable_count": invalid_count},
            ))
        if _FUTURE_DATE_NAME_RE.search(col):
            try:
                future_mask = parsed.dropna() > now
                future_count = int(future_mask.sum())
            except TypeError:
                future_count = 0
            if future_count > 0:
                issues.append(Issue(
                    issue_id=_new_id(), issue_type="future_date", pillar="Validity", column=col,
                    affected_records=future_count, frequency_pct=_pct(future_count, n), severity=3,
                    explanation=f"Column '{col}' (name suggests a past-only event) has {future_count} "
                                f"dates in the future relative to now ({now.date()}).",
                    recommended_action="Validate date entry at capture time; investigate clock/timezone issues.",
                    evidence={"future_count": future_count},
                ))
        if _STALE_NAME_RE.search(col):
            valid = parsed.dropna()
            if len(valid) > 0:
                stale_cutoff = now - pd.Timedelta(days=180)
                stale_count = int((valid < stale_cutoff).sum())
                if stale_count > 0:
                    issues.append(Issue(
                        issue_id=_new_id(), issue_type="stale_record", pillar="Freshness", column=col,
                        affected_records=stale_count, frequency_pct=_pct(stale_count, n), severity=3,
                        explanation=f"Column '{col}' has {stale_count} records last touched more than "
                                    f"180 days ago.",
                        recommended_action="Review stale records for re-sync or archival; confirm "
                                            "freshness SLA with data owner.",
                        evidence={"stale_count": stale_count, "cutoff_days": 180},
                    ))
    return issues


DETECTORS = [
    detect_missing_values,
    detect_duplicate_rows,
    detect_duplicate_identifiers,
    detect_invalid_numeric_ranges,
    detect_outliers,
    detect_categorical_inconsistency,
    detect_type_conformity,
    detect_temporal_issues,
]


def detect_all_issues(df: pd.DataFrame, profile) -> List[Issue]:
    issues: List[Issue] = []
    for detector in DETECTORS:
        try:
            issues.extend(detector(df, profile))
        except Exception as e:  # a single detector failing must not take down the whole scan
            issues.append(Issue(
                issue_id=_new_id(), issue_type="detector_error", pillar="N/A", column=None,
                affected_records=0, frequency_pct=0.0, severity=1,
                explanation=f"Detector '{detector.__name__}' raised an error and was skipped: {e}",
                recommended_action="Report this as a bug; results from other detectors remain valid.",
                evidence={"detector": detector.__name__},
            ))
    return issues
