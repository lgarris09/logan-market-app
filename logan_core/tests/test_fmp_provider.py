"""Sprint 3.6.6B — FmpEarningsProvider contract tests. Every test here uses
httpx.MockTransport (no real network access) so the normal test suite never
depends on FMP being reachable or a real API key existing. The one test that
actually calls the live FMP API lives outside pytest collection entirely --
see logan_core/live_verification/nvda_earnings.py.
"""

import httpx
import pytest

from logan_core.receptors.providers import (
    FMP_SOURCE_ID,
    FMP_SOURCE_NAME,
    FmpEarningsProvider,
    FmpProviderError,
)


def _provider(handler) -> FmpEarningsProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return FmpEarningsProvider(api_key="test-key-not-real", client=client)


def test_missing_api_key_raises_without_making_any_request():
    def handler(request):
        raise AssertionError("must not make a request when the key is missing")

    with pytest.raises(FmpProviderError, match="FMP_API_KEY"):
        FmpEarningsProvider(
            api_key=None, client=httpx.Client(transport=httpx.MockTransport(handler))
        )


def test_api_key_only_from_param_or_env_never_hardcoded(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    with pytest.raises(FmpProviderError):
        FmpEarningsProvider()  # no param, no env var set


def test_api_key_read_from_environment(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "env-key")

    seen = {}

    def handler(request):
        seen["apikey"] = dict(request.url.params)["apikey"]
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    FmpEarningsProvider(client=client).fetch_latest_earnings("NVDA")
    assert seen["apikey"] == "env-key"


def test_successful_response_maps_into_earnings_report():
    def handler(request):
        assert request.url.path.endswith("/earnings")
        assert dict(request.url.params)["symbol"] == "NVDA"
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "date": "2026-05-28",
                    "epsActual": 1.05,
                    "epsEstimated": 0.98,
                    "fiscalDateEnding": "2026-04-30",
                }
            ],
        )

    report = _provider(handler).fetch_latest_earnings("NVDA")

    assert report is not None
    assert report.entity_id == "NVDA"
    assert report.actual_eps == 1.05
    assert report.consensus_eps == 0.98
    assert report.fiscal_quarter == "2026-04-30"
    assert report.report_timestamp.year == 2026
    assert report.report_timestamp.month == 5
    assert report.report_timestamp.day == 28
    assert report.source_id == FMP_SOURCE_ID
    assert report.source_name == FMP_SOURCE_NAME
    # No guidance data in FMP's earnings endpoint -- must stay None, not fabricated.
    assert report.guidance_revised is None
    assert report.guidance_delta_pct is None


def test_picks_most_recent_entry_by_date_not_list_position():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "date": "2026-02-26",  # older, listed first
                    "epsActual": 0.50,
                    "epsEstimated": 0.48,
                },
                {
                    "symbol": "NVDA",
                    "date": "2026-05-28",  # newer, listed second
                    "epsActual": 1.05,
                    "epsEstimated": 0.98,
                },
            ],
        )

    report = _provider(handler).fetch_latest_earnings("NVDA")
    assert report is not None
    assert report.report_timestamp.month == 5
    assert report.actual_eps == 1.05


def test_skips_upcoming_scheduled_report_in_favor_of_latest_reported_one():
    """Live-verification finding (Sprint 3.6.6B): FMP's response can include
    a future, not-yet-reported earnings date (epsEstimated populated,
    epsActual still null) alongside real historical ones. The most recent
    *reported* quarter must win, not the most recent *scheduled* date."""

    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "date": "2026-05-28",  # already reported
                    "epsActual": 1.05,
                    "epsEstimated": 0.98,
                },
                {
                    "symbol": "NVDA",
                    "date": "2026-08-26",  # upcoming, not yet reported -- later date
                    "epsActual": None,
                    "epsEstimated": 2.08,
                },
            ],
        )

    report = _provider(handler).fetch_latest_earnings("NVDA")
    assert report is not None
    assert report.report_timestamp.month == 5
    assert report.actual_eps == 1.05
    assert report.consensus_eps == 0.98


def test_falls_back_to_latest_scheduled_when_nothing_reported_yet():
    """If FMP genuinely has no reported quarter yet (a brand-new listing,
    for example), the honest result is the latest scheduled entry with
    actual_eps=None -- not an error, not a crash."""

    def handler(request):
        return httpx.Response(
            200,
            json=[{"symbol": "NEWCO", "date": "2026-09-15", "epsEstimated": 0.10}],
        )

    report = _provider(handler).fetch_latest_earnings("NEWCO")
    assert report is not None
    assert report.actual_eps is None
    assert report.consensus_eps == 0.10


def test_empty_list_is_legitimate_no_data_not_an_error():
    def handler(request):
        return httpx.Response(200, json=[])

    assert _provider(handler).fetch_latest_earnings("NOSUCHTICKER") is None


def test_missing_eps_fields_stay_none_not_fabricated():
    def handler(request):
        return httpx.Response(
            200,
            json=[{"symbol": "NVDA", "date": "2026-05-28"}],  # no eps fields at all
        )

    report = _provider(handler).fetch_latest_earnings("NVDA")
    assert report is not None
    assert report.actual_eps is None
    assert report.consensus_eps is None


def test_network_error_raises_fmp_provider_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(FmpProviderError, match="network error"):
        _provider(handler).fetch_latest_earnings("NVDA")


def test_rate_limit_raises_fmp_provider_error():
    def handler(request):
        return httpx.Response(429, text="Too Many Requests")

    with pytest.raises(FmpProviderError, match="rate limit"):
        _provider(handler).fetch_latest_earnings("NVDA")


def test_auth_failure_raises_fmp_provider_error():
    def handler(request):
        return httpx.Response(401, text="Invalid API key")

    with pytest.raises(FmpProviderError, match="401"):
        _provider(handler).fetch_latest_earnings("NVDA")


def test_server_error_raises_fmp_provider_error():
    def handler(request):
        return httpx.Response(500, text="Internal Server Error")

    with pytest.raises(FmpProviderError, match="500"):
        _provider(handler).fetch_latest_earnings("NVDA")


def test_malformed_json_raises_fmp_provider_error():
    def handler(request):
        return httpx.Response(200, content=b"not json at all {{{")

    with pytest.raises(FmpProviderError, match="not valid JSON"):
        _provider(handler).fetch_latest_earnings("NVDA")


def test_unexpected_response_shape_raises_fmp_provider_error():
    def handler(request):
        # FMP returns a dict (e.g. an error payload) instead of the expected list.
        return httpx.Response(200, json={"Error Message": "Invalid symbol"})

    with pytest.raises(FmpProviderError, match="not a list"):
        _provider(handler).fetch_latest_earnings("BADSYMBOL")


def test_entries_missing_date_are_rejected_as_malformed():
    def handler(request):
        return httpx.Response(200, json=[{"symbol": "NVDA", "epsActual": 1.05}])

    with pytest.raises(FmpProviderError, match="no usable entries"):
        _provider(handler).fetch_latest_earnings("NVDA")


def test_api_key_never_leaks_into_error_messages():
    def handler(request):
        return httpx.Response(401, text="unauthorized")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = FmpEarningsProvider(api_key="super-secret-key-12345", client=client)

    with pytest.raises(FmpProviderError) as exc_info:
        provider.fetch_latest_earnings("NVDA")
    assert "super-secret-key-12345" not in str(exc_info.value)
