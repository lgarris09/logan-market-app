// Opportunity Card overflow detection (Sprint 3.6, section 7 bug fix).
//
// Vessel.tsx's detail body used to size its ScrollView against a fixed
// estimate of the header/headline's height (DETAIL_BODY_RESERVED), rather
// than the real remaining space. When the real header content ran taller
// than that estimate (a long headline wrapping to 3 lines, a long ticker),
// the ScrollView's rendered box itself extended past the card shell's
// clipped bounds -- so the bottom of the scrollable content was cut off
// by the shell's own overflow:hidden, not just scrolled past. The fix in
// Vessel.tsx is a flex:1 ScrollView (always exactly fills real remaining
// space, however tall the header turns out to be) instead of a computed
// maxHeight. This function is the small, pure piece of that fix that's
// worth testing in isolation: whether the "there's more below" fade should
// show, given the ScrollView's real measured content height vs. its real
// measured container height (both from onLayout/onContentSizeChange,
// unavailable as real numbers in a component-mount test the way they are
// on-device).
const OVERFLOW_EPSILON_PX = 4;

export function shouldShowOverflowFade(contentHeight: number, containerHeight: number): boolean {
  if (containerHeight <= 0) return false;
  return contentHeight > containerHeight + OVERFLOW_EPSILON_PX;
}
