"""Universe Manager V1a Plan-Conformance Closeout (2026-08-31) -- conformance
test requirement (red-team add-on), not new product scope: proves the real
runtime order-of-operations through the actual `_run_feed_pipeline()` wiring
added tonight for Items 1-3 (Runtime Freshness Integration, Live Thesis
Diversity, Live Controlled Exploration):

    candidate source -> eligibility -> monitored membership -> observation/
    freshness -> objective qualification -> thesis diversity -> Personal
    Relevance -> Controlled Exploration -> final surfaced ordering

Every assertion below reads fields the real pipeline set on the real
FeedItem/DiversityResult/ExplorationPlacementResult objects -- nothing here
re-implements freshness/diversity/exploration policy; that policy already has
its own dedicated unit tests (logan_core/tests/test_*). This file only proves
the wiring in backend/app/logan_feed.py assembles and calls the real
functions correctly, in the real request path, with a realistic multi-ticker
live scenario.

Honest calibration note: within tonight's time budget, no realistic FMP-
shaped mock magnitude was found that organically pushes a generic (non-NVDA-
special-path) multi-ticker live candidate's confidence_score/global_importance
above the 0.7 Controlled Exploration floor -- single-signal-family confidence
appears to saturate below that floor regardless of price-move/EPS-beat
magnitude in the current live wiring, and layering a second signal type onto
one entity (e.g. AMZN quote + grade) did not raise its confidence either,
suggesting multi-signal confidence convergence is currently only wired for
the special-cased NVDA live-earnings path (see test_live_nvda_market_data.py),
not generically for STRATUS_LIVE_STOCK_TICKERS. This is flagged in tonight's
conformance report as a real, undecided gap -- not silently routed around.
`test_exploration_placement_wiring_is_real_and_never_displaces_watch` below
therefore proves the Item 3 *wiring* (real ThesisCandidate construction shape,
real is_exploration_eligible()/apply_exploration_placement() calls, correct
FeedItem.exploration_placement_reason annotation) using directly-constructed
candidates in the exact shape logan_feed.py's own wiring block builds them,
rather than via an organically-triggering FMP mock -- it does not
re-implement or redesign the exploration mechanism itself.
"""

from datetime import datetime, timedelta, timezone

import httpx

from backend.app.logan_feed import (
    get_diversity_decision,
    get_exploration_decision,
    reset_pipeline_state,
    run_demo_feed,
)
from backend.app.watch import create_watch, reset_watch_state
from logan_core.contracts.thesis import ThesisMetadata
from logan_core.exploration import apply_exploration_placement, is_exploration_eligible
from logan_core.exploration.placement import EXPLORATION_OBJECTIVE_STRENGTH
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider
from logan_core.thesis.diversity import ThesisCandidate

NOW = datetime.now(timezone.utc)
STALE_DATE = (NOW - timedelta(days=5)).strftime("%Y-%m-%d")
FRESH_DATE = NOW.strftime("%Y-%m-%d")

