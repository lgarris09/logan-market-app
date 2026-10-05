"""Shadow qualification rules (ADR-078): states, reason codes, EPS
comparability as a hard gate, denominator eligibility, timestamp and
fiscal-period matching, and materiality bands for price and revenue."""

import ast
import inspect
import math
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import logan_core.trigger_detection.qualification_shadow as shadow
from logan_core.trigger_detection.qualification_shadow import (
    EPS_ESTIMATE_MIN_ABS,
    PRICE_MOVE_BANDS,
    REASON_CODES,
    REVENUE_SURPRISE_BANDS,
    EstimateActualEvidence,
    denominator_eligible,
    qualify_eps_beat,
    qualify_price_move,
    qualify_revenue_surprise,
)

RELEASE = datetime(2026, 7, 30, 20, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 5, 16, 0, tzinfo=timezone.utc)

# Everything established: the only fully provable shape.
PROVEN_EPS = EstimateActualEvidence(
    actual=1.20,
    estimate=1.00,
    actual_issuer="AAA",
    estimate_issuer="AAA",
    actual_fiscal_period="2026-Q2",
    estimate_fiscal_period="2026-Q2",
    release_at=RELEASE,
    estimate_as_of=RELEASE - timedelta(days=1),
    actual_currency="USD",
    estimate_currency="USD",
    split_between=False,
    restated=False,
    actual_source="provider_a",
    estimate_source="provider_a",
    actual_basis="adjusted",
    estimate_basis="adjusted",
    actual_share_basis="diluted",
    estimate_share_basis="diluted",
)
PROVEN_REVENUE = replace(
    PROVEN_EPS,
    actual=104.0e9,
    estimate=100.0e9,
    actual_basis=None,
    estimate_basis=None,
    actual_share_basis=None,
    estimate_share_basis=None,
    revenue_definition_matched=True,
)


# --- states and reason codes ---------------------------------------------------


def test_every_reason_code_maps_to_one_of_the_five_states():
    states = {state for state, _meaning in REASON_CODES.values()}
    assert states == {
        "qualified",
        "not_qualified",
        "blocked_invalid_input",
        "blocked_incomparable_basis",
        "blocked_stale_or_missing_required_fields",
    }
    for code, (_state, meaning) in REASON_CODES.items():
        assert code == code.lower() and " " not in code
        assert meaning.endswith(".")


def test_the_named_eps_block_code_exists_and_blocks_on_basis():
    assert REASON_CODES["earnings_eps_comparability_unresolved"][0] == (
        "blocked_incomparable_basis"
    )


def test_a_blocked_result_never_carries_magnitude_band_or_direction():
    for result in (
        qualify_eps_beat(replace(PROVEN_EPS, actual_basis=None)),
        qualify_revenue_surprise(replace(PROVEN_REVENUE, estimate=None)),
        qualify_price_move(
            price=110.0, previous_close=0.0, quote_at=NOW, now=NOW, source_id="x"
        ),
    ):
        assert result.state.startswith("blocked_")
        assert result.magnitude_pct is None
        assert result.materiality is None
        assert result.direction is None


def test_the_most_severe_state_governs_and_every_reason_is_kept():
    result = qualify_eps_beat(
        replace(
            PROVEN_EPS,
            estimate_issuer="BBB",  # invalid
            actual_basis=None,  # incomparable
            estimate_as_of=None,  # missing
        )
    )
    assert result.state == "blocked_invalid_input"
    assert {
        "issuer_mismatch",
        "eps_basis_unknown",
        "earnings_eps_comparability_unresolved",
        "estimate_timestamp_unverified",
    } <= set(result.reason_codes)


# --- EPS comparability: hard gate ----------------------------------------------


def test_a_fully_proven_eps_beat_qualifies_and_stays_magnitude_neutral():
    result = qualify_eps_beat(PROVEN_EPS)
    assert result.state == "qualified"
    assert result.reason_codes == ("qualified",)
    assert result.direction == "positive"
    # EPS magnitude is blocked: no size, no band, however large the beat.
    assert result.magnitude_pct is None and result.materiality is None
    huge = qualify_eps_beat(replace(PROVEN_EPS, actual=9.11))
    assert huge.state == "qualified" and huge.materiality is None


