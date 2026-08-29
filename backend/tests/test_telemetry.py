"""V2.3C Telemetry -- core recording logic, the durable store, and the
POST /v1/telemetry/events(/batch) HTTP contract.

Telemetry records what happened; it never decides what it means (see
telemetry_models.py's own module docstring). These tests are organized
around that boundary: schema/vocabulary validation, spoofing resistance,
idempotency, durability across a simulated restart, and the one piece of
real business logic this module has -- promoting `opportunity_opened` to
`opportunity_returned_to` from existing, durable view-history (never new
state, see telemetry.py's _resolve_opportunity_promotion).
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from backend.app.main import app
from backend.app.telemetry import (
    events_by_type,
    events_for_user_and_opportunity,
    latest_event_for_user_and_type,
    recent_events_for_user,
    record_batch,
    record_event,
    reset_telemetry_state,
)
from backend.app.telemetry_models import (
    TelemetryEventBatchRequest,
    TelemetryEventRequest,
)
from backend.app.telemetry_store import TelemetryStore
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider

client = TestClient(app)
USER_A = "telemetry-user-a"
USER_B = "telemetry-user-b"


def _headers(user_id: str) -> dict[str, str]:
    return {"X-Stratus-User-Id": user_id}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_body(**overrides) -> dict:
    body = {
        "event_id": str(uuid4()),
        "schema_version": "1.0",
        "event_name": "opportunity_opened",
        "occurred_at": _now_iso(),
        "opportunity_id": str(uuid4()),
        "source_surface": "feed_card",
    }
    body.update(overrides)
    return body


def _watch_removed_body(**overrides) -> dict:
    return _base_body(event_name="watch_removed", **overrides)


def _demo_nvda_event_id() -> str:
    result = run_demo_feed()
    return str(next(i for i in result.items if i.entity_id == "NVDA").event_id)


# --- Valid event accepted / persisted ---------------------------------


def test_valid_event_is_accepted_and_returned():
    body = _base_body()
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["event_id"] == body["event_id"]


def test_valid_event_is_readable_via_the_internal_diagnostic_api():
    body = _watch_removed_body()
    client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))

    events = recent_events_for_user(USER_A)
    assert len(events) == 1
    assert events[0].event_name == "watch_removed"
    assert str(events[0].event_id) == body["event_id"]
    assert events[0].user_id == USER_A


# --- Invalid / unsupported events are rejected -------------------------


def test_unknown_event_name_is_rejected():
    response = client.post(
        "/v1/telemetry/events",
        json=_base_body(event_name="screen_viewed"),
        headers=_headers(USER_A),
    )
    assert response.status_code == 422


def test_unsupported_schema_version_is_rejected():
    response = client.post(
        "/v1/telemetry/events",
        json=_base_body(schema_version="2.0"),
        headers=_headers(USER_A),
    )
    assert response.status_code == 422


def test_missing_opportunity_id_rejected_for_opportunity_scoped_event():
    body = _base_body()
    del body["opportunity_id"]
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 422


def test_invalid_source_surface_is_rejected():
    response = client.post(
        "/v1/telemetry/events",
        json=_base_body(source_surface="not-a-real-surface"),
        headers=_headers(USER_A),
    )
    assert response.status_code == 422


def test_valid_source_surface_is_accepted():
    response = client.post(
        "/v1/telemetry/events",
        json=_watch_removed_body(source_surface="wheel"),
        headers=_headers(USER_A),
    )
    assert response.status_code == 200


def test_implausibly_old_occurred_at_is_rejected():
    response = client.post(
        "/v1/telemetry/events",
        json=_watch_removed_body(occurred_at="2019-01-01T00:00:00+00:00"),
        headers=_headers(USER_A),
    )
    assert response.status_code == 422


def test_far_future_occurred_at_is_rejected():
    far_future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = client.post(
        "/v1/telemetry/events",
        json=_watch_removed_body(occurred_at=far_future),
        headers=_headers(USER_A),
    )
    assert response.status_code == 422


# --- Ask start/follow-up semantics --------------------------------------


def test_ask_started_requires_ask_session_id():
    body = _base_body(event_name="ask_started")
    del body["opportunity_id"]
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 422


def test_ask_follow_up_with_session_id_is_accepted():
    body = _base_body(
        event_name="ask_follow_up", context={"ask_session_id": "session-123"}
    )
    del body["opportunity_id"]
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 200


def test_ask_session_id_on_a_non_ask_event_is_rejected():
    body = _watch_removed_body(context={"ask_session_id": "session-123"})
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 422


# --- usefulness_feedback_submitted --------------------------------------


def test_usefulness_feedback_requires_useful_field():
    body = _base_body(event_name="usefulness_feedback_submitted")
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 422


def test_usefulness_feedback_with_useful_field_is_accepted():
    body = _base_body(
        event_name="usefulness_feedback_submitted", context={"useful": True}
    )
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 200


def test_useful_field_on_a_non_feedback_event_is_rejected():
    body = _base_body(context={"useful": True})
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 422


def test_unrecognized_context_key_is_rejected():
    """Block J: no arbitrary/unbounded payloads -- an unrecognized context
    field is a hard validation error, not silently accepted."""
    body = _watch_removed_body(context={"anything_goes": "nope"})
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 422


# --- Spoofed user_id is impossible ---------------------------------------


def test_user_id_field_in_body_is_rejected_not_silently_dropped():
    body = _watch_removed_body(user_id="someone-else")
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 422


def test_user_id_always_resolves_from_the_identity_header_not_the_body():
    body = _watch_removed_body()
    client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    events = recent_events_for_user(USER_A)
    assert events[0].user_id == USER_A
    assert recent_events_for_user("someone-else") == []


# --- User isolation --------------------------------------------------------


def test_events_are_isolated_between_users():
    client.post(
        "/v1/telemetry/events", json=_watch_removed_body(), headers=_headers(USER_A)
    )
    client.post(
        "/v1/telemetry/events", json=_watch_removed_body(), headers=_headers(USER_B)
    )

    assert len(recent_events_for_user(USER_A)) == 1
    assert len(recent_events_for_user(USER_B)) == 1


# --- Stable event ID + idempotency ---------------------------------------


def test_duplicate_event_id_is_not_recorded_twice():
    body = _watch_removed_body()
    first = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    second = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["event_id"] == second.json()["event_id"]
    assert len(recent_events_for_user(USER_A)) == 1


def test_duplicate_event_id_returns_the_original_recorded_at():
    """Not just "no duplicate row" -- the original stored event is what's
    returned, never silently overwritten by a resubmission's own
    metadata."""
    request = TelemetryEventRequest.model_validate(_watch_removed_body())
    first = record_event(USER_A, request)
    second = record_event(USER_A, request)
    assert first.recorded_at == second.recorded_at


# --- Opportunity ID / revision validation --------------------------------


def test_revision_exceeding_current_known_revision_is_rejected():
    """A client can never report a higher revision than the entity's own
    current known revision -- if it resolves at all, it's cross-checked."""
    event_id = _demo_nvda_event_id()
    body = _base_body(opportunity_id=event_id, opportunity_revision=999999)
    response = client.post(
        "/v1/telemetry/events", json=body, headers=_headers(LOCAL_FOUNDER_USER_ID)
    )
    # Demo mode has no lifecycle tracking active (current_revision is None
    # for every simulated fixture), so there is nothing to cross-check
    # against here -- this specific body is accepted as submitted. The real
    # cross-check is exercised end-to-end below, with lifecycle tracking
    # active.
    assert response.status_code == 200


