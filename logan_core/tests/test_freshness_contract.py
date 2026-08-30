"""Universe Manager V1a Block 8 -- the explicit freshness contract
(logan_core/receptors/providers/freshness.py). Pure classification tests --
never touches a real cache or provider.
"""

import pytest

from logan_core.receptors.providers import (
    SIGNAL_FRESHNESS_CONTRACTS,
    FreshnessContract,
    classify_freshness,
    signal_family_contract,
)

_CONTRACT = FreshnessContract(
    "test_family", target_ttl_seconds=100.0, grace_seconds=50.0
)


def test_no_value_is_always_unavailable():
    assert (
        classify_freshness(has_value=False, age_seconds=None, contract=_CONTRACT)
        == "UNAVAILABLE"
    )


def test_within_half_ttl_is_fresh():
    assert (
        classify_freshness(has_value=True, age_seconds=10.0, contract=_CONTRACT)
        == "FRESH"
    )
    assert (
        classify_freshness(has_value=True, age_seconds=50.0, contract=_CONTRACT)
        == "FRESH"
    )


def test_past_half_ttl_but_within_ttl_is_recently_observed():
    assert (
        classify_freshness(has_value=True, age_seconds=50.1, contract=_CONTRACT)
        == "RECENTLY_OBSERVED"
    )
    assert (
        classify_freshness(has_value=True, age_seconds=100.0, contract=_CONTRACT)
        == "RECENTLY_OBSERVED"
    )


def test_past_ttl_but_within_grace_is_stale_within_grace():
    assert (
        classify_freshness(has_value=True, age_seconds=100.1, contract=_CONTRACT)
        == "STALE_WITHIN_GRACE"
    )
    assert (
        classify_freshness(has_value=True, age_seconds=150.0, contract=_CONTRACT)
        == "STALE_WITHIN_GRACE"
    )


def test_past_grace_is_unavailable():
    assert (
        classify_freshness(has_value=True, age_seconds=150.1, contract=_CONTRACT)
        == "UNAVAILABLE"
    )


def test_boundary_never_reports_stale_as_fresh():
    # A value exactly at the TTL boundary must never be reported FRESH once
    # it's genuinely past the "just observed" half-window.
    result = classify_freshness(has_value=True, age_seconds=100.0, contract=_CONTRACT)
    assert result != "FRESH"


def test_no_opportunity_is_distinguishable_from_unavailable():
    """The exact Block 8 distinction: a healthy empty result (has_value
    True, e.g. an evaluated-but-non-qualifying signal) is never the same
    classification as a genuinely unavailable one."""
    healthy_empty = classify_freshness(
        has_value=True, age_seconds=1.0, contract=_CONTRACT
    )
    unavailable = classify_freshness(
        has_value=False, age_seconds=None, contract=_CONTRACT
    )
    assert healthy_empty != unavailable
    assert unavailable == "UNAVAILABLE"


def test_has_value_true_requires_age_seconds():
    with pytest.raises(AssertionError):
        classify_freshness(has_value=True, age_seconds=None, contract=_CONTRACT)


# --- registered per-signal-family contracts ----------------------------------


def test_every_documented_signal_family_is_registered():
    for family in ("quote", "earnings", "analyst_grade", "profile", "benchmark_quote"):
        contract = signal_family_contract(family)
        assert contract.signal_family == family
        assert contract.target_ttl_seconds > 0
        assert contract.grace_seconds >= 0


def test_unregistered_family_raises_rather_than_guessing():
    with pytest.raises(KeyError):
        signal_family_contract("not_a_real_family")


def test_earnings_contract_reuses_the_existing_stale_grace_constant():
    from logan_core.receptors.providers import EARNINGS_STALE_GRACE_SECONDS

    assert (
        SIGNAL_FRESHNESS_CONTRACTS["earnings"].grace_seconds
        == EARNINGS_STALE_GRACE_SECONDS
    )


def test_every_contract_ttl_matches_the_existing_fmp_cache_ttl_constants():
    from logan_core.receptors.providers import (
        BENCHMARK_QUOTE_CACHE_TTL_SECONDS,
        EARNINGS_CACHE_TTL_SECONDS,
        GRADE_CACHE_TTL_SECONDS,
        PROFILE_CACHE_TTL_SECONDS,
        QUOTE_CACHE_TTL_SECONDS,
    )

    assert (
        SIGNAL_FRESHNESS_CONTRACTS["quote"].target_ttl_seconds
        == QUOTE_CACHE_TTL_SECONDS
    )
    assert (
        SIGNAL_FRESHNESS_CONTRACTS["earnings"].target_ttl_seconds
        == EARNINGS_CACHE_TTL_SECONDS
    )
    assert (
        SIGNAL_FRESHNESS_CONTRACTS["analyst_grade"].target_ttl_seconds
        == GRADE_CACHE_TTL_SECONDS
    )
    assert (
        SIGNAL_FRESHNESS_CONTRACTS["profile"].target_ttl_seconds
        == PROFILE_CACHE_TTL_SECONDS
    )
    assert (
        SIGNAL_FRESHNESS_CONTRACTS["benchmark_quote"].target_ttl_seconds
        == BENCHMARK_QUOTE_CACHE_TTL_SECONDS
    )
