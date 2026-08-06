import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

# Same local-dev sys.path bridge as logan_demo.py -- see ADR-022. Repeated here
# (rather than imported) so this module doesn't depend on logan_demo's import
# order having already run it.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.community_intelligence import EngagementSample  # noqa: E402
from logan_core.contracts import DeliveredItem, Holding, Interest  # noqa: E402
from logan_core.orchestrator import Orchestrator  # noqa: E402
from logan_core.receptors import (  # noqa: E402
    simulated_fixtures,
    tesla_ai_partnership_corroboration,
)
from logan_core.user_model import UserModelBuilder  # noqa: E402

from .entity_registry import resolve  # noqa: E402

# Per-entity simulated engagement, tuned for visual variety in the demo field --
# not meant to represent real-world volumes. Entities not listed fall back to a
# modest default.
_ENGAGEMENT_BY_ENTITY: dict[str, list[tuple[int, int, int, int]]] = {
    # (volume_at_point, unique_users, saves_shares, questions)
    "TSLA": [(10, 8, 1, 0), (40, 30, 6, 3)],
    "NVDA": [(15, 12, 2, 1), (35, 26, 5, 2)],
    "AAPL": [(6, 5, 1, 0), (12, 9, 2, 0)],
    "MARKETS": [(4, 4, 0, 0), (7, 5, 1, 0)],
    "OIL": [(3, 3, 0, 0), (5, 4, 0, 0)],
    "BTC": [(20, 15, 3, 1), (48, 34, 8, 3)],
    "FED": [(8, 6, 1, 0), (22, 16, 3, 1)],
    "NFL": [(5, 4, 0, 0), (9, 7, 1, 0)],
    "MUSIC": [(30, 20, 4, 2), (55, 38, 9, 4)],
    "POLY": [(3, 3, 0, 0), (4, 3, 0, 0)],
    "AI_SECTOR": [(30, 20, 4, 2), (55, 38, 9, 4)],
}


class FeedItem(BaseModel):
    event_id: UUID
    entity_id: str
    display_name: str
    category: str
    ticker: str | None
    domain: str
    delivered_item: DeliveredItem
    # 1-indexed position in this response's already-sorted order (1 = most
    # important). Deliberately an ordinal, not a raw score: logan_core's
    # internal_rank_score is internal-only and must never be returned via any
    # public API response (ADR-029) -- this field is the correct public-facing
    # substitute for "where does this belong in the field/list."
    rank: int
    confidence_score: float
    confidence_label: str
    connected_event_ids: list[UUID]


class DemoFeedResponse(BaseModel):
    items: list[FeedItem]
    generated_at: datetime


def _engagement_samples(entity_id: str, now: datetime) -> list[EngagementSample]:
    points = _ENGAGEMENT_BY_ENTITY.get(entity_id, [(5, 4, 0, 0), (8, 6, 1, 0)])
    return [
        EngagementSample(
            observed_at=now,
            volume_at_point=v,
            unique_users=u,
            saves_shares=s,
            questions=q,
        )
        for v, u, s, q in points
    ]


def run_demo_feed() -> DemoFeedResponse:
    """Runs the simulated entity fixtures (Tesla, NVIDIA, Apple, Bitcoin, Federal
    Reserve, NFL, Music, Polymarket, Markets, Oil, AI) through one shared Orchestrator
    instance and returns a feed for the Opportunity Field. Sharing one Orchestrator
    (and therefore one World Model, Memory Store, and Prioritization state) across all
    events lets genuinely overlapping entities (e.g. Tesla's downstream ripple
    touching NVIDIA and the AI sector, which have their own direct fixtures too)
    connect to each other, the same way related opportunities would in a real
    session -- not independent runs stitched together after the fact.
    """
    now = datetime.now(timezone.utc)

    user_model = UserModelBuilder().seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=now
            )
        ],
        interests=[
            Interest(
                domain="social",
                topic="AI_SECTOR",
                weight=0.8,
                source="explicit",
                created_at=now,
                last_updated=now,
            )
        ],
        risk_tolerance="moderate",
    )

    orchestrator = Orchestrator()
    fixtures = simulated_fixtures(now)

    results = []
    for entity_id, raw_signal in fixtures.items():
        raw_signals = [raw_signal]
        if entity_id == "TSLA":
            raw_signals.append(tesla_ai_partnership_corroboration(now))

        result = orchestrator.run(
            raw_signals=raw_signals,
            user_id="demo_user",
            user_model=user_model,
            engagement_samples=_engagement_samples(entity_id, now),
            domain=raw_signal.domain,
        )
        results.append((entity_id, result))

    # Connections: two events are "rippled" to each other if the entities either one
    # touches (directly or via World Model's downstream mapping) overlap.
    touched: dict[UUID, set[str]] = {
        r.event.event_id: {e.entity_id for e in r.event.entities}
        | set(r.event.downstream)
        for _, r in results
    }
    connections: dict[UUID, list[UUID]] = {event_id: [] for event_id in touched}
    event_ids = list(touched.keys())
    for i, a in enumerate(event_ids):
        for b in event_ids[i + 1 :]:
            if touched[a] & touched[b]:
                connections[a].append(b)
                connections[b].append(a)

    # Sort by the internal-only ranking score before building the public
    # response -- the score itself is never serialized (ADR-029); only the
    # resulting order (as `rank`, below) is public-facing.
    results.sort(
        key=lambda pair: pair[1].recommendation.internal_rank_score, reverse=True
    )

    items = []
    for position, (entity_id, r) in enumerate(results, start=1):
        entity = r.event.entities[0]
        canonical = resolve(entity_id, entity.display_name, r.event.domain)
        items.append(
            FeedItem(
                event_id=r.event.event_id,
                entity_id=canonical.entity_id,
                display_name=canonical.display_name,
                category=canonical.category,
                ticker=canonical.ticker,
                domain=r.event.domain,
                delivered_item=r.delivered_item,
                rank=position,
                confidence_score=r.confidence.confidence_score,
                confidence_label=r.delivered_item.confidence_label,
                connected_event_ids=connections[r.event.event_id],
            )
        )

    return DemoFeedResponse(items=items, generated_at=now)