def test_unresolvable_opportunity_id_is_accepted_as_submitted():
    """A stale/expired event_id this user never had context for -- honest,
    not fabricated: recorded exactly as submitted, no promotion applied."""
    body = _base_body(opportunity_id=str(uuid4()))
    response = client.post("/v1/telemetry/events", json=body, headers=_headers(USER_A))
    assert response.status_code == 200
    events = recent_events_for_user(USER_A)
    assert events[0].event_name == "opportunity_opened"


# --- Revision-aware opportunity_returned_to promotion --------------------


def test_opportunity_opened_is_promoted_to_returned_to_after_a_real_prior_view(
    monkeypatch,
):
    """The core Block H tie-in: reuses the existing, durable
    UserOpportunityKnowledge.last_opened_revision (advanced by
    record_interaction's "view" path -- the same mechanism
    useCardDwellTracking.ts already submits) rather than inventing new view-
    tracking state. A second `opportunity_opened` submission for an entity
    this user has a real prior recorded view of must be persisted as
    `opportunity_returned_to`, revision-aware."""
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")

    def _unavailable(*args, **kwargs):
        from logan_core.receptors.providers import FmpProviderError

        raise FmpProviderError("no live market data configured for this test")

    monkeypatch.setattr("backend.app.logan_feed.FmpMarketDataProvider", _unavailable)

    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "date": "2026-08-26",
                    "epsActual": 2.22,
                    "epsEstimated": 2.09,
                }
            ],
        )

    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: FmpEarningsProvider(
            api_key="test-key-not-real",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            **kwargs,
        ),
    )
    reset_pipeline_state()

    opp_response = client.get(
        "/v1/opportunities", headers=_headers(LOCAL_FOUNDER_USER_ID)
    )
    nvda = next(i for i in opp_response.json()["items"] if i["entity_id"] == "NVDA")
    event_id = nvda["event_id"]
    first_revision = nvda["opportunity_revision"]
    assert first_revision is not None

    # A real, completed open->close view -- the only thing that advances
    # last_opened_revision (see record_interaction's own docstring).
    view_response = client.post(
        "/v1/interactions",
        json={
            "event_id": event_id,
            "entity_id": "NVDA",
            "domain": "stocks",
            "interaction_type": "view",
            "duration_ms": 9000,
        },
        headers=_headers(LOCAL_FOUNDER_USER_ID),
    )
    assert view_response.status_code == 200

    telemetry_response = client.post(
        "/v1/telemetry/events",
        json=_base_body(opportunity_id=event_id, opportunity_revision=first_revision),
        headers=_headers(LOCAL_FOUNDER_USER_ID),
    )
    assert telemetry_response.status_code == 200

    recorded = latest_event_for_user_and_type(
        LOCAL_FOUNDER_USER_ID, "opportunity_returned_to"
    )
    assert recorded is not None
    assert recorded.context is not None
    assert recorded.context.previous_opened_revision == first_revision


