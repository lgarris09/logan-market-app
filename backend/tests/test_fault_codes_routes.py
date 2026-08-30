"""Operational Beta Hardening Block 1 -- GET /v1/dev/fault-codes and
GET /v1/dev/faults/recent."""

from fastapi.testclient import TestClient

from backend.app.main import app
from logan_core.diagnostics import record_fault, reset_fault_state

client = TestClient(app)


def setup_function() -> None:
    reset_fault_state()


def test_fault_codes_catalog_route_returns_a_report_string():
    response = client.get("/v1/dev/fault-codes")
    assert response.status_code == 200
    body = response.json()
    assert "report" in body
    assert "DATA-302" in body["report"]


def test_recent_faults_route_empty_state():
    response = client.get("/v1/dev/faults/recent")
    assert response.status_code == 200
    assert "No faults recorded" in response.json()["report"]


def test_recent_faults_route_reflects_a_recorded_fault():
    record_fault("DATA-301", "test_subsystem", context={"endpoint": "quote"})
    response = client.get("/v1/dev/faults/recent")
    body = response.json()["report"]
    assert "DATA-301" in body
    assert "test_subsystem" in body


def test_recent_faults_route_never_leaks_a_key():
    record_fault(
        "DATA-302", "test_subsystem", context={"api_key": "totally-real-secret"}
    )
    response = client.get("/v1/dev/faults/recent")
    assert "totally-real-secret" not in response.text


def test_recent_faults_route_honors_limit():
    for i in range(5):
        record_fault("DATA-301", "test_subsystem", context={"i": str(i)})
    response = client.get("/v1/dev/faults/recent", params={"limit": 2})
    body = response.json()["report"]
    assert body.count("DATA-301") == 2
