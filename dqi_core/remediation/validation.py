"""Post-remediation validation: before/after scores, counts, and a KS test
on numeric distributions to check remediation didn't distort the data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from scipy import stats as scipy_stats


@dataclass
class KSResult:
    column: str
    statistic: float
    p_value: float
    interpretation: str


@dataclass
class ValidationReport:
    rows_before: int
    rows_after: int
    missing_cells_before: int
    missing_cells_after: int
    health_before: float
    health_after: float
    issue_count_before: int
    issue_count_after: int
    ks_results: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rows_before": self.rows_before, "rows_after": self.rows_after,
            "missing_cells_before": self.missing_cells_before, "missing_cells_after": self.missing_cells_after,
            "health_before": self.health_before, "health_after": self.health_after,
            "issue_count_before": self.issue_count_before, "issue_count_after": self.issue_count_after,
            "ks_results": [r.__dict__ for r in self.ks_results],
        }


def _interpret_ks(p_value: float) -> str:
    if p_value > 0.05:
        return ("p > 0.05: no statistically significant difference detected between the before/after "
                "distributions — remediation did not distort this column's distribution.")
    return ("p <= 0.05: the before/after distributions differ significantly — review whether this "
            "remediation step changed the underlying signal, not just the defects.")


def run_ks_tests(before_df: pd.DataFrame, after_df: pd.DataFrame, numeric_columns: list) -> list:
    results = []
    for col in numeric_columns:
        if col not in before_df.columns or col not in after_df.columns:
            continue
        before = before_df[col].dropna()
        after = after_df[col].dropna()
        if len(before) < 2 or len(after) < 2:
            continue
        stat, p = scipy_stats.ks_2samp(before, after)
        results.append(KSResult(column=col, statistic=round(float(stat), 4), p_value=round(float(p), 4),
                                 interpretation=_interpret_ks(float(p))))
    return results


def build_validation_report(before_df: pd.DataFrame, after_df: pd.DataFrame,
                             health_before: float, health_after: float,
                             issue_count_before: int, issue_count_after: int,
                             numeric_columns: list) -> ValidationReport:
    return ValidationReport(
        rows_before=len(before_df), rows_after=len(after_df),
        missing_cells_before=int(before_df.isna().sum().sum()),
        missing_cells_after=int(after_df.isna().sum().sum()),
        health_before=health_before, health_after=health_after,
        issue_count_before=issue_count_before, issue_count_after=issue_count_after,
        ks_results=run_ks_tests(before_df, after_df, numeric_columns),
    )
