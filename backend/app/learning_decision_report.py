"""V2.3B Phase 2 (Learning-Driven STRATUS) Block 10 -- Learning Decision
Report: for a given (user_id, entity_id), a developer-readable answer to
"why is this card here" / "why isn't it higher or lower" / "what did
STRATUS learn about this user for this entity" -- combining:

- World: the same real per-signal qualification opportunity_quality_report.py
  already reports (never re-derived, same evaluate_*_condition functions).
- Learned user context: learning/report.py's own Observed/Learned/Not-learned,
  filtered to this one entity.
- Personal relevance: PersonalRelevanceResult (via OpportunityContext,
  ask_context.py) -- the single authoritative Block 2 computation.
- Attention decision: delivered_item.surface mapped through the same
  three-state judgment mobile/lib/attentionJudgment.ts uses (kept in sync
  by hand -- no shared-schema codegen in this project, same discipline as
  every other Python/TypeScript Literal pair here).

Read-only throughout -- this module never writes anything.
"""

from .learning import get_learning_report
from .logan_feed import get_opportunity_context, run_demo_feed
from .opportunity_quality_report import build_ticker_quality_report


def attention_judgment_for(surface: str) -> str:
    """Mirrors mobile/lib/attentionJudgment.ts's attentionJudgmentFor()."""
    if surface in ("alert", "wheel"):
        return "High attention"
    if surface in ("digest", "feed_card"):
        return "Worth a look"
    return "Developing"


def build_learning_decision_report(user_id: str, entity_id: str) -> str:
    feed = run_demo_feed(user_id)
    item = next((i for i in feed.items if i.entity_id == entity_id), None)

    quality = build_ticker_quality_report(entity_id)
    learning_report = get_learning_report(user_id)

    lines = [entity_id, "", "World"]
    for sig in quality.signals:
        status = "QUALIFIED" if sig.qualified else "NOT QUALIFIED"
        lines.append(f"  {sig.name} -- {status} -- {sig.reason}")

    lines.append("")
    lines.append("Learned user context")
    entity_observed = [o for o in learning_report.observed if o.entity_id == entity_id]
    entity_traits = [t for t in learning_report.learned if t.entity_id == entity_id]
    entity_not_learned = [
        t for t in learning_report.not_learned if t.candidate == entity_id
    ]
    if not entity_observed and not entity_traits and not entity_not_learned:
        lines.append("  no meaningful history")
    else:
        for o in entity_observed:
            lines.append(f"  {o.description}")
        for t in entity_traits:
            lines.append(f"  {t.description} ({t.source}, strength {t.strength:.2f})")
        for nl in entity_not_learned:
            lines.append(f"  not learned: {nl.reason}")

    lines.append("")
    lines.append("Personal relevance")
    context = (
        get_opportunity_context(user_id, item.event_id) if item is not None else None
    )
    if context is None:
        lines.append("  Unknown -- this entity is not currently in this user's feed")
    elif context.connection_basis == "none":
        lines.append("  Unknown/low")
        lines.append(f"  {context.personal_relevance_explanation}")
    else:
        state = (
            "High" if context.connection_basis in ("watch", "explicit") else "Moderate"
        )
        lines.append(f"  {state}")
        lines.append(f"  {context.personal_relevance_explanation}")

    lines.append("")
    lines.append("Attention decision")
    if item is None:
        lines.append("  Not currently surfaced for this user")
    else:
        judgment = attention_judgment_for(item.delivered_item.surface)
        lines.append(f"  {judgment}")
        objective_note = f"objective evidence is {item.confidence_label.lower()}"
        if context is not None and context.connection_basis != "none":
            lines.append(
                f"  centered because {objective_note} and "
                f"{context.personal_relevance_explanation.rstrip('.').lower()}"
            )
        else:
            lines.append(
                f"  because {objective_note}, despite limited user history so far"
            )

    lines.append("")
    lines.append("Why not higher/lower")
    if context is not None and context.limiting_factors:
        for factor in context.limiting_factors:
            lines.append(f"  {factor}")
    elif context is not None and context.personal_relevance_not_contributing:
        for reason in context.personal_relevance_not_contributing:
            lines.append(f"  {reason}")
    else:
        lines.append("  nothing currently flagged")

    return "\n".join(lines)
