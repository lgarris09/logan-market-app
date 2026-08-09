// Turns a real backend signal_type ("earnings_signal", "volatility_spike")
// into the Attention Field vessel's small reason tag ("EARNINGS SIGNAL",
// "VOLATILITY SPIKE"). Deliberately just a formatting transform, not a
// lookup table of hand-authored phrases -- there is no field anywhere in
// the pipeline for a polished short label, and inventing one client-side
// would mean displaying a fabricated reason next to a real confidence
// score. See types/loganFeed.ts's FeedItem.signal_type comment.
export function humanizeSignalType(signalType: string): string {
  return signalType.replace(/_/g, " ").toUpperCase();
}
