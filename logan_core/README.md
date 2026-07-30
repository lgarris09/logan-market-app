# logan_core

The Logan Intelligence System — the 18-layer reasoning pipeline that is Logan's canonical Phase 1
architecture. See [`../docs/specs/`](../docs/specs/) for the full locked specification and
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for how this relates to the rest of the project.

This is a Phase 1 **vertical slice**: the full pipeline runs end-to-end on **simulated data only**. No
live API integrations, no authentication, no external HTTP surface yet — see
[`docs/UNRESOLVED_QUESTIONS.md`](docs/UNRESOLVED_QUESTIONS.md) for what's deliberately not built yet.

## Local setup

```powershell
cd logan_core
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the tests

```powershell
python -m pytest logan_core/tests -v
```

28 tests cover contract validation, the Evidence Trust and Opportunity Engine scoring formulas, World
Model deduplication, Policy language rules (including the betting/prediction-market objectivity rule,
ADR-013), and two end-to-end integration tests: the primary Tesla scenario (Raw Signal → Presentation)
and the feedback loop (Feedback → Learning → Memory write).

## Run the Tesla scenario directly

```python
from datetime import datetime, timezone
from logan_core.contracts import Holding
from logan_core.community_intelligence import EngagementSample
from logan_core.orchestrator import Orchestrator
from logan_core.receptors import tesla_ai_partnership_signal, tesla_ai_partnership_corroboration
from logan_core.user_model import UserModelBuilder

now = datetime.now(timezone.utc)
user_model = UserModelBuilder().seed(
    user_id="demo_user",
    holdings=[Holding(domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=now)],
)
samples = [
    EngagementSample(observed_at=now, volume_at_point=10, unique_users=8, saves_shares=1, questions=0),
    EngagementSample(observed_at=now, volume_at_point=40, unique_users=30, saves_shares=6, questions=3),
]

orchestrator = Orchestrator()
result = orchestrator.run(
    raw_signals=[tesla_ai_partnership_signal(now), tesla_ai_partnership_corroboration(now)],
    user_id="demo_user",
    user_model=user_model,
    engagement_samples=samples,
    domain="stocks",
)

print(result.delivered_item.headline)
print(result.delivered_item.why_it_matters_to_me)
print(result.delivered_item.confidence_label, result.delivered_item.confidence_score)
```

## Layer map

One folder per layer, per [ADR-017](../docs/DECISIONS.md#adr-017-new-top-level-logan_core-directory-with-one-folder-per-layer):

```
contracts/              typed objects (Pydantic) for every layer boundary
orchestrator/            pipeline execution, retries, ExecutionTrace, Operational History (ADR-016)
receptors/                5 simulated domain receptors: stocks, sports, poly, social, news (ADR-020)
normalization/            RawSignal -> NormalizedSignal
world_model/               entity graph, dedup, downstream/ripple mapping
evidence_trust/            source credibility, corroboration, trust_score
community_intelligence/    engagement volume/velocity, momentum, bot/coordinated risk
memory/                    Logan Memory (Operational History lives in orchestrator/, per ADR-016)
user_model/                durable interpretation of the user, built from Memory
active_context/            session-scoped present-moment context
reasoning/                 event significance + personal relevance + stance + actionability
mental_model/              V1 pass-through hypothesis tracking (ADR-015)
conclusion_confidence/     fact/inference/hypothesis/speculation classification
opportunity/                10-dimension scoring, priority_score, attention recommendation
policy/                     advice-boundary and betting-objectivity language enforcement (ADR-013)
prioritization/             visibility/interruption, cooldowns, fatigue, AttentionState
presentation/                DeliveredItem — the opportunity card
feedback/                    interaction -> FeedbackSignal, including Memory Inbox confirm/reject (ADR-019)
learning/                    the only layer that writes Memory — FeedbackSignal -> MemoryWrite
tests/                       pytest suite
docs/                        this deliverable set — setup, decisions, open questions
```

See [`docs/IMPLEMENTATION_DECISIONS.md`](docs/IMPLEMENTATION_DECISIONS.md) for decisions made while
building this slice that weren't already covered by the project-level ADRs, and
[`docs/UNRESOLVED_QUESTIONS.md`](docs/UNRESOLVED_QUESTIONS.md) for what's still open.
