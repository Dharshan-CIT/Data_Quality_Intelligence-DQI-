import numpy as np
import pandas as pd

from dqi_core.remediation.validation import run_ks_tests, build_validation_report


def test_ks_test_identical_distributions_high_p():
    rng = np.random.default_rng(0)
    data = rng.normal(0, 1, size=500)
    before = pd.DataFrame({"x": data})
    after = pd.DataFrame({"x": data.copy()})
    results = run_ks_tests(before, after, ["x"])
    assert len(results) == 1
    assert results[0].p_value > 0.05


def test_ks_test_shifted_distribution_low_p():
    rng = np.random.default_rng(0)
    before = pd.DataFrame({"x": rng.normal(0, 1, size=500)})
    after = pd.DataFrame({"x": rng.normal(5, 1, size=500)})
    results = run_ks_tests(before, after, ["x"])
    assert results[0].p_value < 0.05


def test_validation_report_counts_rows_and_missing():
    before = pd.DataFrame({"x": [1.0, None, 3.0]})
    after = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    report = build_validation_report(before, after, 70.0, 85.0, 3, 1, ["x"])
    assert report.rows_before == 3
    assert report.missing_cells_before == 1
    assert report.missing_cells_after == 0
    assert report.health_after > report.health_before
