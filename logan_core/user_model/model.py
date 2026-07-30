from datetime import datetime, timezone
from typing import Literal, Optional

from logan_core.contracts import DomainPref, Holding, Interest, MemoryRecord, UserModel


class UserModelBuilder:
    """Layer 6a — Logan's durable interpretation of who the user is, built from
    retained Memory evidence. Never updates itself from raw events or clicks — only
    ever rebuilt from MemoryRecord[] supplied by the Memory System, which itself
    only accepts writes from the Learning System.
    """

    def seed(
        self,
        user_id: str,
        holdings: Optional[list[Holding]] = None,
        interests: Optional[list[Interest]] = None,
        risk_tolerance: Literal["conservative", "moderate", "aggressive", "unknown"] = "unknown",
    ) -> UserModel:
        now = datetime.now(timezone.utc)
        domains = {h.domain for h in (holdings or [])} | {i.domain for i in (interests or [])}
        return UserModel(
            user_id=user_id,
            interests=interests or [],
            holdings=holdings or [],
            risk_tolerance=risk_tolerance,
            domain_preferences=[
                DomainPref(domain=d, active=True, weight=0.5, last_updated=now) for d in domains
            ],
            model_confidence=0.5,
            last_updated=now,
            version=1,
        )

    def build(self, user_id: str, memory_records: list[MemoryRecord], base: UserModel) -> UserModel:
        """Rebuild the UserModel by folding in preference_signal / user_statement
        memory records. Increases model_confidence as evidence accumulates.
        """
        preference_records = [
            r for r in memory_records if r.record_type in ("preference_signal", "user_statement")
        ]
        evidence_count = len(preference_records)
        model_confidence = min(0.5 + evidence_count * 0.05, 1.0)

        return base.model_copy(
            update={
                "model_confidence": model_confidence,
                "last_updated": datetime.now(timezone.utc),
                "version": base.version + 1,
            }
        )
