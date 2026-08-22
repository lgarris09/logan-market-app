"""Sprint 3.6.6C — the first place `backend/app/` reads `.env` or runtime
config. Reconnaissance before writing this: no config.py/settings.py
existed, and no module under backend/app/ called os.environ or load_dotenv
anywhere -- backend/.env (FMP_API_KEY, gitignored, local-dev-only) was not
being auto-loaded into the backend process at all. This is the minimal
addition needed, not a general settings framework.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# python-dotenv is already an installed dependency (backend/requirements.txt's
# uvicorn[standard] extra pulls it in transitively; confirmed present in this
# venv) -- not a new dependency addition. Loads backend/.env into the real
# process environment once, at import time, before any route or pipeline
# code runs. Safe no-op if the file doesn't exist (e.g. a fresh clone before
# the .env is restored) -- os.environ.get() calls elsewhere degrade to their
# own explicit "not configured" handling, never a crash here.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def live_nvda_earnings_enabled() -> bool:
    """Sprint 3.6.6C: gates whether /v1/opportunities attempts to replace the
    simulated NVDA fixture with a real FMP-driven earnings opportunity.
    Defaults to disabled -- existing simulated-only behavior is the safe,
    backward-compatible default; this must be explicitly turned on via
    STRATUS_LIVE_NVDA_EARNINGS=true.

    A function, not a frozen module-level constant, so it always reflects
    the current environment -- tests toggle this with monkeypatch.setenv
    without needing to reload the module, and the real backend only needs a
    clean restart (not a code change) to flip it.
    """
    return os.environ.get("STRATUS_LIVE_NVDA_EARNINGS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def memory_persistence_enabled() -> bool:
    """Sprint 3.6.7 Block 3: gates whether the shared Orchestrator's
    MemoryStore is backed by a durable local SQLite file (surviving a
    backend restart) instead of the pure in-memory dict every pre-Block-3
    caller/test already gets. Defaults to disabled, matching every other
    new capability's rollout pattern in this codebase
    (STRATUS_LIVE_NVDA_EARNINGS) -- explicit opt-in, not a default-on
    infrastructure change, and critically keeps the existing backend test
    suite's `reset_pipeline_state()` fixture isolated to in-memory state
    (no test run reads/writes the real local database file unless it
    explicitly enables this).

    A function, not a frozen constant, for the same reason
    live_nvda_earnings_enabled() is -- tests toggle it with
    monkeypatch.setenv without needing to reload the module.
    """
    return os.environ.get("STRATUS_PERSIST_MEMORY", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def memory_store_db_path() -> Path:
    """The local SQLite file backing persistent memory when
    memory_persistence_enabled() is true. Overridable via
    STRATUS_STATE_DB_PATH (tests use this to point at an isolated temp file
    rather than the real local database) -- defaults to
    backend/data/stratus_state.db, alongside (but never touching the schema
    of) the historical prototype's own backend/data/logan_memory.db.
    """
    override = os.environ.get("STRATUS_STATE_DB_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "stratus_state.db"
