"""STRATUS 3.6.12 (Notification Candidate + Decision Ledger V1) -- a
developer-readable report over the durable ledger, answering "what could
we have notified users about, and why did STRATUS send or suppress each
one" without reading raw SQLite rows by hand. Mirrors
opportunity_quality_report.py's own "format a real, already-computed state
as a readable string" discipline exactly -- this module never computes a
notification decision itself, it only aggregates rows
notification_ledger_store.py already durably recorded.

Aggregate counts only, deliberately -- same "process-wide operational
data, not a per-user API response" posture as every other /v1/dev/* route
(universe-report, opportunity-quality, fmp-budget): this report reads
`NotificationLedgerStore.all_candidates()`/`all_decisions()` (every user's
rows) but only ever emits counts/breakdowns, never a per-user list of who
got what -- see this module's own docstring on `build_notification_ledger_report()`
for the exact scope boundary.
"""

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from .notification_ledger_store import NotificationLedgerStore  # noqa: E402


@dataclass(frozen=True)
class NotificationLedgerReport:
    total_candidates: int
    total_decisions: int
    sends: int
    suppressions: int
    suppression_reasons: dict
    watch_candidates: int
    non_watch_candidates: int
    signal_family_breakdown: dict
    interruption_breakdown: dict
    shadow_would_earn_interruption: dict
    distinct_users_with_candidates: int
    distinct_entities: int


def build_notification_ledger_report(
    store: NotificationLedgerStore,
) -> NotificationLedgerReport:
    """Pure aggregation over already-durable rows -- never triggers a new
    pipeline run, never mutates anything. Reads `all_candidates()`/
    `all_decisions()` (every user) deliberately: this report exists to
    prove *policy behavior in aggregate* (per the governing instruction:
    "This is for proving policy behavior before consumer notification
    expansion"), not to answer "what did user X see."
    """
    candidates = store.all_candidates()
    decisions = store.all_decisions()

    suppression_reasons: Counter = Counter()
    signal_family_breakdown: Counter = Counter()
    interruption_breakdown: Counter = Counter()
    sends = 0
    suppressions = 0
    for row in decisions:
        if row["outcome"] == "SEND":
            sends += 1
        else:
            suppressions += 1
            suppression_reasons[row["reason"]] += 1

    watch_candidates = 0
    non_watch_candidates = 0
    distinct_users = set()
    distinct_entities = set()
    for row in candidates:
        signal_family_breakdown[row["signal_family"] or "unknown"] += 1
        interruption_breakdown[row["interruption"]] += 1
        distinct_users.add(row["user_id"])
        distinct_entities.add(row["entity_id"])
        if row["is_watched"]:
            watch_candidates += 1
        else:
            non_watch_candidates += 1

    shadow_breakdown: Counter = Counter()
    import json

    for row in decisions:
        try:
            payload = json.loads(row["payload"])
            shadow_breakdown[payload["shadow"]["would_earn_interruption"]] += 1
        except (KeyError, ValueError):
            # Malformed/legacy payload -- counted as unknown rather than
            # silently dropped or crashing the whole report.
            shadow_breakdown["UNKNOWN"] += 1

    return NotificationLedgerReport(
        total_candidates=len(candidates),
        total_decisions=len(decisions),
        sends=sends,
        suppressions=suppressions,
        suppression_reasons=dict(suppression_reasons),
        watch_candidates=watch_candidates,
        non_watch_candidates=non_watch_candidates,
        signal_family_breakdown=dict(signal_family_breakdown),
        interruption_breakdown=dict(interruption_breakdown),
        shadow_would_earn_interruption=dict(shadow_breakdown),
        distinct_users_with_candidates=len(distinct_users),
        distinct_entities=len(distinct_entities),
    )


def format_notification_ledger_report(store: NotificationLedgerStore) -> str:
    r = build_notification_ledger_report(store)
    lines = [
        "STRATUS Notification Candidate + Decision Ledger V1 -- shadow-mode "
        "report (Earned Interruption foundation)",
        "",
        f"Candidates evaluated: {r.total_candidates} "
        f"(distinct users: {r.distinct_users_with_candidates}, "
        f"distinct entities: {r.distinct_entities})",
        f"Decisions recorded: {r.total_decisions} "
        f"(sends: {r.sends}, suppressions: {r.suppressions})",
        "",
        "Suppression reasons:",
    ]
    if r.suppression_reasons:
        for reason, count in sorted(
            r.suppression_reasons.items(), key=lambda kv: -kv[1]
        ):
            lines.append(f"  {reason}: {count}")
    else:
        lines.append("  (none recorded)")

    lines += [
        "",
        f"Watch vs non-Watch candidates: {r.watch_candidates} watched / "
        f"{r.non_watch_candidates} not watched",
        "",
        "Signal-family breakdown (candidates):",
    ]
    for family, count in sorted(
        r.signal_family_breakdown.items(), key=lambda kv: -kv[1]
    ):
        lines.append(f"  {family}: {count}")

    lines += ["", "Interruption breakdown (candidates):"]
    for interruption, count in sorted(
        r.interruption_breakdown.items(), key=lambda kv: -kv[1]
    ):
        lines.append(f"  {interruption}: {count}")

    lines += [
        "",
        "Shadow would_earn_interruption breakdown (decisions) -- shadow-only, "
        "never applied to any real send/suppress decision above:",
    ]
    if r.shadow_would_earn_interruption:
        for state, count in sorted(
            r.shadow_would_earn_interruption.items(), key=lambda kv: -kv[1]
        ):
            lines.append(f"  {state}: {count}")
    else:
        lines.append("  (none recorded)")

    return "\n".join(lines)
