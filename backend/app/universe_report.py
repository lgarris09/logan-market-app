"""Universe Manager V1a Blocks 17/19 -- the developer-readable operational
report: "what valuable opportunity supply is this universe actually
generating," not just a ticker count (Block 17's own explicit framing).

Read-only, and deliberately cheap: this never triggers a new
reevaluation (that makes ~400 real provider calls, Commit 2) -- it reports
on the *already-persisted* membership ledger plus provider/diagnostic
state that's already being tracked passively by real traffic. A caller
that wants a fresh reevaluation calls `universe_manager.run_universe_
reevaluation()` explicitly (a separate, deliberate, monthly-cadence
action).

Honest scope note (Block 19): the Provider section reuses the exact same
fmp_budget_snapshot() this codebase's existing /v1/dev/fmp-budget route
already reports from -- real, live-traffic-derived numbers. The Exploration
section reports the schema/zero-state honestly: exploration/placement.py
(Commit 4) is built and tested but not yet wired into the live per-user
feed-assembly path (backend/app/logan_feed.py) -- doing so is a distinct,
larger integration step deliberately not taken this pass (see this
session's own report), so there is no real placement history to
aggregate yet. This section says so plainly rather than fabricating
numbers.
"""

import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .config import universe_manager_enabled, universe_scheduler_enabled
from .expansion_review import build_expansion_review
from .opportunity_quality_report import format_opportunity_quality_report
from .universe_manager import (
    REEVALUATION_MIN_INTERVAL_SECONDS,
    UNIVERSE_REEVALUATION_JOB,
    get_membership_store,
    get_scheduler_state,
)
from .universe_telemetry import BLOCKED_METRICS, daily_telemetry_range

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.diagnostics import (  # noqa: E402
    format_fault_catalog,
    format_recent_faults,
)
from logan_core.receptors.providers import fmp_budget_snapshot  # noqa: E402
from logan_core.universe.candidate_source import load_candidate_snapshot  # noqa: E402


def _universe_section() -> list[str]:
    snapshot = load_candidate_snapshot()
    lines = [
        "Universe",
        f"  candidate source: {snapshot.source_id} ({snapshot.source_version}, "
        f"effective {snapshot.effective_date})",
        f"  candidate count: {len(snapshot.securities)}",
    ]
    store = get_membership_store()
    if store is None:
        lines.append("  monitored cohort: unavailable (durable persistence disabled)")
        return lines

    open_records = store.load_open()
    all_records = store.load_all()
    lines.append(f"  monitored count: {len(open_records)}")

    symbol_to_sector = {s.symbol: s.sector or "UNKNOWN" for s in snapshot.securities}
    sector_counts = Counter(
        symbol_to_sector.get(r.symbol, "UNKNOWN") for r in open_records
    )
    if sector_counts:
        lines.append("  sector representation:")
        for sector, count in sorted(sector_counts.items()):
            lines.append(f"    {sector}: {count}")

    closed_records = [r for r in all_records if r.effective_until is not None]
    lines.append(f"  historical admissions: {len(all_records)}")
    lines.append(f"  historical removals: {len(closed_records)}")
    if closed_records:
        removal_reasons = Counter(r.removal_reason for r in closed_records)
        for reason, count in sorted(removal_reasons.items()):
            lines.append(f"    removed ({reason}): {count}")
    return lines


def _provider_section() -> list[str]:
    return [
        "",
        "Provider",
        *("  " + line for line in fmp_budget_snapshot().format_report().splitlines()),
    ]


def _exploration_section() -> list[str]:
    """V1a ITERATE block, Phase 5 correctness fix: this section previously
    said Controlled Exploration was "not yet wired into the live per-user
    feed-assembly path," which became false the moment commit `3d6f05f`
    wired `apply_exploration_placement()` into `logan_feed.py` -- flagged
    as stale drift during this session's own deployment review, fixed
    here. Reports today's real, durable aggregate counts (universe_
    telemetry.py) when any exist; an honest zero-state, never fabricated,
    when persistence is off or nothing has run yet today."""
    today = datetime.now(timezone.utc).date()
    rows = daily_telemetry_range(today, today)
    lines = [
        "",
        "Exploration & Thesis Diversity",
        "  wiring: Controlled Exploration (logan_core/exploration/) and "
        "Thesis Diversity (logan_core/thesis/diversity.py) are both live-"
        "wired into the per-user feed path (backend/app/logan_feed.py's "
        "_run_feed_pipeline(), since commit 3d6f05f) -- every real feed "
        "response already applies both, independent of "
        "universe_manager_enabled().",
    ]
    if not rows:
        lines.append(
            "  today's aggregate: no real observations recorded yet today "
            "(durable telemetry persistence off, or no feed request served "
            "yet today) -- an honest zero-state, not a fabricated count."
        )
        return lines
    row = rows[0]
    lines.append(
        f"  today's aggregate ({row.observation_count} observation(s)): "
        f"{row.diversity_selected_count} top-band selections, "
        f"{row.diversity_suppressed_count} diversity suppressions, "
        f"{row.exploration_eligible_count} exploration-eligible candidates, "
        f"{row.exploration_placed_count} exploration placement(s)"
    )
    return lines