@pytest.mark.parametrize(
    "change, code, state",
    [
        ({"actual_basis": None}, "eps_basis_unknown", "blocked_incomparable_basis"),
        ({"estimate_basis": None}, "eps_basis_unknown", "blocked_incomparable_basis"),
        ({"actual_basis": "gaap"}, "eps_basis_mismatch", "blocked_incomparable_basis"),
        (
            {"actual_share_basis": None},
            "eps_share_basis_unknown",
            "blocked_incomparable_basis",
        ),
        (
            {"actual_share_basis": "basic"},
            "eps_share_basis_mismatch",
            "blocked_incomparable_basis",
        ),
        ({"restated": None}, "restatement_unresolved", "blocked_incomparable_basis"),
        ({"restated": True}, "restatement_unresolved", "blocked_incomparable_basis"),
        ({"estimate_issuer": "BBB"}, "issuer_mismatch", "blocked_invalid_input"),
        (
            {"estimate_fiscal_period": "2026-Q1"},
            "fiscal_period_mismatch",
            "blocked_invalid_input",
        ),
        ({"estimate_currency": "EUR"}, "currency_mismatch", "blocked_invalid_input"),
        (
            {"split_between": True},
            "unadjusted_split_between_estimate_and_actual",
            "blocked_invalid_input",
        ),
        ({"actual": math.nan}, "input_non_finite", "blocked_invalid_input"),
        ({"estimate": math.inf}, "input_non_finite", "blocked_invalid_input"),
        (
            {"actual": None},
            "actual_missing",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"estimate": None},
            "estimate_missing",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"actual_fiscal_period": None},
            "fiscal_period_unverified",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"release_at": None},
            "release_timestamp_missing",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"estimate_as_of": None},
            "estimate_timestamp_unverified",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"actual_currency": None},
            "currency_unverified",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"split_between": None},
            "split_status_unverified",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"estimate_source": None},
            "provenance_missing",
            "blocked_stale_or_missing_required_fields",
        ),
    ],
)
def test_each_missing_or_conflicting_fact_blocks_the_eps_trigger(change, code, state):
    result = qualify_eps_beat(replace(PROVEN_EPS, **change))
    assert result.state == state
    assert code in result.reason_codes
    assert not result.is_qualified


def test_any_basis_problem_also_carries_the_named_unresolved_code():
    for change in (
        {"actual_basis": None},
        {"actual_basis": "gaap"},
        {"estimate_share_basis": None},
        {"estimate_share_basis": "basic"},
    ):
        result = qualify_eps_beat(replace(PROVEN_EPS, **change))
        assert result.reason_codes[0] == "earnings_eps_comparability_unresolved"


def test_an_adjusted_split_does_not_block():
    result = qualify_eps_beat(
        replace(PROVEN_EPS, split_between=True, split_adjusted=True)
    )
    assert result.state == "qualified"


def test_what_the_current_provider_supplies_is_blocked_not_discounted():
    """The shape of a real provider row today: values and a symbol, with no
    basis, fiscal period, estimate timestamp, currency or split status."""
    result = qualify_eps_beat(
        EstimateActualEvidence(
            actual=5.75,
            estimate=1.82,
            actual_issuer="AMZN",
            estimate_issuer="AMZN",
            release_at=RELEASE,
            actual_source="fmp",
            estimate_source="fmp",
        )
    )
    assert result.state == "blocked_incomparable_basis"
    assert result.reason_codes[0] == "earnings_eps_comparability_unresolved"
    assert result.magnitude_pct is None and result.materiality is None


@pytest.mark.parametrize(
    "actual, expected_state, code",
    [
        (1.20, "qualified", "qualified"),
        (1.05, "qualified", "qualified"),  # exactly the 5% threshold
        (1.0499, "not_qualified", "below_threshold"),
        (1.00, "not_qualified", "wrong_direction"),
        (0.80, "not_qualified", "wrong_direction"),
    ],
)
def test_the_existing_beat_threshold_is_unchanged(actual, expected_state, code):
    result = qualify_eps_beat(replace(PROVEN_EPS, actual=actual))
    assert (result.state, result.reason_codes) == (expected_state, (code,))


# --- denominator eligibility ---------------------------------------------------


