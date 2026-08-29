"""Minimal STRATUS Watch (V2.3E) -- "STRATUS, keep watching this for me."

Full HTTP-level coverage of POST /v1/watches and DELETE /v1/watches/{entity_id}
(backend/app/main.py), the durable store/business logic they call (backend/app/
watch.py, backend/app/watch_store.py), and the feed contract's is_watched
field (backend/app/logan_feed.py). Mirrors test_multi_user_isolation.py's own
X-Stratus-User-Id header convention and test_account_identity.py's real
RSA-signed-JWT technique for the authenticated-identity/account-link tests.
"""

import time
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from backend.app.main import app
from backend.app.watch import (
    create_watch,
    is_watched,
    list_watches,
    purge_user,
    reset_watch_state,
)
from backend.app.watch_store import WatchStore
from logan_core.receptors.providers import FmpEarningsProvider

client = TestClient(app)


def _headers(user_id: str | None) -> dict[str, str]:
    return {"X-Stratus-User-Id": user_id} if user_id else {}


# --- Real Clerk-style JWT plumbing, for the authenticated/account-link tests -

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


# --- Create ------------------------------------------------------------------


def test_create_watch_persists_and_reports_created_true():
    response = client.post(
        "/v1/watches", json={"entity_id": "NVDA"}, headers=_headers("user-a")
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"entity_id": "NVDA", "watched": True, "created": True}
    assert is_watched("user-a", "NVDA") is True


def test_duplicate_create_is_idempotent_no_duplicate_record_created_false():
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers("user-a"))
    second = client.post(
        "/v1/watches", json={"entity_id": "NVDA"}, headers=_headers("user-a")
    )
    assert second.status_code == 200
    body = second.json()
    assert body["watched"] is True
    assert body["created"] is False  # the repeat call did not create anything new
    assert len(list_watches("user-a")) == 1  # never a duplicate record


# --- Remove --------------------------------------------------------------


def test_remove_watch_reports_removed_true():
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers("user-a"))
    response = client.delete("/v1/watches/NVDA", headers=_headers("user-a"))
    assert response.status_code == 200
    assert response.json() == {"entity_id": "NVDA", "watched": False, "removed": True}
    assert is_watched("user-a", "NVDA") is False


def test_duplicate_remove_is_idempotent_removed_false():
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers("user-a"))
    client.delete("/v1/watches/NVDA", headers=_headers("user-a"))
    second = client.delete("/v1/watches/NVDA", headers=_headers("user-a"))
    assert second.status_code == 200
    assert second.json()["removed"] is False


def test_removing_something_never_watched_is_a_safe_no_op():
    response = client.delete("/v1/watches/AAPL", headers=_headers("user-never-watched"))
    assert response.status_code == 200
    assert response.json() == {"entity_id": "AAPL", "watched": False, "removed": False}


# --- Anonymous / authenticated identity compatibility -----------------------


def test_anonymous_user_can_create_and_remove_a_watch():
    create = client.post(
        "/v1/watches",
        json={"entity_id": "NVDA"},
        headers=_headers("anon-3f9a7b21-4e2d-4c11-9c3a-6b1d2e8f0a11"),
    )
    assert create.json()["created"] is True

    remove = client.delete(
        "/v1/watches/NVDA",
        headers=_headers("anon-3f9a7b21-4e2d-4c11-9c3a-6b1d2e8f0a11"),
    )
    assert remove.json()["removed"] is True


def test_authenticated_user_can_create_a_watch():
    response = client.post(
        "/v1/watches", json={"entity_id": "NVDA"}, headers=_bearer("clerk_watch_user")
    )
    assert response.status_code == 200
    assert response.json()["created"] is True


def test_authenticated_identity_is_authoritative_over_a_spoofed_anonymous_header():
    """An authenticated Bearer token must resolve to its own real identity,
    never whatever X-Stratus-User-Id happens to also be present -- same
    security boundary every other route in this backend already enforces."""
    headers = {**_headers("some-other-users-id"), **_bearer("clerk_watch_user_2")}
    response = client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=headers)

    assert response.json()["created"] is True  # succeeded, just not for the spoofed id
    assert is_watched("some-other-users-id", "NVDA") is False


# --- Account-link continuity -------------------------------------------------