def _scheduler_section() -> list[str]:
    """V1a ITERATE block, Phase 5: real scheduler runtime + durable cadence
    status -- never presents a disabled/never-run scheduler as if it were
    actively maintaining the universe."""
    lines = ["", "Scheduler"]
    lines.append(
        f"  runtime invocation: {'ENABLED' if universe_scheduler_enabled() else 'disabled'} "
        "(STRATUS_UNIVERSE_SCHEDULER_ENABLED) -- whether main.py's background "
        "task automatically calls the reevaluation cadence gate on a schedule"
    )
    lines.append(
        f"  live-feed consumption: {'ENABLED' if universe_manager_enabled() else 'disabled'} "
        "(STRATUS_UNIVERSE_MANAGER_ENABLED) -- whether live_stock_tickers() "
        "actually reads from the monitored cohort this scheduler maintains"
    )
    state = get_scheduler_state(UNIVERSE_REEVALUATION_JOB)
    if state is None:
        lines.append(
            "  reevaluation job state: unavailable (durable persistence off, "
            "or the job has never run) -- an honest zero-state, not a "
            "fabricated success"
        )
        return lines
    lines.append(
        f"  reevaluation job state: last_outcome={state.last_outcome!r}, "
        f"last_started_at={state.last_started_at}, "
        f"last_completed_at={state.last_completed_at}, "
        f"last_succeeded_at={state.last_succeeded_at} "
        f"(cadence floor: {REEVALUATION_MIN_INTERVAL_SECONDS / 86400:.0f} days)"
    )
    return lines


def _telemetry_section() -> list[str]:
    """V1a ITERATE block, Phase 5: real telemetry coverage + the honest
    expansion-review status -- distinguishes an insufficient observation
    window from an inability to evaluate the gates, never presents either
    as a completed, evidence-backed V1a proof."""
    review = build_expansion_review()
    lines = [
        "",
        "Telemetry & Expansion Review",
        f"  observation window: {review.consecutive_days_observed} of "
        f"{review.required_consecutive_days} required consecutive real "
        "calendar days",
        f"  expansion-review status: {review.status}",
    ]
    for note in review.notes:
        lines.append(f"    {note}")
    if review.status == "UNABLE_TO_EVALUATE":
        lines.append(
            f"    unconfirmed required fields ({len(review.unconfirmed_fields)}): "
            + ", ".join(review.unconfirmed_fields)
        )
    lines.append(
        "  blocked metrics (no definition found anywhere in this repository "
        "-- see backend/app/universe_telemetry.py's BLOCKED_METRICS): "
        + ", ".join(BLOCKED_METRICS)
    )
    return lines


def _diagnostics_section() -> list[str]:
    return [
        "",
        "Diagnostics",
        "  " + format_fault_catalog().replace("\n", "\n  "),
        "",
        "  " + format_recent_faults(limit=10).replace("\n", "\n  "),
    ]


def build_universe_report(
    *, include_supply: bool = False, supply_tickers: list | None = None
) -> str:
    """`include_supply=True` additionally reuses
    format_opportunity_quality_report() for the current monitored cohort
    (real, bounded FMP calls -- same cost/posture as
    /v1/dev/opportunity-quality already has) -- off by default so a plain
    universe-report call stays cheap and side-effect-free.
    """
    lines = [
        f"STRATUS Universe Report -- generated {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    lines.extend(_universe_section())
    lines.extend(_provider_section())
    lines.extend(_exploration_section())
    lines.extend(_scheduler_section())
    lines.extend(_telemetry_section())
    lines.extend(_diagnostics_section())

    if include_supply:
        store = get_membership_store()
        tickers = supply_tickers
        if tickers is None and store is not None:
            tickers = [r.symbol for r in store.load_open()]
        if tickers:
            lines.append("")
            lines.append("Supply (per-ticker signal qualification)")
            lines.append(
                "  " + format_opportunity_quality_report(tickers).replace("\n", "\n  ")
            )

    return "\n".join(lines).rstrip()