@pytest.mark.parametrize(
    "estimate, eligible",
    [
        (1.0, True),
        (EPS_ESTIMATE_MIN_ABS, True),
        (EPS_ESTIMATE_MIN_ABS - 0.001, False),
        (0.01, False),
        (0.0, False),
        (-0.5, False),
        (math.nan, False),
        (math.inf, False),
        (None, False),
    ],
)
def test_denominator_eligibility(estimate, eligible):
    assert denominator_eligible(estimate, minimum=EPS_ESTIMATE_MIN_ABS) is eligible


@pytest.mark.parametrize("estimate", [0.0, 0.02, -0.40])
def test_an_ineligible_denominator_blocks_rather_than_caps(estimate):
    """A 0.02 consensus and a 0.30 actual is a '1400% beat'. It must not be
    capped into the top band -- it must not be a trigger at all."""
    result = qualify_eps_beat(replace(PROVEN_EPS, actual=0.30, estimate=estimate))
    assert result.state == "blocked_incomparable_basis"
    assert "estimate_denominator_ineligible" in result.reason_codes
    revenue = qualify_revenue_surprise(replace(PROVEN_REVENUE, estimate=estimate))
    assert "estimate_denominator_ineligible" in revenue.reason_codes
    assert revenue.materiality is None


# --- timestamps and fiscal periods ---------------------------------------------


@pytest.mark.parametrize(
    "offset, code",
    [
        (timedelta(0), "estimate_not_pre_release"),  # same instant is not "before"
        (timedelta(hours=1), "estimate_not_pre_release"),
        (timedelta(days=-46), "estimate_stale"),
    ],
)
def test_the_estimate_must_be_recent_and_strictly_pre_release(offset, code):
    result = qualify_eps_beat(replace(PROVEN_EPS, estimate_as_of=RELEASE + offset))
    assert code in result.reason_codes and not result.is_qualified


@pytest.mark.parametrize("days_before", [0.01, 1, 30, 45])
def test_a_pre_release_estimate_within_the_window_is_accepted(days_before):
    result = qualify_eps_beat(
        replace(PROVEN_EPS, estimate_as_of=RELEASE - timedelta(days=days_before))
    )
    assert result.state == "qualified"


# --- price movement and its bands ----------------------------------------------


def _price(change_pct, **kwargs):
    arguments = dict(
        price=100.0 * (1 + change_pct / 100.0),
        previous_close=100.0,
        quote_at=NOW - timedelta(minutes=5),
        now=NOW,
        source_id="fmp",
    )
    arguments.update(kwargs)
    return qualify_price_move(**arguments)


@pytest.mark.parametrize(
    "change_pct, state, band",
    [
        (0.0, "not_qualified", None),
        (4.99, "not_qualified", None),
        (5.0, "qualified", "barely_qualified"),
        (7.49, "qualified", "barely_qualified"),
        (7.5, "qualified", "meaningful"),
        (12.49, "qualified", "meaningful"),
        (12.5, "qualified", "large"),
        (19.99, "qualified", "large"),
        (20.0, "qualified", "capped_exceptional"),
        (400.0, "qualified", "capped_exceptional"),
        (-6.31, "qualified", "barely_qualified"),
        (-25.0, "qualified", "capped_exceptional"),
    ],
)
def test_price_move_bands_and_boundaries(change_pct, state, band):
    result = _price(change_pct)
    assert (result.state, result.materiality) == (state, band)
    if state == "qualified":
        assert result.direction == ("positive" if change_pct > 0 else "negative")
        assert result.magnitude_pct == pytest.approx(change_pct)


@pytest.mark.parametrize(
    "override, code, state",
    [
        (
            {"previous_close": 0.0},
            "previous_close_not_positive",
            "blocked_invalid_input",
        ),
        (
            {"previous_close": -3.0},
            "previous_close_not_positive",
            "blocked_invalid_input",
        ),
        ({"price": math.nan}, "input_non_finite", "blocked_invalid_input"),
        (
            {"price": None},
            "quote_missing",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"quote_at": NOW - timedelta(hours=25)},
            "quote_stale",
            "blocked_stale_or_missing_required_fields",
        ),
        (
            {"source_id": None},
            "provenance_missing",
            "blocked_stale_or_missing_required_fields",
        ),
    ],
)
def test_invalid_or_stale_quotes_block_the_price_trigger(override, code, state):
    result = _price(30.0, **override)
    assert result.state == state and code in result.reason_codes
    assert result.materiality is None


