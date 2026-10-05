import pandas as pd

from dqi_core.governance.contracts import validate_against_contract


CONTRACT = {
    "columns": {
        "id": {"type": "string", "nullable": False},
        "qty": {"type": "integer", "nullable": False, "min": 0, "max": 100},
        "status": {"type": "string", "nullable": True, "allowed_values": ["open", "closed"]},
    }
}


def test_valid_schema_passes():
    df = pd.DataFrame({"id": ["a", "b"], "qty": [1, 2], "status": ["open", "closed"]})
    result = validate_against_contract(df, CONTRACT, "test")
    assert result.passed
    assert result.deployment_status == "PASS"


def test_missing_required_column_blocks():
    df = pd.DataFrame({"qty": [1, 2], "status": ["open", "closed"]})
    result = validate_against_contract(df, CONTRACT, "test")
    assert not result.passed
    assert result.deployment_status == "BLOCKED"


def test_range_violation_detected():
    df = pd.DataFrame({"id": ["a", "b"], "qty": [1, 200], "status": ["open", "closed"]})
    result = validate_against_contract(df, CONTRACT, "test")
    range_violations = [v for v in result.violations if v.rule == "range_violation"]
    assert len(range_violations) == 1
    assert range_violations[0].affected_rows == 1


def test_invalid_category_detected():
    df = pd.DataFrame({"id": ["a", "b"], "qty": [1, 2], "status": ["open", "pending"]})
    result = validate_against_contract(df, CONTRACT, "test")
    cat_violations = [v for v in result.violations if v.rule == "invalid_category"]
    assert len(cat_violations) == 1
    assert cat_violations[0].affected_rows == 1
