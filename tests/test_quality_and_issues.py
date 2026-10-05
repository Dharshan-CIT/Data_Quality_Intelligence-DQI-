from dqi_core.profiling import profile_dataset
from dqi_core.issues.detection import detect_all_issues
from dqi_core.quality.pillars import assess_all_pillars


def test_detects_missing_values(messy_df):
    profile = profile_dataset(messy_df, "messy")
    issues = detect_all_issues(messy_df, profile)
    missing_issues = [i for i in issues if i.issue_type == "missing_values" and i.column == "price"]
    assert len(missing_issues) == 1
    assert missing_issues[0].affected_records == 2


def test_detects_duplicates(messy_df):
    profile = profile_dataset(messy_df, "messy")
    issues = detect_all_issues(messy_df, profile)
    dup_issues = [i for i in issues if i.issue_type == "duplicate_row"]
    assert len(dup_issues) == 1
    assert dup_issues[0].affected_records == 1


def test_detects_invalid_numeric_range(messy_df):
    profile = profile_dataset(messy_df, "messy")
    issues = detect_all_issues(messy_df, profile)
    neg = [i for i in issues if i.issue_type == "invalid_numeric_range" and i.column == "price"
           and "negative" in i.explanation.lower()]
    assert len(neg) == 1
    assert neg[0].affected_records == 1


def test_detects_categorical_inconsistency_minority_only(messy_df):
    profile = profile_dataset(messy_df, "messy")
    issues = detect_all_issues(messy_df, profile)
    inconsistent = [i for i in issues if i.issue_type == "formatting_inconsistency" and i.column == "category"]
    assert len(inconsistent) == 1
    # "A" group: {"A": 1, "a": 1, " A ": 1} -> dominant has count 1, so 2 minority rows.
    # "B" group: {"B": 2, "b": 1} -> dominant "B" has 2, minority = 1.
    # total minority-flagged = 2 + 1 = 3 (not the whole group).
    assert inconsistent[0].affected_records == 3


def test_pillar_scores_are_bounded(messy_df):
    profile = profile_dataset(messy_df, "messy")
    issues = detect_all_issues(messy_df, profile)
    pillars = assess_all_pillars(messy_df, profile, issues)
    assert len(pillars) == 10
    for name, result in pillars.items():
        assert 0 <= result.score <= 100