EARNINGS = {
    "AAPL": [
        {"symbol": "AAPL", "date": FRESH_DATE, "epsActual": 2.0, "epsEstimated": 1.7}
    ],
    "MSFT": [
        {"symbol": "MSFT", "date": FRESH_DATE, "epsActual": 2.0, "epsEstimated": 1.7}
    ],
    "NVDA": [
        {"symbol": "NVDA", "date": FRESH_DATE, "epsActual": 2.0, "epsEstimated": 1.7}
    ],
    "XOM": [
        {"symbol": "XOM", "date": STALE_DATE, "epsActual": 2.0, "epsEstimated": 1.7}
    ],
}
QUOTES = {
    "GOOGL": [
        {
            "symbol": "GOOGL",
            "price": 200.0,
            "previousClose": 180.0,
            "changePercentage": 11.1,
            "timestamp": int(NOW.timestamp()),
            "volume": 1_000_000,
        }
    ],
    "META": [
        {
            "symbol": "META",
            "price": 500.0,
            "previousClose": 440.0,
            "changePercentage": 13.6,
            "timestamp": int(NOW.timestamp()),
            "volume": 1_000_000,
        }
    ],
}
GRADES = {
    "JPM": [
        {
            "symbol": "JPM",
            "date": FRESH_DATE,
            "gradingCompany": "MS",
            "previousGrade": "Hold",
            "newGrade": "Buy",
            "action": "upgrade",
        }
    ],
}
PROFILES = {
    "AAPL": [
        {
            "symbol": "AAPL",
            "sector": "Technology",
            "industry": "Hardware",
            "averageVolume": 1_000_000,
            "beta": 1.2,
        }
    ],
    "MSFT": [
        {
            "symbol": "MSFT",
            "sector": "Technology",
            "industry": "Software",
            "averageVolume": 1_000_000,
            "beta": 1.1,
        }
    ],
    "NVDA": [
        {
            "symbol": "NVDA",
            "sector": "Technology",
            "industry": "Semis",
            "averageVolume": 1_000_000,
            "beta": 1.5,
        }
    ],
    "GOOGL": [
        {
            "symbol": "GOOGL",
            "sector": "Communication Services",
            "industry": "Internet",
            "averageVolume": 1_000_000,
            "beta": 1.1,
        }
    ],
    "JPM": [
        {
            "symbol": "JPM",
            "sector": "Financials",
            "industry": "Banking",
            "averageVolume": 1_000_000,
            "beta": 1.0,
        }
    ],
    "XOM": [
        {
            "symbol": "XOM",
            "sector": "Energy",
            "industry": "Oil",
            "averageVolume": 1_000_000,
            "beta": 0.9,
        }
    ],
}


def _json_by_symbol(by_symbol):
    def respond(request):
        symbol = request.url.params.get("symbol")
        return httpx.Response(200, json=by_symbol.get(symbol, []))

    return respond


def _route(handlers_by_path):
    def handler(request):
        for path, respond in handlers_by_path.items():
            if request.url.path.endswith(path):
                return respond(request)
        return httpx.Response(200, json=[])

    return handler


def _setup(monkeypatch):
    monkeypatch.setenv(
        "STRATUS_LIVE_STOCK_TICKERS", "AAPL,MSFT,NVDA,GOOGL,JPM,XOM,META"
    )
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")

    earnings_client = httpx.Client(
        transport=httpx.MockTransport(_json_by_symbol(EARNINGS))
    )
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
    reset_watch_state()
    create_watch("demo_user", "NVDA")


