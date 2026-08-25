"""Stock Opportunity Logic V2 -- Opportunity Lifecycle tracking.

See docs/DECISIONS.md's Sprint 3.6.9 Stock Opportunity Logic V2 ADR for the
full audit/design record. This is the missing piece the audit found: every
existing layer (World Model through Presentation) recomputes its output
fresh from the current poll alone -- nothing anywhere persisted a *prior*
snapshot to diff against, which is why the same opportunity could look
identical day after day with no sense of whether it was still strengthening,
unchanged, cooling, or no longer worth attention.

Mirrors StockConvergenceTracker's own established pattern exactly: a
persistent, process-lifetime, opt-in PipelineDependency (Optional[...] =
None, wired only when a caller explicitly opts in -- see
orchestrator/pipeline.py), entity-keyed for objective/shared world facts.
Not a change to WorldModel's own `(entity_id, signal_type)` dedup/event
identity semantics at all -- this is a separate, additional layer that
watches the same confidence/trigger outputs the existing pipeline already
produces and tracks how they evolve over repeated polls, exactly the way
StockConvergenceTracker watches TriggerEvents without touching WorldModel's
dedup.
"""

from datetime import datetime
from typing import Optional

from logan_core.contracts import (
    EvidenceSnapshot,
    LifecycleDelta,
    LifecycleSnapshot,
    LifecycleState,
    MarketEvidenceInput,
    MeaningfulChangeType,
    TrajectoryState,
)

# Signal-specific natural relevance windows (hours) -- reasoned per signal
# semantics, per the owner's explicit instruction not to use one arbitrary
# blanket timeout. Each trigger_code's story has a genuinely different
# natural shelf life: an earnings report's reaction plays out over days: a
# price breakout's relevance is measured in hours; an analyst action sits
# in between; convergence (already the strongest, multi-signal-confirmed
# case) gets a longer window than any single signal alone. Declared,
# reasoned constants -- not learned/computed -- matching this codebase's
# existing threshold-setting discipline (FATIGUE_LIMIT, COOLDOWN_WINDOW,
# CONVERGENCE_WINDOW, etc.).
_MONITORING_WINDOW_HOURS: dict[str, float] = {
    "STOCK_EARNINGS_BEAT": 72.0,
    "STOCK_EARNINGS_MISS": 72.0,
    "STOCK_EARNINGS_IN_LINE": 48.0,
    "STOCK_PRICE_MOVE_SIGNIFICANT": 6.0,
    "STOCK_ANALYST_UPGRADE": 48.0,
    "STOCK_ANALYST_DOWNGRADE": 48.0,
    "STOCK_CONVERGENCE_MULTI_SOURCE": 24.0,
}
_STALE_WINDOW_HOURS: dict[str, float] = {
    "STOCK_EARNINGS_BEAT": 240.0,
    "STOCK_EARNINGS_MISS": 240.0,
    "STOCK_EARNINGS_IN_LINE": 168.0,
    "STOCK_PRICE_MOVE_SIGNIFICANT": 24.0,
    "STOCK_ANALYST_UPGRADE": 168.0,
    "STOCK_ANALYST_DOWNGRADE": 168.0,
    "STOCK_CONVERGENCE_MULTI_SOURCE": 72.0,
}
_EXPIRE_WINDOW_HOURS: dict[str, float] = {
    "STOCK_EARNINGS_BEAT": 720.0,
    "STOCK_EARNINGS_MISS": 720.0,
    "STOCK_EARNINGS_IN_LINE": 360.0,
    "STOCK_PRICE_MOVE_SIGNIFICANT": 72.0,
    "STOCK_ANALYST_UPGRADE": 360.0,
    "STOCK_ANALYST_DOWNGRADE": 360.0,
    "STOCK_CONVERGENCE_MULTI_SOURCE": 168.0,
}
_DEFAULT_MONITORING_WINDOW_HOURS = 24.0
_DEFAULT_STALE_WINDOW_HOURS = 96.0
_DEFAULT_EXPIRE_WINDOW_HOURS = 240.0

