# mypy: disable-error-code="index,union-attr,var-annotated,arg-type"
"""ADR-084 -- the narrow SEC Form 8-K catalyst path.

A filing surfaces only when a governed rule validly fires on its structured
fields. An 8-K existing is never a reason on its own; nothing is scored;
several items in one filing are one opportunity; the provider fails closed.
"""

import json
import pathlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest

from logan_core.normalization import Normalizer
from logan_core.receptors.company_filings import filing_to_raw_signal
from logan_core.receptors.providers.base import CompanyFiling
from logan_core.receptors.providers.sec_edgar import (
    CIK_BY_TICKER,
    SEC_FILINGS_CACHE_TTL_SECONDS,
    SEC_SOURCE_ID,
    SecEdgarFilingsProvider,
    SecProviderError,
    parse_submissions,
    recent_window,
)
from logan_core.thesis.market_driver import (
    primary_signal_family,
    secondary_signal_families,
)
from logan_core.trigger_detection.filings import (
    FILING_MAX_AGE_AT_DETECTION,
    FILING_TRIGGER_CODES,
    GOVERNED_ITEMS,
    REASON_CODES,
    STOCK_FILING_LEADERSHIP_CHANGE,
    STOCK_FILING_MATERIAL_AGREEMENT,
    STOCK_FILING_RESULTS_REPORTED,
    UNGOVERNED_ITEMS,
    describe_filing,
    qualify_filing,
)
from logan_core.trigger_detection.stocks import (
    STOCK_PRICE_MOVE_SIGNIFICANT,
    StocksTriggerEvaluator,
)

NOW = datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc)
ACCESSION = "0001551152-26-000030"
SAMPLE = pathlib.Path(__file__).parent / "data" / "sec_8k_cohort_sample_2026-10-07.json"


def _qualify(**overrides):
    kwargs: dict[str, Any] = dict(
        form="8-K",
        items="2.02,9.01",
        accession_number=ACCESSION,
        accepted_at=NOW - timedelta(days=1),
        now=NOW,
        source_id=SEC_SOURCE_ID,
        expected_issuer="ABBV",
        filing_issuer="ABBV",
    )
    kwargs.update(overrides)
    return qualify_filing(**kwargs)


def _filing(**overrides) -> CompanyFiling:
    fields: dict[str, Any] = dict(
        entity_id="ABBV",
        issuer_ticker="ABBV",
        issuer_cik="0001551152",
        form="8-K",
        items="2.02,9.01",
        accession_number=ACCESSION,
        accepted_at=NOW - timedelta(days=1),
        filing_date="2026-10-05",
        report_date="2026-10-05",
        filing_url="https://www.sec.gov/Archives/edgar/data/1551152/x/y.htm",
        source_id=SEC_SOURCE_ID,
        source_name="SEC EDGAR",
    )
    fields.update(overrides)
    return CompanyFiling(**fields)


# --- taxonomy ------------------------------------------------------------------


def test_governed_and_ungoverned_items_are_disjoint_and_explicit():
    assert not set(GOVERNED_ITEMS) & set(UNGOVERNED_ITEMS)
    # The catch-all items are never governed: an issuer can file anything
    # under them, so their presence says nothing deterministic.
    for catch_all in ("7.01", "8.01", "9.01"):
        assert catch_all in UNGOVERNED_ITEMS
    assert "2.03" in UNGOVERNED_ITEMS  # routine financing


@pytest.mark.parametrize("item", sorted(GOVERNED_ITEMS))
def test_each_governed_item_qualifies_alone(item):
    result = _qualify(items=item)
    assert result.is_qualified
    assert result.primary is GOVERNED_ITEMS[item]
    assert result.primary.trigger_code in FILING_TRIGGER_CODES
    assert result.governed_items == (item,)


@pytest.mark.parametrize("item", sorted(UNGOVERNED_ITEMS))
def test_an_8k_with_only_ungoverned_items_does_not_surface(item):
    result = _qualify(items=item)
    assert result.state == "not_qualified"
    assert result.primary is None
    assert result.reason_codes in (
        ("no_governed_item",),
        ("routine_financing_not_governed",),
    )


def test_an_8k_existing_is_not_a_reason():
    for items in ("8.01,9.01", "7.01", "7.01,8.01,9.01", "5.07", "3.03,5.03,8.01,9.01"):
        assert _qualify(items=items).state == "not_qualified"