# --- revenue surprise and its bands --------------------------------------------


@pytest.mark.parametrize(
    "surprise_pct, state, band",
    [
        (1.99, "not_qualified", None),
        (2.0, "qualified", "barely_qualified"),
        (3.0, "qualified", "meaningful"),
        (5.0, "qualified", "large"),
        (8.0, "qualified", "capped_exceptional"),
        (60.0, "qualified", "capped_exceptional"),
        (-4.0, "qualified", "meaningful"),
        (-1.0, "not_qualified", None),
    ],
)
def test_revenue_surprise_bands_and_boundaries(surprise_pct, state, band):
    result = qualify_revenue_surprise(
        replace(PROVEN_REVENUE, actual=100.0e9 * (1 + surprise_pct / 100.0))
    )
    assert (result.state, result.materiality) == (state, band)


def test_revenue_needs_a_matched_definition_and_a_pre_release_estimate():
    unmatched = qualify_revenue_surprise(
        replace(PROVEN_REVENUE, revenue_definition_matched=None)
    )
    assert unmatched.state == "blocked_incomparable_basis"
    assert "revenue_definition_unresolved" in unmatched.reason_codes

    undated = qualify_revenue_surprise(replace(PROVEN_REVENUE, estimate_as_of=None))
    assert undated.state == "blocked_stale_or_missing_required_fields"
    assert "estimate_timestamp_unverified" in undated.reason_codes


def test_revenue_can_qualify_while_eps_is_blocked_for_the_same_report():
    eps = qualify_eps_beat(replace(PROVEN_EPS, actual_basis=None))
    revenue = qualify_revenue_surprise(PROVEN_REVENUE)
    assert eps.state == "blocked_incomparable_basis"
    assert revenue.state == "qualified" and revenue.materiality == "meaningful"


# --- band tables: structure, determinism ---------------------------------------


@pytest.mark.parametrize("table", [PRICE_MOVE_BANDS, REVENUE_SURPRISE_BANDS])
def test_band_tables_are_ordered_and_explainable(table):
    assert (
        0 < table.threshold < table.meaningful < table.large < table.capped_exceptional
    )
    # Fixed multiples of the family's own threshold: 1.5x, 2.5x, 4x.
    assert table.meaningful == pytest.approx(table.threshold * 1.5)
    assert table.large == pytest.approx(table.threshold * 2.5)
    assert table.capped_exceptional == pytest.approx(table.threshold * 4.0)


@pytest.mark.parametrize("table", [PRICE_MOVE_BANDS, REVENUE_SURPRISE_BANDS])
def test_bands_are_monotonic_symmetric_and_bounded(table):
    order = [None, "barely_qualified", "meaningful", "large", "capped_exceptional"]
    previous = 0
    for tenths in range(0, 600):
        magnitude = tenths / 10.0
        band = table.band(magnitude)
        assert band == table.band(-magnitude)
        assert order.index(band) >= previous
        previous = order.index(band)
    assert table.band(1e9) == "capped_exceptional"
    assert table.band(math.nan) is None and table.band(math.inf) is None


def test_there_is_no_eps_or_analyst_band_table():
    tables = [
        value for value in vars(shadow).values() if isinstance(value, shadow.BandTable)
    ]
    assert {table.family for table in tables} == {"price_move", "revenue_surprise"}


def test_identical_inputs_give_identical_results():
    assert qualify_eps_beat(PROVEN_EPS) == qualify_eps_beat(PROVEN_EPS)
    assert qualify_revenue_surprise(PROVEN_REVENUE) == qualify_revenue_surprise(
        PROVEN_REVENUE
    )
    assert _price(9.0) == _price(9.0)


# --- shadow only ---------------------------------------------------------------


def test_nothing_in_the_pipeline_imports_the_shadow_module():
    import pathlib

    root = pathlib.Path(shadow.__file__).resolve().parents[2]
    offenders = []
    for path in list((root / "logan_core").rglob("*.py")) + list(
        (root / "backend" / "app").rglob("*.py")
    ):
        if "tests" in path.parts or path.name == "qualification_shadow.py":
            continue
        if "qualification_shadow" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    assert offenders == []


def test_the_shadow_module_computes_no_score():
    tree = ast.parse(inspect.getsource(shadow))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"confidence_score", "trust_score", "confidence_contribution"}
