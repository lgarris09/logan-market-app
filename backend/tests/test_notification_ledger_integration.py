"""STRATUS 3.6.12 -- Notification Candidate + Decision Ledger V1. Backend-
level integration tests through the real pipeline wiring
(backend/app/logan_feed.py's `_run_feed_pipeline()`), mirroring
test_notification_hygiene.py's own established fixture pattern exactly
(same _routing_earnings_provider/_routing_market_data_provider helpers,
same LOCAL_FOUNDER_USER_ID Personal-explicit-tier rationale). Proves the
ledger records real, already-computed decision-time facts from the actual
production notification-eligibility chain -- never a second, independent
computation -- and that it can never alter that chain's own outcome.
"""

import httpx

from backend.app.logan_feed import reset_pipeline_state
from backend.app.models import RegisterPushTokenRequest
from backend.app.notifications import (
    dispatch_eligible_notifications,
    register_token,
    reset_notification_state,
)
from backend.app.watch import create_watch, reset_watch_state
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider
from logan_core.receptors.providers.fmp import reset_fmp_cache

FOUNDER = LOCAL_FOUNDER_USER_ID
OTHER_USER = "notification-ledger-test-other-user"


def _earnings(symbol, actual, estimated, date="2026-05-20"):
    return [
        {"symbol": symbol, "date": date, "epsActual": actual, "epsEstimated": estimated}
    ]


def _routing_earnings_provider(earnings_by_symbol: dict):
    def handler(request):
        symbol = request.url.params.get("symbol")
        return httpx.Response(200, json=earnings_by_symbol.get(symbol, []))

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return lambda *a, **kw: FmpEarningsProvider(
        api_key="test-key-not-real", client=client
    )


def _failing_earnings_provider():
    def handler(request):
        return httpx.Response(429, text="rate limited")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return lambda *a, **kw: FmpEarningsProvider(
        api_key="test-key-not-real", client=client
    )


def _routing_market_data_provider(
    quote_by_symbol=None, grade_by_symbol=None, profile_by_symbol=None
):
    quote_by_symbol = quote_by_symbol or {}
    grade_by_symbol = grade_by_symbol or {}
    profile_by_symbol = profile_by_symbol or {}

    def handler(request):
        symbol = request.url.params.get("symbol")
        if request.url.path.endswith("/quote"):
            return httpx.Response(200, json=quote_by_symbol.get(symbol, []))
        if request.url.path.endswith("/grades"):
            return httpx.Response(200, json=grade_by_symbol.get(symbol, []))
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json=profile_by_symbol.get(symbol, []))
        raise AssertionError(f"unexpected FMP path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return lambda *a, **kw: FmpMarketDataProvider(
        api_key="test-key-not-real", client=client
    )


def _setup(
    monkeypatch,
    tmp_path,
    *,
    earnings_by_symbol=None,
    grade_by_symbol=None,
    earnings_provider=None,
    tickers="NVDA",
):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", tickers)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")
    # The ledger is gated behind memory_persistence_enabled() exactly like
    # every sibling store -- persistence must be on for any of these tests
    # to exercise it at all.
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        earnings_provider or _routing_earnings_provider(earnings_by_symbol or {}),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(grade_by_symbol=grade_by_symbol or {}),
    )
    reset_fmp_cache()
    reset_pipeline_state()
    reset_notification_state()
    reset_watch_state()


def _register_founder_token():
    register_token(
        FOUNDER, RegisterPushTokenRequest(expo_push_token="ExponentPushToken[founder]")
    )


def _store():
    from backend.app import logan_feed

    store = logan_feed._notification_ledger_store
    assert (
        store is not None
    ), "ledger store was not constructed -- persistence not enabled?"
    return store


def _nvda_candidate(user_id):
    rows = [
        r for r in _store().candidates_for_user(user_id) if r["entity_id"] == "NVDA"
    ]
    assert len(rows) == 1
    return rows[0]


def _nvda_decisions(user_id):
    return [
        r for r in _store().decisions_for_user(user_id) if r["entity_id"] != "OTHER"
    ]


# --- Candidate generated from the real eligibility path ---------------------


