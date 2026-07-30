from uuid import UUID

from logan_core.contracts import MemoryRecord


class MemoryPermissionError(PermissionError):
    pass


class MemoryStore:
    """Layer 5 (Logan Memory only — Operational History is owned by the Orchestrator,
    see orchestrator/history.py per ADR-016). Only the Learning System may write here
    (enforced at the call site by requiring a `LearningSystem` writer token).
    """

    def __init__(self) -> None:
        self._records: dict[UUID, MemoryRecord] = {}

    def write(self, record: MemoryRecord, *, writer: str) -> None:
        if writer != "learning_system":
            raise MemoryPermissionError("Only the Learning System may write to Memory (see ADR-019).")
        self._records[record.record_id] = record

    def query(self, domain: str | None = None, entities: list[str] | None = None) -> list[MemoryRecord]:
        results = list(self._records.values())
        if domain is not None:
            results = [r for r in results if r.domain == domain]
        if entities is not None:
            entity_set = set(entities)
            results = [r for r in results if entity_set.intersection(r.entities)]
        return sorted(results, key=lambda r: r.created_at)

    def all(self) -> list[MemoryRecord]:
        return list(self._records.values())
