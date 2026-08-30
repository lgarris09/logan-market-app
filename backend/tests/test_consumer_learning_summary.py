"""Operational Beta Hardening Block 4 -- GET /v1/learning/summary
(backend/app/main.py, backend/app/learning.py's get_consumer_learning_summary()).

The smallest credible "What STRATUS is learning" consumer surface -- proves
it never leaks a raw decimal, timestamp, or evidence_count that the dev-
oriented /v1/learning/report legitimately carries, while still reflecting
real learned traits and their explicit/inferred basis.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _headers(user_id: str) -> dict[str, str]:
    return {"X-Stratus-User-Id": user_id}


def _save(user_id: str, entity_id: str = "NVDA") -> None:
    response = client.post(
        "/v1/interactions",
        json={
            "event_id": str(uuid4()),
            "entity_id": entity_id,
            "domain": "stocks",
            "interaction_type": "save",
        },
        headers=_headers(user_id),
    )
    assert response.status_code == 200


def test_fresh_user_has_an_empty_but_well_formed_summary():
    response = client.get(
        "/v1/learning/summary", headers=_headers("summary-fresh-user")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "summary-fresh-user"
    assert body["traits"] == []
    assert body["explanation"]


def test_learned_trait_appears_with_plain_description_and_basis():
    _save("summary-user-a")
    _save("summary-user-a")
    response = client.get("/v1/learning/summary", headers=_headers("summary-user-a"))
    body = response.json()
    nvda = next(t for t in body["traits"] if t["entity_id"] == "NVDA")
    assert nvda["basis"] == "inferred"
    assert nvda["description"]
    assert nvda["can_suppress"] is True


def test_summary_never_exposes_a_raw_strength_or_confidence_float():
    _save("summary-user-b")
    _save("summary-user-b")
    response = client.get("/v1/learning/summary", headers=_headers("summary-user-b"))
    body = response.json()
    for trait in body["traits"]:
        assert "strength" not in trait
        assert "confidence" not in trait
        assert "evidence_count" not in trait
    assert "model_confidence" not in body


def test_summary_never_exposes_timestamps_or_event_ids():
    _save("summary-user-c")
    _save("summary-user-c")
    response = client.get("/v1/learning/summary", headers=_headers("summary-user-c"))
    body = response.json()
    for trait in body["traits"]:
        assert "first_learned_at" not in trait
        assert "last_updated_at" not in trait
        assert "event_id" not in trait


def test_summary_never_includes_not_learned_candidates():
    """not_learned is a dev-report-only concept -- a consumer summary has
    nothing useful to say about a candidate STRATUS declined to conclude."""
    _save("summary-user-d")
    response = client.get("/v1/learning/summary", headers=_headers("summary-user-d"))
    assert "not_learned" not in response.json()


def test_suppressed_trait_disappears_from_the_summary():
    _save("summary-user-suppress")
    _save("summary-user-suppress")
    before = client.get(
        "/v1/learning/summary", headers=_headers("summary-user-suppress")
    )
    assert any(t["entity_id"] == "NVDA" for t in before.json()["traits"])

    suppress = client.post(
        "/v1/learning/suppress",
        json={"entity_id": "NVDA", "domain": "stocks"},
        headers=_headers("summary-user-suppress"),
    )
    assert suppress.status_code == 200

    after = client.get(
        "/v1/learning/summary", headers=_headers("summary-user-suppress")
    )
    assert not any(t["entity_id"] == "NVDA" for t in after.json()["traits"])


def test_summary_never_leaks_across_users():
    _save("summary-user-e")
    _save("summary-user-e")
    other = client.get("/v1/learning/summary", headers=_headers("summary-user-f"))
    assert other.json()["traits"] == []
