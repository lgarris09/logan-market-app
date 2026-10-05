"""Freshness clock correction (ADR-075): freshness is the age of STRATUS's
latest successful fetch of an item's evidence, compared against that
family's refresh/cache lifetime -- never the age of the market event.

Event age keeps its existing owners (lifecycle aging, EvidenceTrust's
recency score); these tests prove both halves.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

import backend.app.logan_feed as feed
from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from backend.tests.test_universe_v1a_decision_trace import (
    GRADES,
    PROFILES,
    QUOTES,
    _json_by_symbol,
    _route,
)
from logan_core.receptors.providers import (
    EARNINGS_CACHE_TTL_SECONDS,
    EARNINGS_STALE_GRACE_SECONDS,
    FmpEarningsProvider,
    FmpMarketDataProvider,
    classify_freshness,
    fmp_last_successful_fetch_age_seconds,
    signal_family_contract,
)
from logan_core.receptors.providers.fmp import (
    FmpProviderError,
    FmpResponseCache,
    _shared_fmp_cache,
)

NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")
FIVE_DAYS_AGO = (NOW - timedelta(days=5)).strftime("%Y-%m-%d")
SIX_WEEKS_AGO = (NOW - timedelta(days=42)).strftime("%Y-%m-%d")

EARNINGS = {
    "AAPL": [{"symbol": "AAPL", "date": TODAY, "epsActual": 2.0, "epsEstimated": 1.7}],
    "XOM": [
        {"symbol": "XOM", "date": FIVE_DAYS_AGO, "epsActual": 2.0, "epsEstimated": 1.7}
    ],
    "MSFT": [
        {"symbol": "MSFT", "date": SIX_WEEKS_AGO, "epsActual": 2.0, "epsEstimated": 1.7}
    ],
}


class _Switch:
    """Lets a test turn the mocked earnings endpoint into an outage."""

    failing = False


def _setup_live(monkeypatch, tickers="AAPL,XOM,MSFT,GOOGL,META,JPM"):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", tickers)
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")
    switch = _Switch()

    def earnings_handler(request):
        if switch.failing:
            return httpx.Response(503, json={"error": "simulated outage"})
        return _json_by_symbol(EARNINGS)(request)

    earnings_client = httpx.Client(transport=httpx.MockTransport(earnings_handler))
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real", client=earnings_client
        ),
    )
    market_client = httpx.Client(
        transport=httpx.MockTransport(
            _route(
                {
                    "/quote": _json_by_symbol(QUOTES),
                    "/grades": _json_by_symbol(GRADES),
                    "/profile": _json_by_symbol(PROFILES),
                }
            )
        )
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real", client=market_client
        ),
    )
    reset_pipeline_state()
    return switch


def _by_ticker():
    return {item.entity_id: item for item in run_demo_feed("demo_user").items}


def _age_cache_entry(endpoint: str, entity_id: str, seconds: float) -> None:
    """Moves one entry's fetch time into the past, as if that long had
    elapsed since STRATUS last fetched it."""
    _shared_fmp_cache._entries[(endpoint, entity_id)].cached_at -= seconds


# --- the accessor -------------------------------------------------------------


def test_fetch_age_accessor_reports_time_since_the_last_successful_fetch():
    clock = {"now": 1_000.0}
    cache = FmpResponseCache(clock=lambda: clock["now"])
    assert cache.last_successful_fetch_age_seconds("earnings", "AAPL") is None

    cache.get_or_fetch("earnings", "AAPL", 600.0, lambda: "report")
    assert cache.last_successful_fetch_age_seconds("earnings", "AAPL") == 0.0

    clock["now"] += 250.0
    cache.get_or_fetch("earnings", "AAPL", 600.0, lambda: "must-not-be-called")
    assert cache.last_successful_fetch_age_seconds("earnings", "AAPL") == 250.0
    # Keyed like the cache itself: another endpoint or ticker is unknown.
    assert cache.last_successful_fetch_age_seconds("quote", "AAPL") is None
    assert cache.last_successful_fetch_age_seconds("earnings", "MSFT") is None


def test_fetch_age_accessor_is_read_only():
    clock = {"now": 0.0}
    cache = FmpResponseCache(clock=lambda: clock["now"])
    cache.get_or_fetch("quote", "AAPL", 600.0, lambda: "quote")
    before = cache.budget_snapshot()
    for _ in range(50):
        cache.last_successful_fetch_age_seconds("quote", "AAPL")
        cache.last_successful_fetch_age_seconds("quote", "NOPE")
    after = cache.budget_snapshot()
    assert after.by_endpoint == before.by_endpoint  # no hit/call counted
    assert set(cache._entries) == {("quote", "AAPL")}


def test_a_refetch_resets_the_age_and_a_stale_grace_serve_does_not():
    clock = {"now": 0.0}
    cache = FmpResponseCache(clock=lambda: clock["now"])
    cache.get_or_fetch("earnings", "AAPL", 100.0, lambda: "v1", stale_grace_seconds=500)

    clock["now"] = 150.0  # past TTL; the provider is down

    def _down():
        raise FmpProviderError("simulated outage", status_code=503)

    served = cache.get_or_fetch(
        "earnings", "AAPL", 100.0, _down, stale_grace_seconds=500
    )
    assert served == "v1"  # served from grace
    # ...and still as old as its real fetch: grace never looks fresh.
    assert cache.last_successful_fetch_age_seconds("earnings", "AAPL") == 150.0

    clock["now"] = 160.0  # the provider is back
    cache._failures.clear()
    cache.get_or_fetch("earnings", "AAPL", 100.0, lambda: "v2", stale_grace_seconds=500)
    assert cache.last_successful_fetch_age_seconds("earnings", "AAPL") == 0.0


# --- recent fetch + old event = fresh -----------------------------------------


def test_recently_fetched_evidence_about_an_old_event_is_fresh(monkeypatch):
    _setup_live(monkeypatch)
    items = _by_ticker()
    # Five days and six weeks after the earnings report, both far beyond
    # the 30h (6h TTL + 24h grace) that used to read UNAVAILABLE.
    assert items["XOM"].freshness_state == "FRESH"
    assert items["MSFT"].freshness_state == "FRESH"
    assert items["AAPL"].freshness_state == "FRESH"
    for ticker in ("XOM", "MSFT"):
        age = fmp_last_successful_fetch_age_seconds("earnings", ticker)
        assert age is not None and age < 60.0


def test_the_recorded_freshness_ratio_uses_fetch_age(monkeypatch):
    recorded = []
    monkeypatch.setattr(
        feed,
        "record_freshness_ratio_observation",
        lambda **kwargs: recorded.append(kwargs),
    )
    _setup_live(monkeypatch)
    _by_ticker()
    earnings = [r for r in recorded if r["signal_family"] == "earnings"]
    assert len(earnings) == 3  # AAPL, XOM, MSFT
    for row in earnings:
        assert row["ttl_seconds"] == EARNINGS_CACHE_TTL_SECONDS
        assert row["age_seconds"] < 60.0  # seconds since fetch, not weeks since report


# --- stale fetch + recent event = stale / unavailable -------------------------


def test_a_stale_fetch_of_a_recent_event_is_not_fresh(monkeypatch):
    switch = _setup_live(monkeypatch)
    assert _by_ticker()["AAPL"].freshness_state == "FRESH"  # event dated today

    # Seven hours pass without a successful refetch: past the 6h TTL,
    # inside the 24h grace. The provider is down, so grace is served.
    _age_cache_entry("earnings", "AAPL", EARNINGS_CACHE_TTL_SECONDS + 3600)
    switch.failing = True
    aapl = _by_ticker()["AAPL"]
    assert aapl.freshness_state in {"STALE_WITHIN_GRACE", "UNAVAILABLE"}
    assert aapl.freshness_state != "FRESH"


def test_within_ttl_but_past_half_reads_recently_observed(monkeypatch):
    _setup_live(monkeypatch)
    _by_ticker()
    _age_cache_entry("earnings", "AAPL", EARNINGS_CACHE_TTL_SECONDS * 0.75)
    assert _by_ticker()["AAPL"].freshness_state == "RECENTLY_OBSERVED"


def test_a_live_item_with_no_fetch_record_fails_closed(monkeypatch):
    _setup_live(monkeypatch)
    monkeypatch.setattr(
        feed, "fmp_last_successful_fetch_age_seconds", lambda endpoint, entity: None
    )
    recorded = []
    monkeypatch.setattr(
        feed,
        "record_freshness_ratio_observation",
        lambda **kwargs: recorded.append(kwargs),
    )
    items = _by_ticker()
    assert items["XOM"].freshness_state == "UNAVAILABLE"
    assert items["GOOGL"].freshness_state == "UNAVAILABLE"
    assert recorded == []  # no age exists, so no ratio is invented


def test_contract_boundaries_are_the_existing_ones():
    contract = signal_family_contract("earnings")
    ttl, grace = EARNINGS_CACHE_TTL_SECONDS, EARNINGS_STALE_GRACE_SECONDS
    assert (contract.target_ttl_seconds, contract.grace_seconds) == (ttl, grace)

    def state(age):
        return classify_freshness(has_value=True, age_seconds=age, contract=contract)

    assert state(ttl * 0.5) == "FRESH"
    assert state(ttl) == "RECENTLY_OBSERVED"
    assert state(ttl + grace) == "STALE_WITHIN_GRACE"
    assert state(ttl + grace + 1) == "UNAVAILABLE"


# --- event age still belongs to its existing owners ---------------------------


def test_event_age_still_drives_recency_weighting_and_thesis_age(monkeypatch):
    """Identical earnings beats, fetched in the same poll, both FRESH --
    but the older event still scores lower (EvidenceTrust recency)."""
    _setup_live(monkeypatch)
    items = _by_ticker()
    recent, older = items["AAPL"], items["MSFT"]
    assert recent.freshness_state == older.freshness_state == "FRESH"
    assert older.confidence_score < recent.confidence_score


def test_lifecycle_aging_is_unaffected_by_the_freshness_clock(monkeypatch):
    """Freshness must not reset lifecycle aging: an opportunity that keeps
    being refetched stays FRESH while its lifecycle state is decided only
    by the lifecycle tracker (never forced back to an active state)."""
    _setup_live(monkeypatch)
    first = _by_ticker()["MSFT"]
    for _ in range(3):
        later = _by_ticker()["MSFT"]
    assert later.freshness_state == "FRESH"
    assert later.lifecycle_state in {first.lifecycle_state, "monitoring"}
    assert later.opportunity_revision == first.opportunity_revision


# --- demo and live agree -------------------------------------------------------


def test_demo_and_live_use_the_same_observation_time_clock(monkeypatch):
    # Live: evidence fetched this poll.
    _setup_live(monkeypatch)
    live_states = {
        item.freshness_state
        for item in run_demo_feed("demo_user").items
        if item.freshness_state is not None
    }
    # Demo: simulated signals captured this poll.
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    reset_pipeline_state()
    demo_states = {
        item.freshness_state
        for item in run_demo_feed("demo_user").items
        if item.freshness_state is not None
    }
    assert live_states == {"FRESH"}
    assert demo_states == {"FRESH"}


# --- nothing else about the feed changes ---------------------------------------


def _everything_but_freshness(items) -> list[tuple]:
    return [
        (
            item.entity_id,
            item.rank,
            item.signal_type,
            item.confidence_label,
            # Two decimals: each run takes seconds, and the pre-existing
            # wall-clock recency decay moves a quote's score in the 4th.
            round(item.confidence_score, 2),
            item.lifecycle_state,
            item.opportunity_revision,
            item.meaningful_change_type,
            item.trajectory,
            item.diversity_suppressed,
            item.diversity_suppression_reason,
            item.exploration_placement_reason,
            item.delivered_item.headline,
            item.delivered_item.why_now,
        )
        for item in items
    ]


@pytest.mark.parametrize("forced_age", [0.0, 10.0**9, None])
def test_freshness_is_an_annotation_and_changes_nothing_else(monkeypatch, forced_age):
    """Whatever the freshness clock says -- fresh, hopelessly stale, or
    unknown -- ranking, confidence, lifecycle, revisions, diversity and
    exploration are identical."""
    _setup_live(monkeypatch)
    baseline = _everything_but_freshness(run_demo_feed("demo_user").items)

    _setup_live(monkeypatch)
    monkeypatch.setattr(
        feed,
        "fmp_last_successful_fetch_age_seconds",
        lambda endpoint, entity: forced_age,
    )
    forced = run_demo_feed("demo_user").items
    assert _everything_but_freshness(forced) == baseline
    expected = "FRESH" if forced_age == 0.0 else "UNAVAILABLE"
    assert {item.freshness_state for item in forced} == {expected}
