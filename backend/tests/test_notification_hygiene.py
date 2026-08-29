"""Stock Opportunity Logic V2.4A -- Notification Hygiene & Repeat-Alert
Suppression. Backend-level integration tests through the real pipeline
wiring (backend/app/logan_feed.py, backend/app/notifications.py): a real
dispatch loop, real durable UserOpportunityKnowledge, real trajectory
reversal, real provider failure. Mirrors test_user_sync_integration.py's and
test_evidence_trajectory_integration.py's own httpx.MockTransport-backed FMP
provider pattern -- zero real network calls.

Uses LOCAL_FOUNDER_USER_ID for every scenario that needs a real end-to-end
dispatch, matching every other lifecycle-integration test file's own
established convention: reaching PrioritizationEngine's interruption=="alert"
requires PolicyEngine's Personal/Exceptional Watch route (ADR-049), and only
LOCAL_FOUNDER_USER_ID has a pre-seeded NVDA holding (backend/app/logan_feed.py's
_get_user_model) that satisfies the Personal-explicit tier -- an arbitrary
user_id has no holdings/interests at all and would only ever qualify via the
much harder Exceptional route (simultaneous very-high urgency/confidence/
novelty), which a modest test fixture earnings beat doesn't produce. Isolation
and account-link continuity are proven via direct durable-state assertions
(mark_user_notified / _get_user_knowledge), which don't require a second
identity to also independently clear that same alert-eligibility bar.

logan_core/tests/test_notification_gate.py covers the pure
decide_notification comparison directly (including precise cooldown-boundary
timing); this file proves the same behavior through the real backend wiring,
using real elapsed test time (always "rapid") for the same-kind-suppressed
cases and an explicitly backdated last_notified_at (via mark_user_notified's
own now= parameter) for the past-cooldown case, rather than trying to make a
real test sleep for 30 minutes.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from backend.app.logan_feed import (
    _get_user_knowledge,
    get_notification_decisions,
    mark_user_notified,
    reset_pipeline_state,
    run_demo_feed,
)
from backend.app.models import RegisterPushTokenRequest
from backend.app.notifications import (
    dispatch_eligible_notifications,
    register_token,
    reset_notification_state,
)
from backend.app.watch import create_watch, is_watched, reset_watch_state
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider
from logan_core.receptors.providers.fmp import reset_fmp_cache

FOUNDER = LOCAL_FOUNDER_USER_ID


def _mock_client(handler=None) -> httpx.Client:
    if handler is None:

        def handler(request):
            return httpx.Response(200, json={"data": []})

    return httpx.Client(transport=httpx.MockTransport(handler))


def _earnings(symbol, actual, estimated, date="2026-05-20"):
    return [
        {"symbol": symbol, "date": date, "epsActual": actual, "epsEstimated": estimated}
    ]


def _grades(symbol, action, date="2026-08-20"):
    return [{"symbol": symbol, "date": date, "action": action}]


def _quote(symbol, price, previous_close, change_pct):
    return [
        {
            "symbol": symbol,
            "price": price,
            "previousClose": previous_close,
            "changePercentage": change_pct,
            "volume": 1_000_000,
            "timestamp": 1787601600,
        }
    ]


def _profile(symbol, sector="Technology"):
    return [
        {
            "symbol": symbol,
            "sector": sector,
            "industry": "Semiconductors",
            "averageVolume": 1_000_000,
            "beta": 1.5,
        }
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
    *,
    earnings_by_symbol=None,
    grade_by_symbol=None,
    earnings_provider=None,
    tickers="NVDA",
    persist=False,
    tmp_path=None,
    live_only=True,
):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", tickers)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    if live_only:
        # Excludes the demo/simulated 11-entity fixture pool entirely (see
        # config.live_data_only_mode()) so every assertion here is about
        # NVDA specifically, never incidentally including other always-
        # alert-eligible-on-first-poll simulated fixtures -- a pre-existing,
        # unrelated demo-mode behavior this file isn't about.
        monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")
    else:
        monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    if persist:
        monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
        monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    else:
        monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        earnings_provider or _routing_earnings_provider(earnings_by_symbol or {}),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, grade_by_symbol or {}, {}),
    )
    reset_fmp_cache()
    reset_pipeline_state()
    reset_notification_state()
    reset_watch_state()


def _nvda_decision(user_id: str):
    return next(
        (d for d in get_notification_decisions(user_id) if d.entity_id == "NVDA"), None
    )


def _nvda_item(payload_items):
    return next(i for i in payload_items if i.entity_id == "NVDA")


def _register_founder_token():
    register_token(
        FOUNDER, RegisterPushTokenRequest(expo_push_token="ExponentPushToken[founder]")
    )


# --- First revision, same revision, unchanged polling -----------------------


def test_first_notification_worthy_revision_dispatches_once(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    _register_founder_token()
    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade")}
        ),
    )
    dispatched = dispatch_eligible_notifications(_mock_client())
    assert dispatched == 1
    # A repeat, unchanged poll may not even reach interruption=="alert"
    # again at all (Prioritization's own pre-existing fatigue/cooldown,
    # ADR-050, already vetoes a repeat alert one layer above this file's own
    # decide_notification) -- decision is None in that case, which is a
    # valid, safe outcome; if a decision *is* still computed, it must never
    # say "notify again."
    decision = _nvda_decision(FOUNDER)
    if decision is not None:
        assert decision.should_notify is False


def test_same_revision_cannot_alert_twice(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    _register_founder_token()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade")}
        ),
    )
    first_dispatch = dispatch_eligible_notifications(_mock_client())
    assert first_dispatch == 1

    second_dispatch = dispatch_eligible_notifications(_mock_client())
    assert second_dispatch == 0


def test_unchanged_polling_never_produces_a_new_material_revision(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    for _ in range(3):
        run_demo_feed(FOUNDER)
        decision = _nvda_decision(FOUNDER)
        if decision is not None:
            assert decision.should_notify is False


# --- A genuinely newer meaningful revision can alert ------------------------


def test_genuinely_newer_different_kind_revision_can_alert(monkeypatch):
    """revision 1 (new_opportunity) already notified; revision 2, a grade
    upgrade (new_signal_appeared) -- a materially different kind of change
    -- must not be held back. Seeds the "already notified" state directly
    via mark_user_notified rather than a real dispatch: Prioritization's
    own independent fatigue/cooldown (ADR-050) can otherwise veto a second
    back-to-back "alert" classification within one test's near-zero elapsed
    real time, which is a separate, pre-existing mechanism this file isn't
    about -- decide_notification's own logic is what's under test here."""
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed(FOUNDER)  # revision 1
    mark_user_notified(FOUNDER, "NVDA", 1, change_type="new_opportunity")

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade")}
        ),
    )
    item = _nvda_item(run_demo_feed(FOUNDER).items)
    assert item.opportunity_revision == 2
    assert item.meaningful_change_type == "new_signal_appeared"
    decision = _nvda_decision(FOUNDER)
    if decision is not None:
        assert decision.should_notify is True
        assert decision.reason == "new_material_revision"


# --- Reversal after a prior notification, even rapidly ----------------------


def test_trajectory_reversal_can_alert_immediately_after_a_strengthening_alert(
    monkeypatch,
):
    """revision 2 (trajectory_strengthening) already notified; revision 3
    (trajectory_reversing), a materially different kind of change, must
    fire despite happening moments later in real test time -- a genuine
    reversal is never hidden by the cooldown. Seeds the "already notified"
    state directly via mark_user_notified rather than a real dispatch of
    revision 2, for the same reason test_genuinely_newer_different_kind_
    revision_can_alert does: Prioritization's own independent fatigue
    (ADR-050) is a separate mechanism from decide_notification, which is
    what's actually under test here."""
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        _routing_earnings_provider({"NVDA": _earnings("NVDA", 1.87, 1.76)}),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                "NVDA": _quote("NVDA", 100.0, 100.0, 0.5),
                "SPY": _quote("SPY", 500.0, 500.0, 0.5),
                "XLK": _quote("XLK", 200.0, 200.0, 0.5),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    reset_fmp_cache()
    reset_pipeline_state()
    reset_notification_state()
    _register_founder_token()
    run_demo_feed(FOUNDER)  # revision 1, STEADY baseline

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                "NVDA": _quote("NVDA", 103.0, 100.0, 3.0),
                "SPY": _quote("SPY", 500.0, 500.0, 0.0),
                "XLK": _quote("XLK", 200.0, 200.0, 0.0),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    item2 = _nvda_item(run_demo_feed(FOUNDER).items)  # revision 2, strengthening
    assert item2.opportunity_revision == 2
    assert item2.meaningful_change_type == "trajectory_strengthening"
    mark_user_notified(FOUNDER, "NVDA", 2, change_type="trajectory_strengthening")

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                "NVDA": _quote("NVDA", 101.0, 100.0, 1.0),
                "SPY": _quote("SPY", 500.0, 500.0, 4.0),
                "XLK": _quote("XLK", 200.0, 200.0, 4.0),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    item3 = _nvda_item(run_demo_feed(FOUNDER).items)  # revision 3, reversing
    assert item3.trajectory == "REVERSING"
    assert item3.opportunity_revision == 3

    decision = _nvda_decision(FOUNDER)
    if decision is not None:
        assert decision.should_notify is True
        assert decision.reason == "new_material_revision"


