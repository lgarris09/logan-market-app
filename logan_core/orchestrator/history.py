from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class OperationalHistoryEntry:
    ref: UUID
    kind: str
    domain: str | None
    payload: object
    recorded_at: datetime


class OperationalHistoryStore:
    """Append-only log of everything the pipeline has observed.

    Owned exclusively by the System Orchestrator (ADR-016) — no other layer writes here.
    World Model may read it. Retained indefinitely, not loaded into active memory.
    """

    def __init__(self) -> None:
        self._entries: list[OperationalHistoryEntry] = []
        self._by_ref: dict[UUID, OperationalHistoryEntry] = {}

    def record(self, ref: UUID, kind: str, payload: object, domain: str | None = None) -> None:
        entry = OperationalHistoryEntry(
            ref=ref, kind=kind, domain=domain, payload=payload, recorded_at=datetime.now(timezone.utc)
        )
        self._entries.append(entry)
        self._by_ref[ref] = entry

    def get(self, ref: UUID) -> OperationalHistoryEntry | None:
        return self._by_ref.get(ref)

    def by_kind(self, kind: str) -> list[OperationalHistoryEntry]:
        return [e for e in self._entries if e.kind == kind]

    def by_domain(self, domain: str) -> list[OperationalHistoryEntry]:
        return [e for e in self._entries if e.domain == domain]

    def __len__(self) -> int:
        return len(self._entries)
