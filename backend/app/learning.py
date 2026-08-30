"""V2.3B Personal Learning Phase 1 -- inspection + correction surface over the
existing, already-live UserModel/MemoryStore/FeedbackEngine/LearningEngine
pipeline (see logan_core/learning/report.py's own module docstring for why
this deliberately isn't a second, parallel "learned profile" system).
Mirrors backend/app/watch.py's own module shape: a thin, identity-scoped
surface over logan_core, no new domain logic of its own.

2026-08-29 architecture audit finding (see docs/DECISIONS.md): Personal
Learning already exists and already feeds `personal_relevance` into ranking
today, via the same `_get_user_model()`/`memory_store` this module reads.
This module adds visibility and correction only -- it never touches
ranking, scoring, or Attention Field placement.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .logan_feed import _get_orchestrator, _seed_user_model
from .models import ConsumerLearningSummary, ConsumerLearningTrait

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import Domain, LearningReport  # noqa: E402
from logan_core.learning import build_learning_report  # noqa: E402
from logan_core.user_model import UserModelBuilder  # noqa: E402

# Operational Beta Hardening Block 4 -- one honest, standing sentence about
# what "learning" means here, never per-user data. Kept separate from
# LearningReport.architecture_notes (a developer-facing list of several
# specific limitations) -- a consumer needs one plain boundary statement,
# not the full technical caveat list.
_CONSUMER_LEARNING_EXPLANATION = (
    "This reflects only what you've explicitly told STRATUS (holdings, "
    "interests, Watches) or how you've used the app (what you open, read, "
    "or act on) -- never data from outside sources. You can turn off any "
    "of these at any time."
)


def get_learning_report(user_id: str) -> LearningReport:
    """Read-only. Independently seeds + folds this user's full memory
    history via the same, pure UserModelBuilder.build() the real
    `/v1/opportunities` poll uses (see logan_feed._get_user_model()) --
    deliberately not sharing that function's own process-lifetime cache, so
    this report is correct and complete on its very first call for a
    user_id, even one that has never polled `/v1/opportunities` at all (e.g.
    interacted only via /v1/interactions). Never itself writes anything to
    Memory or UserModel.
    """
    orchestrator = _get_orchestrator()
    now = datetime.now(timezone.utc)
    memory_records = orchestrator.deps.memory_store.query(user_id=user_id)
    base = _seed_user_model(user_id, now)
    user_model = UserModelBuilder().build(user_id, memory_records, base, now=now)
    return build_learning_report(user_id, user_model, memory_records, now=now)


def suppress_entity_learning(
    user_id: str, entity_id: str, domain: Optional[Domain] = None
) -> None:
    """Explicit trait correction/suppression -- "stop treating this as a
    preference for me." See logan_core/learning/engine.py's
    LearningEngine.suppress_entity() for the full mechanics (writes a
    correction_record; never mutates the raw feedback_record/exposure_record
    history it's correcting). No cache invalidation is needed here:
    logan_feed._get_user_model() rebuilds from a fresh `memory_store.query()`
    on every call regardless of caller, so the very next report or poll for
    this user_id picks up the correction automatically, the same way it
    would pick up any other new MemoryRecord.
    """
    orchestrator = _get_orchestrator()
    orchestrator.run_suppress_entity_learning(user_id, entity_id, domain)


def get_consumer_learning_summary(user_id: str) -> ConsumerLearningSummary:
    """Operational Beta Hardening Block 4 -- the smallest credible "What
    STRATUS is learning" consumer surface. Derived from the exact same
    LearningReport get_learning_report() already computes (never a second,
    parallel computation) -- just a smaller, consumer-safe projection of it:
    plain description + explicit/inferred basis only, never the underlying
    strength float, evidence_count, or timestamps.
    """
    report = get_learning_report(user_id)
    traits = [
        ConsumerLearningTrait(
            entity_id=t.entity_id, description=t.description, basis=t.source
        )
        for t in report.learned
    ]
    return ConsumerLearningSummary(
        user_id=user_id,
        generated_at=report.generated_at,
        traits=traits,
        explanation=_CONSUMER_LEARNING_EXPLANATION,
    )
