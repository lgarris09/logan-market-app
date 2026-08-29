// 2026-08-29 confidence-ring audit: two different live tickers (NVDA, AAPL)
// both rounded to the same 60% confidence display despite genuinely
// different evidence profiles -- root cause was that confidence_score
// answers "how well-evidenced is this event" (source reputation +
// corroboration + recency + a flat per-trigger bonus), not "how much
// attention does this deserve," and for this class of event (single-source,
// FMP-sourced, earnings-beat-triggered) the formula has no term left that
// differentiates one qualifying stock from another. Rather than retune that
// formula (a scoring-model change, explicitly deferred), this replaces the
// consumer-facing percentage with a plain three-state judgment answering
// the question users actually care about on the card.
//
// Deliberately reuses `delivered_item.surface` -- already computed by
// PresentationEngine from PrioritizationEngine's own visibility (primary/
// feed/background, driven by internal_rank_score -- the Attention Field's
// own comparative-prioritization signal, unchanged and still authoritative)
// and interruption (alert/digest/none, driven by Policy's communication_mode
// -- the same ADR-049/050 Personal/Exceptional Watch route already gating
// real alerts) -- rather than inventing a new score. This is presentation
// of an existing decision, not a new opaque composite.
import type { DeliveredItem } from "../types/loganFeed";

export type AttentionJudgment = "Developing" | "Worth a look" | "High attention";

/**
 * "alert" (Policy-cleared interruption) and "wheel" (the single item STRATUS
 * has put in central focus right now) are the field's two strongest
 * attention signals -- both read as High attention. "digest" and
 * "feed_card" are ordinary visible content -- Worth a look. "background" is
 * the lowest tier still being tracked -- Developing.
 */
export function attentionJudgmentFor(surface: DeliveredItem["surface"]): AttentionJudgment {
  switch (surface) {
    case "alert":
    case "wheel":
      return "High attention";
    case "digest":
    case "feed_card":
      return "Worth a look";
    case "background":
      return "Developing";
  }
}

export type AttentionTone = "high" | "worth-a-look" | "developing";

export function attentionToneFor(judgment: AttentionJudgment): AttentionTone {
  switch (judgment) {
    case "High attention":
      return "high";
    case "Worth a look":
      return "worth-a-look";
    case "Developing":
      return "developing";
  }
}
