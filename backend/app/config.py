"""Sprint 3.6.6C — the first place `backend/app/` reads `.env` or runtime
config. Reconnaissance before writing this: no config.py/settings.py
existed, and no module under backend/app/ called os.environ or load_dotenv
anywhere -- backend/.env (FMP_API_KEY, gitignored, local-dev-only) was not
being auto-loaded into the backend process at all. This is the minimal
addition needed, not a general settings framework.
"""

import os
import re
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


_TICKER_PATTERN = re.compile(r"^[A-Z]{1,10}$")
# The original single-ticker flag (Sprint 3.6.6C) -- kept working unchanged
# for backward compatibility, not deprecated outright. See
# live_stock_tickers()'s own docstring for how the two flags interact.
_LEGACY_NVDA_ONLY_TICKERS: tuple[str, ...] = ("NVDA",)


def live_stock_tickers() -> tuple[str, ...]:
    """Sprint 3.6.8 Block 5: the deterministic, code-free mechanism for
    configuring which equity tickers the live runtime evaluates -- reads
    STRATUS_LIVE_STOCK_TICKERS (comma-separated, e.g. "NVDA,TSLA,AAPL").
    Adding a new supported ticker later is a config change, not a Python
    change (see backend/app/logan_feed.py's generalized _live_earnings_raw_
    signal/_live_price_move_raw_signal/_live_analyst_grade_raw_signal, which
    already accept any ticker the underlying FMP provider can serve).

    No network call -- this only parses and validates the environment
    variable. Each comma-separated entry is stripped and upper-cased; an
    entry that doesn't match a plausible ticker shape (1-10 letters -- FMP
    symbols are alphabetic in every case this codebase's providers already
    handle) is dropped with a loud log line rather than silently included or
    crashing the pipeline over a config typo -- "invalid ticker
    configuration fails safely" means the *rest* of a valid list still
    works, not that the whole flag is discarded. Duplicate entries are
    silently de-duplicated (a repeated ticker in the list must never cause
    a double-fetch or manufacture an extra signal source). An empty/unset
    variable and a variable that parses to zero valid entries are treated
    identically -- no arbitrary distinction between "not configured" and
    "configured with nothing usable."

    Backward compatibility, not a silent behavior change: when
    STRATUS_LIVE_STOCK_TICKERS is unset (or parses to nothing), this falls
    back to the original STRATUS_LIVE_NVDA_EARNINGS flag -- exactly
    ("NVDA",) when that's true, exactly () when it's false/unset. Every
    existing deployment/test using only the old flag is completely
    unaffected. Setting STRATUS_LIVE_STOCK_TICKERS at all takes over
    entirely (the old flag is not additionally consulted in that case) --
    one clear source of truth per configuration, not a merge of both.
    """
    raw = os.environ.get("STRATUS_LIVE_STOCK_TICKERS", "").strip()
    if not raw:
        return _LEGACY_NVDA_ONLY_TICKERS if live_nvda_earnings_enabled() else ()

    tickers: list[str] = []
    seen: set[str] = set()
    for piece in raw.split(","):
        ticker = piece.strip().upper()
        if not ticker:
            continue
        if not _TICKER_PATTERN.match(ticker):
            print(
                f"[config] STRATUS_LIVE_STOCK_TICKERS: ignoring invalid entry "
                f"{ticker!r} (expected 1-10 letters)"
            )
            continue
        if ticker in seen:
            continue
        seen.add(ticker)
        tickers.append(ticker)
    return tuple(tickers)


def live_data_only_mode() -> bool:
    """Sprint 3.6.8 Block 5: the production-vs-demo runtime boundary.
    STRATUS_RUNTIME_MODE=live (or "beta"/"production", treated identically
    for now -- this codebase doesn't yet distinguish a trusted-beta
    deployment from public production, see
    27_SECURITY_PRIVACY_COMPLIANCE.md) switches `_run_feed_pipeline()`
    (backend/app/logan_feed.py) from "simulated fixtures for every entity,
    optionally replaced by live data" (the existing, unchanged demo/
    development behavior -- this function returns False by default) to
    "only entities with genuinely live-fetched data appear at all."

    In live-data-only mode: unsupported domains (no live provider exists for
    them at all -- crypto, sports, social, prediction markets, news/macro)
    contribute nothing, honestly absent rather than backfilled with
    simulated intelligence. A configured live ticker (live_stock_tickers())
    whose live fetch fails or doesn't qualify this poll is *also* honestly
    absent -- a provider failure never silently substitutes a fixture in
    this mode, unlike demo mode's existing, intentional fixture fallback.
    Fixtures are not deleted or made unreachable -- simulated_fixtures()
    itself is completely unchanged -- this only gates whether
    _run_feed_pipeline() ever calls it.
    """
    mode = os.environ.get("STRATUS_RUNTIME_MODE", "").strip().lower()
    return mode in ("live", "beta", "production")


