from dataclasses import dataclass
from datetime import datetime, timezone

from logan_core.contracts import CommunitySignal, DecisionTraceEntry, EnrichedEvent


@dataclass
class EngagementSample:
    """One simulated point-in-time reading from an engagement data stream."""

    observed_at: datetime
    volume_at_point: int
    unique_users: int
    saves_shares: int
    questions: int


class CommunityIntelligenceEngine:
    """Layer 4b — measures aggregate community attention. Runs in parallel with Evidence
    Trust. Never substitutes for personal relevance. `lifecycle_state` is derived from the
    velocity trend within the given samples, not from a persisted history of prior
    CommunitySignal values (Community Intelligence has no persistent data ownership).
    """

    def measure(
        self, event: EnrichedEvent, samples: list[EngagementSample], now: datetime | None = None
    ) -> CommunitySignal:
        now = now or datetime.now(timezone.utc)
        if not samples:
            return CommunitySignal(
                event_id=event.event_id,
                engagement_volume=0,
                engagement_velocity=0.0,
                unique_users=0,
                saves_shares=0,
                questions=0,
                lifecycle_state="dormant",
                coordinated_risk=0.0,
                bot_risk=0.0,
                momentum_score=0.0,
                measured_at=now,
                decision_trace=[
                    DecisionTraceEntry(
                        layer="community_intelligence",
                        rule="no engagement samples provided -> dormant, all-zero signal",
                        timestamp=now,
                    )
                ],
            )

        ordered = sorted(samples, key=lambda s: s.observed_at)
        engagement_volume = sum(s.volume_at_point for s in ordered)
        unique_users = max(s.unique_users for s in ordered)
        saves_shares = sum(s.saves_shares for s in ordered)
        questions = sum(s.questions for s in ordered)

        first, last = ordered[0], ordered[-1]
        hours_elapsed = max((last.observed_at - first.observed_at).total_seconds() / 3600.0, 0.25)
        engagement_velocity = (last.volume_at_point - first.volume_at_point) / hours_elapsed

        if engagement_velocity > 5:
            lifecycle_state = "emerging"
        elif engagement_velocity > 0:
            lifecycle_state = "peak"
        elif engagement_velocity > -5:
            lifecycle_state = "fading"
        else:
            lifecycle_state = "dormant"

        # Heuristic: high volume from very few unique users looks coordinated/bot-driven.
        volume_per_user = engagement_volume / max(unique_users, 1)
        coordinated_risk = min(max((volume_per_user - 5) / 20, 0.0), 1.0)
        bot_risk = coordinated_risk

        momentum_score = min(
            (engagement_volume / 100) * 0.5
            + (saves_shares / max(engagement_volume, 1)) * 0.3
            + min(engagement_velocity / 20, 1.0) * 0.2,
            1.0,
        )
        momentum_score = max(momentum_score, 0.0)

        return CommunitySignal(
            event_id=event.event_id,
            engagement_volume=engagement_volume,
            engagement_velocity=engagement_velocity,
            unique_users=unique_users,
            saves_shares=saves_shares,
            questions=questions,
            lifecycle_state=lifecycle_state,
            coordinated_risk=coordinated_risk,
            bot_risk=bot_risk,
            momentum_score=momentum_score,
            measured_at=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="community_intelligence",
                    rule=f"lifecycle_state={lifecycle_state} from engagement_velocity={engagement_velocity:.2f}; "
                    f"momentum_score={momentum_score:.2f}",
                    timestamp=now,
                )
            ],
        )