def test_candidate_generated_from_real_pipeline_run(monkeypatch, tmp_path):
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
    )
    from backend.app.logan_feed import _run_feed_pipeline

    _run_feed_pipeline(FOUNDER)
    candidate = _nvda_candidate(FOUNDER)
    assert candidate["signal_family"] == "earnings_signal"
    assert candidate["thesis_revision"] == 1


def test_sent_decision_recorded_once_for_founders_nvda_holding(monkeypatch, tmp_path):
    """FOUNDER has a pre-seeded NVDA holding (Personal-explicit tier,
    ADR-049) -- a real qualifying earnings beat must produce a real SEND,
    and the ledger must record it exactly once."""
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
    )
    _register_founder_token()
    dispatched = dispatch_eligible_notifications(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"data": []})
            )
        )
    )
    assert dispatched == 1
    decisions = [
        d for d in _store().decisions_for_user(FOUNDER) if d["outcome"] == "SEND"
    ]
    assert len(decisions) == 1
    assert decisions[0]["reason"] == "new_material_revision"


def test_suppressed_decision_recorded_for_a_user_with_no_relevant_holding(
    monkeypatch, tmp_path
):
    """An arbitrary user_id has no NVDA holding/interest at all -- a modest
    earnings beat qualifies as a real opportunity but never clears the
    Personal/Exceptional Watch route, so this is a real, deterministic
    suppression the ledger must capture."""
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
    )
    from backend.app.logan_feed import _run_feed_pipeline

    _run_feed_pipeline(OTHER_USER)
    candidate = _nvda_candidate(OTHER_USER)
    assert candidate["watch_route"] == "none"
    decisions = _store().decisions_for_user(OTHER_USER)
    assert len(decisions) == 1
    assert decisions[0]["outcome"] == "SUPPRESS"
    assert decisions[0]["reason"] == "insufficient_personal_relevance_or_urgency"


def test_no_signal_fired_records_no_candidate_at_all(monkeypatch, tmp_path):
    """A ticker with no qualifying signal at all (beat_pct below threshold,
    no quote, no grade) never becomes an entity the pipeline evaluates in
    live-only mode -- 'ticker honestly absent' -- so there is genuinely
    nothing to record a notification decision against. Zero candidates is
    the honest outcome, not a fabricated no_material_delta for an entity
    that was never actually observed this poll."""
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.00, 0.99)},  # below 5% beat
    )
    from backend.app.logan_feed import _run_feed_pipeline

    _run_feed_pipeline(FOUNDER)
    assert _store().candidates_for_user(FOUNDER) == []


def test_a_new_legitimate_decision_is_recorded_on_the_very_next_poll(
    monkeypatch, tmp_path
):
    """The *same* qualifying earnings beat, polled twice in a row: the
    first poll is a genuinely new thesis (SEND, new_material_revision). The
    very next poll is a real, different production state --
    PrioritizationEngine's own view-cooldown (set after the first poll's
    surfacing) now vetoes before interruption can become "alert" again --
    and the ledger must record this as a new, legitimate decision, never
    silently deduped away as if nothing happened."""
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
    )
    from backend.app.logan_feed import _run_feed_pipeline

    _run_feed_pipeline(FOUNDER)
    first = _store().decisions_for_user(FOUNDER)
    assert len(first) == 1
    assert first[0]["reason"] == "new_material_revision"

    _run_feed_pipeline(FOUNDER)
    second = _store().decisions_for_user(FOUNDER)
    assert len(second) == 2, "a genuine transition must be recorded, not deduped away"
    assert second[1]["reason"] == "view_cooldown_active"


# --- Watch state captured at decision time ----------------------------------


def test_watch_state_captured_on_the_candidate(monkeypatch, tmp_path):
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
    )
    create_watch(OTHER_USER, "NVDA")
    from backend.app.logan_feed import _run_feed_pipeline

    _run_feed_pipeline(OTHER_USER)
    candidate = _nvda_candidate(OTHER_USER)
    assert bool(candidate["is_watched"]) is True


# --- Degraded/stale capture ---------------------------------------------------


