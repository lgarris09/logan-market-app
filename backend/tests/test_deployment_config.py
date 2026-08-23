"""Sprint 3.6.9 Block 1 -- remote-hosting configuration surface: durable
SQLite path resolution for the notification store and the legacy memory
prototype, and the environment-configurable CORS policy. See
docs/DECISIONS.md's Sprint 3.6.9 Block 1 ADR for the full reasoning behind
each default.
"""

from pathlib import Path

from backend.app.config import (
    cors_allowed_origins,
    legacy_memory_db_path,
    notification_store_db_path,
    startup_config_summary,
)

# --- notification_store_db_path ---------------------------------------------


def test_notification_store_db_path_defaults_to_sibling_of_state_db(monkeypatch):
    monkeypatch.delenv("STRATUS_NOTIFICATIONS_DB_PATH", raising=False)
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(Path("/data/stratus_state.db")))
    assert notification_store_db_path() == Path("/data/notifications.db")


def test_notification_store_db_path_override_wins(monkeypatch, tmp_path):
    override = tmp_path / "custom_notifications.db"
    monkeypatch.setenv("STRATUS_NOTIFICATIONS_DB_PATH", str(override))
    assert notification_store_db_path() == override


# --- legacy_memory_db_path ---------------------------------------------------


def test_legacy_memory_db_path_default_unchanged(monkeypatch):
    monkeypatch.delenv("STRATUS_LEGACY_MEMORY_DB_PATH", raising=False)
    path = legacy_memory_db_path()
    assert path.name == "logan_memory.db"
    assert path.parent.name == "data"


def test_legacy_memory_db_path_override_wins(monkeypatch, tmp_path):
    override = tmp_path / "custom_logan_memory.db"
    monkeypatch.setenv("STRATUS_LEGACY_MEMORY_DB_PATH", str(override))
    assert legacy_memory_db_path() == override


# --- cors_allowed_origins -----------------------------------------------------


def test_cors_defaults_to_wildcard_in_demo_mode(monkeypatch):
    monkeypatch.delenv("STRATUS_CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert cors_allowed_origins() == ["*"]


def test_cors_defaults_to_empty_allowlist_in_beta_mode(monkeypatch):
    monkeypatch.delenv("STRATUS_CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    assert cors_allowed_origins() == []


def test_cors_defaults_to_empty_allowlist_in_production_mode(monkeypatch):
    monkeypatch.delenv("STRATUS_CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "production")
    assert cors_allowed_origins() == []


def test_cors_explicit_origins_win_regardless_of_mode(monkeypatch):
    monkeypatch.setenv(
        "STRATUS_CORS_ALLOWED_ORIGINS",
        "https://app.example.com, https://admin.example.com",
    )
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    assert cors_allowed_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]

    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert cors_allowed_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_cors_blank_explicit_value_falls_back_to_mode_default(monkeypatch):
    monkeypatch.setenv("STRATUS_CORS_ALLOWED_ORIGINS", "   ")
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert cors_allowed_origins() == ["*"]


# --- startup_config_summary ---------------------------------------------------


def test_startup_config_summary_never_contains_a_secret_value(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "totally-real-secret-value")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "another-real-secret-value")
    summary = startup_config_summary()
    assert "totally-real-secret-value" not in summary
    assert "another-real-secret-value" not in summary


def test_startup_config_summary_reflects_effective_mode(monkeypatch):
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert "runtime_mode=demo" in startup_config_summary()

    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    assert "runtime_mode=live-data-only" in startup_config_summary()