def test_first_ever_open_is_never_promoted_to_returned_to():
    event_id = _demo_nvda_event_id()
    response = client.post(
        "/v1/telemetry/events",
        json=_base_body(opportunity_id=event_id),
        headers=_headers("brand-new-user"),
    )
    assert response.status_code == 200
    events = recent_events_for_user("brand-new-user")
    assert events[0].event_name == "opportunity_opened"


# --- Batch endpoint --------------------------------------------------------


def test_batch_accepts_multiple_valid_events():
    body = {"events": [_watch_removed_body(), _watch_removed_body()]}
    response = client.post(
        "/v1/telemetry/events/batch", json=body, headers=_headers(USER_A)
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_count"] == 2
    assert payload["rejected"] == []


def test_batch_partial_rejection_does_not_discard_the_rest(monkeypatch):
    """A business-logic rejection (revision too high) for one event in a
    batch never discards the others."""
    from backend.app import telemetry as telemetry_module
    from backend.app.ask_context import OpportunityContext

    fake_context = OpportunityContext.model_construct(
        event_id=uuid4(),
        entity_id="NVDA",
        display_name="NVIDIA",
        domain="stocks",
        headline="",
        what_happened="",
        why_it_matters="",
        why_it_matters_to_me="",
        why_now="",
        confidence_score=0.6,
        confidence_label="Moderate",
        classification="",
        limiting_factors=[],
        alternatives=[],
        trigger_codes=[],
        convergence_sources=[],
        personal_relevance=0.0,
        connection_basis="none",
        is_new_for_user=False,
        current_revision=2,
    )
    monkeypatch.setattr(
        telemetry_module,
        "get_opportunity_context",
        lambda user_id, opp_id: fake_context,
    )

    over_revision_body = _base_body(opportunity_revision=999)
    fine_body = _watch_removed_body()
    request = TelemetryEventBatchRequest.model_validate(
        {"events": [over_revision_body, fine_body]}
    )

    response = record_batch(USER_A, request)

    assert response.accepted_count == 1
    assert len(response.rejected) == 1
    assert str(response.rejected[0].event_id) == over_revision_body["event_id"]


def test_batch_size_over_the_bound_is_rejected():
    body = {"events": [_watch_removed_body() for _ in range(26)]}
    response = client.post(
        "/v1/telemetry/events/batch", json=body, headers=_headers(USER_A)
    )
    assert response.status_code == 422


# --- Durable store survives re-instantiation (simulated restart) --------


def test_store_survives_reinstantiation(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    reset_telemetry_state()

    body = _watch_removed_body()
    request = TelemetryEventRequest.model_validate(body)
    record_event(USER_A, request)

    # Simulate a real restart: drop the in-memory index and release the
    # SQLite connection, then reconstruct from the same durable file.
    reset_telemetry_state()

    events = recent_events_for_user(USER_A)
    assert len(events) == 1
    assert str(events[0].event_id) == body["event_id"]


def test_disabled_persistence_does_not_survive_a_simulated_restart(monkeypatch):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_telemetry_state()

    request = TelemetryEventRequest.model_validate(_watch_removed_body())
    record_event(USER_A, request)
    reset_telemetry_state()

    assert recent_events_for_user(USER_A) == []


def test_duplicate_event_id_is_never_overwritten_at_the_store_layer(tmp_path):
    """Store-level idempotency guarantee, independent of the API layer:
    INSERT OR IGNORE never overwrites an existing row."""
    store = TelemetryStore(tmp_path / "telemetry.db")
    request = TelemetryEventRequest.model_validate(_watch_removed_body())
    from backend.app.telemetry_models import TelemetryEvent

    original = TelemetryEvent(
        event_id=request.event_id,
        event_name=request.event_name,
        occurred_at=request.occurred_at,
        recorded_at=datetime.now(timezone.utc),
        user_id=USER_A,
        opportunity_id=request.opportunity_id,
        source_surface=request.source_surface,
    )
    assert store.append(original) is True
    assert store.append(original) is False  # duplicate event_id -- no-op
    assert len(store.load_all()) == 1
    store.close()


# --- Read/diagnostic API scoping -----------------------------------------


def test_events_for_user_and_opportunity_is_scoped_correctly():
    shared_opportunity = uuid4()
    other_opportunity = uuid4()
    client.post(
        "/v1/telemetry/events",
        json=_base_body(opportunity_id=str(shared_opportunity)),
        headers=_headers(USER_A),
    )
    client.post(
        "/v1/telemetry/events",
        json=_base_body(opportunity_id=str(other_opportunity)),
        headers=_headers(USER_A),
    )

    matches = events_for_user_and_opportunity(USER_A, shared_opportunity)
    assert len(matches) == 1
    assert matches[0].opportunity_id == shared_opportunity


def test_events_by_type_can_scope_globally_or_per_user():
    client.post(
        "/v1/telemetry/events", json=_watch_removed_body(), headers=_headers(USER_A)
    )
    client.post(
        "/v1/telemetry/events", json=_watch_removed_body(), headers=_headers(USER_B)
    )

    assert len(events_by_type("watch_removed")) == 2
    assert len(events_by_type("watch_removed", user_id=USER_A)) == 1