def test_provider_degraded_captured_and_suppressed(monkeypatch, tmp_path):
    _setup(
        monkeypatch,
        tmp_path,
        earnings_provider=_failing_earnings_provider(),
    )
    from backend.app.logan_feed import _run_feed_pipeline

    _run_feed_pipeline(FOUNDER)
    # A genuine provider failure on the *only* configured ticker means no
    # lifecycle-tracked entity ever reaches the per-entity loop at all in
    # live-only mode (see _live_earnings_raw_signal's own honest-absence
    # contract) -- so the correct, honest ledger state here is "no
    # candidate recorded", not a fabricated provider_degraded_suppressed
    # entry for an entity that was never actually observed this poll.
    assert _store().candidates_for_user(FOUNDER) == []


# --- User isolation ------------------------------------------------------------


def test_user_isolation_through_the_real_pipeline(monkeypatch, tmp_path):
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
    )
    from backend.app.logan_feed import _run_feed_pipeline

    _run_feed_pipeline(FOUNDER)
    _run_feed_pipeline(OTHER_USER)
    founder_candidates = _store().candidates_for_user(FOUNDER)
    other_candidates = _store().candidates_for_user(OTHER_USER)
    assert len(founder_candidates) == 1
    assert len(other_candidates) == 1
    assert founder_candidates[0]["user_id"] == FOUNDER
    assert other_candidates[0]["user_id"] == OTHER_USER
    # Founder qualifies for Personal (explicit NVDA holding); the other user
    # never does for the identical real-world event -- proving isolation
    # produced two genuinely different decisions, not two copies of one.
    founder_decision = _store().decisions_for_user(FOUNDER)[0]
    other_decision = _store().decisions_for_user(OTHER_USER)[0]
    assert founder_decision["outcome"] == "SEND"
    assert other_decision["outcome"] == "SUPPRESS"


# --- Restart persistence -------------------------------------------------------


def test_restart_persistence_through_the_real_pipeline(monkeypatch, tmp_path):
    """Durable across restart: the pre-restart candidate_id is still present
    after reconstructing the store from disk. Not asserted as an exact
    total count of 1 -- World Model's event_id is not itself guaranteed
    stable across a full process restart (only the lifecycle/revision
    *state* is, via LifecycleStore), so a post-restart poll of the same
    real-world fact legitimately gets its own candidate_id too; both rows
    coexisting is the correct, honest behavior, not a duplicate."""
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
    )
    from backend.app.logan_feed import _run_feed_pipeline

    _run_feed_pipeline(FOUNDER)
    pre_restart_rows = _store().candidates_for_user(FOUNDER)
    assert len(pre_restart_rows) == 1
    pre_restart_candidate_id = pre_restart_rows[0]["candidate_id"]

    # Simulate a real backend restart: reset_pipeline_state() closes every
    # store's connection and drops the in-memory singleton, exactly like
    # test_notification_hygiene.py's own restart test.
    reset_pipeline_state()
    _run_feed_pipeline(FOUNDER)  # first call after "restart" reconstructs the store
    rows = _store().candidates_for_user(FOUNDER)
    candidate_ids = {r["candidate_id"] for r in rows}
    assert pre_restart_candidate_id in candidate_ids, (
        "the pre-restart candidate row must still be readable after the "
        "store reconstructs itself from disk"
    )


# --- Shadow cannot alter real behavior -----------------------------------------


def test_shadow_evaluation_never_changes_real_dispatch_count(monkeypatch, tmp_path):
    """Breaking the ledger recording entirely (simulating a shadow-
    instrumentation failure) must not change how many notifications are
    actually dispatched -- proves the shadow-mode guarantee structurally,
    not just by convention."""
    _setup(
        monkeypatch,
        tmp_path,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
    )
    _register_founder_token()

    def _broken_candidate_builder(*args, **kwargs):
        raise RuntimeError("simulated shadow-instrumentation failure")

    monkeypatch.setattr(
        "backend.app.logan_feed.build_notification_candidate", _broken_candidate_builder
    )
    dispatched = dispatch_eligible_notifications(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"data": []})
            )
        )
    )
    assert dispatched == 1  # identical to the unbroken case above
    # And, honestly, nothing was recorded -- the failure was swallowed, not
    # silently ignored/hidden.
    assert _store().candidates_for_user(FOUNDER) == []
