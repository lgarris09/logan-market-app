"""Universe Manager V1a -- backend/app orchestration layer: real provider
I/O for eligibility evaluation (logan_core/universe/eligibility.py stays a
pure function; this module is the adapter that actually calls FMP, mirrors
opportunity_quality_report.py's own established split), the durable
membership-store singleton (mirrors watch.py's `_get_store()` pattern
exactly), and `monitored_tickers()` -- the accessor `logan_feed.py` can
optionally read from once `config.universe_manager_enabled()` is turned on.

`run_universe_reevaluation()` makes real FMP calls (quote + profile +
earnings + analyst grade per candidate) -- an explicit, developer/operator-
triggered action for the monthly-cadence reevaluation Block 2/6 describe,
never invoked from the regular request/poll path. A full run against all
100 V1a candidates is ~300 provider calls; pacing that within STRATUS's
own 220-calls/minute operating ceiling is the Provider Scheduler's job
(logan_core/receptors/providers/scheduler.py) -- this function is written
to be wrapped by that scheduler once wired, not to self-pace.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Protocol, TypeVar

from .config import memory_persistence_enabled, universe_membership_db_path
from .universe_store import UniverseMembershipStore

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import (  # noqa: E402
    CandidateSecurity,
    CohortRebalanceResult,
    EligibilityResult,
)
from logan_core.receptors.providers import (  # noqa: E402
    CompanyProfile,
    EarningsProvider,
    FmpEarningsProvider,
    FmpMarketDataProvider,
    FmpProviderError,
    GradeChange,
    ProviderScheduler,
    Quote,
)
from logan_core.universe import (  # noqa: E402
    evaluate_eligibility,
    load_candidate_snapshot,
    rebalance_membership,
    select_monitored_cohort,
)

T = TypeVar("T")


class _MarketDataSource(Protocol):
    """Structural type combining exactly the three FmpMarketDataProvider
    methods this module needs -- lets a test inject FixtureMarketDataProvider
    (or any other duck-typed stand-in) without this module depending on the
    concrete Fmp* classes or a new shared Protocol being added to
    logan_core/receptors/providers/base.py just for this."""

    def fetch_quote(self, entity_id: str) -> Optional[Quote]: ...

    def fetch_company_profile(self, entity_id: str) -> Optional[CompanyProfile]: ...

    def fetch_latest_grade_change(self, entity_id: str) -> Optional[GradeChange]: ...


_store: Optional[UniverseMembershipStore] = None


def _get_store() -> Optional[UniverseMembershipStore]:
    global _store
    if not memory_persistence_enabled():
        return None
    if _store is None:
        _store = UniverseMembershipStore(universe_membership_db_path())
    return _store


def reset_universe_manager_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring
    reset_watch_state(). Releases the durable store's SQLite connection
    (a no-op when persistence is disabled) without touching the underlying
    file."""
    global _store
    if _store is not None:
        _store.close()
    _store = None


def _paced_call(
    scheduler: Optional[ProviderScheduler],
    endpoint: str,
    priority: str,
    max_wait_seconds: float,
    fetch: Callable[[], T],
) -> T:
    """Routes `fetch` through the Provider Scheduler's admission control
    when one is supplied, otherwise calls it directly (byte-identical to
    pre-Block-7 behavior) -- gating only ever wraps a real call, so a
    caller that never passes a scheduler sees no change at all."""
    if scheduler is None:
        return fetch()
    return scheduler.gate(
        endpoint, fetch, priority=priority, max_wait_seconds=max_wait_seconds
    )


DEFAULT_SCHEDULER_MAX_WAIT_SECONDS = 90.0


