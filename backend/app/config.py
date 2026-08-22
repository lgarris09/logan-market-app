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


def _env_flag(name: str) -> bool:
    """Shared boolean-env-var parsing for every config-gated capability in
    this file (Sprint 3.6.7 Block 4 integration-hardening pass -- extracted
    after `live_nvda_earnings_enabled`/`memory_persistence_enabled` were
    found byte-identical except for the variable name). Not a frozen
    constant anywhere it's used -- always reflects the current environment,
    so tests toggle a flag with monkeypatch.setenv without reloading any
    module, and the real backend only needs a clean restart (not a code
    change) to flip one.
    """
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def live_nvda_earnings_enabled() -> bool:
    """Sprint 3.6.6C: gates whether /v1/opportunities attempts to replace the
    simulated NVDA fixture with a real FMP-driven earnings opportunity.
    Defaults to disabled -- existing simulated-only behavior is the safe,
    backward-compatible default; this must be explicitly turned on via
    STRATUS_LIVE_NVDA_EARNINGS=true.
    """
    return _env_flag("STRATUS_LIVE_NVDA_EARNINGS")


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
    """
    return _env_flag("STRATUS_PERSIST_MEMORY")


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


def llm_ask_enabled() -> bool:
    """Sprint 3.6.8 Block 1: gates whether contextual Ask STRATUS attempts a
    real, grounded LLM call (AnthropicAskLlmProvider, ask_llm_anthropic.py)
    instead of going straight to the existing deterministic
    answer_question() path. Defaults to disabled, matching every other new
    capability's rollout pattern in this codebase (STRATUS_LIVE_NVDA_EARNINGS,
    STRATUS_PERSIST_MEMORY) -- explicit opt-in, and critically keeps the
    entire pre-existing Ask STRATUS test suite deterministic and isolated
    from any real network call unless a test explicitly enables this. Even
    when enabled, a missing ANTHROPIC_API_KEY or any provider failure falls
    back to the deterministic path rather than erroring (see
    ask_engine.generate_grounded_answer) -- this flag only controls whether
    STRATUS *attempts* the LLM path, never whether Ask STRATUS keeps working
    at all.
    """
    return _env_flag("STRATUS_LLM_ASK")
