"""Operational Beta Live Supply V2, Block 1/2 (2026-08-29/30) -- proves
earnings/price-move/analyst-grade now qualify *independently* for a live
ticker, closing the pre-existing coupling where a non-qualifying or missing
earnings report silently starved price-move/analyst-grade signals (and the
market-evidence fetch) for that ticker too, even when one of them
genuinely fired this poll.

Full HTTP-level mocking via httpx.MockTransport (mirrors
test_ask_lifecycle_grounding.py's own established technique) -- no real
network call, real parsing/qualification logic exercised end-to-end through
`run_demo_feed()` -> `_run_feed_pipeline()` in STRATUS_RUNTIME_MODE=live
(live-data-only mode), so an entity only appears in results at all if a
real signal genuinely fired this poll.
"""

import httpx

from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider


def _route(handlers_by_path):
    def handler(request: httpx.Request) -> httpx.Response:
        for path, respond in handlers_by_path.items():
            if request.url.path.endswith(path):
                return respond(request)
        return httpx.Response(200, json=[])

    return handler


def _json_by_symbol(by_symbol: dict):
    def respond(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params.get("symbol")
        return httpx.Response(200, json=by_symbol.get(symbol, []))

    return respond


def _unavailable(request: httpx.Request) -> httpx.Response:
    return httpx.Response(429, text="rate limited")


NON_QUALIFYING_EARNINGS = {
    "NVDA": [
        {
            "symbol": "NVDA",
            "date": "2026-08-26",
            "epsActual": 1.70,
            "epsEstimated": 1.76,
        }
    ]
}
NO_EARNINGS = {}

QUALIFYING_PRICE_MOVE = {
    "NVDA": [
        {
            "symbol": "NVDA",
            "price": 120.0,
            "previousClose": 110.0,
            "changePercentage": 9.09,
            "timestamp": 1798000000,
            "volume": 1000000,
        }
    ]
}
NON_QUALIFYING_PRICE_MOVE = {
    "NVDA": [
        {
            "symbol": "NVDA",
            "price": 111.0,
            "previousClose": 110.0,
            "changePercentage": 0.9,
            "timestamp": 1798000000,
            "volume": 1000000,
        }
    ]
}
QUALIFYING_UPGRADE = {
    "NVDA": [
        {
            "symbol": "NVDA",
            "date": "2026-08-26",
            "gradingCompany": "Morgan Stanley",
            "previousGrade": "Hold",
            "newGrade": "Buy",
            "action": "upgrade",
        }
    ]
}
NON_TRIGGERING_MAINTAIN = {
    "NVDA": [
        {
            "symbol": "NVDA",
            "date": "2026-08-26",
            "gradingCompany": "Morgan Stanley",
            "previousGrade": "Buy",
            "newGrade": "Buy",
            "action": "maintain",
        }
    ]
}


def _wire(monkeypatch, *, earnings, quotes, grades):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")

    earnings_client = httpx.Client(
        transport=httpx.MockTransport(_json_by_symbol(earnings))
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
                    "/quote": _json_by_symbol(quotes),
                    "/grades": _json_by_symbol(grades),
                    "/profile": lambda r: httpx.Response(200, json=[]),
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


def _nvda_item(feed):
    return next((i for i in feed.items if i.entity_id == "NVDA"), None)


# --- Price qualifies independently, without earnings ----------------------


def test_price_move_qualifies_without_a_qualifying_earnings_report(monkeypatch):
    _wire(
        monkeypatch,
        earnings=NON_QUALIFYING_EARNINGS,
        quotes=QUALIFYING_PRICE_MOVE,
        grades={},
    )
    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    item = _nvda_item(feed)
    assert (
        item is not None
    ), "NVDA must appear from an independently-qualifying price move alone"
    assert item.signal_type == "price_change"


def test_price_move_qualifies_with_no_earnings_data_at_all(monkeypatch):
    _wire(monkeypatch, earnings=NO_EARNINGS, quotes=QUALIFYING_PRICE_MOVE, grades={})
    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    assert _nvda_item(feed) is not None


def test_sub_threshold_price_move_does_not_qualify_alone(monkeypatch):
    _wire(
        monkeypatch,
        earnings=NON_QUALIFYING_EARNINGS,
        quotes=NON_QUALIFYING_PRICE_MOVE,
        grades={},
    )
    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    assert (
        _nvda_item(feed) is None
    ), "no signal family fired -- NVDA must be honestly absent"


# --- Analyst grade qualifies independently, without earnings ---------------


def test_analyst_upgrade_qualifies_without_a_qualifying_earnings_report(monkeypatch):
    _wire(
        monkeypatch,
        earnings=NON_QUALIFYING_EARNINGS,
        quotes={},
        grades=QUALIFYING_UPGRADE,
    )
    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    assert _nvda_item(feed) is not None


def test_maintain_grade_does_not_qualify_alone(monkeypatch):
    _wire(
        monkeypatch,
        earnings=NON_QUALIFYING_EARNINGS,
        quotes={},
        grades=NON_TRIGGERING_MAINTAIN,
    )
    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    assert _nvda_item(feed) is None


# --- Cross-signal coexistence -----------------------------------------------


def test_earnings_and_price_move_can_coexist_on_one_opportunity(monkeypatch):
    qualifying_earnings = {
        "NVDA": [
            {
                "symbol": "NVDA",
                "date": "2026-08-26",
                "epsActual": 2.0,
                "epsEstimated": 1.76,
            }
        ]
    }
    _wire(
        monkeypatch,
        earnings=qualifying_earnings,
        quotes=QUALIFYING_PRICE_MOVE,
        grades={},
    )
    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    item = _nvda_item(feed)
    assert item is not None
    assert item.rank >= 1  # a single coherent opportunity, not two competing entries
    assert len([i for i in feed.items if i.entity_id == "NVDA"]) == 1


def test_analyst_and_price_move_can_coexist_without_earnings(monkeypatch):
    _wire(
        monkeypatch,
        earnings=NON_QUALIFYING_EARNINGS,
        quotes=QUALIFYING_PRICE_MOVE,
        grades=QUALIFYING_UPGRADE,
    )
    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    item = _nvda_item(feed)
    assert item is not None
    assert len([i for i in feed.items if i.entity_id == "NVDA"]) == 1


# --- Provider failure isolation ---------------------------------------------


def test_a_failed_earnings_fetch_does_not_suppress_a_valid_price_signal(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")

    earnings_client = httpx.Client(transport=httpx.MockTransport(_unavailable))
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
                    "/quote": _json_by_symbol(QUALIFYING_PRICE_MOVE),
                    "/grades": lambda r: httpx.Response(200, json=[]),
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

    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    assert (
        _nvda_item(feed) is not None
    ), "a failed earnings fetch must not suppress a valid price signal"
    assert (
        feed.provider_degraded is True
    ), "the earnings failure must still be surfaced honestly"


def test_a_failed_price_fetch_does_not_suppress_a_valid_earnings_signal(monkeypatch):
    qualifying_earnings = {
        "NVDA": [
            {
                "symbol": "NVDA",
                "date": "2026-08-26",
                "epsActual": 2.0,
                "epsEstimated": 1.76,
            }
        ]
    }
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")

    earnings_client = httpx.Client(
        transport=httpx.MockTransport(_json_by_symbol(qualifying_earnings))
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real", client=earnings_client
        ),
    )
    market_client = httpx.Client(transport=httpx.MockTransport(_unavailable))
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real", client=market_client
        ),
    )
    reset_pipeline_state()

    feed = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    assert (
        _nvda_item(feed) is not None
    ), "a failed price/grade fetch must not suppress a valid earnings signal"


# --- No duplicate polling-generated events ----------------------------------


def test_repeated_polls_never_duplicate_the_opportunity(monkeypatch):
    _wire(
        monkeypatch,
        earnings=NON_QUALIFYING_EARNINGS,
        quotes=QUALIFYING_PRICE_MOVE,
        grades={},
    )
    first = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    second = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    assert len([i for i in first.items if i.entity_id == "NVDA"]) == 1
    assert len([i for i in second.items if i.entity_id == "NVDA"]) == 1
    first_item = _nvda_item(first)
    second_item = _nvda_item(second)
    assert first_item is not None and second_item is not None
    assert (
        first_item.event_id == second_item.event_id
    ), "the same underlying opportunity must keep a stable event_id across polls"
