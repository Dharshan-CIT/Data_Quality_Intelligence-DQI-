"""Builds the two rankings DQI exists to compare: frequency-based vs impact-aware."""
from __future__ import annotations

from typing import List

import pandas as pd

from dqi_core.models import Issue


def build_rankings(issues: List[Issue]) -> pd.DataFrame:
    """Returns a DataFrame with both rankings and the rank movement between them.
    Assumes `score_issues` has already populated `impact_score` on each issue."""
    if not issues:
        return pd.DataFrame(columns=[
            "issue_id", "issue_type", "column", "affected_records", "frequency_pct",
            "severity", "downstream_sensitivity", "business_exposure", "impact_score",
            "frequency_rank", "impact_rank", "rank_change",
        ])

    rows = [i.to_dict() for i in issues]
    df = pd.DataFrame(rows)

    df["frequency_rank"] = df["affected_records"].rank(ascending=False, method="min").astype(int)
    df["impact_rank"] = df["impact_score"].rank(ascending=False, method="min").astype(int)
    df["rank_change"] = df["frequency_rank"] - df["impact_rank"]

    df = df.sort_values("impact_rank").reset_index(drop=True)
    cols = ["issue_id", "issue_type", "pillar", "column", "affected_records", "frequency_pct",
            "severity", "downstream_sensitivity", "business_exposure", "impact_score",
            "frequency_rank", "impact_rank", "rank_change", "explanation", "recommended_action"]
    return df[[c for c in cols if c in df.columns]]
