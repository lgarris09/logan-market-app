from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from logan_core.contracts import (
    AttentionRecommendation,
    AttentionState,
    CooldownRecord,
    DecisionTraceEntry,
    Domain,
    FatigueRecord,
    NotificationReviewRecord,
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
        domain: Domain,
        policy_result: PolicyResult,
        recommendation: AttentionRecommendation,
        rank: int = 1,
        changed_since_view: bool = True,
        now: datetime | None = None,
    ) -> PrioritizedItem:
        now = now or datetime.now(timezone.utc)
        state = self._state_for(user_id, now)
        event_id = policy_result.event_id

        # Attention/user-view state, deliberately independent of World Model
        # event identity: whether *this user* has acknowledged this exact
        # event_id before, not whether World Model considers it a "new"
        # underlying event (EnrichedEvent.is_new/prior_event_id -- a
        # different question, answered upstream in world_model/model.py).
        # An event that's been surfaced five times but never reviewed stays
        # is_new_for_user=True on every one of those five surfacings; only
        # mark_reviewed() clears it, not re-observation.
        is_new_for_user = not any(
            r.event_id == event_id for r in state.notifications_reviewed
        )

        cooldown = next(
            (c for c in state.cooldowns if c.event_id == event_id and c.until > now),
            None,
        )
        in_cooldown = cooldown is not None and not changed_since_view

        # A fatigue record whose window started more than FATIGUE_WINDOW ago has
        # fully decayed -- it no longer counts toward the limit (V3.1.4 BATCH-2;
        # previously FATIGUE_WINDOW was declared but never read, so fatigue only
        # ever grew and never expired).
        fatigue = next((f for f in state.fatigue if f.domain == domain), None)
        domain_fatigued = (
            fatigue is not None
            and (now - fatigue.window) <= FATIGUE_WINDOW
            and fatigue.count >= FATIGUE_LIMIT
        )

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
            interruption = (
                "alert" if policy_result.communication_mode == "alert" else "digest"
            )
        elif recommendation.internal_rank_score >= 0.35:
            visibility = "feed"
            interruption = (
                "digest"
                if policy_result.communication_mode != "informational"
                else "none"
            )
        else:
            visibility = "background"
            interruption = "none"

        if visibility in ("primary", "feed"):
            state.surfaced.append(SurfaceRecord(event_id=event_id, surfaced_at=now))
            state.cooldowns = [c for c in state.cooldowns if c.event_id != event_id]
            state.cooldowns.append(
                CooldownRecord(event_id=event_id, until=now + COOLDOWN_WINDOW)
            )

            existing_fatigue = next(
                (f for f in state.fatigue if f.domain == domain), None
            )
            existing_active = (
                existing_fatigue is not None
                and (now - existing_fatigue.window) <= FATIGUE_WINDOW
            )
            if not existing_active:
                # No record yet, or the previous window fully expired -- start a
                # fresh window rather than incrementing a stale count.
                state.fatigue = [f for f in state.fatigue if f.domain != domain]
                state.fatigue.append(FatigueRecord(domain=domain, count=1, window=now))
            else:
                # Window start stays fixed (not slid forward) until it expires --
                # a fixed 24h counting window, not a rolling average.
                state.fatigue = [
                    (
                        f
                        if f.domain != domain
                        else FatigueRecord(
                            domain=domain, count=f.count + 1, window=f.window
                        )
                    )
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
            is_new_for_user=is_new_for_user,
            prioritized_at=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="prioritization",
                    rule=f"visibility={visibility}, interruption={interruption} "
                    f"(in_cooldown={in_cooldown}, domain_fatigued={domain_fatigued}, "
                    f"is_new_for_user={is_new_for_user})",
                    timestamp=now,
                )
            ],
        )

    def attention_state(self, user_id: str) -> AttentionState | None:
        return self._states.get(user_id)

    def mark_reviewed(
        self,
        user_id: str,
        event_ids: list[UUID],
        now: datetime | None = None,
    ) -> None:
        """Records that `user_id` has reviewed each of `event_ids` -- the only
        way is_new_for_user ever clears for a given event_id (re-observing the
        same event again does not clear it; see prioritize()'s comment).
        Idempotent: an event_id already in notifications_reviewed is skipped
        rather than duplicated.
        """
        now = now or datetime.now(timezone.utc)
        state = self._state_for(user_id, now)
        already_reviewed = {r.event_id for r in state.notifications_reviewed}
        for event_id in event_ids:
            if event_id not in already_reviewed:
                state.notifications_reviewed.append(
                    NotificationReviewRecord(event_id=event_id, reviewed_at=now)
                )
                already_reviewed.add(event_id)
        state.last_updated = now
