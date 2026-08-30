"""V2.3B Phase 2 (Learning-Driven STRATUS) Block 10 -- Learning Decision
Report, extended by Operational Beta Hardening Block 3 (Learning Decision
Explainability V2): for a given (user_id, entity_id), a developer-readable
answer to "why is this card here" / "why isn't it higher or lower" / "what
did STRATUS learn about this user for this entity" -- combining, in order,
the full WORLD / USER / PERSONAL RELEVANCE / ATTENTION / DISCOVERY / WHY
chain:

- World: the same real per-signal qualification opportunity_quality_report.py
  already reports (never re-derived, same evaluate_*_condition functions).
- Learned user context (USER): learning/report.py's own
  Observed/Learned/Not-learned, filtered to this one entity.
- Personal relevance: PersonalRelevanceResult (via OpportunityContext,
  ask_context.py) -- the single authoritative Block 2 computation.
- Attention decision: delivered_item.surface mapped through the same
  three-state judgment mobile/lib/attentionJudgment.ts uses (kept in sync
  by hand -- no shared-schema codegen in this project, same discipline as
  every other Python/TypeScript Literal pair here).
- Discovery: PrioritizedItem.attention_reason (via OpportunityContext,
  Operational Beta Hardening Block 2's logan_core/exploration/engine.py) --
  whether this item reached its visibility through the ordinary
  personal-relevance-driven path or one of Controlled Exploration's three
  deterministic anti-echo-chamber promotion reasons. Never fabricated: a
  None attention_reason is reported as exactly that, not guessed at.
- Why not higher/lower: limiting_factors / personal_relevance_not_contributing.

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


_DISCOVERY_EXPLANATIONS = {
    "personal_relevance": (
        "Ordinary path -- personal relevance to this user was the dominant "
        "factor in this item's visibility, no exploration promotion applied."
    ),
    "strong_world_signal": (
        "Promoted by Controlled Exploration (strong_world_signal): this is "
        "objectively significant on its own, regardless of this user's "
        "personal connection to it."
    ),
    "unseen_material_change": (
        "Promoted by Controlled Exploration (unseen_material_change): a "
        "genuinely new development this user has never been shown before."
    ),
    "EXPLORATION_OBJECTIVE_STRENGTH": (
        "Placed by Universe Manager V1a's batch-level Controlled Exploration "
        "slot (at most one among the top five, per feed refresh) -- shown "
        "outside this user's usual profile because the underlying evidence "
        "was objectively strong, fresh, and materially new, not because of "
        "anything this user has done."
    ),
}


def discovery_line_for(attention_reason: str | None) -> str:
    """Mirrors _DISCOVERY_EXPLANATIONS' own closed set -- an unrecognized or
    absent reason is reported honestly, never guessed at."""
    if attention_reason is None:
        return (
            "No exploration involved -- this item's visibility came from "
            "ordinary ranking alone."
        )
    return _DISCOVERY_EXPLANATIONS.get(
        attention_reason, f"Unrecognized attention_reason: {attention_reason}"
    )


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
    lines.append("Discovery")
    if item is None:
        lines.append("  Not currently surfaced for this user")
    else:
        attention_reason = context.attention_reason if context is not None else None
        lines.append(f"  {discovery_line_for(attention_reason)}")

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
