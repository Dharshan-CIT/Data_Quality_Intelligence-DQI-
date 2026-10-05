import numpy as np
import pandas as pd

from dqi_core.remediation.engine import RemediationSession


def test_remove_duplicates_does_not_mutate_original():
    df = pd.DataFrame({"a": [1, 1, 2, 3]})
    session = RemediationSession(df)
    session.remove_duplicate_rows()
    assert len(session.original_df) == 4  # untouched
    assert len(session.current_df) == 3
    assert len(session.audit_trail) == 1
    assert session.audit_trail[0].rows_affected == 1


def test_handle_missing_constant_strategy():
    df = pd.DataFrame({"email": ["a@x.com", None, "b@x.com"]})
    session = RemediationSession(df)
    session.handle_missing("email", "constant", constant="unknown@example.com")
    assert session.current_df["email"].isna().sum() == 0
    assert session.audit_trail[0].rows_affected == 1


def test_handle_missing_mean_strategy():
    df = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0]})
    session = RemediationSession(df)
    session.handle_missing("x", "mean")
    assert session.current_df["x"].isna().sum() == 0
    assert abs(session.current_df["x"].iloc[2] - 7 / 3) < 1e-6


def test_handle_invalid_numeric_quarantine():
    df = pd.DataFrame({"qty": [1, -5, 3, -2]})
    session = RemediationSession(df)
    session.handle_invalid_numeric("qty", "negative", "quarantine")
    assert len(session.current_df) == 2
    assert len(session.quarantine_df) == 2
    assert (session.quarantine_df["qty"] < 0).all()


def test_handle_invalid_numeric_replace():
    df = pd.DataFrame({"price": [10.0, 0.0, 20.0, 0.0]})
    session = RemediationSession(df)
    session.handle_invalid_numeric("price", "zero", "replace", replacement=15.0)
    assert (session.current_df["price"] == 0.0).sum() == 0
    assert len(session.current_df) == 4  # no rows removed
