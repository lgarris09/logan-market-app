"""Sprint 3.6.7 Block 4 -- deterministic, grounded Ask STRATUS responses for
a specific opportunity. No LLM is used anywhere in this codebase today
(confirmed by inspection before writing this -- the pre-existing generic
`/v1/ask` path in main.py is itself a template/lookup, not a model call);
adding one would be a new external dependency requiring the explicit
confirmation CLAUDE.md's collaboration model requires for dependency
additions, which is a separate decision this block does not make. Instead:
real, already-computed pipeline data (DeliveredItem's narrative fields,
ConclusionConfidence's classification/limiting_factors/alternatives, the
entity's attached TriggerEvents, Dimensions.personal_relevance) is matched
against the question via deterministic keyword classification and returned
as-is or lightly composed -- never fabricated, never inferring a fact this
codebase's own pipeline hasn't actually computed. "Deterministic intelligence
first, LLM interpretation second" -- there is no second stage here yet; this
*is* the first stage, exposed directly.
"""

from .ask_context import OpportunityContext

_EARNINGS_CODES = {
    "STOCK_EARNINGS_BEAT",
    "STOCK_EARNINGS_MISS",
    "STOCK_EARNINGS_IN_LINE",
}
_PRICE_CODES = {"STOCK_PRICE_MOVE_SIGNIFICANT"}
_ANALYST_CODES = {"STOCK_ANALYST_UPGRADE", "STOCK_ANALYST_DOWNGRADE"}

_TRIGGER_LABELS = {
    "STOCK_EARNINGS_BEAT": "an earnings beat",
    "STOCK_EARNINGS_MISS": "an earnings miss",
    "STOCK_EARNINGS_IN_LINE": "an in-line earnings report",
    "STOCK_PRICE_MOVE_SIGNIFICANT": "a significant price move",
    "STOCK_ANALYST_UPGRADE": "an analyst upgrade",
    "STOCK_ANALYST_DOWNGRADE": "an analyst downgrade",
    "STOCK_CONVERGENCE_MULTI_SOURCE": "multiple signals converging",
}