def evaluate_candidate_eligibility(
    candidate: CandidateSecurity,
    *,
    market_data_provider: _MarketDataSource,
    earnings_provider: EarningsProvider,
    scheduler: Optional[ProviderScheduler] = None,
    priority: str = "normal",
    scheduler_max_wait_seconds: float = DEFAULT_SCHEDULER_MAX_WAIT_SECONDS,
    now: Optional[datetime] = None,
) -> EligibilityResult:
    """Real-I/O adapter around the pure `evaluate_eligibility()` -- fetches
    quote/profile/earnings/analyst-grade for one candidate and translates
    the result into that function's plain, typed inputs.

    Two honest V1a simplifications, both scoped to this specific candidate
    source (an S&P 100 snapshot): `is_supported_exchange` is always True --
    CompanyProfile (logan_core/receptors/providers/base.py) carries no
    exchange field FMP's free-tier profile response doesn't return, and
    every real S&P 100 constituent is by definition a supported US
    exchange listing, so this can't meaningfully fail for this source
    today. `is_actively_trading` is inferred from quote presence and a
    positive price -- this codebase's Quote contract has no explicit
    halted/delisted flag; a real halt/delisting shows up here as a missing
    or failed quote fetch (REJECT_DATA_HEALTH), an honestly coarser signal
    than a dedicated trading-status field would give.

    `scheduler` (Operational Beta Hardening / Universe Manager V1a Block 7,
    optional, default None): when supplied, every one of this candidate's
    four provider calls is paced through it (`ProviderScheduler.gate()`),
    so a reevaluation run against the whole candidate source can never
    burst past STRATUS's own operating ceiling -- see
    `run_universe_reevaluation()`, the real caller that supplies one.
    `scheduler_max_wait_seconds` defaults generously above the scheduler's
    own 60s rolling window, since a bulk reevaluation run legitimately
    takes a couple of minutes to pace through ~400 calls at the ceiling --
    a short per-call wait budget would raise
    `ProviderSchedulerSaturatedError` partway through a perfectly healthy
    run.
    """
    now = now or datetime.now(timezone.utc)
    try:
        quote = _paced_call(
            scheduler,
            "quote",
            priority,
            scheduler_max_wait_seconds,
            lambda: market_data_provider.fetch_quote(candidate.symbol),
        )
        provider_health_ok = True
    except FmpProviderError:
        quote = None
        provider_health_ok = False

    try:
        profile = _paced_call(
            scheduler,
            "profile",
            priority,
            scheduler_max_wait_seconds,
            lambda: market_data_provider.fetch_company_profile(candidate.symbol),
        )
    except FmpProviderError:
        profile = None

    try:
        earnings = _paced_call(
            scheduler,
            "earnings",
            priority,
            scheduler_max_wait_seconds,
            lambda: earnings_provider.fetch_latest_earnings(candidate.symbol),
        )
        has_earnings_coverage = earnings is not None
    except FmpProviderError:
        has_earnings_coverage = False

    try:
        grade = _paced_call(
            scheduler,
            "analyst_grade",
            priority,
            scheduler_max_wait_seconds,
            lambda: market_data_provider.fetch_latest_grade_change(candidate.symbol),
        )
        has_analyst_grade_coverage = grade is not None
    except FmpProviderError:
        has_analyst_grade_coverage = False

    # A genuine provider failure (exception) is a data-health problem, not
    # evidence the security isn't trading -- `not provider_health_ok` short-
    # circuits this to True so eligibility.py's REJECT_DATA_HEALTH (which
    # checks `provider_health_ok` directly) is what actually fires, rather
    # than a coincidental REJECT_TRADING_INACTIVE masking the real cause. A
    # clean response with no quote (no exception, just nothing on file) is
    # still treated as "not actively trading" -- the honest, coarser signal
    # this codebase's Quote contract supports for a delisted/invalid symbol.
    is_actively_trading = not provider_health_ok or (
        quote is not None and quote.price > 0
    )
    average_dollar_volume: Optional[float] = None
    if profile is not None and profile.average_volume is not None and quote is not None:
        average_dollar_volume = profile.average_volume * quote.price

    return evaluate_eligibility(
        candidate,
        is_actively_trading=is_actively_trading,
        is_supported_exchange=True,
        has_price_coverage=quote is not None,
        has_earnings_coverage=has_earnings_coverage,
        has_analyst_grade_coverage=has_analyst_grade_coverage,
        average_dollar_volume=average_dollar_volume,
        provider_health_ok=provider_health_ok,
        now=now,
    )


def run_universe_reevaluation(
    *,
    market_data_provider: Optional[_MarketDataSource] = None,
    earnings_provider: Optional[EarningsProvider] = None,
    scheduler: Optional[ProviderScheduler] = None,
    now: Optional[datetime] = None,
) -> CohortRebalanceResult:
    """The full Block 2->6 pipeline against real (or injected fixture)
    providers: load the candidate snapshot, evaluate eligibility for every
    candidate, select the monitored cohort, diff against current
    membership, and persist the result (when persistence is enabled).
    Providers default to real FmpMarketDataProvider/FmpEarningsProvider
    instances (constructed fresh per call, same pattern as
    opportunity_quality_report.py) -- tests inject fixtures instead.

    `scheduler` (Block 7, optional, default None): a real production
    invocation of this function against the full ~100-candidate V1a
    snapshot is ~400 provider calls (quote + profile + earnings + grade
    per candidate) -- a caller making that real call should always supply a
    `ProviderScheduler` (paced against STRATUS's own operating ceiling,
    well under FMP's actual limit) so this can never burst the shared
    provider budget. Left as an explicit opt-in, not auto-constructed here,
    so a test exercising this function's selection/rebalance logic with a
    handful of fixture candidates isn't forced to pace through a real
    (or fake-clocked) scheduler it doesn't need.
    """
    now = now or datetime.now(timezone.utc)
    market_data_provider = market_data_provider or FmpMarketDataProvider()
    earnings_provider = earnings_provider or FmpEarningsProvider()

    snapshot = load_candidate_snapshot()
    evaluated: list[tuple[CandidateSecurity, EligibilityResult]] = []
    for candidate in snapshot.securities:
        result = evaluate_candidate_eligibility(
            candidate,
            market_data_provider=market_data_provider,
            earnings_provider=earnings_provider,
            scheduler=scheduler,
            scheduler_max_wait_seconds=DEFAULT_SCHEDULER_MAX_WAIT_SECONDS,
            now=now,
        )
        evaluated.append((candidate, result))

    cohort = select_monitored_cohort(evaluated)
    reason_codes_by_id = {
        candidate.canonical_id: result.reason_codes
        for candidate, result in evaluated
        if result.eligible
    }

    store = _get_store()
    current_members = store.load_open() if store is not None else []
    rebalance = rebalance_membership(
        current_members,
        cohort,
        source_version=snapshot.source_version,
        now=now,
        admission_reason_codes_by_id=reason_codes_by_id,
    )

    if store is not None:
        for record in rebalance.admitted:
            store.save_admission(record)
        for record in rebalance.removed:
            store.save_removal(record)

    return rebalance


def monitored_tickers() -> tuple[str, ...]:
    """Universe Manager V1a's own live accessor -- the current MONITORED
    cohort's symbols, sourced from the durable membership store. Returns an
    empty tuple when persistence is disabled (nothing durable to read) or
    no reevaluation has ever run -- callers (config.live_stock_tickers(),
    once wired) must treat that identically to "not configured," never a
    fault. Deliberately independent of config.universe_manager_enabled() --
    that flag gates whether `live_stock_tickers()` calls this at all, not
    whether this function itself works.
    """
    store = _get_store()
    if store is None:
        return ()
    return tuple(sorted(record.symbol for record in store.load_open()))
