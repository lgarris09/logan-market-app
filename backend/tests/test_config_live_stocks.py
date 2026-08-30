"""Sprint 3.6.8 Block 5 -- config.live_stock_tickers()/live_data_only_mode()
parsing and validation. No network, no pipeline -- pure deterministic
config-parsing tests.
"""

import re

from backend.app.config import (
    PROPOSED_BETA_UNIVERSE_TICKERS,
    live_data_only_mode,
    live_stock_tickers,
)


def test_unset_both_flags_returns_empty(monkeypatch):
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    assert live_stock_tickers() == ()


def test_single_ticker_configured(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    assert live_stock_tickers() == ("NVDA",)


def test_multiple_tickers_configured(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA,TSLA,AAPL")
    assert live_stock_tickers() == ("NVDA", "TSLA", "AAPL")


def test_multiple_tickers_with_whitespace_and_mixed_case(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", " nvda , Tsla ,aapl ")
    assert live_stock_tickers() == ("NVDA", "TSLA", "AAPL")


def test_duplicate_ticker_config_is_deduplicated(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA,TSLA,NVDA,nvda")
    assert live_stock_tickers() == ("NVDA", "TSLA")


def test_invalid_ticker_entries_are_dropped_not_crashed(monkeypatch, capsys):
    monkeypatch.setenv(
        "STRATUS_LIVE_STOCK_TICKERS", "NVDA,123,TOO-LONG-SYMBOL-XX,TSLA,"
    )
    result = live_stock_tickers()
    assert result == ("NVDA", "TSLA")
    captured = capsys.readouterr()
    assert "ignoring invalid entry" in captured.out


def test_empty_string_config_falls_back_to_legacy_flag_semantics(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "")
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    assert live_stock_tickers() == ("NVDA",)


def test_config_of_only_commas_and_whitespace_returns_empty(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", " , , ")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    assert live_stock_tickers() == ()


# --- Backward compatibility with the original single-ticker flag -----------


def test_legacy_flag_true_and_new_flag_unset_yields_nvda_only(monkeypatch):
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    assert live_stock_tickers() == ("NVDA",)


# --- Operational Beta Hardening Block 5 -- Ten-Ticker Beta Universe --------
#
# PROPOSED_BETA_UNIVERSE_TICKERS is a documented proposal, never read by
# live_stock_tickers() or any runtime code path -- these tests prove the
# proposal itself is well-formed and, separately, that it stays inert
# (setting it as a Python constant never changes live_stock_tickers()'s
# actual behavior, which is driven only by the real environment variable).

_TICKER_PATTERN = re.compile(r"^[A-Z]{1,10}$")


def test_proposed_universe_has_exactly_ten_tickers():
    assert len(PROPOSED_BETA_UNIVERSE_TICKERS) == 10


def test_proposed_universe_has_no_duplicates():
    assert len(set(PROPOSED_BETA_UNIVERSE_TICKERS)) == 10


def test_proposed_universe_entries_are_all_valid_ticker_shapes():
    for ticker in PROPOSED_BETA_UNIVERSE_TICKERS:
        assert _TICKER_PATTERN.match(ticker), ticker


def test_proposed_universe_is_never_wired_into_live_stock_tickers(monkeypatch):
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    assert live_stock_tickers() == ()
    assert live_stock_tickers() != PROPOSED_BETA_UNIVERSE_TICKERS


def test_proposed_universe_can_be_pasted_directly_as_the_env_value(monkeypatch):
    """Proves the constant is genuinely config-shaped -- a human adopting
    this proposal only needs to comma-join it into the real env var, no
    reformatting."""
    monkeypatch.setenv(
        "STRATUS_LIVE_STOCK_TICKERS", ",".join(PROPOSED_BETA_UNIVERSE_TICKERS)
    )
    assert live_stock_tickers() == PROPOSED_BETA_UNIVERSE_TICKERS


def test_legacy_flag_false_and_new_flag_unset_yields_empty(monkeypatch):
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "false")
    assert live_stock_tickers() == ()


def test_new_flag_set_takes_over_entirely_ignoring_legacy_flag(monkeypatch):
    """Setting STRATUS_LIVE_STOCK_TICKERS at all is one clear source of
    truth -- it does not merge with or get overridden by the legacy flag,
    even when the legacy flag would imply something different."""
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "TSLA,AAPL")
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    result = live_stock_tickers()
    assert result == ("TSLA", "AAPL")
    assert "NVDA" not in result


def test_new_flag_set_with_only_invalid_entries_does_not_fall_back_to_legacy(
    monkeypatch,
):
    """A config typo that parses to nothing usable is still "configured with
    nothing," not "unconfigured" -- must not silently resurrect the legacy
    NVDA-only behavior behind the caller's back."""
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "123,!!!")
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    assert live_stock_tickers() == ()


# --- live_data_only_mode() --------------------------------------------------


def test_runtime_mode_unset_is_demo_mode(monkeypatch):
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert live_data_only_mode() is False


def test_runtime_mode_live_is_live_data_only(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")
    assert live_data_only_mode() is True


def test_runtime_mode_beta_and_production_also_count_as_live(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    assert live_data_only_mode() is True
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "production")
    assert live_data_only_mode() is True


def test_runtime_mode_case_insensitive(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "LIVE")
    assert live_data_only_mode() is True


def test_runtime_mode_unrecognized_value_defaults_to_demo(monkeypatch):
    """An unrecognized value fails safely toward the existing, fixture-rich
    demo behavior rather than an unpredictable state."""
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "not-a-real-mode")
    assert live_data_only_mode() is False
