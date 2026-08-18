"""Real (non-demo) versioned opportunities API -- V3.1.4 BATCH-4.

A thin adapter over `logan_core`: `_run_feed_pipeline()` in `logan_feed.py` is the
single place the pipeline actually runs. This module owns nothing but the public
response shape and schema-version metadata. No scoring, ranking, or policy logic is
duplicated here -- see CLAUDE.md's layer ownership rules.

Receptors remain simulated (`logan_core/receptors/simulated.py`); "real" here means a
real logan_core pipeline run producing this response, not a real external data source.
See `docs/specs/Logan_Documentation_v3.1.4/23_CURRENT_IMPLEMENTATION_STATE.md`.
"""

from datetime import datetime

from pydantic import BaseModel

from .logan_feed import FeedItem, _run_feed_pipeline

OPPORTUNITIES_SCHEMA_VERSION = "1.0"


class OpportunitiesResponse(BaseModel):
    schema_version: str = OPPORTUNITIES_SCHEMA_VERSION
    items: list[FeedItem]
    generated_at: datetime


def run_opportunities() -> OpportunitiesResponse:
    """Builds the `/v1/opportunities` response. `FeedItem` (see `logan_feed.py`)
    already excludes `internal_rank_score` and every other internal-only field --
    this function adds nothing but `schema_version` and `generated_at` on top of the
    pipeline's own output.
    """
    items, now, _alert_event_ids = _run_feed_pipeline()
    return OpportunitiesResponse(items=items, generated_at=now)
