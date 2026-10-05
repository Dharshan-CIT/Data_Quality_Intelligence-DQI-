import pandas as pd

from dqi_core.models import Issue
from dqi_core.impact.scoring import score_issues
from dqi_core.impact.ranking import build_rankings
from dqi_core.impact.stats import compute_rank_correlation


def _make_issue(issue_id, column, affected, freq_pct, severity):
    return Issue(
        issue_id=issue_id, issue_type="test_issue", pillar="Validity", column=column,
        affected_records=affected, frequency_pct=freq_pct, severity=severity,
        explanation="test", recommended_action="test",
    )


def test_impact_score_bounded_0_100():
    issues = [
        _make_issue("I1", "price", 500, 50.0, 5),
        _make_issue("I2", "notes", 10, 1.0, 2),
    ]
    scored = score_issues(issues, total_rows=1000, critical_columns=["price"])
    for i in scored:
        assert 0 <= i.impact_score <= 100


def test_high_severity_critical_column_outranks_high_frequency_low_severity():
    # Issue A: low frequency but critical column + high severity.
    # Issue B: very high frequency but non-critical column + low severity.
    issue_a = _make_issue("A", "price", 20, 2.0, 5)
    issue_b = _make_issue("B", "notes", 800, 80.0, 1)
    scored = score_issues([issue_a, issue_b], total_rows=1000, critical_columns=["price"])
    a = next(i for i in scored if i.issue_id == "A")
    b = next(i for i in scored if i.issue_id == "B")
    assert a.impact_score > b.impact_score


def test_frequency_rank_differs_from_impact_rank():
    issue_a = _make_issue("A", "price", 20, 2.0, 5)
    issue_b = _make_issue("B", "notes", 800, 80.0, 1)
    scored = score_issues([issue_a, issue_b], total_rows=1000, critical_columns=["price"])
    ranking = build_rankings(scored)
    row_a = ranking[ranking.issue_id == "A"].iloc[0]
    row_b = ranking[ranking.issue_id == "B"].iloc[0]
    assert row_a.frequency_rank > row_b.frequency_rank  # A is less frequent
    assert row_a.impact_rank < row_b.impact_rank  # but A is higher impact
    assert row_a.rank_change > 0


def test_rank_correlation_perfect_agreement():
    issues = [_make_issue(f"I{i}", "col", 100 - i * 10, 100 - i * 10, 3) for i in range(5)]
    scored = score_issues(issues, total_rows=1000)
    ranking = build_rankings(scored)
    corr = compute_rank_correlation(ranking)
    assert corr.n == 5
    assert corr.spearman_rs == 1.0 or corr.spearman_rs > 0.9


def test_rank_correlation_handles_small_input():
    ranking = build_rankings([])
    corr = compute_rank_correlation(ranking)
    assert corr.n == 0