def test_financing_agreements_do_not_qualify():
    """A material agreement filed with a new financial obligation is a
    credit facility or notes offering. STRATUS cannot tell from structured
    fields whether it matters, so it says nothing."""
    result = _qualify(items="1.01,2.03,9.01")
    assert result.state == "not_qualified"
    assert result.reason_codes == ("routine_financing_not_governed",)
    assert _qualify(items="1.01,9.01").primary.trigger_code == (
        STOCK_FILING_MATERIAL_AGREEMENT
    )
    # Another governed item in the same filing still qualifies on its own.
    mixed = _qualify(items="1.01,2.03,5.02")
    assert mixed.is_qualified
    assert mixed.primary.trigger_code == STOCK_FILING_LEADERSHIP_CHANGE
    assert mixed.governed_items == ("5.02",)


# --- one filing, one opportunity -----------------------------------------------


def test_several_governed_items_are_one_qualification_with_a_fixed_primary():
    result = _qualify(items="2.02,5.02,9.01")
    assert result.is_qualified
    assert result.governed_items == ("5.02", "2.02")
    assert result.primary.trigger_code == STOCK_FILING_LEADERSHIP_CHANGE
    # Order in the filing does not change the answer.
    assert _qualify(items="9.01,5.02,2.02") == result


def test_one_filing_yields_exactly_one_trigger():
    filing = _filing(items="2.02,5.02,9.01")
    qualification = _qualify(items=filing.items)
    raw = filing_to_raw_signal(filing, qualification)
    evaluator = StocksTriggerEvaluator()
    trigger = evaluator.evaluate(raw, Normalizer().normalize(raw))
    assert trigger is not None
    assert trigger.trigger_code == STOCK_FILING_LEADERSHIP_CHANGE
    assert trigger.context["governed_items"] == ["5.02", "2.02"]


# --- governed states -----------------------------------------------------------

BLOCKED = [
    ({"accession_number": None}, "accession_missing", "blocked_stale_or_missing"),
    (
        {"accession_number": "not-an-accession"},
        "accession_malformed",
        "blocked_invalid",
    ),
    ({"accepted_at": None}, "filing_timestamp_missing", "blocked_stale_or_missing"),
    ({"accepted_at": NOW + timedelta(hours=2)}, "filing_in_future", "blocked_invalid"),
    (
        {"accepted_at": NOW - FILING_MAX_AGE_AT_DETECTION - timedelta(hours=1)},
        "filing_too_old",
        "blocked_stale_or_missing",
    ),
    ({"items": ""}, "items_missing", "blocked_stale_or_missing"),
    ({"items": None}, "items_missing", "blocked_stale_or_missing"),
    ({"items": "2.02,9.99"}, "item_unrecognized", "blocked_invalid"),
    ({"source_id": ""}, "source_missing", "blocked_stale_or_missing"),
    ({"filing_issuer": "ABT"}, "issuer_mismatch", "blocked_invalid"),
    ({"filing_issuer": None}, "issuer_mismatch", "blocked_invalid"),
]


@pytest.mark.parametrize("overrides,code,state_prefix", BLOCKED)
def test_blocked_filings_resolve_to_a_governed_state(overrides, code, state_prefix):
    result = _qualify(**overrides)
    assert code in result.reason_codes
    assert result.state.startswith(state_prefix)
    assert result.primary is None and result.governed_items == ()


def test_other_forms_are_not_governed():
    for form in ("10-Q", "10-K", "4", "S-3", None):
        result = _qualify(form=form)
        assert not result.is_qualified
        assert "form_not_governed" in result.reason_codes


def test_every_reason_code_is_registered_and_stable():
    for _overrides, code, _ in BLOCKED:
        assert code in REASON_CODES
    first = _qualify(items="8.01").reason_codes
    assert first == _qualify(items="8.01").reason_codes
    assert _qualify().reason_codes == ("qualified",)


def test_unknown_never_becomes_qualified():
    """Removing any one required field blocks the filing."""
    for field in (
        "form",
        "items",
        "accession_number",
        "accepted_at",
        "source_id",
        "expected_issuer",
        "filing_issuer",
    ):
        assert not _qualify(**{field: None}).is_qualified, field


# --- amendments ----------------------------------------------------------------


def test_an_amendment_qualifies_and_is_worded_as_an_amendment():
    result = _qualify(form="8-K/A", items="5.02")
    assert result.is_qualified
    text = describe_filing(result, form="8-K/A", filing_date="2026-09-01")
    assert text == (
        "8-K/A Item 5.02: amended disclosure, director or principal officer "
        "change, filed 2026-09-01"
    )
    raw = filing_to_raw_signal(_filing(form="8-K/A", items="5.02"), result)
    trigger = StocksTriggerEvaluator().evaluate(raw, Normalizer().normalize(raw))
    assert trigger is not None and trigger.context["is_amendment"] is True


