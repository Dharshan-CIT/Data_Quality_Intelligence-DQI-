"""Governed remediation engine.

Operates on a copy of the uploaded data; the original dataframe is never
mutated. Every operation appends a RemediationAction audit record with
before/after summaries. Records that cannot be safely repaired go to a
separate quarantine dataframe rather than being silently dropped.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from dqi_core.models import RemediationAction


class RemediationSession:
    def __init__(self, original_df: pd.DataFrame):
        self.original_df = original_df.copy(deep=True)
        self.current_df = original_df.copy(deep=True)
        self.quarantine_df = original_df.iloc[0:0].copy(deep=True)
        self.audit_trail: List[RemediationAction] = []

    def _record(self, operation: str, column: Optional[str], rows_affected: int,
                reason: str, before_summary: dict, after_summary: dict):
        action = RemediationAction(
            operation=operation, column=column, rows_affected=rows_affected, reason=reason,
            before_summary=before_summary, after_summary=after_summary,
        )
        self.audit_trail.append(action)
        return action

    def remove_duplicate_rows(self, reason: str = "Exact duplicate rows removed.") -> RemediationAction:
        before = len(self.current_df)
        dup_mask = self.current_df.duplicated(keep="first")
        removed = int(dup_mask.sum())
        self.current_df = self.current_df.loc[~dup_mask].reset_index(drop=True)
        return self._record("remove_duplicates", None, removed, reason,
                             {"row_count": before}, {"row_count": len(self.current_df)})

    def handle_missing(self, column: str, strategy: str, constant=None,
                        reason: str = "") -> RemediationAction:
        """strategy in {drop, mean, median, mode, constant, ffill}"""
        s = self.current_df[column]
        before_nulls = int(s.isna().sum())
        before_summary = {"null_count": before_nulls}

        if strategy == "drop":
            mask = s.isna()
            self.current_df = self.current_df.loc[~mask].reset_index(drop=True)
            rows_affected = before_nulls
        elif strategy == "mean":
            fill_value = s.mean()
            self.current_df[column] = s.fillna(fill_value)
            rows_affected = before_nulls
        elif strategy == "median":
            fill_value = s.median()
            self.current_df[column] = s.fillna(fill_value)
            rows_affected = before_nulls
        elif strategy == "mode":
            mode_vals = s.mode(dropna=True)
            fill_value = mode_vals.iloc[0] if not mode_vals.empty else None
            self.current_df[column] = s.fillna(fill_value)
            rows_affected = before_nulls
        elif strategy == "constant":
            self.current_df[column] = s.fillna(constant)
            rows_affected = before_nulls
        elif strategy == "ffill":
            self.current_df[column] = s.ffill()
            rows_affected = before_nulls
        else:
            raise ValueError(f"Unknown missing-value strategy: {strategy}")

        after_nulls = int(self.current_df[column].isna().sum())
        return self._record("handle_missing", column, rows_affected,
                             reason or f"Applied '{strategy}' strategy to missing values.",
                             before_summary, {"null_count": after_nulls})

    def handle_invalid_numeric(self, column: str, condition: str, strategy: str,
                                replacement: Optional[float] = None, reason: str = "") -> RemediationAction:
        """condition in {negative, zero}; strategy in {replace, remove, quarantine}"""
        s = self.current_df[column]
        if condition == "negative":
            mask = s < 0
        elif condition == "zero":
            mask = s == 0
        else:
            raise ValueError(f"Unknown condition: {condition}")

        affected = int(mask.sum())
        before_summary = {"affected_count": affected, "mean": float(s.mean()) if len(s) else None}

        if strategy == "replace":
            self.current_df.loc[mask, column] = replacement if replacement is not None else s[~mask].median()
        elif strategy == "remove":
            self.current_df = self.current_df.loc[~mask].reset_index(drop=True)
        elif strategy == "quarantine":
            self.quarantine_df = pd.concat([self.quarantine_df, self.current_df.loc[mask]], ignore_index=True)
            self.current_df = self.current_df.loc[~mask].reset_index(drop=True)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        after_series = self.current_df[column]
        after_summary = {"mean": float(after_series.mean()) if len(after_series) else None}
        return self._record("handle_invalid_numeric", column, affected,
                             reason or f"{strategy} applied to {condition} values.",
                             before_summary, after_summary)

    def normalize_formatting(self, column: str, reason: str = "Trimmed whitespace and normalized case.") -> RemediationAction:
        s = self.current_df[column].astype(str)
        before_unique = int(s.nunique())
        normalized = s.str.strip()
        # Title-case categorical text for a consistent display form; preserve original casing intent
        # only when values look like free text rather than short labels (heuristic: avg length).
        if normalized.str.len().mean() <= 30:
            normalized = normalized.str.strip().str.lower().str.title()
        changed = int((normalized != s).sum())
        self.current_df[column] = normalized
        after_unique = int(normalized.nunique())
        return self._record("normalize_formatting", column, changed, reason,
                             {"unique_count": before_unique}, {"unique_count": after_unique})

    def normalize_dates(self, column: str, reason: str = "Parsed and standardized to ISO 8601.") -> RemediationAction:
        s = self.current_df[column]
        before_invalid = int(pd.to_datetime(s, errors="coerce").isna().sum() - s.isna().sum())
        parsed = pd.to_datetime(s, errors="coerce")
        changed = int((parsed.notna() & s.notna()).sum())
        self.current_df[column] = parsed.dt.strftime("%Y-%m-%d")
        after_invalid = int(self.current_df[column].isna().sum() - s.isna().sum())
        return self._record("normalize_dates", column, changed, reason,
                             {"unparseable": before_invalid}, {"unparseable": after_invalid})
