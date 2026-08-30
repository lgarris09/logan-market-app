"""Operational Beta Live Supply V2, Block 4 -- GET /v1/dev/fmp-budget."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_fmp_budget_route_returns_a_report_string():
    response = client.get("/v1/dev/fmp-budget")
    assert response.status_code == 200
    body = response.json()
    assert "report" in body
    assert "FMP Provider Budget" in body["report"]


def test_fmp_budget_route_never_leaks_a_key(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "totally-real-secret-key-value")
    response = client.get("/v1/dev/fmp-budget")
    assert "totally-real-secret-key-value" not in response.text