def legacy_memory_db_path() -> Path:
    """Sprint 3.6.9 Block 1: the historical `memory_engine.py` prototype
    (`/v1/memories`) previously hardcoded its SQLite file to
    `backend/data/logan_memory.db` relative to `main.py` -- fine for local
    dev (that path is writable, ephemeral disk on the dev machine), wrong for
    a hosted deployment, where `backend/data/` inside the container is
    ephemeral container storage, not the durable Fly Volume. Overridable via
    STRATUS_LEGACY_MEMORY_DB_PATH so a hosted deployment can point this at
    the same durable volume `memory_store_db_path()` already uses (e.g.
    `/data/logan_memory.db`) -- defaults to the exact pre-Block-1 path when
    unset, so local dev is completely unaffected.
    """
    override = os.environ.get("STRATUS_LEGACY_MEMORY_DB_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "logan_memory.db"


def notification_store_db_path() -> Path:
    """Sprint 3.6.9 Block 1: the durable SQLite file backing registered push
    tokens and dispatch/review dedup state (see notification_store.py) when
    memory_persistence_enabled() is true -- deliberately reuses that same
    flag rather than inventing a second persistence toggle (see the Sprint
    3.6.9 Block 1 ADR): "durable state persistence is enabled for this
    deployment" is one operator decision, not two. A separate SQLite *file*
    from memory_store_db_path() (not a shared connection to the same file) --
    same durable directory, independent schema/lifecycle, so this store's
    tests and MemoryStore's tests never contend for the same file. Defaults
    to a sibling `notifications.db` next to memory_store_db_path()'s own
    file, so a hosted deployment only has to set STRATUS_STATE_DB_PATH to
    point both stores at the durable volume. Overridable independently via
    STRATUS_NOTIFICATIONS_DB_PATH for test isolation.
    """
    override = os.environ.get("STRATUS_NOTIFICATIONS_DB_PATH", "").strip()
    if override:
        return Path(override)
    return memory_store_db_path().parent / "notifications.db"


def lifecycle_store_db_path() -> Path:
    """Stock Opportunity Logic V2: the durable SQLite file backing
    OpportunityLifecycleTracker's per-entity_id snapshots (see
    lifecycle_store.py) when memory_persistence_enabled() is true --
    mirrors notification_store_db_path()'s identical pattern: a separate
    file from memory_store_db_path(), same durable directory, own
    independent schema. Defaults to a sibling `lifecycle_state.db`;
    overridable via STRATUS_LIFECYCLE_DB_PATH for test isolation.
    """
    override = os.environ.get("STRATUS_LIFECYCLE_DB_PATH", "").strip()
    if override:
        return Path(override)
    return memory_store_db_path().parent / "lifecycle_state.db"


def earnings_cache_store_db_path() -> Path:
    """V2.3A.1 field reliability work: the durable SQLite file backing
    FmpEarningsProvider's last-successful-earnings-observation-per-entity_id
    (see earnings_cache_store.py) when memory_persistence_enabled() is true
    -- mirrors lifecycle_store_db_path()'s identical pattern: a separate
    file, same durable directory, own independent schema. Defaults to a
    sibling `earnings_observations.db`; overridable via
    STRATUS_EARNINGS_CACHE_DB_PATH for test isolation.
    """
    override = os.environ.get("STRATUS_EARNINGS_CACHE_DB_PATH", "").strip()
    if override:
        return Path(override)
    return memory_store_db_path().parent / "earnings_observations.db"


def revision_store_db_path() -> Path:
    """Stock Opportunity Logic V2.1 (User Sync Gap): the durable SQLite file
    backing each entity's meaningful-revision history (see
    revision_store.py) when memory_persistence_enabled() is true -- mirrors
    lifecycle_store_db_path()'s identical pattern: a separate file, same
    durable directory, own independent schema. Defaults to a sibling
    `opportunity_revisions.db`; overridable via STRATUS_REVISIONS_DB_PATH
    for test isolation.
    """
    override = os.environ.get("STRATUS_REVISIONS_DB_PATH", "").strip()
    if override:
        return Path(override)
    return memory_store_db_path().parent / "opportunity_revisions.db"


def account_store_db_path() -> Path:
    """Stock Opportunity Logic V2.3A (Identity & Account Foundation): the
    durable SQLite file backing the account/external-identity mapping (see
    account_store.py) when memory_persistence_enabled() is true -- same
    pattern as every other Sprint 3.6.9+ store. Defaults to a sibling
    `accounts.db`; overridable via STRATUS_ACCOUNTS_DB_PATH for test
    isolation.
    """
    override = os.environ.get("STRATUS_ACCOUNTS_DB_PATH", "").strip()
    if override:
        return Path(override)
    return memory_store_db_path().parent / "accounts.db"


def clerk_issuer_url() -> str | None:
    """V2.3A: the Clerk Frontend API URL that also serves as this project's
    JWT issuer (e.g. https://your-instance.clerk.accounts.dev, or a custom
    domain in production) -- read from CLERK_ISSUER_URL. Unset by default,
    matching every other new capability's rollout pattern in this codebase
    (STRATUS_LLM_ASK, STRATUS_PERSIST_MEMORY): authentication stays
    completely inert -- no JWKS fetch, no token verification attempted --
    until this is explicitly configured with a real Clerk instance.
    """
    value = os.environ.get("CLERK_ISSUER_URL", "").strip()
    return value.rstrip("/") or None


def clerk_configured() -> bool:
    return clerk_issuer_url() is not None


def user_knowledge_store_db_path() -> Path:
    """Stock Opportunity Logic V2.1 (User Sync Gap): the durable SQLite file
    backing per-`(user_id, entity_id)` knowledge pointers (see
    user_knowledge_store.py) when memory_persistence_enabled() is true --
    same pattern as the other Sprint 3.6.9+ stores. Defaults to a sibling
    `user_opportunity_knowledge.db`; overridable via
    STRATUS_USER_KNOWLEDGE_DB_PATH for test isolation.
    """
    override = os.environ.get("STRATUS_USER_KNOWLEDGE_DB_PATH", "").strip()
    if override:
        return Path(override)
    return memory_store_db_path().parent / "user_opportunity_knowledge.db"


def cors_allowed_origins() -> list[str]:
    """Sprint 3.6.9 Block 1: environment-configurable CORS policy, replacing
    the previous hardcoded `allow_origins=["*"]`. Reads
    STRATUS_CORS_ALLOWED_ORIGINS (comma-separated, e.g.
    "https://app.example.com,https://admin.example.com") when set -- an
    explicit operator choice always wins, in any runtime mode.

    When unset, the default depends on live_data_only_mode(): demo/
    development mode (the default) keeps the exact pre-Block-1 behavior,
    `["*"],` so nothing changes for local dev or the existing test suite.
    Beta/production mode defaults to an empty allowlist (`[]`) instead of
    silently inheriting the wildcard -- a hosted deployment must not
    accidentally serve every browser origin just because nobody set this
    variable.

    Irrelevant to the mobile app either way: CORS is a browser-enforced
    mechanism (preflight + `Origin` header checks) that React Native's
    `fetch` is not subject to at all -- restricting this list can never
    block a native mobile request, only a hypothetical future browser-based
    client from an origin not on the list.
    """
    raw = os.environ.get("STRATUS_CORS_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [] if live_data_only_mode() else ["*"]


def startup_config_summary() -> str:
    """Sprint 3.6.9 Block 1: one loud, non-secret line logged at process
    startup (see main.py's `_lifespan`) so the *effective* configuration of a
    given deployment is always visible in its logs -- "fail clearly" means
    visibly stating what mode this process actually came up in, not just
    handling misconfiguration silently. Never includes a secret value, only
    which optional capabilities are on/off and which mode is active.
    """
    tickers = live_stock_tickers()
    return (
        f"[startup] runtime_mode={'live-data-only' if live_data_only_mode() else 'demo'} "
        f"live_tickers={','.join(tickers) if tickers else '(none)'} "
        f"memory_persistence={memory_persistence_enabled()} "
        f"llm_ask={llm_ask_enabled()} "
        f"clerk_auth={clerk_configured()} "
        f"cors_origins={cors_allowed_origins()}"
    )


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