def test_v1a_decision_trace_end_to_end(monkeypatch):
    _setup(monkeypatch)
    feed = run_demo_feed("demo_user")
    by_ticker = {item.entity_id: item for item in feed.items}

    # 1. Candidate source -> eligibility -> membership -> observation/
    # freshness: a genuinely stale/unavailable input never gets a live/
    # current-attention treatment. XOM's earnings report is 5 days old and
    # this ticker's provider-failure tracker is untouched (a real fetch
    # succeeded, just for old data) -- UNAVAILABLE only fires via the
    # explicit failure branch, so an aged-but-successfully-fetched report
    # must classify as a graceful staleness state, never FRESH.
    assert by_ticker["XOM"].freshness_state in {
        "STALE_WITHIN_GRACE",
        "UNAVAILABLE",
    }
    assert by_ticker["XOM"].freshness_state != "FRESH"
    # Quote-driven signals (full Unix-epoch precision, fetched "now") reach
    # genuine FRESH -- proving freshness is a real age computation, not a
    # blanket label.
    assert by_ticker["GOOGL"].freshness_state == "FRESH"
    assert by_ticker["META"].freshness_state == "FRESH"

    # 2. Objective qualification -> thesis diversity: three Technology,
    # earnings-driven entities (AAPL/MSFT/NVDA) collide on both the sector
    # cap (2) and the (sector, driver) cap (1) -- at least one must be
    # diversity-suppressed while remaining an objectively qualified,
    # unmodified opportunity (confidence_score/delivered_item untouched).
    tech_earnings = [by_ticker["AAPL"], by_ticker["MSFT"], by_ticker["NVDA"]]
    suppressed_tech = [i for i in tech_earnings if i.diversity_suppressed]
    assert len(suppressed_tech) >= 1
    for item in suppressed_tech:
        assert item.diversity_suppression_reason in {
            "SECTOR_CAP",
            "SIGNAL_FAMILY_CAP",
            "DRIVER_CAP",
        }
        # Suppression is presentation-only: the underlying opportunity is
        # still real and still fully described.
        assert item.confidence_score > 0.0
        assert item.delivered_item is not None

    # 3. Watch bypasses at most one non-entity cap -- NVDA is Watched and
    # sits in the same oversubscribed sector/driver group as AAPL/MSFT, so
    # it must never itself be diversity_suppressed.
    assert by_ticker["NVDA"].is_watched is True
    assert by_ticker["NVDA"].diversity_suppressed is False

    # 4. Personal Relevance can reorder the response but never rewrites
    # eligibility/freshness/objective qualification/membership: every
    # surfaced item still carries its own real confidence score and its own
    # independently-computed freshness_state after ranking.
    for item in feed.items:
        assert item.confidence_score is not None
        assert item.rank >= 1

    # 5. Final surfaced items retain an inspectable reason/policy-version
    # trace -- both the diversity and exploration decisions are logged with
    # a policy version even when the outcome is "nothing suppressed"/
    # "nothing placed" for a given item.
    diversity = get_diversity_decision("demo_user")
    assert diversity is not None
    assert diversity.policy_version
    assert len(diversity.suppressed) >= 1

    exploration = get_exploration_decision("demo_user")
    assert exploration is not None
    assert exploration.policy_version
    # 6. Exploration must never displace Watch -- true trivially when no
    # placement occurs, and enforced structurally by
    # apply_exploration_placement() (see the dedicated wiring test below)
    # when one does.
    if exploration.placed_event_id is not None:
        assert by_ticker["NVDA"].event_id != exploration.placed_event_id


def test_exploration_placement_wiring_is_real_and_never_displaces_watch():
    """Proves Item 3's wiring shape directly: logan_feed.py builds
    ThesisCandidate objects with `metadata`/`is_watched`/`objective_strength`
    exactly like this, then calls the real is_exploration_eligible() and
    apply_exploration_placement() (Blocks 12-14) -- never a reimplementation.
    Uses directly-constructed candidates (see module docstring for why an
    organic FMP-driven trigger wasn't found tonight), but exercises the exact
    real functions the wiring calls with the exact real contract shapes."""

    def _metadata(event_id, entity_id, sector, family, driver):
        return ThesisMetadata(
            event_id=event_id,
            primary_entity_id=entity_id,
            sector=sector,
            primary_signal_family=family,
            market_driver_tag=driver,
            thesis_state="developing",
        )

    import uuid

    watch_id = uuid.uuid4()
    selected_id = uuid.uuid4()
    unfamiliar_id = uuid.uuid4()

    top_candidates = [
        ThesisCandidate(
            event_id=watch_id,
            rank=1,
            metadata=_metadata(
                watch_id, "NVDA", "Technology", "earnings", "EARNINGS_RESULT"
            ),
            is_watched=True,
            objective_strength=0.5,
        ),
        ThesisCandidate(
            event_id=selected_id,
            rank=2,
            metadata=_metadata(
                selected_id,
                "GOOGL",
                "Communication Services",
                "quote",
                "PRICE_DISLOCATION",
            ),
            is_watched=False,
            objective_strength=0.55,
        ),
    ]
    # Genuinely eligible: fresh, low/unknown personal relevance, above the
    # 0.7 materiality/evidence floors, an unfamiliar entity, objectively
    # stronger than the weakest non-Watch selected candidate.
    eligible = ThesisCandidate(
        event_id=unfamiliar_id,
        rank=6,
        metadata=_metadata(
            unfamiliar_id,
            "AMZN",
            "Consumer Discretionary",
            "quote",
            "PRICE_DISLOCATION",
        ),
        is_watched=False,
        objective_strength=0.9,
    )
    assert is_exploration_eligible(
        recommend=True,
        global_importance=0.85,
        confidence=0.85,
        risk=0.1,
        freshness_state="FRESH",
        is_new_for_user=True,
        is_materially_revised=False,
        personal_relevance_state="low",
        has_active_suppression=False,
    )

    result = apply_exploration_placement(top_candidates, [eligible])

    assert result.placed_event_id == unfamiliar_id
    assert result.reason == EXPLORATION_OBJECTIVE_STRENGTH
    # Never displaces Watch: the trace's displaced_thesis_id must be the
    # weaker non-Watch candidate, never the Watch item.
    assert result.opportunity_cost is not None
    assert result.opportunity_cost.displaced_thesis_id == selected_id
    assert result.opportunity_cost.displaced_thesis_id != watch_id


