from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from logan_core.contracts import (
    AttentionRecommendation,
    AttentionState,
    CooldownRecord,
    DecisionTraceEntry,
    FatigueRecord,
    PolicyResult,
    PrioritizedItem,
    SurfaceRecord,
)

COOLDOWN_WINDOW = timedelta(hours=2)
FATIGUE_WINDOW = timedelta(hours=24)
FATIGUE_LIMIT = 5


class PrioritizationEngine:
    """Layer 12 — manages competition and repetition across pending items. Separates
    visibility from interruption. Owns AttentionState. Forbidden per spec: modifying
    reasoning/scores/policy decisions, writing to Memory System directly (fatigue
    signals route through Learning).
    """

    def __init__(self) -> None:
        self._states: dict[str, AttentionState] = {}

    def _state_for(self, user_id: str, now: datetime) -> AttentionState:
        state = self._states.get(user_id)
        if state is None:
            state = AttentionState(user_id=user_id, last_updated=now)
            self._states[user_id] = state
        return state

    def prioritize(
        self,
        user_id: str,
        domain: str,
        policy_result: PolicyResult,
        recommendation: AttentionRecommendation,
        rank: int = 1,
        changed_since_view: bool = True,
        now: datetime | None = None,
    ) -> PrioritizedItem:
        now = now or datetime.now(timezone.utc)
        state = self._state_for(user_id, now)
        event_id = policy_result.event_id

        cooldown = next((c for c in state.cooldowns if c.event_id == event_id and c.until > now), None)
        in_cooldown = cooldown is not None and not changed_since_view

        fatigue = next((f for f in state.fatigue if f.domain == domain), None)
        domain_fatigued = fatigue is not None and fatigue.count >= FATIGUE_LIMIT

        visibility: Literal["primary", "feed", "background", "hidden"]
        interruption: Literal["alert", "digest", "none"]

        if not policy_result.permitted or in_cooldown:
            visibility = "hidden"
            interruption = "none"
        elif domain_fatigued:
            visibility = "background"
            interruption = "none"
        elif recommendation.internal_rank_score >= 0.6:
            visibility = "primary"
            interruption = "alert" if policy_result.communication_mode == "alert" else "digest"
        elif recommendation.internal_rank_score >= 0.35:
            visibility = "feed"
            interruption = "digest" if policy_result.communication_mode != "informational" else "none"
        else:
            visibility = "background"
            interruption = "none"

        if visibility in ("primary", "feed"):
            state.surfaced.append(SurfaceRecord(event_id=event_id, surfaced_at=now))
            state.cooldowns = [c for c in state.cooldowns if c.event_id != event_id]
            state.cooldowns.append(CooldownRecord(event_id=event_id, until=now + COOLDOWN_WINDOW))

            existing_fatigue = next((f for f in state.fatigue if f.domain == domain), None)
            if existing_fatigue is None:
                state.fatigue.append(FatigueRecord(domain=domain, count=1, window=now))
            else:
                state.fatigue = [
                    f if f.domain != domain else FatigueRecord(domain=domain, count=f.count + 1, window=now)
                    for f in state.fatigue
                ]

        state.last_updated = now

        return PrioritizedItem(
            event_id=event_id,
            visibility=visibility,
            interruption=interruption,
            rank=rank,
            cooldown_until=cooldown.until if cooldown else None,
            changed_since_view=changed_since_view,
            prioritized_at=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="prioritization",
                    rule=f"visibility={visibility}, interruption={interruption} "
                    f"(in_cooldown={in_cooldown}, domain_fatigued={domain_fatigued})",
                    timestamp=now,
                )
            ],
        )

    def attention_state(self, user_id: str) -> AttentionState | None:
        return self._states.get(user_id)
