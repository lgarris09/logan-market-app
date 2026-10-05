from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

# STRATUS reliability correction (residual memory growth, ADR-074): the most
# recent entries this in-memory store keeps. Every pipeline run records one
# entry per normalized signal and one per enriched event, and the store is
# process-lifetime (one Orchestrator serves every poll), so without a bound
# it retained every signal and every per-poll event copy forever -- measured
# as ~87% of v31's remaining memory growth. Nothing in production reads this
# store (`get`/`by_kind`/`by_domain` have no caller outside tests); it exists
# for diagnostics. 2,000 entries is several complete pipeline runs of recent
# history at the current 30-ticker cohort (~7 MB), which is what a developer
# inspecting "what did the pipeline just see" needs.
OPERATIONAL_HISTORY_MAX_ENTRIES = 2000


@dataclass
class OperationalHistoryEntry:
    ref: UUID
    kind: str
    domain: str | None
    payload: object
    recorded_at: datetime


class OperationalHistoryStore:
    """Recent-history log of what the pipeline has observed.

    Owned exclusively by the System Orchestrator (ADR-016) — no other layer writes here.
    World Model may read it.

    This is the *in-memory* store. The spec's Operational History ("all raw
    signals ... retained indefinitely ... not loaded into active memory") is a
    durable store that has not been built (database undecided, ADR-006); until
    it exists, keeping everything in process memory is the opposite of "not
    loaded into active memory". This class therefore keeps only the most
    recent `max_entries` entries (ADR-074): the oldest entry is dropped first,
    deterministically, each time a new one would exceed the bound.
    """

    def __init__(self, max_entries: int = OPERATIONAL_HISTORY_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._max_entries = max_entries
        self._entries: deque[OperationalHistoryEntry] = deque()
        self._by_ref: dict[UUID, OperationalHistoryEntry] = {}

    def record(
        self, ref: UUID, kind: str, payload: object, domain: str | None = None
    ) -> None:
        entry = OperationalHistoryEntry(
            ref=ref,
            kind=kind,
            domain=domain,
            payload=payload,
            recorded_at=datetime.now(timezone.utc),
        )
        self._entries.append(entry)
        self._by_ref[ref] = entry
        while len(self._entries) > self._max_entries:
            expired = self._entries.popleft()
            # The same ref is recorded again on every poll of an unchanged
            # event; only forget the ref when its newest entry is the one
            # expiring.
            if self._by_ref.get(expired.ref) is expired:
                del self._by_ref[expired.ref]

    def get(self, ref: UUID) -> OperationalHistoryEntry | None:
        return self._by_ref.get(ref)

    def by_kind(self, kind: str) -> list[OperationalHistoryEntry]:
        return [e for e in self._entries if e.kind == kind]

    def by_domain(self, domain: str) -> list[OperationalHistoryEntry]:
        return [e for e in self._entries if e.domain == domain]

    def __len__(self) -> int:
        return len(self._entries)
