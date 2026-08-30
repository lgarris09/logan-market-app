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

from .opportunity_quality_report import format_opportunity_quality_report
from .universe_manager import get_membership_store

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
    return [
        "",
        "Exploration",
        "  placement history: not yet available -- exploration/placement.py "
        "(Commit 4) is built and tested but not wired into the live "
        "per-user feed-assembly path yet, so there is no real placement "
        "history to report on. This is an honest zero-state, not a "
        "fabricated count.",
    ]


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