# Confidence-delta thresholds. CONFIDENCE_DELTA_THRESHOLD gates "meaningful
# enough to update the card"; MAJOR_CONFIDENCE_DELTA_THRESHOLD is the
# stricter bar for "a confidence *decrease* worth interrupting the user for"
# (a real weakening/invalidation, not routine noise) -- confidence
# *increases* use the base threshold for notification-worthiness too (an
# emerging opportunity strengthening is exactly what Watch exists to catch),
# but a modest decrease alone should update the card without alerting.
CONFIDENCE_DELTA_THRESHOLD = 0.05
MAJOR_CONFIDENCE_DELTA_THRESHOLD = 0.15

# Reuses PrioritizationEngine's own visibility="primary" bar (0.6,
# prioritization/engine.py) as the HIGH_ATTENTION confidence floor, and
# opportunity/engine.py's own explicit-connection bump (0.6) as the personal-
# relevance threshold -- existing anchors, not new numbers.
HIGH_ATTENTION_CONFIDENCE_THRESHOLD = 0.6
PERSONAL_RELEVANCE_THRESHOLD = 0.6
PERSONAL_RELEVANCE_DELTA_THRESHOLD = 0.1

_CONVERGENCE_TRIGGER_CODE = "STOCK_CONVERGENCE_MULTI_SOURCE"

# Notification-worthy is a strict subset of meaningful -- aging alone
# (cooling/stale/expired purely from time passing with no new evidence) is
# never in this set, matching the explicit "do not equate opportunity
# exists with send notification" product rule. "confidence_decreased" is
# deliberately absent here -- see _is_major_decrease below, which promotes
# it into notification-worthy only past MAJOR_CONFIDENCE_DELTA_THRESHOLD.
_NOTIFICATION_WORTHY_CHANGE_TYPES = {
    "new_opportunity",
    "confidence_increased",
    "new_signal_appeared",
    "convergence_formed",
    "reactivated",
    "personal_relevance_increased",
    # Stock Opportunity Logic V2.2: a trajectory turning against the thesis,
    # or a genuinely strengthening/reaccelerating one, is exactly the kind of
    # real evidence-backed transition Watch exists to catch -- matching the
    # existing confidence_increased precedent. "trajectory_weakening" is
    # deliberately absent, mirroring confidence_decreased's own asymmetry: a
    # modest weakening updates the card without interrupting the user.
    "trajectory_strengthening",
    "trajectory_reaccelerated",
    "trajectory_reversing",
}


def _window_hours(
    trigger_codes: list[str], table: dict[str, float], default: float
) -> float:
    """The most generous (longest) window among this opportunity's currently
    active trigger codes -- if a slower-decaying signal (e.g. an earnings
    beat) is still part of the story, its longer natural relevance window
    governs even when a faster-decaying one (e.g. a price move) is also
    attached.
    """
    windows = [table.get(code, default) for code in trigger_codes]
    return max(windows) if windows else default


# --- Stock Opportunity Logic V2.2 -- Evidence + Trajectory Enrichment ------
#
# Deliberately explicit, declared thresholds -- not a learned/opaque score --
# matching this file's own existing discipline (CONFIDENCE_DELTA_THRESHOLD
# etc.). All units are percentage points of *thesis-aligned, market-relative*
# performance (see _signed_relative_strength) unless noted otherwise.

# The delta (poll-over-poll) in thesis-aligned relative strength required to
# call the trajectory STRENGTHENING or WEAKENING at all.
TRAJECTORY_STRENGTHEN_DELTA = 1.0
# A further, materially larger jump while *already* STRENGTHENING -- "a
# strong thesis reaccelerates while remaining in the same trajectory
# category" from the product spec. Deliberately a distinct, larger bar than
# the base delta so ordinary quote noise while strengthening doesn't spam a
# fresh meaningful revision every poll.
TRAJECTORY_REACCELERATION_DELTA = 2.5
# REVERSING requires the *sign* of thesis-aligned relative strength to flip
# from genuinely confirming to genuinely contradicting -- both sides of the
# flip must clear this small deadband, so a move hovering near zero (neither
# clearly confirming nor contradicting) never registers as a "reversal."
TRAJECTORY_REVERSAL_CONFIRM_THRESHOLD = 0.5
# Volume confirmation: participation this poll vs. the entity's own average
# volume baseline (see MarketEvidenceInput.average_volume). 1.5x is a
# conservative, explicit "unusually high" bar -- not derived from any
# statistical distribution, matching this file's declared-constant style.
HIGH_VOLUME_RATIO = 1.5