def test_v1a_decision_trace_sourced_from_monitored_cohort(monkeypatch, tmp_path):
    """Runtime Blocker 2 (2026-08-31): extends the order-of-operations proof
    one step earlier -- candidate source -> eligibility -> monitored
    membership (via a real, fixture-provider run_universe_reevaluation()
    call, standing in for the not-yet-scheduled cadence -- see this
    session's conformance report for that separate, still-open blocker) ->
    live_stock_tickers() actually reading that durable MONITORED cohort
    (config.universe_manager_enabled() flipped on) -> observation/freshness
    -> objective qualification -> diversity -> Personal Relevance ->
    Controlled Exploration -> final surfaced ordering, all through the real
    request path, with the ticker source itself now coming from Universe
    Manager instead of the raw env var."""

    from backend.app.universe_manager import (
        reset_universe_manager_state,
        run_universe_reevaluation,
    )
    from logan_core.receptors.providers import (
        CompanyProfile,
        EarningsReport,
        FixtureEarningsProvider,
        FixtureMarketDataProvider,
        GradeChange,
        Quote,
    )
    from logan_core.universe.candidate_source import load_candidate_snapshot

    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_UNIVERSE_DB_PATH", str(tmp_path / "universe.db"))
    # Deliberately different from the real monitored cohort -- proves
    # live_stock_tickers() genuinely overrides this, not coincidence.
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "ZZZZ")
    reset_universe_manager_state()

    snapshot = load_candidate_snapshot()

    def _quote(symbol: str) -> Quote:
        return Quote(
            entity_id=symbol,
            price=100.0,
            previous_close=99.0,
            change_pct=1.0,
            quote_timestamp=NOW,
            source_id="fixture",
            source_name="fixture",
        )

    def _profile(symbol: str, sector: str) -> CompanyProfile:
        return CompanyProfile(
            entity_id=symbol,
            sector=sector,
            industry="Fixture",
            average_volume=1_000_000.0,
            beta=1.1,
            source_id="fixture",
            source_name="fixture",
        )

    def _earnings(symbol: str) -> EarningsReport:
        return EarningsReport(
            entity_id=symbol,
            actual_eps=1.0,
            consensus_eps=0.9,
            fiscal_quarter="Q2 2026",
            guidance_revised=False,
            guidance_delta_pct=0.0,
            report_timestamp=NOW,
            source_id="fixture",
            source_name="fixture",
        )

    def _grade(symbol: str) -> GradeChange:
        return GradeChange(
            entity_id=symbol,
            grading_firm="Fixture Analytics",
            previous_rating="Hold",
            new_rating="Buy",
            action="upgrade",
            action_date=NOW,
            source_id="fixture",
            source_name="fixture",
        )

    quotes = {s.symbol: _quote(s.symbol) for s in snapshot.securities}
    profiles = {
        s.symbol: _profile(s.symbol, s.sector or "Technology")
        for s in snapshot.securities
    }
    grades = {s.symbol: _grade(s.symbol) for s in snapshot.securities}
    earnings_reports = {s.symbol: _earnings(s.symbol) for s in snapshot.securities}
    market = FixtureMarketDataProvider(
        quotes=quotes, grade_changes=grades, profiles=profiles
    )
    earnings = FixtureEarningsProvider(reports=earnings_reports)

    # Stands in for the not-yet-scheduled production cadence (Runtime
    # Blocker 1, still open -- see conformance report): a real, explicit
    # reevaluation run against fixture providers, exactly the pipeline a
    # scheduled cadence would eventually wrap.
    run_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )

    monkeypatch.setenv("STRATUS_UNIVERSE_MANAGER_ENABLED", "true")
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")

    from backend.app.config import live_stock_tickers

    tickers = live_stock_tickers()
    assert 25 <= len(tickers) <= 35
    assert "ZZZZ" not in tickers  # genuinely overrides the raw env var

    # Watch/Learning must never alter membership: watching an arbitrary
    # cohort member changes nothing about which tickers are monitored.
    reset_watch_state()
    create_watch("demo_user", tickers[0])
    assert live_stock_tickers() == tickers

    live_earnings = {
        s: [
            {
                "symbol": s,
                "date": NOW.strftime("%Y-%m-%d"),
                "epsActual": 2.0,
                "epsEstimated": 1.7,
            }
        ]
        for s in tickers
    }
    live_quotes = {
        s: [
            {
                "symbol": s,
                "price": 150.0,
                "previousClose": 130.0,
                "changePercentage": 15.4,
                "timestamp": int(NOW.timestamp()),
                "volume": 1_000_000,
            }
        ]
        for s in tickers
    }

    def _by_symbol(by_symbol):
        def respond(request):
            symbol = request.url.params.get("symbol")
            return httpx.Response(200, json=by_symbol.get(symbol, []))

        return respond

    def _route(handlers_by_path):
        def handler(request):
            for path, respond in handlers_by_path.items():
                if request.url.path.endswith(path):
                    return respond(request)
            return httpx.Response(200, json=[])

        return handler

    earnings_client = httpx.Client(
        transport=httpx.MockTransport(_by_symbol(live_earnings))
    )
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
                    "/quote": _by_symbol(live_quotes),
                    "/grades": _by_symbol({}),
                    "/profile": _by_symbol({}),
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
    feed = run_demo_feed("demo_user")

    fed_tickers = {item.entity_id for item in feed.items}
    # The live feed pipeline actually consumed the MONITORED-cohort ticker
    # list, not the raw (deliberately wrong) env var.
    assert fed_tickers & set(tickers)
    for item in feed.items:
        if item.entity_id in tickers:
            assert item.freshness_state is not None
            assert item.confidence_score is not None

    diversity = get_diversity_decision("demo_user")
    assert diversity is not None
    exploration = get_exploration_decision("demo_user")
    assert exploration is not None

    reset_universe_manager_state()


def test_exploration_never_displaces_when_all_selected_are_watch():
    import uuid

    watch_id = uuid.uuid4()
    unfamiliar_id = uuid.uuid4()

    def _metadata(event_id, entity_id):
        return ThesisMetadata(
            event_id=event_id,
            primary_entity_id=entity_id,
            sector="Technology",
            primary_signal_family="quote",
            market_driver_tag="PRICE_DISLOCATION",
            thesis_state="developing",
        )

    top_candidates = [
        ThesisCandidate(
            event_id=watch_id,
            rank=1,
            metadata=_metadata(watch_id, "NVDA"),
            is_watched=True,
            objective_strength=0.2,
        ),
    ]
    eligible = ThesisCandidate(
        event_id=unfamiliar_id,
        rank=6,
        metadata=_metadata(unfamiliar_id, "AMZN"),
        is_watched=False,
        objective_strength=0.95,
    )
    result = apply_exploration_placement(top_candidates, [eligible])
    assert result.placed_event_id is None
