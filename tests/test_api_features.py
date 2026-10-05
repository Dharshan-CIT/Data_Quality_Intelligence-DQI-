"""Regression tests for the drift timeline, pillar re-weighting, row inspector and shareable reports."""
import pytest

pytest.importorskip("httpx")  # TestClient needs httpx

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

SID = "pytest-session"
HEADERS = {"X-Session-Id": SID}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        loaded = c.post("/api/datasets/load-sample", headers=HEADERS)
        assert loaded.status_code == 200
        yield c


def test_history_records_one_snapshot_per_load(client):
    client.post("/api/datasets/load-sample", headers=HEADERS)
    res = client.get("/api/datasets/history", params={"filename": "retail_sample.csv"}, headers=HEADERS)
    snaps = res.json()["snapshots"]
    assert len(snaps) >= 2
    assert {"at", "rows", "health", "band", "issues", "critical"} <= set(snaps[-1])


def test_weights_normalise_and_persist_into_health(client):
    res = client.post("/api/results/health/weights", params={"filename": "retail_sample.csv"}, headers=HEADERS,
                      json={"weights": {"traceability": 0.9}})
    assert res.status_code == 200
    body = res.json()
    assert body["weights_used"]["traceability"] == pytest.approx(0.9)
    assert "default_weights" in body
    # Only traceability carries weight, so the index equals its pillar score.
    assert body["overall"] == pytest.approx(body["pillar_scores"]["traceability"], abs=0.01)

    restored = client.post("/api/results/health/weights", params={"filename": "retail_sample.csv"}, headers=HEADERS,
                           json={"weights": body["default_weights"]})
    assert restored.json()["overall"] == pytest.approx(94.02, abs=0.01)


def test_weights_reject_unknown_pillar_and_non_positive_sum(client):
    unknown = client.post("/api/results/health/weights", params={"filename": "retail_sample.csv"}, headers=HEADERS,
                          json={"weights": {"not_a_pillar": 1.0}})
    assert unknown.status_code == 400
    zero = client.post("/api/results/health/weights", params={"filename": "retail_sample.csv"}, headers=HEADERS,
                       json={"weights": {"completeness": 0.0}})
    assert zero.status_code == 400


def test_bin_rows_puts_missing_rows_first_and_flags_nulls(client):
    res = client.get("/api/results/bin-rows", params={"filename": "retail_sample.csv", "column": "customer_email",
                                                      "bin": 3, "bins": 60}, headers=HEADERS)
    body = res.json()
    assert res.status_code == 200
    assert body["null_in_column"] == 4
    first_four = body["rows"][:4]
    assert all("customer_email" in r["null_columns"] for r in first_four)
    assert body["rows"][0]["values"]["customer_email"] is None


def test_bin_rows_rejects_bad_bin_and_column(client):
    bad_bin = client.get("/api/results/bin-rows", params={"filename": "retail_sample.csv", "column": "region",
                                                          "bin": 999, "bins": 60}, headers=HEADERS)
    assert bad_bin.status_code == 400
    bad_col = client.get("/api/results/bin-rows", params={"filename": "retail_sample.csv", "column": "nope",
                                                          "bin": 0, "bins": 60}, headers=HEADERS)
    assert bad_col.status_code == 404


def test_share_roundtrip_and_rejects_traversal(client):
    created = client.post("/api/reports/share", params={"filename": "retail_sample.csv"}, headers=HEADERS)
    assert created.status_code == 200
    share_id = created.json()["id"]
    assert len(share_id) == 10

    fetched = client.get(f"/api/reports/shared/{share_id}")
    assert fetched.status_code == 200
    assert fetched.json()["executive_summary"]["dataset"] == "retail_sample.csv"

    assert client.get("/api/reports/shared/..%2F..%2Fsecret").status_code == 404
    assert client.get("/api/reports/shared/ZZZZZZZZZZ").status_code == 404