def _thesis_direction(trigger_directions: list[str]) -> str:
    """Aggregate directional bias of this poll's active TriggerEvents
    (TriggerEvent.direction is already a real, implemented field -- see
    contracts/trigger.py -- reused here rather than inventing a second
    directionality concept). "positive" (e.g. an earnings beat, an analyst
    upgrade) means the thesis expects the price to outperform; "negative"
    (a miss, a downgrade) means it expects underperformance. Any mix of both
    (or neither/empty) is "mixed" -- trajectory takes no directional stance
    on genuinely ambiguous or absent evidence rather than guessing.
    """
    has_positive = "positive" in trigger_directions
    has_negative = "negative" in trigger_directions
    if has_positive and not has_negative:
        return "positive"
    if has_negative and not has_positive:
        return "negative"
    return "mixed"


def _signed_relative_strength(
    relative_to_market_pct: Optional[float], thesis_direction: str
) -> Optional[float]:
    """Thesis-aligned relative-to-market performance: positive always means
    "confirming this opportunity's own directional thesis," negative always
    means "contradicting it," regardless of whether the thesis itself is
    bullish or bearish -- this is the single number trajectory compares
    poll-to-poll. None when there's no usable market-relative figure, or the
    active triggers give no clear directional stance to align against.
    """
    if relative_to_market_pct is None or thesis_direction == "mixed":
        return None
    return (
        relative_to_market_pct
        if thesis_direction == "positive"
        else -relative_to_market_pct
    )


def _build_evidence(
    entity_id: str,
    evidence_input: MarketEvidenceInput,
    trigger_price: float,
    price_at_last_revision: Optional[float],
    now: datetime,
) -> EvidenceSnapshot:
    """Pure arithmetic over already-fetched, already-verified provider data
    (see backend/app/logan_feed.py for how MarketEvidenceInput is populated)
    -- makes zero provider calls itself. Every ratio is None when an input it
    needs is missing, never a fabricated/estimated value.
    """
    price = evidence_input.price
    assert price is not None  # guaranteed by the caller's own guard
    price_change_since_trigger_pct = (
        (price - trigger_price) / trigger_price * 100.0 if trigger_price else None
    )
    price_change_since_last_revision_pct = (
        (price - price_at_last_revision) / price_at_last_revision * 100.0
        if price_at_last_revision
        else None
    )
    relative_to_market_pct = (
        evidence_input.change_pct - evidence_input.market_change_pct
        if evidence_input.change_pct is not None
        and evidence_input.market_change_pct is not None
        else None
    )
    relative_to_sector_pct = (
        evidence_input.change_pct - evidence_input.sector_change_pct
        if evidence_input.change_pct is not None
        and evidence_input.sector_change_pct is not None
        else None
    )
    volume_ratio = (
        evidence_input.volume / evidence_input.average_volume
        if evidence_input.volume is not None and evidence_input.average_volume
        else None
    )
    beta_normalized_move_pct = (
        evidence_input.change_pct / evidence_input.beta
        if evidence_input.change_pct is not None and evidence_input.beta
        else None
    )
    return EvidenceSnapshot(
        entity_id=entity_id,
        price=price,
        trigger_price=trigger_price,
        price_change_since_trigger_pct=price_change_since_trigger_pct,
        price_change_since_last_revision_pct=price_change_since_last_revision_pct,
        market_change_pct=evidence_input.market_change_pct,
        relative_to_market_pct=relative_to_market_pct,
        sector=evidence_input.sector,
        sector_change_pct=evidence_input.sector_change_pct,
        relative_to_sector_pct=relative_to_sector_pct,
        volume=evidence_input.volume,
        average_volume=evidence_input.average_volume,
        volume_ratio=volume_ratio,
        beta=evidence_input.beta,
        beta_normalized_move_pct=beta_normalized_move_pct,
        evaluated_at=now,
    )