def _matches(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _trigger_label(code: str) -> str:
    return _TRIGGER_LABELS.get(code, code.replace("_", " ").lower())


def _signals_answer(context: OpportunityContext) -> str:
    if not context.trigger_codes:
        return (
            f"{context.display_name} hasn't crossed any of STRATUS's registered stock "
            "signal thresholds right now -- this opportunity is being surfaced on "
            "general context, not a specific fired trigger."
        )
    real_codes = [
        c for c in context.trigger_codes if c != "STOCK_CONVERGENCE_MULTI_SOURCE"
    ]
    labels = [_trigger_label(c) for c in real_codes] or [
        _trigger_label(c) for c in context.trigger_codes
    ]
    if len(labels) == 1:
        signal_sentence = f"The signal behind this is {labels[0]}."
    else:
        signal_sentence = (
            f"There are {len(labels)} distinct signals behind this: "
            f"{', '.join(labels[:-1])} and {labels[-1]}."
        )
    return f"{signal_sentence} {context.what_happened}"


def _convergence_answer(context: OpportunityContext) -> str:
    if not context.convergence_sources:
        return (
            f"No, this isn't a multi-signal convergence right now -- "
            f"{context.display_name}'s opportunity is currently based on "
            f"{'a single signal type' if len(context.trigger_codes) <= 1 else f'{len(context.trigger_codes)} signal types that have not (yet) reached the registered 3-signal convergence threshold'}. "
            "STRATUS only reports convergence when at least 3 distinct signal "
            "sources genuinely align within its 30-minute window -- it isn't close "
            "to that here."
        )
    sources = ", ".join(context.convergence_sources)
    return (
        f"Yes -- {len(context.convergence_sources)} distinct signal types have "
        f"genuinely converged for {context.display_name} within STRATUS's 30-minute "
        f"window: {sources}. That's a real, registered convergence "
        "(STOCK_CONVERGENCE_MULTI_SOURCE), not just one signal reported multiple ways."
    )


def _confidence_answer(context: OpportunityContext) -> str:
    classification_explainer = {
        "fact": "backed by a highly-reputable source with real independent corroboration",
        "inference": "a reasonable read of the current evidence, not yet fully corroborated",
        "hypothesis": "still tentative -- the evidence points this way but isn't strong yet",
        "speculation": "weakly supported right now -- treat this as an early, unconfirmed read",
    }.get(context.classification, "evaluated using STRATUS's standard confidence model")
    base = (
        f"STRATUS rates this {context.confidence_label.lower()} confidence "
        f"({context.confidence_score:.2f} on a 0-1 scale) -- {classification_explainer}."
    )
    if context.limiting_factors:
        base += (
            " What's currently limiting that confidence: "
            + "; ".join(f.rstrip(".") for f in context.limiting_factors)
            + "."
        )
    return base


def _limiting_factors_answer(context: OpportunityContext) -> str:
    parts = []
    if context.limiting_factors:
        parts.append(
            "What would weaken this: "
            + "; ".join(f.rstrip(".") for f in context.limiting_factors)
            + "."
        )
    if context.alternatives:
        parts.append("Worth keeping in mind: " + " ".join(context.alternatives))
    if not parts:
        return (
            f"Nothing currently limits STRATUS's read on this -- confidence is "
            f"{context.confidence_label.lower()} with no flagged limiting factors right now. "
            "That can still change as new signals come in."
        )
    return " ".join(parts)


def _personal_answer(context: OpportunityContext) -> str:
    if context.connection_basis == "explicit":
        return (
            f"{context.why_it_matters_to_me} This connection is based on something you "
            "explicitly hold or follow, not an inferred pattern."
        )
    if context.connection_basis == "inferred":
        return (
            f"{context.why_it_matters_to_me} This is based on STRATUS's read of your "
            f"past engagement (personal relevance {context.personal_relevance:.2f}), not "
            "an explicit holding or interest -- it can grow or fade as your behavior does."
        )
    return context.why_it_matters_to_me


def _dominant_signal_answer(context: OpportunityContext) -> str:
    if not context.trigger_codes:
        return _signals_answer(context)
    real_codes = [
        c for c in context.trigger_codes if c != "STOCK_CONVERGENCE_MULTI_SOURCE"
    ]
    if len(real_codes) <= 1:
        only = real_codes[0] if real_codes else context.trigger_codes[0]
        return (
            f"There's only one real signal driving this right now: {_trigger_label(only)}. "
            "Nothing else to compare it against yet."
        )
    labels = ", ".join(_trigger_label(c) for c in real_codes)
    return (
        f"This opportunity currently combines {len(real_codes)} signals: {labels}. "
        "STRATUS doesn't rank one as definitively 'stronger' in isolation -- each "
        "contributes its own registered confidence weight, and the strongest single "
        f"one currently drives the {context.confidence_label.lower()} overall confidence "
        f"({context.confidence_score:.2f})."
    )


def answer_question(context: OpportunityContext, message: str) -> str:
    """Deterministically routes `message` to the real, already-computed field
    (or small composition of fields) it's actually asking about. Order
    matters -- more specific categories are checked before more generic
    ones, mirroring this codebase's existing "explicit checked before
    inferred" precedent (policy/engine.py's _watch_route). Falls through to
    an honest overview, never a fabricated answer, when nothing matches.
    """
    text = message.lower()

    if _matches(text, ["converg", "multiple signals", "confirm each other", "align"]):
        return _convergence_answer(context)
    if _matches(
        text,
        [
            "stronger than",
            "weaker than",
            "compare",
            " vs ",
            " versus ",
            "which is bigger",
        ],
    ):
        return _dominant_signal_answer(context)
    if _matches(
        text,
        [
            "what signal",
            "which signal",
            "what's driving",
            "whats driving",
            "what's behind",
            "whats behind",
        ],
    ):
        return _signals_answer(context)
    if _matches(
        text,
        [
            "less interesting",
            "weaker",
            "change your mind",
            "what would make",
            "concern",
            "risk",
            "wrong about this",
            "could be wrong",
            "weaken",
        ],
    ):
        return _limiting_factors_answer(context)
    if _matches(
        text,
        [
            "how sure",
            "how confident",
            "certain",
            "trust this",
            "reliable",
            "confidence",
        ],
    ):
        return _confidence_answer(context)
    if _matches(
        text,
        [
            "matter to me",
            "my portfolio",
            "relevant to me",
            "personally",
            "affect me",
            "care about",
        ],
    ):
        return _personal_answer(context)
    if _matches(
        text,
        ["why now", "why today", "timing", "urgent", "matter right now", "matter now"],
    ):
        return context.why_now or context.why_it_matters
    if _matches(
        text,
        ["why does this matter", "why matter", "why should i care", "significance"],
    ):
        return context.why_it_matters
    if _matches(text, ["what changed", "what happened", "what's new", "whats new"]):
        return context.what_happened

    return (
        f"{context.headline} {context.what_happened} {context.why_it_matters} "
        f"Confidence: {context.confidence_label.lower()} ({context.confidence_score:.2f}). "
        "Ask what changed, why it matters, which signals are involved, or what would "
        "weaken this for more detail."
    )
