"""Sprint 3.6.9 -- hosted attack-surface review: minimal, in-memory,
vendor-neutral rate limiting for /v1/opportunities and /v1/ask.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.rate_limit import check_rate_limit, reset_rate_limits

client = TestClient(app)


# --- The underlying limiter, unit-tested directly ----------------------------


def test_requests_under_the_limit_never_raise():
    reset_rate_limits()
    for _ in range(5):
        check_rate_limit("test-route", "user-a", max_requests=5, window_seconds=60)


def test_exceeding_the_limit_raises_429():
    reset_rate_limits()
    for _ in range(5):
        check_rate_limit("test-route", "user-a", max_requests=5, window_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit("test-route", "user-a", max_requests=5, window_seconds=60)
    assert exc_info.value.status_code == 429


def test_different_users_have_independent_budgets():
    reset_rate_limits()
    for _ in range(5):
        check_rate_limit("test-route", "user-a", max_requests=5, window_seconds=60)

    # user-b's own budget is untouched by user-a exhausting theirs.
    check_rate_limit("test-route", "user-b", max_requests=5, window_seconds=60)


def test_different_routes_have_independent_budgets_for_the_same_user():
    reset_rate_limits()
    for _ in range(5):
        check_rate_limit("route-a", "user-a", max_requests=5, window_seconds=60)

    # A different route for the same user is a separate budget.
    check_rate_limit("route-b", "user-a", max_requests=5, window_seconds=60)


def test_window_resets_after_expiry(monkeypatch):
    import backend.app.rate_limit as rate_limit_module

    reset_rate_limits()
    fake_now = [1000.0]
    monkeypatch.setattr(rate_limit_module.time, "monotonic", lambda: fake_now[0])

    for _ in range(5):
        check_rate_limit("test-route", "user-a", max_requests=5, window_seconds=60)

    fake_now[0] += 61  # past the window
    # Does not raise -- a fresh window started.
    check_rate_limit("test-route", "user-a", max_requests=5, window_seconds=60)


# --- End-to-end proof through real routes ------------------------------------


def test_opportunities_route_returns_429_once_exceeded(monkeypatch):
    from backend.app.logan_feed import reset_pipeline_state

    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    reset_pipeline_state()
    reset_rate_limits()

    headers = {"X-Stratus-User-Id": "rate-limit-test-user"}
    last_status = None
    for _ in range(35):  # over the 30/60s limit
        last_status = client.get("/v1/opportunities", headers=headers).status_code

    assert last_status == 429


def test_opportunities_route_different_users_not_cross_throttled(monkeypatch):
    from backend.app.logan_feed import reset_pipeline_state

    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    reset_pipeline_state()
    reset_rate_limits()

    exhausted_user_headers = {"X-Stratus-User-Id": "rate-limit-exhausted-user"}
    for _ in range(30):
        client.get("/v1/opportunities", headers=exhausted_user_headers)

    fresh_user_response = client.get(
        "/v1/opportunities", headers={"X-Stratus-User-Id": "rate-limit-fresh-user"}
    )
    assert fresh_user_response.status_code == 200


def test_ask_route_returns_429_once_exceeded(monkeypatch):
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    reset_rate_limits()

    headers = {"X-Stratus-User-Id": "rate-limit-ask-test-user"}
    last_status = None
    for _ in range(25):  # over the 20/300s limit
        last_status = client.post(
            "/v1/ask", json={"message": "What changed?"}, headers=headers
        ).status_code

    assert last_status == 429


def test_notifications_register_returns_429_once_exceeded():
    """Sprint 3.6.9 hosted attack-surface re-review: /v1/notifications/register
    was previously left unlimited; reused the existing limiter rather than a
    new subsystem, per the owner's explicit instruction."""
    reset_rate_limits()

    headers = {"X-Stratus-User-Id": "rate-limit-register-test-user"}
    last_status = None
    for i in range(15):  # over the 10/60s limit
        last_status = client.post(
            "/v1/notifications/register",
            json={"expo_push_token": f"ExponentPushToken[test-{i}]"},
            headers=headers,
        ).status_code

    assert last_status == 429


def test_notifications_register_normal_app_launch_pattern_unaffected():
    """Real usage: registers once per app launch, idempotent for an
    already-known token -- a handful of registrations (e.g. a few quick
    restarts) must never be throttled."""
    reset_rate_limits()

    headers = {"X-Stratus-User-Id": "rate-limit-register-normal-user"}
    for _ in range(5):
        response = client.post(
            "/v1/notifications/register",
            json={"expo_push_token": "ExponentPushToken[same-token]"},
            headers=headers,
        )
        assert response.status_code == 200
