"""V2.3B Personal Learning Phase 1 -- GET /v1/learning/report and
POST /v1/learning/suppress (backend/app/main.py, backend/app/learning.py).

Full HTTP-level coverage: identity scoping/isolation, real feedback
interactions reflected in the report, suppression reflected in the report,
anonymous -> authenticated continuity, and account purge removing learning
data. Mirrors test_watch.py's own X-Stratus-User-Id/real-JWT conventions.
"""

import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.app.account_lifecycle import purge_user_data
from backend.app.main import app

client = TestClient(app)


def _headers(user_id: str | None) -> dict[str, str]:
    return {"X-Stratus-User-Id": user_id} if user_id else {}


_ISSUER = "https://test-instance.clerk.accounts.dev"
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()


def _token(subject: str, expires_in: float = 3600) -> str:
    payload = {
        "iss": _ISSUER,
        "iat": int(time.time()),
        "exp": int(time.time() + expires_in),
        "sub": subject,
    }
    return jwt.encode(payload, _private_key, algorithm="RS256")


def _bearer(subject: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(subject)}"}


@pytest.fixture(autouse=True)
def _configure_clerk(monkeypatch):
    from backend.app import clerk_auth

    monkeypatch.setenv("CLERK_ISSUER_URL", _ISSUER)
    monkeypatch.setattr(
        clerk_auth,
        "_get_jwks_client",
        lambda: type(
            "FakeJwksClient",
            (),
            {
                "get_signing_key_from_jwt": staticmethod(
                    lambda token: type("K", (), {"key": _public_key})()
                )
            },
        )(),
    )
    yield


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


def test_fresh_user_has_an_empty_but_well_formed_report():
    response = client.get("/v1/learning/report", headers=_headers("fresh-user"))
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "fresh-user"
    assert body["observed"] == []
    assert body["learned"] == []
    assert body["not_learned"] == []
    assert len(body["architecture_notes"]) >= 1


def test_two_qualifying_saves_produce_a_learned_interest():
    _save("report-user-a")
    _save("report-user-a")

    response = client.get("/v1/learning/report", headers=_headers("report-user-a"))
    body = response.json()
    assert any(o["description"] == "Saved NVDA 2 times" for o in body["observed"])
    nvda = next(t for t in body["learned"] if t["entity_id"] == "NVDA")
    assert nvda["source"] == "inferred"
    assert nvda["evidence_count"] == 2


def test_one_save_alone_is_reported_as_not_learned():
    _save("report-user-single")
    response = client.get("/v1/learning/report", headers=_headers("report-user-single"))
    body = response.json()
    assert body["learned"] == []
    nvda = next(t for t in body["not_learned"] if t["candidate"] == "NVDA")
    assert "Only 1 qualifying observation" in nvda["reason"]


def test_suppress_route_removes_the_trait_from_the_next_report():
    _save("report-user-suppress")
    _save("report-user-suppress")
    before = client.get("/v1/learning/report", headers=_headers("report-user-suppress"))
    assert any(t["entity_id"] == "NVDA" for t in before.json()["learned"])

    suppress = client.post(
        "/v1/learning/suppress",
        json={"entity_id": "NVDA", "domain": "stocks"},
        headers=_headers("report-user-suppress"),
    )
    assert suppress.status_code == 200
    assert suppress.json() == {"entity_id": "NVDA", "suppressed": True}

    after = client.get("/v1/learning/report", headers=_headers("report-user-suppress"))
    body = after.json()
    assert not any(t["entity_id"] == "NVDA" for t in body["learned"])
    nvda = next(t for t in body["not_learned"] if t["candidate"] == "NVDA")
    assert "Suppressed by an explicit correction" in nvda["reason"]


def test_report_never_leaks_across_users():
    _save("isolation-user-a")
    _save("isolation-user-a")

    report_a = client.get(
        "/v1/learning/report", headers=_headers("isolation-user-a")
    ).json()
    report_b = client.get(
        "/v1/learning/report", headers=_headers("isolation-user-b")
    ).json()

    assert any(t["entity_id"] == "NVDA" for t in report_a["learned"])
    assert report_b["learned"] == []
    assert report_b["observed"] == []


def test_suppress_route_never_affects_another_user():
    _save("suppress-isolation-a")
    _save("suppress-isolation-a")
    _save("suppress-isolation-b")
    _save("suppress-isolation-b")

    client.post(
        "/v1/learning/suppress",
        json={"entity_id": "NVDA"},
        headers=_headers("suppress-isolation-a"),
    )

    report_a = client.get(
        "/v1/learning/report", headers=_headers("suppress-isolation-a")
    ).json()
    report_b = client.get(
        "/v1/learning/report", headers=_headers("suppress-isolation-b")
    ).json()
    assert not any(t["entity_id"] == "NVDA" for t in report_a["learned"])
    assert any(t["entity_id"] == "NVDA" for t in report_b["learned"])


def test_learning_survives_anonymous_to_authenticated_account_link():
    """The exact same continuity every other user-scoped store in this
    codebase already gets from link_account()'s first-link-wins design
    (the anonymous device id *becomes* the canonical id, zero migration) --
    proven here specifically for Personal Learning."""
    device_id = "anon-device-learning-continuity"
    _save(device_id)
    _save(device_id)

    link = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": device_id},
        headers=_bearer("clerk-subject-learning-continuity"),
    )
    assert link.status_code == 200
    assert link.json()["stratus_user_id"] == device_id

    # Now authenticated as the same canonical id -- the report must still
    # show the pre-link learning, not a blank slate.
    report = client.get(
        "/v1/learning/report", headers=_bearer("clerk-subject-learning-continuity")
    ).json()
    assert any(t["entity_id"] == "NVDA" for t in report["learned"])


def test_account_purge_removes_learning_data():
    _save("purge-user")
    _save("purge-user")
    before = client.get("/v1/learning/report", headers=_headers("purge-user")).json()
    assert any(t["entity_id"] == "NVDA" for t in before["learned"])

    purge_user_data("purge-user")

    after = client.get("/v1/learning/report", headers=_headers("purge-user")).json()
    assert after["learned"] == []
    assert after["observed"] == []