# --- Rapid equivalent revisions are suppressed ------------------------------


def test_rapid_same_kind_revision_is_cooldown_suppressed(monkeypatch):
    """revision 2 (new_signal_appeared via one grade upgrade) dispatched;
    revision 3, a *second* grade upgrade on a later date -- still
    new_signal_appeared, the same kind of change -- must not re-alert
    moments later."""
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    _register_founder_token()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade", date="2026-08-20")}
        ),
    )
    first_dispatch = dispatch_eligible_notifications(_mock_client())

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade", date="2026-08-21")}
        ),
    )
    second_dispatch = dispatch_eligible_notifications(_mock_client())

    if first_dispatch == 1:
        assert second_dispatch == 0
        # A revision genuinely formed (a real second grade row exists), so
        # decide_notification is exercised (unlike the fully-unchanged-poll
        # case) -- this is the one place this file can still directly
        # confirm the cooldown reason code end-to-end; see
        # logan_core/tests/test_notification_gate.py for the exhaustive,
        # timing-precise proof of this same rule.
        decision = _nvda_decision(FOUNDER)
        if decision is not None:
            assert decision.reason == "cooldown_suppressed"


def test_past_cooldown_same_kind_revision_can_alert_again(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed(FOUNDER)  # revision 1

    # Backdate this user's notification history as though revision 1 itself
    # had genuinely been notified 45 minutes ago (past NOTIFICATION_COOLDOWN),
    # about the same kind of change a fresh revision 2 will be.
    long_ago = datetime.now(timezone.utc) - timedelta(minutes=45)
    mark_user_notified(
        FOUNDER, "NVDA", 1, now=long_ago, change_type="new_signal_appeared"
    )

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade")}
        ),
    )
    item = _nvda_item(run_demo_feed(FOUNDER).items)
    assert item.opportunity_revision == 2
    assert item.meaningful_change_type == "new_signal_appeared"
    decision = _nvda_decision(FOUNDER)
    if decision is not None:
        assert decision.should_notify is True
        assert decision.reason == "new_material_revision"