# --- the signal says only what the filing index says ---------------------------


def test_signal_text_is_objective_and_carries_provenance():
    filing = _filing()
    raw = filing_to_raw_signal(filing, _qualify())
    assert raw.source_id == SEC_SOURCE_ID
    assert raw.captured_at == filing.accepted_at
    value = raw.raw_value
    assert (
        value["value"] == "8-K Item 2.02: financial results furnished, filed 2026-10-05"
    )
    for field in (
        "form",
        "items",
        "accession_number",
        "accepted_at",
        "filing_date",
        "report_date",
        "issuer_ticker",
        "issuer_cik",
        "filing_url",
    ):
        assert value[field]
    text = value["value"].lower()
    assert "(" not in text and ")" not in text
    for claim in ("beat", "miss", "consensus", "eps", "%", "strong", "weak", "surpris"):
        assert claim not in text


def test_no_category_phrase_makes_a_directional_or_magnitude_claim():
    for category in GOVERNED_ITEMS.values():
        phrase = category.phrase.lower()
        for word in ("beat", "miss", "strong", "weak", "positive", "negative", "%"):
            assert word not in phrase


def test_trigger_is_neutral_with_no_magnitude_and_one_shared_contribution():
    contributions = set()
    for item in GOVERNED_ITEMS:
        filing = _filing(items=item)
        raw = filing_to_raw_signal(filing, _qualify(items=item))
        trigger = StocksTriggerEvaluator().evaluate(raw, Normalizer().normalize(raw))
        assert trigger is not None
        assert trigger.direction == "neutral"
        assert trigger.raw_magnitude == 1.0
        assert trigger.trigger_type == "company_filing"
        contributions.add(trigger.confidence_contribution)
    assert len(contributions) == 1


def test_a_tampered_signal_does_not_fire():
    raw = filing_to_raw_signal(_filing(), _qualify())
    raw.raw_value["issuer_ticker"] = "ABT"
    evaluator = StocksTriggerEvaluator()
    assert evaluator.evaluate(raw, Normalizer().normalize(raw)) is None
    assert "issuer_mismatch" in evaluator.last_filing_qualification.reason_codes


def test_only_a_qualified_filing_becomes_a_signal():
    with pytest.raises(ValueError):
        filing_to_raw_signal(_filing(items="8.01"), _qualify(items="8.01"))


# --- families ------------------------------------------------------------------


def test_results_filing_is_its_own_family_distinct_from_eps_surprise():
    assert primary_signal_family([STOCK_FILING_RESULTS_REPORTED]) == "earnings_result"
    assert primary_signal_family([STOCK_FILING_LEADERSHIP_CHANGE]) == "company_event"
    assert primary_signal_family(["STOCK_EARNINGS_BEAT"]) == "earnings"
    codes = [STOCK_FILING_RESULTS_REPORTED, STOCK_PRICE_MOVE_SIGNIFICANT]
    assert primary_signal_family(codes) == "earnings_result"
    assert secondary_signal_families(codes) == ["price"]


# --- provider ------------------------------------------------------------------


def _payload(ticker="ABBV", **columns):
    recent = {
        "form": ["8-K", "10-Q", "8-K/A"],
        "accessionNumber": [ACCESSION, "0001551152-26-000029", "0001551152-26-000028"],
        "acceptanceDateTime": [
            "2026-10-06T00:07:45.000Z",
            "2026-08-01T12:00:00.000Z",
            "2026-09-30T12:00:00.000Z",
        ],
        "filingDate": ["2026-10-05", "2026-08-01", "2026-09-30"],
        "reportDate": ["2026-10-05", "2026-06-30", "2026-09-01"],
        "items": ["2.02,9.01", "", "5.02"],
        "primaryDocument": ["a.htm", "b.htm", "c.htm"],
    }
    recent.update(columns)
    return {"tickers": [ticker], "filings": {"recent": recent}}


def test_parse_keeps_only_8k_forms_with_provenance():
    filings = parse_submissions(_payload(), "ABBV", "0001551152")
    assert [f.form for f in filings] == ["8-K", "8-K/A"]
    first = filings[0]
    assert first.accession_number == ACCESSION
    assert first.accepted_at == datetime(2026, 10, 6, 0, 7, 45, tzinfo=timezone.utc)
    assert first.filing_date == "2026-10-05" and first.report_date == "2026-10-05"
    assert first.filing_url.endswith("/1551152/000155115226000030/a.htm")
    assert first.source_id == SEC_SOURCE_ID