def _compute_trajectory(
    prior_trajectory: TrajectoryState,
    prior_relative_strength: Optional[float],
    relative_strength: Optional[float],
    prior_volume_ratio: Optional[float],
    volume_ratio: Optional[float],
) -> tuple[TrajectoryState, str, bool, Optional[MeaningfulChangeType]]:
    """The trajectory state machine: STRENGTHENING/STEADY/WEAKENING/REVERSING,
    a reason sentence, whether this poll's trajectory is itself meaningful
    enough to surface as a change_type, and (when so) which one. Explicit
    deterministic predicates, not a composite/opaque score -- each branch is
    independently readable and testable. Never reads user_id/
    personal_relevance -- purely a function of two polls' worth of objective
    market evidence.
    """
    if relative_strength is None:
        # No usable directional evidence this poll (mixed/absent trigger
        # direction, or a missing market-relative figure) -- hold the prior
        # trajectory rather than guessing; not itself a meaningful event.
        return (
            prior_trajectory,
            "No directional market evidence available this poll.",
            False,
            None,
        )

    if prior_relative_strength is None:
        return (
            "STEADY",
            "First evidence-bearing poll for this opportunity -- no prior "
            "trajectory to compare against yet.",
            False,
            None,
        )

    delta = relative_strength - prior_relative_strength

    if (
        prior_relative_strength > TRAJECTORY_REVERSAL_CONFIRM_THRESHOLD
        and relative_strength < -TRAJECTORY_REVERSAL_CONFIRM_THRESHOLD
    ):
        return (
            "REVERSING",
            (
                f"Evidence has flipped against the thesis: relative "
                f"performance moved from +{prior_relative_strength:.1f}pp to "
                f"{relative_strength:.1f}pp."
            ),
            True,
            "trajectory_reversing",
        )

    if delta >= TRAJECTORY_STRENGTHEN_DELTA:
        if (
            prior_trajectory == "STRENGTHENING"
            and delta >= TRAJECTORY_REACCELERATION_DELTA
        ):
            return (
                "STRENGTHENING",
                f"Thesis reaccelerated: relative performance improved by "
                f"{delta:.1f}pp, well beyond ordinary continued strengthening.",
                True,
                "trajectory_reaccelerated",
            )
        first_time = prior_trajectory != "STRENGTHENING"
        return (
            "STRENGTHENING",
            f"Relative performance improved by {delta:.1f}pp -- evidence is "
            "strengthening the thesis.",
            first_time,
            "trajectory_strengthening" if first_time else None,
        )

    if delta <= -TRAJECTORY_STRENGTHEN_DELTA:
        first_time = prior_trajectory != "WEAKENING"
        return (
            "WEAKENING",
            f"Relative performance declined by {abs(delta):.1f}pp -- evidence "
            "is weakening.",
            first_time,
            "trajectory_weakening" if first_time else None,
        )

    # Volume confirmation: a real, separate predicate -- "significant volume
    # confirmation appears" -- that can promote an otherwise-steady thesis
    # into strengthening even without a big relative-strength move yet, but
    # only while the price action is still net-confirming (never on its own
    # against contradicting evidence).
    if (
        volume_ratio is not None
        and prior_volume_ratio is not None
        and volume_ratio >= HIGH_VOLUME_RATIO > prior_volume_ratio
        and relative_strength > 0
    ):
        return (
            "STRENGTHENING",
            f"Volume confirmation: participation jumped to {volume_ratio:.1f}x "
            "average while price action continues to confirm the thesis.",
            True,
            "trajectory_strengthening",
        )

    return (
        prior_trajectory,
        "No material change in evidence trajectory this poll.",
        False,
        None,
    )