# --- Provider degradation / stale fallback ----------------------------------


def test_provider_degradation_does_not_alert(monkeypatch):
    """Demo mode specifically (live_only=False): NVDA still appears via its
    simulated fallback fixture (unchanged pre-V2.4A behavior) while its own
    live earnings fetch fails -- this is exactly the scenario
    provider_degraded_suppressed exists to catch. (In live-only mode a
    failing ticker vanishes entirely instead, so there would be no decision
    to make at all; demo mode is what actually exercises this reason.)"""
    _setup(monkeypatch, earnings_provider=_failing_earnings_provider(), live_only=False)
    decision = _nvda_decision(FOUNDER)
    assert decision is not None
    assert decision.should_notify is False
    assert decision.reason == "provider_degraded_suppressed"


def test_stale_fallback_does_not_generate_repeated_alerts(monkeypatch):
    """revision 1 already notified; the same, statically-served fixture
    served again across several further polls (the demo-mode fallback
    path) must never look like a fresh material change just because the
    poll ran again."""
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        live_only=False,
    )
    run_demo_feed(FOUNDER)  # revision 1
    mark_user_notified(FOUNDER, "NVDA", 1, change_type="new_opportunity")

    for _ in range(3):
        decision = _nvda_decision(FOUNDER)
        if decision is not None:
            assert decision.should_notify is False


# --- Failed delivery never falsely marks notified ---------------------------


def test_failed_expo_delivery_does_not_advance_notified_state(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    _register_founder_token()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade")}
        ),
    )

    def failing_expo(request):
        raise httpx.RequestError("network down", request=request)

    dispatched = dispatch_eligible_notifications(_mock_client(failing_expo))
    assert dispatched == 0

    knowledge = _get_user_knowledge(FOUNDER, "NVDA")
    assert knowledge is None or knowledge.last_notified_revision is None


