from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import uuid4

from logan_core.contracts import ActiveContext, ActivityRecord

SESSION_TTL = timedelta(hours=1)


def _time_of_day(
    now: datetime,
) -> Literal["morning", "midday", "afternoon", "evening", "night"]:
    hour = now.hour
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "midday"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


class ActiveContextBuilder:
    """Layer 6b — describes the user's present moment. Temporary, never overwrites the
    durable User Model, expires at session end.
    """

    def build(
        self,
        user_id: str,
        current_question: Optional[str] = None,
        recent_activity: Optional[list[ActivityRecord]] = None,
        now: Optional[datetime] = None,
    ) -> ActiveContext:
        now = now or datetime.now(timezone.utc)
        return ActiveContext(
            session_id=uuid4(),
            user_id=user_id,
            current_question=current_question,
            time_of_day=_time_of_day(now),
            recent_activity=recent_activity or [],
            created_at=now,
            expires_at=now + SESSION_TTL,
        )