def test_watch_created_anonymously_survives_account_linking():
    """Watch state is keyed by the literal stratus_user_id string -- since
    account linking makes the anonymous device's own id *become* the
    canonical authenticated id (no rotation), a watch created before sign-in
    must still be there immediately after, under the same call."""
    anon_id = f"anon-{uuid4()}"
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers(anon_id))
    assert is_watched(anon_id, "NVDA") is True

    link_response = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": anon_id},
        headers=_bearer("clerk_linking_user"),
    )
    stratus_user_id = link_response.json()["stratus_user_id"]
    assert stratus_user_id == anon_id  # first-ever link: id becomes canonical

    assert is_watched(stratus_user_id, "NVDA") is True


# --- User isolation --------------------------------------------------------


def test_one_users_watch_never_appears_as_another_users_watch():
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers("user-a"))

    assert is_watched("user-a", "NVDA") is True
    assert is_watched("user-b", "NVDA") is False
    assert list_watches("user-b") == []


def test_removing_one_users_watch_route_never_affects_another_users():
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers("user-a"))
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers("user-b"))

    client.delete("/v1/watches/NVDA", headers=_headers("user-a"))

    assert is_watched("user-a", "NVDA") is False
    assert is_watched("user-b", "NVDA") is True


# --- Feed contract: is_watched -----------------------------------------------


def test_feed_response_reflects_watch_state():
    reset_pipeline_state()
    nvda = next(i for i in run_demo_feed("user-a").items if i.entity_id == "NVDA")
    assert nvda.is_watched is False

    create_watch("user-a", "NVDA")
    nvda_after = next(i for i in run_demo_feed("user-a").items if i.entity_id == "NVDA")
    assert nvda_after.is_watched is True


def test_is_watched_is_not_gated_behind_lifecycle_tracking():
    """Unlike opportunity_revision/since_last_looked/etc, is_watched must
    work for a simulated demo entity with no live tickers configured at
    all -- a user can watch any opportunity they can see."""
    reset_pipeline_state()
    result = run_demo_feed("user-a")
    tesla = next(i for i in result.items if i.entity_id == "TSLA")
    assert tesla.opportunity_revision is None  # lifecycle tracking not active
    assert tesla.is_watched is False  # but is_watched still reports a real value

    create_watch("user-a", "TSLA")
    tesla_after = next(
        i for i in run_demo_feed("user-a").items if i.entity_id == "TSLA"
    )
    assert tesla_after.is_watched is True


# --- Degraded provider state must never remove a Watch ----------------------


def test_degraded_provider_state_does_not_remove_a_watch(monkeypatch):
    """Watch represents user intent, not current provider availability -- a
    live-data outage must never silently unwatch something."""
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)

    def failing_handler(request):
        return httpx.Response(429, text="rate limited")

    transport = httpx.MockTransport(failing_handler)
    fmp_client = httpx.Client(transport=transport)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real", client=fmp_client
        ),
    )
    reset_pipeline_state()

    create_watch("user-a", "NVDA")
    result = run_demo_feed("user-a")
    assert result.provider_degraded is True
    nvda = next(i for i in result.items if i.entity_id == "NVDA")
    assert nvda.is_watched is True  # unaffected by the outage


# --- Persistence across a simulated restart ---------------------------------


def test_watch_persists_across_a_simulated_restart(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    reset_watch_state()

    create_watch("user-a", "NVDA")
    assert is_watched("user-a", "NVDA") is True

    reset_watch_state()  # simulates a process restart -- reloads from disk

    assert is_watched("user-a", "NVDA") is True


def test_watch_store_delete_reports_whether_a_row_actually_existed(tmp_path):
    store = WatchStore(str(tmp_path / "watches.db"))
    assert store.delete("user-a", "NVDA") is False  # nothing to delete yet

    from datetime import datetime, timezone

    from backend.app.watch_store import Watch

    store.save(
        Watch(user_id="user-a", entity_id="NVDA", created_at=datetime.now(timezone.utc))
    )
    assert store.delete("user-a", "NVDA") is True
    assert store.delete("user-a", "NVDA") is False  # already gone
    store.close()


# --- Account deletion purges Watch state -------------------------------------


def test_deleting_account_purges_its_watches():
    anon_id = f"anon-{uuid4()}"
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers(anon_id))
    assert is_watched(anon_id, "NVDA") is True

    delete_response = client.delete("/v1/account", headers=_headers(anon_id))
    assert delete_response.status_code == 200

    assert is_watched(anon_id, "NVDA") is False


def test_purge_user_is_a_safe_no_op_for_a_user_with_no_watches():
    purge_user("user-with-nothing-watched")  # must not raise