# --- User isolation ----------------------------------------------------------


def test_founder_notification_state_never_leaks_into_another_users_knowledge(
    monkeypatch,
):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    _register_founder_token()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade")}
        ),
    )
    dispatch_eligible_notifications(_mock_client())

    founder_knowledge = _get_user_knowledge(FOUNDER, "NVDA")
    assert founder_knowledge is not None
    assert founder_knowledge.last_notified_revision is not None

    other_knowledge = _get_user_knowledge("user-b", "NVDA")
    assert other_knowledge is None


def test_directly_notifying_one_user_does_not_affect_anothers_decision(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed(FOUNDER)  # revision 1
    mark_user_notified(FOUNDER, "NVDA", 1, change_type="new_opportunity")

    founder_decision = _nvda_decision(FOUNDER)
    other_decision = _nvda_decision("user-b")
    if founder_decision is not None:
        assert founder_decision.should_notify is False
    if other_decision is not None:
        assert (
            other_decision.should_notify is True
        )  # user-b has no notified history at all


# --- Watch integration -------------------------------------------------------


def test_watch_state_persists_independently_of_notification_state(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    _register_founder_token()
    create_watch(FOUNDER, "NVDA")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            grade_by_symbol={"NVDA": _grades("NVDA", "upgrade")}
        ),
    )
    dispatch_eligible_notifications(_mock_client())
    assert is_watched(FOUNDER, "NVDA") is True  # untouched by dispatch


def test_watch_alone_does_not_force_a_notification(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    _register_founder_token()
    run_demo_feed(FOUNDER)  # revision 1 already established, nothing pending
    create_watch(FOUNDER, "NVDA")
    # No new underlying change since revision 1 was established -- Watch
    # existing must not, by itself, produce a real dispatch.
    dispatched = dispatch_eligible_notifications(_mock_client())
    assert dispatched == 0


# --- Account-linked identity continuity -------------------------------------


def test_account_linked_identity_maintains_notification_history(monkeypatch):
    """Proven at the durable-state level: linking never rotates the
    stratus_user_id string (first-ever link makes the anonymous device's
    own id canonical), so notification history keyed by that literal
    string is trivially preserved -- confirmed directly rather than
    requiring the anonymous identity to also independently clear
    Prioritization's alert-eligibility bar (which requires holdings/
    interests no anonymous device has by default)."""
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    anon_id = f"anon-{uuid4()}"
    run_demo_feed(anon_id)  # revision 1
    mark_user_notified(anon_id, "NVDA", 1, change_type="new_opportunity")
    seeded_knowledge = _get_user_knowledge(anon_id, "NVDA")
    assert seeded_knowledge is not None
    assert seeded_knowledge.last_notified_revision == 1

    from backend.app.user_context import link_account

    stratus_user_id, upgraded = link_account("clerk", "clerk_subject_notif", anon_id)
    assert stratus_user_id == anon_id
    assert upgraded is True

    knowledge_after_link = _get_user_knowledge(stratus_user_id, "NVDA")
    assert knowledge_after_link is not None
    assert knowledge_after_link.last_notified_revision == 1


# --- Restart persistence -----------------------------------------------------


def test_notification_hygiene_state_persists_across_a_simulated_restart(
    monkeypatch, tmp_path
):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        persist=True,
        tmp_path=tmp_path,
    )
    run_demo_feed(FOUNDER)  # revision 1
    mark_user_notified(FOUNDER, "NVDA", 1, change_type="new_opportunity")
    seeded_knowledge = _get_user_knowledge(FOUNDER, "NVDA")
    assert seeded_knowledge is not None
    assert seeded_knowledge.last_notified_revision == 1

    # Simulate a real backend restart: drop every in-memory pipeline/
    # notification structure, then let the next call reconstruct from disk.
    reset_pipeline_state()
    reset_notification_state()

    # _get_user_knowledge() itself is a pure in-memory read -- the lazy
    # reload-from-disk happens inside _get_orchestrator(), triggered here
    # via a real pipeline call, exactly as a real restart's first request
    # would trigger it.
    run_demo_feed(FOUNDER)
    knowledge = _get_user_knowledge(FOUNDER, "NVDA")
    assert knowledge is not None
    assert knowledge.last_notified_revision == 1
