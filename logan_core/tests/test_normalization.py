"""Layer 2 direct unit tests (V3.1.4 BATCH-2 -- previously only exercised
indirectly via other layers' tests; error paths were entirely untested).
"""

from datetime import datetime, timezone

import pytest

from logan_core.contracts import RawSignal
from logan_core.normalization import Normalizer
from logan_core.normalization.normalize import NormalizationError

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def _raw(raw_value, domain="stocks"):
    return RawSignal(
        domain=domain,
        source_id="sec_filing",
        source_name="SEC EDGAR",
        raw_value=raw_value,
        captured_at=NOW,
    )


def test_valid_signal_normalizes_successfully():
    raw = _raw(
        {
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "earnings_signal",
            "value": "beat",
        }
    )
    normalized = Normalizer().normalize(raw)
    assert normalized.entity_id == "NVDA"
    assert normalized.signal_type == "earnings_signal"
    assert normalized.decision_trace


def test_non_dict_raw_value_is_rejected():
    raw = _raw("not a dict")
    with pytest.raises(NormalizationError):
        Normalizer().normalize(raw)


def test_missing_entity_id_is_rejected():
    raw = _raw(
        {"entity_type": "ticker", "signal_type": "earnings_signal", "value": "beat"}
    )
    with pytest.raises(NormalizationError):
        Normalizer().normalize(raw)


def test_missing_value_is_rejected():
    raw = _raw(
        {"entity_id": "NVDA", "entity_type": "ticker", "signal_type": "earnings_signal"}
    )
    with pytest.raises(NormalizationError):
        Normalizer().normalize(raw)


def test_unregistered_signal_type_for_domain_is_rejected():
    raw = _raw(
        {
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "odds_move",
            "value": "x",
        },
        domain="stocks",
    )
    with pytest.raises(NormalizationError):
        Normalizer().normalize(raw)


def test_signal_type_valid_in_its_own_domain():
    raw = _raw(
        {
            "entity_id": "LAL",
            "entity_type": "team",
            "signal_type": "odds_move",
            "value": "x",
        },
        domain="sports",
    )
    normalized = Normalizer().normalize(raw)
    assert normalized.signal_type == "odds_move"