class OpportunityLifecycleTracker:
    """Persistent, process-lifetime, per-`entity_id` (shared across users)
    lifecycle state, plus a lightweight per-`(user_id, entity_id)` personal-
    relevance index. A single instance must be reused across polls -- like
    StockConvergenceTracker and WorldModel itself -- for its history to mean
    anything; see PipelineDependencies' `lifecycle_tracker` field and
    backend/app/logan_feed.py's process-lifetime Orchestrator.
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, LifecycleSnapshot] = {}
        self._personal_relevance: dict[tuple[str, str], float] = {}

    def load_snapshot(self, snapshot: LifecycleSnapshot) -> None:
        """Restores one entity's snapshot -- used by the durable persistence
        wrapper (backend/app/lifecycle_store.py) to rehydrate state after a
        restart, before any observe() call this process's lifetime.
        """
        self._snapshots[snapshot.entity_id] = snapshot

    def export_snapshot(self, entity_id: str) -> Optional[LifecycleSnapshot]:
        return self._snapshots.get(entity_id)

    def all_snapshots(self) -> list[LifecycleSnapshot]:
        return list(self._snapshots.values())

    def observe(
        self,
        entity_id: str,
        confidence_score: float,
        trigger_codes: list[str],
        user_id: str,
        personal_relevance: float,
        now: datetime,
        market_evidence: Optional[MarketEvidenceInput] = None,
        trigger_directions: Optional[list[str]] = None,
    ) -> LifecycleDelta:
        """The core comparison: current authoritative facts (confidence,
        active trigger_codes, this user's personal_relevance) against the
        last stored snapshot for this entity, producing a structured
        LifecycleDelta. Deterministic and stateless *given* the stored
        snapshot -- every threshold/window used here is a declared constant
        above, never learned or LLM-influenced (the LLM layer, see
        backend/app/lifecycle_narrative.py, only ever narrates a delta this
        method already computed -- it cannot produce one itself).

        `market_evidence`/`trigger_directions` (Stock Opportunity Logic V2.2,
        both Optional, default None) are the only new inputs -- every
        pre-V2.2 caller/test that never passes them gets byte-for-byte
        unchanged lifecycle_state/confidence/revision behavior, with
        trajectory staying at its inert "STEADY" default. Never mixed with
        `user_id`/`personal_relevance` in the evidence/trajectory
        computation below -- trajectory is purely objective, entity-keyed,
        identical for every user, per the explicit "keep global vs personal
        state separate" requirement carried forward from V2.1.
        """
        prior = self._snapshots.get(entity_id)
        personal_key = (user_id, entity_id)
        prior_personal_relevance = self._personal_relevance.get(personal_key)
        self._personal_relevance[personal_key] = personal_relevance

        if prior is None:
            trigger_price: Optional[float] = None
            evidence: Optional[EvidenceSnapshot] = None
            trajectory: TrajectoryState = "STEADY"
            if market_evidence is not None and market_evidence.price is not None:
                trigger_price = market_evidence.price
                evidence = _build_evidence(
                    entity_id, market_evidence, trigger_price, trigger_price, now
                )
            relative_strength = (
                _signed_relative_strength(
                    evidence.relative_to_market_pct,
                    _thesis_direction(trigger_directions or []),
                )
                if evidence is not None
                else None
            )
            self._snapshots[entity_id] = LifecycleSnapshot(
                entity_id=entity_id,
                lifecycle_state="new",
                confidence_score=confidence_score,
                trigger_codes=list(trigger_codes),
                first_seen_at=now,
                last_meaningful_change_at=now,
                last_notification_worthy_at=now,
                last_evaluated_at=now,
                revision=1,
                trigger_price=trigger_price,
                price_at_last_revision=trigger_price,
                last_relative_strength=relative_strength,
                last_volume_ratio=evidence.volume_ratio if evidence else None,
                trajectory=trajectory,
            )
            return LifecycleDelta(
                entity_id=entity_id,
                change_type="new_opportunity",
                is_meaningful=True,
                is_notification_worthy=True,
                previous_state="new",
                new_state="new",
                previous_confidence=confidence_score,
                new_confidence=confidence_score,
                new_trigger_codes=list(trigger_codes),
                added_trigger_codes=list(trigger_codes),
                personal_relevance_changed=False,
                reason="First time STRATUS has observed this opportunity.",
                evaluated_at=now,
                last_meaningful_change_at=now,
                thesis_age_hours=0.0,
                previous_revision=1,
                new_revision=1,
                trajectory=trajectory,
                previous_trajectory=trajectory,
                trajectory_reason=None,
                evidence=evidence,
            )

        confidence_delta = confidence_score - prior.confidence_score
        confidence_meaningful = abs(confidence_delta) >= CONFIDENCE_DELTA_THRESHOLD
        added_codes = [c for c in trigger_codes if c not in prior.trigger_codes]
        new_signal_meaningful = bool(added_codes)
        world_meaningful = confidence_meaningful or new_signal_meaningful

        personal_meaningful = False
        if prior_personal_relevance is not None:
            personal_delta = personal_relevance - prior_personal_relevance
            crossed_threshold = (
                prior_personal_relevance
                < PERSONAL_RELEVANCE_THRESHOLD
                <= personal_relevance
            ) or (
                personal_relevance
                < PERSONAL_RELEVANCE_THRESHOLD
                <= prior_personal_relevance
            )
            personal_meaningful = (
                abs(personal_delta) >= PERSONAL_RELEVANCE_DELTA_THRESHOLD
                or crossed_threshold
            )

        thesis_age_hours = (now - prior.first_seen_at).total_seconds() / 3600.0
        since_change_hours = (
            now - prior.last_meaningful_change_at
        ).total_seconds() / 3600.0

        monitoring_window = _window_hours(
            trigger_codes, _MONITORING_WINDOW_HOURS, _DEFAULT_MONITORING_WINDOW_HOURS
        )
        stale_window = _window_hours(
            trigger_codes, _STALE_WINDOW_HOURS, _DEFAULT_STALE_WINDOW_HOURS
        )
        expire_window = _window_hours(
            trigger_codes, _EXPIRE_WINDOW_HOURS, _DEFAULT_EXPIRE_WINDOW_HOURS
        )

        # Stock Opportunity Logic V2.2 (Evidence + Trajectory Enrichment):
        # objective evidence/trajectory computation, entirely independent of
        # user_id/personal_relevance. `effective_trigger_price` carries prior
        # trigger_price forward untouched when this poll has no market
        # evidence (or sets it for the first time, exactly once, the first
        # poll evidence ever arrives -- possibly later than this
        # opportunity's own first_seen_at, if evidence wasn't available yet).
        evidence = None
        trajectory = prior.trajectory
        previous_trajectory = prior.trajectory
        trajectory_reason = None
        trajectory_meaningful = False
        trajectory_change_type: Optional[MeaningfulChangeType] = None
        relative_strength = None
        effective_trigger_price = prior.trigger_price

        if market_evidence is not None and market_evidence.price is not None:
            if effective_trigger_price is None:
                effective_trigger_price = market_evidence.price
            evidence = _build_evidence(
                entity_id,
                market_evidence,
                effective_trigger_price,
                prior.price_at_last_revision,
                now,
            )
            relative_strength = _signed_relative_strength(
                evidence.relative_to_market_pct,
                _thesis_direction(trigger_directions or []),
            )
            (
                trajectory,
                trajectory_reason,
                trajectory_meaningful,
                trajectory_change_type,
            ) = _compute_trajectory(
                prior_trajectory=prior.trajectory,
                prior_relative_strength=prior.last_relative_strength,
                relative_strength=relative_strength,
                prior_volume_ratio=prior.last_volume_ratio,
                volume_ratio=evidence.volume_ratio,
            )

        is_meaningful = world_meaningful or personal_meaningful or trajectory_meaningful
        reactivated = prior.lifecycle_state in ("cooling", "stale") and world_meaningful

        new_state: LifecycleState
        change_type: MeaningfulChangeType
        reason: str

        if reactivated:
            new_state = (
                "high_attention"
                if confidence_score >= HIGH_ATTENTION_CONFIDENCE_THRESHOLD
                else "developing"
            )
            change_type = "reactivated"
            reason = (
                "New evidence appeared after a period with no material change -- "
                "STRATUS is paying attention to this again."
            )
        elif world_meaningful:
            new_state = (
                "high_attention"
                if (
                    confidence_score >= HIGH_ATTENTION_CONFIDENCE_THRESHOLD
                    or _CONVERGENCE_TRIGGER_CODE in trigger_codes
                )
                else "developing"
            )
            if new_signal_meaningful and _CONVERGENCE_TRIGGER_CODE in added_codes:
                change_type = "convergence_formed"
                reason = (
                    "Multiple independent signals have now converged on this "
                    "opportunity."
                )
            elif new_signal_meaningful:
                change_type = "new_signal_appeared"
                reason = f"New evidence appeared: {', '.join(added_codes)}."
            elif confidence_delta > 0:
                change_type = "confidence_increased"
                reason = (
                    f"Confidence strengthened from {prior.confidence_score:.2f} "
                    f"to {confidence_score:.2f}."
                )
            else:
                change_type = "confidence_decreased"
                reason = (
                    f"Confidence weakened from {prior.confidence_score:.2f} to "
                    f"{confidence_score:.2f}."
                )
        elif since_change_hours >= expire_window:
            new_state = "expired"
            first_time = prior.lifecycle_state != "expired"
            change_type = "aged_to_expired" if first_time else "none"
            is_meaningful = is_meaningful or first_time
            reason = (
                "No new evidence for an extended period -- no longer worth the "
                "user's attention."
            )
        elif since_change_hours >= stale_window:
            new_state = "stale"
            first_time = prior.lifecycle_state != "stale"
            change_type = "aged_to_stale" if first_time else "none"
            is_meaningful = is_meaningful or first_time
            reason = (
                "The original thesis remains valid, but no new evidence has "
                "appeared in a long time."
            )
        elif since_change_hours >= monitoring_window:
            new_state = "cooling"
            first_time = prior.lifecycle_state != "cooling"
            change_type = "aged_to_cooling" if first_time else "none"
            is_meaningful = is_meaningful or first_time
            reason = (
                "No new evidence since the original signal -- STRATUS is still "
                "monitoring, but this is cooling."
            )
        elif personal_meaningful:
            new_state = (
                "monitoring"
                if prior.lifecycle_state == "new"
                else prior.lifecycle_state
            )
            change_type = (
                "personal_relevance_increased"
                if personal_relevance > (prior_personal_relevance or 0.0)
                else "personal_relevance_decreased"
            )
            reason = "This opportunity's relevance to you has changed."
        else:
            new_state = (
                "monitoring"
                if prior.lifecycle_state in ("new", "developing", "high_attention")
                else prior.lifecycle_state
            )
            # Stock Opportunity Logic V2.2: a trajectory-only change is the
            # lowest-priority meaningful reason -- every higher-priority
            # branch above (world-fact, aging, personal) already claimed
            # change_type/reason if it fired this poll. Deliberately does
            # NOT alter `new_state`/lifecycle_state at all -- trajectory and
            # lifecycle remain orthogonal dimensions, per the explicit
            # product requirement.
            if trajectory_meaningful and trajectory_change_type is not None:
                change_type = trajectory_change_type
                reason = trajectory_reason or "The evidence trajectory has changed."
            else:
                change_type = "none"
                reason = "No material change -- STRATUS is still monitoring."

        is_notification_worthy = (
            is_meaningful and change_type in _NOTIFICATION_WORTHY_CHANGE_TYPES
        ) or (
            # A confidence *decrease* only notifies past the stricter "major
            # invalidation" bar -- a modest weakening updates the card
            # (is_meaningful=True above) without interrupting the user.
            change_type == "confidence_decreased"
            and abs(confidence_delta) >= MAJOR_CONFIDENCE_DELTA_THRESHOLD
        )

        last_meaningful_change_at = (
            now if is_meaningful else prior.last_meaningful_change_at
        )

        # Stock Opportunity Logic V2.1 (User Sync Gap): the revision counter
        # is the *global*, objective/shared meaningful-change history --
        # deliberately narrower than the card-update `is_meaningful` flag
        # above, which also (correctly, for V2's own scope) folds in this
        # call's personal_relevance signal. A revision must never advance
        # from one user's personal relevance crossing alone: two users must
        # see the identical global revision number for the same real-world
        # opportunity, and personalization must only change how much a given
        # revision matters to them, never manufacture a new one (see the
        # V2.1 ADR's explicit "keep global vs personal state separate"
        # requirement). `change_type` is only ever "personal_relevance_*"
        # when this poll's meaningful flag was driven purely by personal
        # relevance (the elif chain above only reaches that branch when
        # world_meaningful and every aging threshold are both false) -- every
        # other meaningful change_type (new_signal_appeared,
        # confidence_increased/decreased, convergence_formed, reactivated,
        # aged_to_cooling/stale/expired) is a real, objective world-fact
        # change and does advance the counter.
        is_global_meaningful = is_meaningful and change_type not in (
            "personal_relevance_increased",
            "personal_relevance_decreased",
        )
        new_revision = prior.revision + 1 if is_global_meaningful else prior.revision

        # Stock Opportunity Logic V2.2: "price at last meaningful snapshot"
        # advances only on a genuine global revision boundary, matching the
        # literal product question ("how far has price moved since the last
        # meaningful snapshot") -- not every poll, and not on a
        # personal-relevance-only change either (is_global_meaningful already
        # excludes that case, same as the revision counter itself).
        price_at_last_revision = (
            market_evidence.price
            if (
                market_evidence is not None
                and market_evidence.price is not None
                and is_global_meaningful
            )
            else prior.price_at_last_revision
        )
        # last_relative_strength/last_volume_ratio only advance on a poll
        # that actually had usable evidence -- a poll with none (provider
        # failure, demo mode) must never erase previously-established
        # trajectory history.
        last_relative_strength = (
            relative_strength if evidence is not None else prior.last_relative_strength
        )
        last_volume_ratio = (
            evidence.volume_ratio if evidence is not None else prior.last_volume_ratio
        )

        self._snapshots[entity_id] = LifecycleSnapshot(
            entity_id=entity_id,
            lifecycle_state=new_state,
            confidence_score=confidence_score,
            trigger_codes=list(trigger_codes),
            first_seen_at=prior.first_seen_at,
            last_meaningful_change_at=last_meaningful_change_at,
            last_notification_worthy_at=(
                now if is_notification_worthy else prior.last_notification_worthy_at
            ),
            last_evaluated_at=now,
            revision=new_revision,
            trigger_price=effective_trigger_price,
            price_at_last_revision=price_at_last_revision,
            last_relative_strength=last_relative_strength,
            last_volume_ratio=last_volume_ratio,
            trajectory=trajectory,
        )

        return LifecycleDelta(
            entity_id=entity_id,
            change_type=change_type,
            is_meaningful=is_meaningful,
            is_notification_worthy=is_notification_worthy,
            previous_state=prior.lifecycle_state,
            new_state=new_state,
            previous_confidence=prior.confidence_score,
            new_confidence=confidence_score,
            new_trigger_codes=list(trigger_codes),
            added_trigger_codes=added_codes,
            personal_relevance_changed=personal_meaningful,
            reason=reason,
            evaluated_at=now,
            last_meaningful_change_at=last_meaningful_change_at,
            thesis_age_hours=thesis_age_hours,
            previous_revision=prior.revision,
            new_revision=new_revision,
            trajectory=trajectory,
            previous_trajectory=previous_trajectory,
            trajectory_reason=trajectory_reason,
            evidence=evidence,
        )
