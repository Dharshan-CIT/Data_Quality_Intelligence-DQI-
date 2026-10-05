import pandas as pd

from dqi_core.governance.pii import detect_pii, tokenize_column


def test_detects_email_column():
    df = pd.DataFrame({"contact_email": [f"user{i}@example.com" for i in range(20)]})
    results = detect_pii(df)
    email_hits = [r for r in results if r.pattern == "email"]
    assert len(email_hits) == 1
    assert email_hits[0].match_count == 20


def test_does_not_flag_unrelated_numeric_column():
    df = pd.DataFrame({"amount": [1.0, 2.0, 3.5, 4.25] * 5})
    results = detect_pii(df)
    assert results == []


def test_tokenize_is_referentially_consistent():
    df = pd.DataFrame({"email": ["a@x.com", "b@x.com", "a@x.com"]})
    tokenized = tokenize_column(df, "email")
    assert tokenized["email"].iloc[0] == tokenized["email"].iloc[2]
    assert tokenized["email"].iloc[0] != tokenized["email"].iloc[1]
    assert tokenized["email"].iloc[0] != "a@x.com"
    assert len(tokenized["email"].iloc[0]) == 64  # sha256 hex digest length