def test_parse_refuses_another_issuers_payload():
    with pytest.raises(SecProviderError):
        parse_submissions(_payload(ticker="ABT"), "ABBV", "0001551152")
    for bad in (None, [], {"tickers": ["ABBV"]}, {"tickers": ["ABBV"], "filings": {}}):
        with pytest.raises(SecProviderError):
            parse_submissions(bad, "ABBV", "0001551152")


def test_provider_makes_no_request_without_a_user_agent():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    for missing in (None, "", "   "):
        with pytest.raises(SecProviderError):
            SecEdgarFilingsProvider(user_agent=missing, client=client)
    assert calls == []


def _provider(handler, clock):
    return SecEdgarFilingsProvider(
        user_agent="STRATUS test contact@example.invalid",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=lambda: clock["t"],
        sleep=lambda seconds: clock.__setitem__(
            "slept", clock.get("slept", 0) + seconds
        ),
    )


def test_provider_sends_the_configured_user_agent_and_caches():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=_payload())

    clock = {"t": 1000.0}
    provider = _provider(handler, clock)
    assert provider.last_successful_fetch_age_seconds("ABBV") is None
    first = provider.fetch_recent_filings("ABBV")
    assert len(first) == 2
    assert seen[0].headers["user-agent"] == "STRATUS test contact@example.invalid"
    assert str(seen[0].url).endswith("/CIK0001551152.json")

    clock["t"] += 60
    provider.fetch_recent_filings("ABBV")
    assert len(seen) == 1  # served from cache
    assert provider.last_successful_fetch_age_seconds("ABBV") == 60

    clock["t"] += SEC_FILINGS_CACHE_TTL_SECONDS
    provider.fetch_recent_filings("ABBV")
    assert len(seen) == 2


def test_provider_refuses_unmapped_tickers_and_bad_responses():
    clock = {"t": 0.0}
    provider = _provider(lambda request: httpx.Response(503, text="x"), clock)
    with pytest.raises(SecProviderError):
        provider.fetch_recent_filings("NOT_IN_COHORT")
    with pytest.raises(SecProviderError):
        provider.fetch_recent_filings("ABBV")
    assert provider.last_successful_fetch_age_seconds("ABBV") is None

    not_json = _provider(lambda request: httpx.Response(200, text="<html>"), clock)
    with pytest.raises(SecProviderError):
        not_json.fetch_recent_filings("ABBV")


def test_provider_paces_requests():
    clock = {"t": 0.0}
    provider = _provider(lambda request: httpx.Response(200, json=_payload()), clock)
    provider.fetch_recent_filings("ABBV")
    provider._cache.clear()
    provider.fetch_recent_filings("ABBV")
    assert clock.get("slept", 0) > 0


def test_cik_table_is_well_formed():
    assert len(CIK_BY_TICKER) == 30
    for ticker, cik in CIK_BY_TICKER.items():
        assert ticker.isupper() and len(cik) == 10 and cik.isdigit()


def test_recent_window_is_newest_first_and_bounded():
    filings = parse_submissions(_payload(), "ABBV", "0001551152")
    kept = recent_window(filings, NOW, 14)
    assert [f.accession_number for f in kept] == [ACCESSION, "0001551152-26-000028"]
    assert recent_window(filings, NOW, 2) == [kept[0]]


# --- the real cohort sample ----------------------------------------------------


def test_real_cohort_sample_qualifies_a_minority_of_filings():
    """48 real 8-K / 8-K/A index rows for the 30-company cohort, filed
    2026-08-01 to 2026-10-06 (fetched 2026-10-07). The rules must surface
    some and decline most, and every row must resolve to a governed state."""
    rows = json.loads(SAMPLE.read_text(encoding="utf-8"))
    assert len(rows) == 48
    outcomes: Counter = Counter()
    codes: Counter = Counter()
    for ticker, form, _filing_date, accepted, _report, items, accession in rows:
        accepted_at = datetime.fromisoformat(accepted.replace("Z", "+00:00"))
        result = qualify_filing(
            form=form,
            items=items,
            accession_number=accession,
            accepted_at=accepted_at,
            now=accepted_at + timedelta(hours=1),
            source_id=SEC_SOURCE_ID,
            expected_issuer=ticker,
            filing_issuer=ticker,
        )
        outcomes[result.state] += 1
        if result.primary is not None:
            codes[result.primary.trigger_code] += 1
    assert set(outcomes) == {"qualified", "not_qualified"}
    assert outcomes["qualified"] == 20
    assert outcomes["not_qualified"] == 28
    assert codes == {
        STOCK_FILING_RESULTS_REPORTED: 11,
        STOCK_FILING_LEADERSHIP_CHANGE: 9,
    }
