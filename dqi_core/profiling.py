"""Dataset- and column-level profiling engine.

Pure pandas/numpy, no UI dependency. Returns structured dqi_core.models
objects consumed by the quality, issue-detection and reporting layers.
"""
from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd

from dqi_core.models import ColumnProfile, DatasetProfile

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ID_NAME_RE = re.compile(r"(^id$|_id$|^id_|uuid|guid)", re.IGNORECASE)


def _infer_type(series: pd.Series, name: str) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "identifier" if _ID_NAME_RE.search(name) else "numeric"
    non_null = series.dropna().astype(str)
    if len(non_null) == 0:
        return "text"
    # Try datetime coercion on a sample.
    sample = non_null.sample(min(50, len(non_null)), random_state=0)
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(sample, errors="coerce")
        if parsed.notna().mean() > 0.85:
            return "datetime"
    except Exception:
        pass
    uniq_ratio = series.nunique(dropna=True) / max(len(non_null), 1)
    if _ID_NAME_RE.search(name) and uniq_ratio > 0.9:
        return "identifier"
    if uniq_ratio <= 0.5 or series.nunique(dropna=True) <= 50:
        return "categorical"
    return "text"


def _cardinality_bucket(unique_count: int, n: int) -> str:
    if n == 0:
        return "low"
    ratio = unique_count / n
    if ratio >= 0.98:
        return "unique"
    if ratio >= 0.5:
        return "high"
    if ratio >= 0.05:
        return "medium"
    return "low"


def _outlier_count(series: pd.Series) -> Optional[int]:
    s = series.dropna()
    if len(s) < 5:
        return None
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return int(((s < q1) | (s > q3)).sum())
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((s < lower) | (s > upper)).sum())


def profile_column(series: pd.Series, name: str) -> ColumnProfile:
    n = len(series)
    null_count = int(series.isna().sum())
    null_pct = round(100 * null_count / n, 4) if n else 0.0
    unique_count = int(series.nunique(dropna=True))
    uniqueness_ratio = round(unique_count / n, 4) if n else 0.0
    inferred = _infer_type(series, name)
    cardinality = _cardinality_bucket(unique_count, n)

    profile_kwargs = dict(
        name=name,
        dtype=str(series.dtype),
        inferred_type=inferred,
        null_count=null_count,
        null_pct=null_pct,
        unique_count=unique_count,
        uniqueness_ratio=uniqueness_ratio,
        cardinality=cardinality,
    )

    if inferred in ("numeric", "identifier") and pd.api.types.is_numeric_dtype(series):
        s = series.dropna()
        if len(s):
            profile_kwargs.update(
                min=float(s.min()),
                max=float(s.max()),
                mean=round(float(s.mean()), 6),
                median=round(float(s.median()), 6),
                std=round(float(s.std()), 6) if len(s) > 1 else 0.0,
                q1=round(float(s.quantile(0.25)), 6),
                q3=round(float(s.quantile(0.75)), 6),
                outlier_count=_outlier_count(s),
            )
    elif inferred == "datetime":
        parsed = pd.to_datetime(series, errors="coerce")
        s = parsed.dropna()
        if len(s):
            profile_kwargs.update(min=str(s.min()), max=str(s.max()))
    elif inferred == "categorical":
        vc = series.value_counts(dropna=True).head(5)
        profile_kwargs["top_values"] = {str(k): int(v) for k, v in vc.items()}

    if inferred == "categorical" or inferred == "text":
        non_null = series.dropna().astype(str)
        suspicious = non_null.str.strip().eq("") | non_null.str.lower().isin(
            {"null", "n/a", "na", "none", "?", "-", "unknown"}
        )
        profile_kwargs["suspicious_value_count"] = int(suspicious.sum())

    return ColumnProfile(**profile_kwargs)


def profile_dataset(df: pd.DataFrame, filename: str = "dataset") -> DatasetProfile:
    rows, cols = df.shape
    memory_bytes = int(df.memory_usage(deep=True).sum())
    duplicate_rows = int(df.duplicated().sum())
    missing_cells = int(df.isna().sum().sum())
    missing_pct = round(100 * missing_cells / (rows * cols), 4) if rows * cols else 0.0

    column_profiles = {}
    numeric_cols, categorical_cols, datetime_cols, boolean_cols, identifier_cols = [], [], [], [], []

    for col in df.columns:
        cp = profile_column(df[col], col)
        column_profiles[col] = cp
        bucket = {
            "numeric": numeric_cols,
            "categorical": categorical_cols,
            "datetime": datetime_cols,
            "boolean": boolean_cols,
            "identifier": identifier_cols,
            "text": categorical_cols,
        }.get(cp.inferred_type)
        if bucket is not None:
            bucket.append(col)

    return DatasetProfile(
        filename=filename,
        rows=rows,
        columns=cols,
        memory_bytes=memory_bytes,
        duplicate_rows=duplicate_rows,
        missing_cells=missing_cells,
        missing_pct=missing_pct,
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        datetime_columns=datetime_cols,
        boolean_columns=boolean_cols,
        identifier_columns=identifier_cols,
        column_profiles=column_profiles,
    )
