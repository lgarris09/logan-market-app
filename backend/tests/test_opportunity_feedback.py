"""ADR-082 -- opportunity-linked beta feedback.

A feedback report is an observed user fact. It preserves what the user saw
when they reported it, is attributable to one opportunity and revision, and
changes nothing about scoring, qualification, Watch or the user model.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.account_lifecycle import purge_user_data
from backend.app.logan_feed import run_demo_feed
from backend.app.main import app
from backend.app.telemetry import events_by_type, recent_events_for_user
from backend.app.telemetry_models import TelemetryEventRequest
from backend.app.telemetry_store import TelemetryStore
from backend.app.watch import is_watched
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.contracts.model_version import EVIDENCE_MODEL_VERSION

client = TestClient(app)

USER = "feedback-user-a"
OTHER = "feedback-user-b"
REASONS = ["seems_wrong", "stale", "not_useful", "unclear_why", "expected_else"]


def _headers(user_id: str) -> dict[str, str]:
    return {"X-Stratus-User-Id": user_id}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _feedback_body(reason: str = "seems_wrong", **context) -> dict:
    ctx = {
        "feedback_reason": reason,
        "entity_id": "NVDA",
        "displayed_headline": "NVIDIA: analyst upgrade",
        "displayed_evidence_label": "Supported",
        "displayed_trajectory": "strengthening",
        "displayed_freshness_state": "FRESH",
        "displayed_at": _now_iso(),
        "displayed_trigger_codes": ["STOCK_ANALYST_UPGRADE"],
        "app_build": "1.0.0 (42)",
    }
    ctx.update(context)
    return {
        "event_id": str(uuid4()),
        "schema_version": "1.0",
        "event_name": "opportunity_feedback_submitted",
        "occurred_at": _now_iso(),
        "opportunity_id": str(uuid4()),
        "opportunity_revision": 2,
        "source_surface": "feed_card",
        "context": {k: v for k, v in ctx.items() if v is not None},
    }


def _post(body: dict, user: str = USER):
    return client.post("/v1/telemetry/events", json=body, headers=_headers(user))


# --- the five governed reasons -------------------------------------------------


@pytest.mark.parametrize("reason", REASONS)
def test_each_governed_reason_is_accepted_and_recorded(reason):
    body = _feedback_body(reason)
    response = _post(body)
    assert response.status_code == 200, response.text
    recorded = [
        e
        for e in events_by_type("opportunity_feedback_submitted")
        if str(e.event_id) == body["event_id"]
    ]
    assert len(recorded) == 1
    assert recorded[0].context is not None
    assert recorded[0].context.feedback_reason == reason


def test_an_ungoverned_reason_is_rejected():
    assert _post(_feedback_body("i_want_a_refund")).status_code == 422


# --- context preservation ------------------------------------------------------


def test_submission_preserves_everything_needed_to_investigate():
    body = _feedback_body("stale", feedback_note="Shown as new but it is last week's.")
    assert _post(body).status_code == 200
    event = next(
        e for e in recent_events_for_user(USER) if str(e.event_id) == body["event_id"]
    )
    ctx = event.context
    assert ctx is not None
    assert event.user_id == USER
    assert str(event.opportunity_id) == body["opportunity_id"]
    assert event.opportunity_revision == 2
    assert ctx.entity_id == "NVDA"
    assert ctx.feedback_reason == "stale"
    assert ctx.feedback_note == "Shown as new but it is last week's."
    assert ctx.displayed_headline == "NVIDIA: analyst upgrade"
    assert ctx.displayed_evidence_label == "Supported"
    assert ctx.displayed_trajectory == "strengthening"
    assert ctx.displayed_freshness_state == "FRESH"
    assert ctx.displayed_at is not None
    assert ctx.displayed_trigger_codes == ["STOCK_ANALYST_UPGRADE"]
    assert ctx.app_build == "1.0.0 (42)"
    assert event.occurred_at is not None and event.recorded_at is not None


def test_model_version_is_server_set_and_cannot_be_spoofed():
    body = _feedback_body()
    body["context"]["model_version"] = "client-says-so"
    assert _post(body).status_code == 200
    event = next(
        e for e in recent_events_for_user(USER) if str(e.event_id) == body["event_id"]
    )
    assert event.context is not None
    assert event.context.model_version == EVIDENCE_MODEL_VERSION


def test_user_identity_is_server_resolved_not_client_supplied():
    body = _feedback_body()
    body["user_id"] = OTHER
    assert _post(body).status_code == 422


@pytest.mark.parametrize(
    "missing",
    ["feedback_reason", "entity_id", "opportunity_revision", "opportunity_id"],
)
def test_a_report_without_its_attribution_is_rejected(missing):
    body = _feedback_body()
    if missing in body:
        del body[missing]
    else:
        del body["context"][missing]
    assert _post(body).status_code == 422


def test_note_is_bounded():
    assert _post(_feedback_body(feedback_note="x" * 501)).status_code == 422
    assert _post(_feedback_body(feedback_note="x" * 500)).status_code == 200


def test_feedback_fields_are_refused_on_other_events():
    body = {
        "event_id": str(uuid4()),
        "schema_version": "1.0",
        "event_name": "opportunity_opened",
        "occurred_at": _now_iso(),
        "opportunity_id": str(uuid4()),
        "context": {"feedback_reason": "stale"},
    }
    assert _post(body).status_code == 422


def test_resubmission_is_idempotent():
    body = _feedback_body()
    assert _post(body).status_code == 200
    assert _post(body).status_code == 200
    matches = [
        e
        for e in events_by_type("opportunity_feedback_submitted")
        if str(e.event_id) == body["event_id"]
    ]
    assert len(matches) == 1


def test_feedback_survives_a_restart(tmp_path):
    store = TelemetryStore(tmp_path / "telemetry.db")
    request = TelemetryEventRequest.model_validate(_feedback_body("unclear_why"))
    from backend.app.telemetry_models import TelemetryEvent

    store.append(
        TelemetryEvent(
            event_id=request.event_id,
            event_name=request.event_name,
            occurred_at=request.occurred_at,
            recorded_at=datetime.now(timezone.utc),
            user_id=USER,
            opportunity_id=request.opportunity_id,
            opportunity_revision=request.opportunity_revision,
            source_surface=request.source_surface,
            context=request.context,
        )
    )
    store.close()
    reopened = TelemetryStore(tmp_path / "telemetry.db")
    loaded = reopened.load_all()
    assert len(loaded) == 1
    assert loaded[0].context is not None
    assert loaded[0].context.feedback_reason == "unclear_why"
    assert loaded[0].context.displayed_headline == "NVIDIA: analyst upgrade"
    reopened.close()


# --- feedback is an observation, not an instruction ----------------------------


def _feed_fingerprint():
    feed = run_demo_feed()
    return [
        (
            item.entity_id,
            item.delivered_item.headline,
            item.opportunity_revision,
            item.lifecycle_state,
        )
        for item in feed.items
    ]


def test_feedback_does_not_change_the_feed_watch_or_qualification():
    before = _feed_fingerprint()
    nvda = next(i for i in run_demo_feed().items if i.entity_id == "NVDA")
    for reason in REASONS:
        body = _feedback_body(reason)
        body["opportunity_id"] = str(nvda.event_id)
        body["opportunity_revision"] = nvda.opportunity_revision or 1
        assert _post(body, LOCAL_FOUNDER_USER_ID).status_code == 200
    after = _feed_fingerprint()
    assert [row[0] for row in after] == [row[0] for row in before]
    assert [row[1] for row in after] == [row[1] for row in before]
    assert is_watched(LOCAL_FOUNDER_USER_ID, "NVDA") is False


def test_feedback_module_has_no_path_to_learning_or_scoring():
    """Structural: the telemetry path neither imports nor calls anything
    that scores, learns or mutates the user model."""
    import ast

    import backend.app.telemetry as telemetry
    import backend.app.telemetry_models as telemetry_models

    forbidden = {
        "learning_engine",
        "feedback_engine",
        "FeedbackEngine",
        "LearningEngine",
        "UserModel",
        "record_interaction",
        "MemoryStore",
    }
    for module in (telemetry, telemetry_models):
        assert module.__file__ is not None
        with open(module.__file__, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        used: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                used.update(alias.name.split(".")[-1] for alias in node.names)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    used.add(func.id)
                elif isinstance(func, ast.Attribute):
                    used.add(func.attr)
        assert used.isdisjoint(forbidden), used & forbidden


# --- Ask carries the selected opportunity --------------------------------------


def test_ask_event_can_carry_the_selected_opportunity():
    opportunity_id = str(uuid4())
    body = {
        "event_id": str(uuid4()),
        "schema_version": "1.0",
        "event_name": "ask_started",
        "occurred_at": _now_iso(),
        "opportunity_id": opportunity_id,
        "opportunity_revision": 3,
        "source_surface": "ask",
        "context": {"ask_session_id": "s-1", "entity_id": "NVDA"},
    }
    assert _post(body).status_code == 200
    event = next(
        e for e in recent_events_for_user(USER) if str(e.event_id) == body["event_id"]
    )
    assert str(event.opportunity_id) == opportunity_id
    assert event.opportunity_revision == 3
    assert event.context is not None
    assert event.context.entity_id == "NVDA"
    assert event.context.model_version == EVIDENCE_MODEL_VERSION


def test_ask_without_an_opportunity_is_still_valid():
    body = {
        "event_id": str(uuid4()),
        "schema_version": "1.0",
        "event_name": "ask_started",
        "occurred_at": _now_iso(),
        "source_surface": "ask",
        "context": {"ask_session_id": "s-2"},
    }
    assert _post(body).status_code == 200


# --- account deletion ----------------------------------------------------------


def test_account_deletion_removes_the_users_telemetry():
    assert _post(_feedback_body(), USER).status_code == 200
    assert _post(_feedback_body(), OTHER).status_code == 200
    assert recent_events_for_user(USER)
    purge_user_data(USER)
    assert recent_events_for_user(USER) == []
    assert recent_events_for_user(OTHER)


def test_store_delete_user_removes_only_that_user(tmp_path):
    from backend.app.telemetry_models import TelemetryEvent

    store = TelemetryStore(tmp_path / "telemetry.db")
    for user in (USER, OTHER):
        request = TelemetryEventRequest.model_validate(_feedback_body())
        store.append(
            TelemetryEvent(
                event_id=request.event_id,
                event_name=request.event_name,
                occurred_at=request.occurred_at,
                recorded_at=datetime.now(timezone.utc),
                user_id=user,
                opportunity_id=request.opportunity_id,
                opportunity_revision=request.opportunity_revision,
                context=request.context,
            )
        )
    assert store.delete_user(USER) == 1
    assert [e.user_id for e in store.load_all()] == [OTHER]
    store.close()


# --- robustness and separation -------------------------------------------------


def test_an_unreadable_row_is_skipped_not_fatal(tmp_path):
    """A row written by a different build (an event name or context field
    this build does not know) must not stop the store from loading."""
    store = TelemetryStore(tmp_path / "telemetry.db")
    store._conn.execute(
        "INSERT INTO telemetry_events (event_id, schema_version, event_name, "
        "occurred_at, recorded_at, user_id, context) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid4()),
            "1.0",
            "an_event_from_the_future",
            _now_iso(),
            _now_iso(),
            USER,
            '{"unknown_field": 1}',
        ),
    )
    store._conn.commit()
    assert store.load_all() == []
    store.close()


def test_watch_state_never_reaches_the_evidence_layers():
    """Watch is personal relevance. It must not be an input to trigger
    detection, evidence trust, conclusion confidence, the world model or
    lifecycle classification."""
    import pathlib

    import logan_core

    root = pathlib.Path(logan_core.__file__).resolve().parent
    evidence_layers = [
        "trigger_detection",
        "evidence_trust",
        "conclusion_confidence",
        "confidence",
        "world_model",
        "normalization",
        "receptors",
    ]
    offenders = []
    for layer in evidence_layers:
        for path in (root / layer).rglob("*.py") if (root / layer).is_dir() else []:
            text = path.read_text(encoding="utf-8")
            if any(k in text for k in ("is_watched", "watch_route", "watched_")):
                offenders.append(str(path.relative_to(root)))
    tracker = (root / "opportunity_lifecycle" / "tracker.py").read_text(
        encoding="utf-8"
    )
    assert "is_watched" not in tracker and "watch_route" not in tracker
    assert offenders == []
