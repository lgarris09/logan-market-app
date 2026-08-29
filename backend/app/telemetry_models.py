"""V2.3C Telemetry -- versioned event contracts.

Guiding principle (owner's explicit instruction): telemetry records what
happened, it never decides what the behavior means. Every model here is a
raw fact shape -- no inferred_intent, no confidence score, no affinity, no
computed relevance. This is a deliberately separate concern from
`logan_core.contracts.feedback.FeedbackSignal` (the existing Learning/
Feedback pipeline's own event shape, which DOES carry an inferred
interpretation at write time via FeedbackEngine.interpret()) -- the two are
not duplicates of one concept; they serve genuinely different consumers
(FeedbackSignal feeds MemoryStore/UserModel today; TelemetryEvent is raw
history so V2.3B can recompute learning later, per the owner's own framing).

`schema_version` is a closed Literal, not a free string with a default --
an unsupported version must be rejected outright (see main.py's route),
never silently coerced.
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TELEMETRY_SCHEMA_VERSION = "1.0"

# Initial supported vocabulary (V2.3C Block B) -- a closed set, deliberately.
# Adding a new value here is a real product/schema decision, never done
# implicitly by accepting whatever a client happens to send.
TelemetryEventName = Literal[
    "opportunity_opened",
    "opportunity_returned_to",
    "watch_created",
    "watch_removed",
    "ask_started",
    "ask_follow_up",
    "usefulness_feedback_submitted",
]

# Mirrors logan_core.contracts.presentation.DeliveredItem's own surface
# vocabulary (wheel/feed_card/alert/digest/background -- no named export
# exists to import, it's an inline Literal there), plus "ask" for the one
# surface that isn't a delivered opportunity at all -- the Ask STRATUS
# screen. Optional everywhere: many events (e.g. ask_* ) don't need it.
TelemetrySourceSurface = Literal[
    "wheel", "feed_card", "alert", "digest", "background", "ask"
]

# A future point after which a client-supplied occurred_at is almost
# certainly a bug (wrong units, wrong epoch) rather than real clock skew.
_MIN_OCCURRED_AT = datetime(2020, 1, 1, tzinfo=timezone.utc)
_MAX_FUTURE_SKEW_SECONDS = 300  # 5 minutes -- generous mobile clock tolerance


class TelemetryContext(BaseModel):
    """Narrowly-typed, per-event context -- deliberately NOT a free-form
    dict. `extra="forbid"` means an unrecognized key is a validation error,
    not silently accepted -- this is what keeps the payload bounded (see the
    V2.3C ADR's "no arbitrary/unbounded payloads" requirement) as the event
    vocabulary grows, rather than becoming an escape hatch for whatever a
    client wants to attach.
    """

    model_config = ConfigDict(extra="forbid")

    # ask_started / ask_follow_up: ties the event to the same client-
    # generated Ask STRATUS session concept _ask_sessions already uses
    # (see logan_feed.py's own docstring: "session_id is client-generated
    # and not itself a secret"). Bounded length -- defense in depth, not a
    # real format constraint.
    ask_session_id: Optional[str] = Field(default=None, max_length=128)
    # opportunity_returned_to: the revision this user last had a real,
    # completed open->close disclosure of, before *this* open. Always
    # server-computed (see telemetry.py's record_event) -- a client-
    # supplied value here is never trusted, only overwritten.
    previous_opened_revision: Optional[int] = Field(default=None, ge=1)
    # usefulness_feedback_submitted: the actual feedback given. Required
    # for that event, forbidden for every other (see the cross-field
    # validator on TelemetryEventRequest below).
    useful: Optional[bool] = None


class TelemetryEventRequest(BaseModel):
    """The client-submitted shape -- deliberately has no `user_id` field at
    all. user_id is resolved server-side from the same identity headers
    every other authenticated route already uses (see main.py's
    Depends(resolve_user_id)); a client cannot supply, override, or spoof
    it because there is nowhere in this model to put one. `extra="forbid"`
    means attempting to smuggle a `user_id` (or any other field) into the
    body is a hard validation error, not a silently-dropped no-op -- an
    auditable rejection, not an ignorable one.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    schema_version: Literal["1.0"]
    event_name: TelemetryEventName
    occurred_at: datetime
    opportunity_id: Optional[UUID] = None
    opportunity_revision: Optional[int] = Field(default=None, ge=1)
    source_surface: Optional[TelemetrySourceSurface] = None
    context: Optional[TelemetryContext] = None

    @field_validator("occurred_at")
    @classmethod
    def _occurred_at_is_plausible(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if value < _MIN_OCCURRED_AT:
            raise ValueError("occurred_at is implausibly old")
        now = datetime.now(timezone.utc)
        if (value - now).total_seconds() > _MAX_FUTURE_SKEW_SECONDS:
            raise ValueError("occurred_at is too far in the future")
        return value

    @model_validator(mode="after")
    def _context_matches_event_name(self) -> "TelemetryEventRequest":
        ctx = self.context
        if self.event_name == "usefulness_feedback_submitted":
            if ctx is None or ctx.useful is None:
                raise ValueError(
                    "usefulness_feedback_submitted requires context.useful"
                )
        elif ctx is not None and ctx.useful is not None:
            raise ValueError(
                "context.useful is only valid for usefulness_feedback_submitted"
            )

        if self.event_name in ("ask_started", "ask_follow_up"):
            if ctx is None or not ctx.ask_session_id:
                raise ValueError(f"{self.event_name} requires context.ask_session_id")
        elif ctx is not None and ctx.ask_session_id is not None:
            raise ValueError(
                "context.ask_session_id is only valid for ask_started/ask_follow_up"
            )

        opportunity_scoped = (
            "opportunity_opened",
            "opportunity_returned_to",
            "watch_created",
            "watch_removed",
        )
        if self.event_name in opportunity_scoped and self.opportunity_id is None:
            raise ValueError(f"{self.event_name} requires opportunity_id")

        return self


class TelemetryEventBatchRequest(BaseModel):
    """Bounded batch form (V2.3C Block D) -- so mobile doesn't need one HTTP
    round-trip per event, without becoming a general ingestion pipeline.
    Each event is validated/persisted independently; one bad event in a
    batch never discards the rest (see telemetry.py's record_batch)."""

    events: list[TelemetryEventRequest] = Field(min_length=1, max_length=25)


class TelemetryEvent(BaseModel):
    """The durable, authoritative record -- what actually gets persisted and
    returned by every read/diagnostic function. `user_id` is always the
    server-resolved identity, never the client's. `event_name` may differ
    from what the client submitted (see telemetry.py: an `opportunity_opened`
    is promoted to `opportunity_returned_to` server-side when this user's
    own durable view history shows a genuine prior open of this entity --
    the client never has to compute that itself)."""

    schema_version: str = TELEMETRY_SCHEMA_VERSION
    event_id: UUID
    event_name: TelemetryEventName
    occurred_at: datetime
    recorded_at: datetime
    user_id: str
    opportunity_id: Optional[UUID] = None
    opportunity_revision: Optional[int] = None
    source_surface: Optional[TelemetrySourceSurface] = None
    context: Optional[TelemetryContext] = None


class TelemetryEventResponse(BaseModel):
    schema_version: str = TELEMETRY_SCHEMA_VERSION
    accepted: bool = True
    event_id: UUID


class TelemetryBatchRejection(BaseModel):
    event_id: Optional[UUID]
    reason: str


class TelemetryEventBatchResponse(BaseModel):
    schema_version: str = TELEMETRY_SCHEMA_VERSION
    accepted_count: int
    rejected: list[TelemetryBatchRejection] = Field(default_factory=list)
