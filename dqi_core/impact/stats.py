"""Statistical validation of the frequency-vs-impact ranking comparison.

Computes Spearman's rank correlation and Kendall's Tau between the two
rankings produced by impact.ranking.build_rankings — never hard-coded,
always derived from the current dataset's actual rankings.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from scipy import stats as scipy_stats


@dataclass
class RankCorrelationResult:
    spearman_rs: float
    spearman_p: float
    kendall_tau: float
    kendall_p: float
    n: int
    interpretation: str


def _interpret(rs: float) -> str:
    abs_rs = abs(rs)
    if abs_rs >= 0.8:
        strength = "very strong"
    elif abs_rs >= 0.6:
        strength = "strong"
    elif abs_rs >= 0.4:
        strength = "moderate"
    elif abs_rs >= 0.2:
        strength = "weak"
    else:
        strength = "negligible"
    direction = "positive" if rs >= 0 else "negative"
    return (f"A {strength} {direction} correlation ({rs:.4f}) between frequency rank and impact rank. "
            f"The closer this is to 1.0, the more frequency-based prioritization would have matched "
            f"impact-aware prioritization; the lower it is, the more the two approaches disagree on "
            f"what to fix first — which is exactly the gap DQI is designed to surface.")


def compute_rank_correlation(ranking_df: pd.DataFrame) -> RankCorrelationResult:
    if ranking_df.empty or len(ranking_df) < 2:
        return RankCorrelationResult(
            spearman_rs=float("nan"), spearman_p=float("nan"),
            kendall_tau=float("nan"), kendall_p=float("nan"), n=len(ranking_df),
            interpretation="Fewer than 2 issues detected — rank correlation is not meaningful.",
        )
    freq_rank = ranking_df["frequency_rank"].to_numpy()
    impact_rank = ranking_df["impact_rank"].to_numpy()

    rs, p_s = scipy_stats.spearmanr(freq_rank, impact_rank)
    tau, p_k = scipy_stats.kendalltau(freq_rank, impact_rank)

    return RankCorrelationResult(
        spearman_rs=round(float(rs), 4), spearman_p=round(float(p_s), 4),
        kendall_tau=round(float(tau), 4), kendall_p=round(float(p_k), 4),
        n=len(ranking_df), interpretation=_interpret(float(rs)),
    )
