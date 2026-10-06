"""Beta 1 -- a live-data-only deployment serves no simulated or static demo
content. The two legacy demo routes remain for local development only."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_demo_routes_are_served_in_demo_mode(monkeypatch):
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert client.get("/v1/briefing").status_code == 200
    assert client.post("/v1/demo/tesla").status_code == 200


def test_demo_routes_are_not_served_in_live_mode(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")
    assert client.get("/v1/briefing").status_code == 404
    assert client.post("/v1/demo/tesla").status_code == 404
