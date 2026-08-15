import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";
import Svg, { Circle, Defs, RadialGradient, Stop } from "react-native-svg";
import { Ionicons } from "@expo/vector-icons";
import Animated, {
  Easing,
  Extrapolation,
  interpolate,
  SharedValue,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withSpring,
  withTiming,
} from "react-native-reanimated";

import { font, radius, spacing, theme, tracking, type } from "../constants/theme";
import { ConfidenceRing } from "./ConfidenceRing";
import { EntitySymbol } from "./EntitySymbol";
import { RecommendationPanel } from "./RecommendationPanel";
import { relativeTimeFrom } from "../lib/relativeTime";
import { resolveSymbol } from "../lib/symbolResolver";
import { shouldShowOverflowFade } from "../lib/cardOverflow";
import { humanizeSignalType } from "../lib/signalType";
import { LABEL_WIDTH_FRACTION, VesselLayout } from "../lib/attentionLayout";
import { FeedItem } from "../types/loganFeed";

const MIN_TOUCH_TARGET = 44;
// Round 3 (owner physical-iPhone review): 13/10px (V3.1.4.3), 18/14px
// (Sprint 3.6.5), then 32/24px (round 2) all still read as "too small" --
// one more meaningful step, targeting roughly 40/30px. The icon still stays
// subordinate to the name via restLabelIconWrap's reduced opacity below, not
// via being physically smaller than the text -- that's the same mechanism
// this file already used at every smaller size. Sizes must stay in sync
// with attentionLayout.ts's NAME_ICON_ALLOWANCE, which reserves the icon's
// own footprint as an independent width floor -- growing this only ever
// grows the bubble that floor demands (minDiameterForLabel), never causes
// clipping (icon-above-name doesn't share a line with the name text, so it
// doesn't widen the *name line's* own estimate).
const FULL_NAME_ICON_SIZE = 40;
const COMPACT_NAME_ICON_SIZE = 30;
// Vertical gap between the icon and the name below it -- deliberately
// tighter than the icon-to-percentage/percentage-to-descriptor gaps
// (restLabelPct's marginTop, restLabelDescriptor's marginTop) so the icon
// reads as attached to the name it identifies, not as a floating fourth
// line with equal weight. Widened slightly alongside the larger icon sizes
// above so the gap still reads proportional, not swallowed by the icon.
const ICON_NAME_GAP = 5;
// Shared with AttentionField.tsx's viewport-clamp math (round 2, real-device
// screenshot review: the card could render partially off-screen for vessels
// near the field's edges since it grew symmetrically from the vessel's own
// anchor). Exported so both files stay in sync instead of duplicating magic
// numbers.
export const CARD_HEIGHT = 372;
export const CARD_SAFE_MARGIN = 16;

// Attention Gravity motion (see the class comment below). A new vessel's
// position starts this many times farther from the field center than its
// own target, along the same angle -- pushed toward the periphery, not
// off-field -- so its first spring visibly arrives from the outer field.
const ENTRY_PUSH_MULTIPLIER = 1.6;
// Gentler than the disclosure/focus springs elsewhere in this file --
// those are direct interaction feedback (should feel immediate); this is
// the field "continuously reorganizing itself," which reads better as an
// unhurried settle than a snappy one, especially for a position change
// that can cover real distance (a rank promotion migrating toward center).
const POSITION_SPRING = { damping: 18, stiffness: 50 };

// Every entity on the Attention Field renders through this one component --
// there is no separate "card" anywhere. A vessel is always alive (drifting,
// breathing with its own confidence, pulsing with its own priority, rippling
// when something it's connected to stirs) whether or not anyone is looking
// at it. Disclosure (0..1) is how much of it has condensed into words and
// grown into the full Opportunity Card; tapping it again (or the close
// button, or another vessel) lets it dissolve back into pure atmosphere.
//
// V3.1.4.1 (Sprint 3.5 device-validation fix, round 1): this used to run on
// the classic `Animated` API with `useNativeDriver: false` driving the
// actual width/height/borderRadius growth -- i.e. the one animation that
// visibly turns a dot into a card ran on the JS thread, contending with
// several other concurrent per-vessel loops plus the Skia atmosphere
// canvas. On a real iPhone under New Architecture that combination
// measurably stalled; state updated but the card never visibly grew.
// Everything here now runs through Reanimated (already a dependency,
// already used by the atmosphere layer) so every animated property --
// including layout ones -- runs on the UI thread regardless of JS load.
//
// Round 2 (real-device screenshots): the glow's own resting position could
// place the *card* partially off-screen, and the frosted-glass card read as
// too transparent against the moving Atmosphere. `cardOffsetX/Y` (computed
// by AttentionField.tsx from the real field bounds) let the card glide to a
// safe on-screen position as it grows, independent of the glow/label, which
// stay at the vessel's natural field position -- the card "detaches" for
// legibility, the glow still marks where the opportunity structurally lives.
//
// Attention Gravity motion architecture: `layout.x/y` used to be consumed
// as a static `left/top` percentage -- if the target changed between polls
// (a re-ranked item, a newly-admitted one), the vessel would snap there
// instantly. Position is now owned by a pair of Reanimated shared values
// (`posX`/`posY`, in real px) that spring toward whatever target this
// render's `layout` provides, the same "animate toward the latest prop"
// pattern already used for `disclosureAnim`/`focusAnim` below. Because
// Reanimated shared values live on the mounted component instance (not
// recreated per render), a vessel that's still on-screen across polls
// keeps whatever position it's currently mid-spring toward -- continuity
// is a property of the component staying mounted (same `event_id` key in
// AttentionField.tsx), not anything persisted externally. A newly-mounted
// vessel seeds `posX/posY` at a point pushed outward from its own target
// (toward the field's periphery) instead of the target itself, so it
// visibly arrives from the outer field on its very first spring rather
// than materializing in place.
export function Vessel({
  item,
  layout,
  isFocused,
  disclosure,
  isDimmed,
  readingWidth,
  cardOffsetX,
  cardOffsetY,
  maxCardHeight,
  echoSignal,
  fieldWidth,
  fieldHeight,
  biasState = "neutral",
  isExiting,
  onPress,
}: {
  item: FeedItem;
  layout: VesselLayout;
  isFocused: boolean;
  disclosure: 0 | 1;
  isDimmed: boolean;
  readingWidth: number;
  cardOffsetX: number;
  cardOffsetY: number;
  maxCardHeight: number;
  echoSignal: SharedValue<number>;
  /** Real field dimensions in px -- lets this vessel convert its own
   * layout.x/y fraction into a pixel position it can animate toward
   * (Attention Gravity motion architecture; see the class comment). */
  fieldWidth: number;
  fieldHeight: number;
  /** FIELD BIAS presentation state (see lib/fieldBias.ts and
   * AttentionField.tsx's per-item computation): "neutral" when no lens is
   * active or this vessel wasn't judged either way, "emphasized" when it
   * matches the active lens (a modest scale bump plus a small breathing-
   * opacity floor lift -- paint order and visual definition, still bounded
   * well under a rank promotion's own effect, per the product guardrail
   * against a low-priority matching item becoming the dominant
   * opportunity), "receded" when it doesn't match (dimmer, via the same
   * opacity-multiplier pattern `dimAnim` already uses for the focused-card
   * spotlight effect -- never fully invisible; ranking stays authoritative,
   * this is presentation only). Defaults to "neutral" so every existing
   * call site keeps behaving exactly as before this prop existed.
   */
  biasState?: "neutral" | "emphasized" | "receded";
  /** True once this event_id has left the live feed but AttentionField is
   * still holding it on-screen to let it fade out rather than vanish
   * instantly -- see AttentionField.tsx's departure tracking. */
  isExiting?: boolean;
  onPress: () => void;
}) {
  const symbol = resolveSymbol(item);
  const instability = 1 - item.confidence_score; // low confidence -> more visible flicker
  // Already 0..1 and rank-derived (see attentionLayout.ts) -- no raw score is
  // ever available here, per ADR-029.
  const prominence = layout.prominence;
  const reducedMotion = useReducedMotion();
  // Sprint 3.6 overflow-fade affordance (section 7) -- see the
  // detailBodyWrap comment below for why these are measured rather than
  // estimated.
  const [detailContainerH, setDetailContainerH] = useState(0);
  const [detailContentH, setDetailContentH] = useState(0);

  // Attention Gravity: this vessel's real-pixel target position, from the
  // layout fraction this render provides.
  const targetX = layout.x * fieldWidth;
  const targetY = layout.y * fieldHeight;
  // A brand-new vessel's position shared values start pushed outward from
  // the target -- toward the field's periphery, same angle from center,
  // farther out -- rather than at the target itself, so its first spring
  // visibly arrives from the outer field (see the class comment). Only
  // matters at mount: useSharedValue's initializer is ignored on
  // subsequent renders, same as useState's.
  const fieldCenterX = fieldWidth / 2;
  const fieldCenterY = fieldHeight / 2;
  const entryOffsetX = targetX - fieldCenterX;
  const entryOffsetY = targetY - fieldCenterY;
  const entryDist = Math.hypot(entryOffsetX, entryOffsetY);
  const entryX = entryDist < 1 ? targetX : fieldCenterX + entryOffsetX * ENTRY_PUSH_MULTIPLIER;
  const entryY = entryDist < 1 ? targetY : fieldCenterY + entryOffsetY * ENTRY_PUSH_MULTIPLIER;

  const posX = useSharedValue(entryX);
  const posY = useSharedValue(entryY);
  const entrance = useSharedValue(0);
  const drift = useSharedValue(0);
  const breath = useSharedValue(0);
  const pulse = useSharedValue(0);
  const disclosureAnim = useSharedValue(0);
  const focusAnim = useSharedValue(isFocused ? 1 : 0);
  const dimAnim = useSharedValue(0);
  // FIELD BIAS (see the biasState prop doc above): two independent shared
  // values, not one -- recede is an opacity effect and emphasis is a scale
  // effect, and a vessel is never both at once (biasState is one of three
  // mutually exclusive states), but keeping them separate mirrors how the
  // rest of this file already treats "dim" (opacity) and "focus scale"
  // (transform) as distinct concerns even though they're driven together.
  const biasRecedeAnim = useSharedValue(0);
  const biasEmphasisAnim = useSharedValue(0);

  // Springs toward whatever target this render's `layout` provides --
  // covers both the mount case (spring from the peripheral entry point
  // above to the real target) and every later poll where rank/relationships
  // moved this vessel's target (spring from wherever it currently is,
  // mid-flight or settled, to the new one). Reduced motion still moves,
  // just without the spring's overshoot/settle feel.
  useEffect(() => {
    if (reducedMotion) {
      posX.value = withTiming(targetX, { duration: 260 });
      posY.value = withTiming(targetY, { duration: 260 });
      return;
    }
    posX.value = withSpring(targetX, POSITION_SPRING);
    posY.value = withSpring(targetY, POSITION_SPRING);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetX, targetY, reducedMotion]);

  // Condensation: this vessel did not simply appear -- it accreted, starting
  // diffuse and settling. Staggered per entity so the whole field doesn't
  // form in unison. Also owns the reverse: dissolving back out once this
  // event_id has left the live feed (see AttentionField.tsx's departure
  // tracking) reuses the same shared value rather than a second, separate
  // opacity concept -- kept in one effect (not a second one also writing
  // `entrance.value`) since Reanimated's lint rules disallow a shared
  // value being mutated from two different effects.
  useEffect(() => {
    if (isExiting) {
      entrance.value = withTiming(0, { duration: reducedMotion ? 160 : 420 });
      return;
    }
    if (reducedMotion) {
      entrance.value = 1;
      return;
    }
    const delay = stableDelay(item.event_id);
    entrance.value = withDelay(delay, withSpring(1, { damping: 11, stiffness: 90 }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reducedMotion, isExiting]);

  useEffect(() => {
    if (reducedMotion) {
      drift.value = 0;
      return;
    }
    const base = 6000 / layout.driftFreq;
    const delay = (layout.driftPhase / (Math.PI * 2)) * base;
    const ease = Easing.inOut(Easing.sin);
    drift.value = withRepeat(
      withSequence(
        withDelay(delay, withTiming(1, { duration: base, easing: ease })),
        withTiming(-1, { duration: base * 2, easing: ease }),
        withTiming(0, { duration: base, easing: ease })
      ),
      -1,
      false
    );
  }, [drift, layout.driftFreq, layout.driftPhase, reducedMotion]);

  // Confidence made continuous: a settled belief barely moves; an uncertain
  // one visibly wavers the whole time you look at it, not just once.
  useEffect(() => {
    if (reducedMotion) {
      breath.value = 0;
      return;
    }
    const base = 3400 / layout.breathFreq;
    const delay = (layout.breathPhase / (Math.PI * 2)) * base;
    const ease = Easing.inOut(Easing.sin);
    breath.value = withRepeat(
      withSequence(
        withDelay(delay, withTiming(1, { duration: base, easing: ease })),
        withTiming(0, { duration: base, easing: ease })
      ),
      -1,
      false
    );
  }, [breath, layout.breathFreq, layout.breathPhase, reducedMotion]);

  // Priority made continuous: what matters more visibly asserts itself more
  // often -- a slow heartbeat, not a fixed brightness.
  useEffect(() => {
    if (reducedMotion) {
      pulse.value = 0;
      return;
    }
    const base = 2200 / layout.pulseFreq;
    const delay = (layout.pulsePhase / (Math.PI * 2)) * base;
    const ease = Easing.inOut(Easing.sin);
    pulse.value = withRepeat(
      withSequence(
        withDelay(delay, withTiming(1, { duration: base, easing: ease })),
        withTiming(0, { duration: base, easing: ease })
      ),
      -1,
      false
    );
  }, [pulse, layout.pulseFreq, layout.pulsePhase, reducedMotion]);

  useEffect(() => {
    disclosureAnim.value = reducedMotion
      ? withTiming(disclosure, { duration: 120 })
      : withSpring(disclosure, { damping: 15, stiffness: 110 });
  }, [disclosure, disclosureAnim, reducedMotion]);

  useEffect(() => {
    focusAnim.value = withTiming(isFocused ? 1 : 0, { duration: reducedMotion ? 120 : 420 });
  }, [isFocused, focusAnim, reducedMotion]);

  // Spotlight effect: while something else holds the field's attention, the
  // rest recede strongly rather than compete with it -- Atmosphere stays
  // present (AttentionAtmosphere.tsx dampens itself the same way) but the
  // dormant field should read as clearly secondary to an open card, not a
  // subtle suggestion of it (round 2: "strongly dim" per real-device review).
  useEffect(() => {
    dimAnim.value = withTiming(isDimmed ? 1 : 0, { duration: 260 });
  }, [isDimmed, dimAnim]);

  // FIELD BIAS: same "animate toward the latest prop" pattern as every
  // other shared value in this file. Reduced motion still moves, just
  // faster/no-overshoot, matching this file's existing reduced-motion
  // convention (e.g. the position spring above).
  useEffect(() => {
    const duration = reducedMotion ? 120 : 320;
    biasRecedeAnim.value = withTiming(biasState === "receded" ? 1 : 0, { duration });
    biasEmphasisAnim.value = withTiming(biasState === "emphasized" ? 1 : 0, { duration });
  }, [biasState, reducedMotion, biasRecedeAnim, biasEmphasisAnim]);

  // V3.1.4.2 (brand-alignment pass): this used to be Math.max(layout.size,
  // MIN_TOUCH_TARGET / 0.72), which silently inflated every low-priority
  // vessel's *visual* glow up to the accessibility touch-target minimum --
  // undermining "don't make every vessel equally prominent." The true
  // rank-derived size is used for everything visual now; `touchPad` below
  // pads the tappable hit area (via hitSlop) up to 44pt instead, so small
  // vessels stay small to look at but are still easy to tap.
  const dormantSize = layout.size;
  const cardHeight = Math.min(CARD_HEIGHT, maxCardHeight);

  // Sprint 3.6 (real-device correction pass): the real-device screen still
  // read as "one large illuminated cloud" through the middle/lower field --
  // every vessel's glow used the same fixed opacity regardless of how
  // important it actually was, so a field with many secondary vessels
  // stayed uniformly bright even though `layout.size` (and therefore ring
  // radius) already scales down for them. Bloom opacity and the bubble's own
  // gradient/stroke intensity all scale with `prominence` (0..1, rank-
  // derived, already computed by attentionLayout.ts) so the strongest bloom
  // is reserved for the highest-attention vessels and secondary vessels
  // recede toward true negative space instead of contributing an
  // equally-bright halo.
  //
  // Sprint 3.6 (bubble-match pass): the vessel used to be three stacked
  // flat-color circles (outer/mid/core), which read as a fairly solid disc
  // rather than a glowing sphere. First gradient attempt had this backwards
  // (bright/opaque center fading to a transparent edge) -- the owner's
  // reference is the other way around: the center, where the label sits, is
  // the *most transparent* part, and the color thickens into a darker,
  // more saturated "smoke" ring toward the bubble's edge. `bubbleSize` is
  // the crisp gradient-filled sphere itself (matches `dormantSize`, so it
  // lines up with the existing touch-target/label-footprint math
  // elsewhere); `bloom` is a separate, much fainter halo bleeding beyond it
  // for ambient depth.
  const bubbleSize = dormantSize;
  // Second gradient pass (owner review of the first): still read as too
  // dark/filled through the middle. The fix isn't more stops, it's that
  // rank/prominence was darkening the *center*, not just the edge -- a
  // vessel's importance should show up as a stronger, denser outer shell,
  // never as a less transparent middle. The center 40-50% of the radius
  // (offsets 0 and 0.35 below) is now a fixed, near-nothing opacity
  // regardless of prominence; only the outer-third stops (0.60/0.80/1.00)
  // scale with it, so a high-priority vessel gets a denser "smoke" shell,
  // not a darker hole. Five stops (not three) so the build from transparent
  // to smoke is gradual through the middle and only becomes obvious in the
  // outer third, rather than one linear ramp across the whole radius. This
  // profile itself is unchanged by the third (material-softening) pass
  // below -- that pass is entirely about structure/layering, not these
  // numbers.
  const gradientCenterOpacity = 0.01; // offset 0 -- not prominence-scaled, by design
  const gradientInnerOpacity = 0.03; // offset 0.35 -- still "the center," not prominence-scaled
  // Sprint 3.6.5 device-feedback pass: widened every prominence-scaled
  // coefficient below (lower baseline, larger range) -- on a physical
  // device, secondary/contextual vessels still competed too closely with
  // the primary one for visual weight. Purely a presentation-layer
  // sharpening of the existing prominence signal (already 0..1, rank-
  // derived) -- no change to rank, Attention Gravity, or any geometry.
  const gradientTransitionOpacity = 0.06 + prominence * 0.06; // offset 0.60
  const gradientOuterOpacity = 0.16 + prominence * 0.16; // offset 0.80
  const gradientRimFillOpacity = 0.38 + prominence * 0.24; // offset 1.00 -- softer than the stroke rim below
  // SVG element ids must be unique per screen and stable across re-renders;
  // event_id already satisfies both, just sanitized of characters SVG ids
  // don't allow.
  const gradientId = `vgrad-${item.event_id.replace(/[^a-zA-Z0-9_-]/g, "_")}`;

  // Third pass (owner review of the second) added a second gradient shell,
  // three off-center "smoke lobe" blobs, a split two-layer bloom, and an
  // inner haze blob -- explicitly walked back (owner review of the third):
  // too many overlapping translucent layers, reading as a washed-out region
  // rather than a precise object, and the lobes/broadened bloom could bleed
  // into neighboring vessels' space. The opacity *profile* from the second
  // pass above (fixed-transparent center, prominence-scaled outer third) is
  // still right and untouched; this is back to the minimum set of distinct
  // layers that can carry "soft volumetric bubble" without reading as
  // stacked discs: one faint bloom outside the bubble, the single gradient
  // shell (its own 5-stop curve already carries transparent-center ->
  // subtle-inner -> stronger-outer, no second shell needed), and one
  // restrained rim stroke. No lobes, no separate haze, no split bloom.
  const bloom = dormantSize * (1.12 + prominence * 0.32);
  const bloomOpacity = 0.02 + prominence * 0.08;

  // Restrained -- defines the edge without becoming a hard perimeter line;
  // the gradient shell's own outer stops (above) carry most of that job.
  // Widened range (Sprint 3.6.5, see the gradient-opacity comment above).
  const rimOpacity = 0.14 + prominence * 0.26;

  const glowBoxSize = Math.max(bloom, readingWidth) + 40;

  const relatedCount = item.connected_event_ids.length;
  // STRATUS's own interpretation, not a second copy of "what happened" --
  // why_it_matters is a template concatenation of why_it_matters_to_me and
  // what_happened server-side, so it's deliberately not used here; using it
  // would just repeat WHAT CHANGED below.
  const stratusTake =
    item.delivered_item.why_it_matters_to_me?.trim() || item.delivered_item.why_it_matters?.trim();
  const lastUpdated = relativeTimeFrom(item.delivered_item.delivered_at);

  // Attention Gravity: position itself (posX/posY) is now the animated
  // part of this style, not a static left/top percentage -- see the class
  // comment. Combined with the existing drift wobble in one transform
  // (rather than a second wrapping Animated.View) since RN sums multiple
  // translateX/Y transform entries; host is centered on (posX,posY) via
  // the -glowBoxSize/2 offset here instead of host's own marginLeft/Top.
  const containerStyle = useAnimatedStyle(() => {
    const driftX = interpolate(drift.value, [-1, 1], [-5, 5]);
    const driftY = interpolate(drift.value, [-1, 1], [-7, 7]);
    return {
      // FIELD BIAS: a third multiplicative factor, same "recede but stay
      // visible" pattern as dimAnim just above -- 0.58 (not 0.85 like the
      // focused-card spotlight dim) is deliberately gentler, since a
      // bias-receded vessel is still meant to "provide context," not
      // disappear into the background the way the rest of the field does
      // once a card is open. Strengthened from 0.5 (Sprint 3.6.5
      // device-feedback pass: on a physical device the original effect read
      // as a slight highlight rather than a meaningful rebalance) -- still
      // well short of dimAnim's own 0.85, so a bias-receded vessel never
      // reads as strongly suppressed as one sitting behind an open card.
      opacity: entrance.value * (1 - dimAnim.value * 0.85) * (1 - biasRecedeAnim.value * 0.58),
      transform: [
        { translateX: posX.value - glowBoxSize / 2 + driftX },
        { translateY: posY.value - glowBoxSize / 2 + driftY },
      ],
    };
  });

  // Drives the gradient bubble itself (replaces the old tiny "core" dot's
  // coreStyle -- the whole bubble now breathes/pulses together, not just a
  // small inner point, since the gradient fill carries the visual weight
  // the stacked flat circles used to split across three layers).
  const bubbleStyle = useAnimatedStyle(() => {
    const breatheOpacity = interpolate(
      breath.value,
      [0, 1],
      [1 - instability * 0.12, 1 + instability * 0.12]
    );
    // Widened range (Sprint 3.6.5, see the gradient-opacity comment above)
    // -- the primary vessel's own priority pulse now reads more distinctly
    // against secondary/contextual ones.
    const pulseScale = interpolate(pulse.value, [0, 1], [1, 1 + 0.03 + prominence * 0.19]);
    const focusScale = interpolate(focusAnim.value, [0, 1], [1, 1.14]);
    const entranceScale = interpolate(entrance.value, [0, 0.6, 1], [0.3, 1.12, 1]);
    // FIELD BIAS: a small additional scale term, meaningfully smaller than
    // focusScale's 1.14 tap-to-open bump (1.10, not something that could
    // read as "this vessel was opened"). Strengthened from 1.06 (Sprint
    // 3.6.5 device-feedback pass: the original effect read as a slight
    // highlight rather than a meaningful rebalance) -- still bounded well
    // under a rank promotion's own effect, so a low-priority matching item
    // still can't out-scale a genuinely higher-ranked one.
    const biasEmphasisScale = interpolate(biasEmphasisAnim.value, [0, 1], [1, 1.1]);
    // New (Sprint 3.6.5): emphasis also lifts the breathing-opacity floor a
    // touch -- "clearer visibility"/"stronger visual definition" without a
    // second, separate brightness concept. Reuses this file's existing
    // breathing-opacity mechanism (values >1 clamp to fully opaque, same as
    // every other opacity style here) rather than adding new animated SVG
    // stop/stroke opacity plumbing for a modest, bounded effect.
    const biasDefinitionBoost = 1 + biasEmphasisAnim.value * 0.08;
    return {
      opacity: breatheOpacity * biasDefinitionBoost,
      transform: [
        { scale: entranceScale },
        { scale: pulseScale },
        { scale: focusScale },
        { scale: biasEmphasisScale },
      ],
    };
  });

  const echoRingStyle = useAnimatedStyle(() => ({
    opacity: interpolate(echoSignal.value, [0, 0.15, 1], [0, 0.55, 0]),
    transform: [{ scale: interpolate(echoSignal.value, [0, 1], [0.7, 2.1]) }],
  }));

  const restLabelStyle = useAnimatedStyle(() => ({
    opacity:
      interpolate(disclosureAnim.value, [0, 0.3], [1, 0], Extrapolation.CLAMP) *
      (1 - dimAnim.value * 0.95),
  }));

  // The card detaches toward a safe on-screen position as it grows (see the
  // class comment above); at disclosure 0 the offset is fully zero, so a
  // dormant vessel's card-shell-to-be sits exactly at its natural glow
  // position until it actually starts expanding.
  const cardPositionStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: cardOffsetX * disclosureAnim.value },
      { translateY: cardOffsetY * disclosureAnim.value },
    ],
  }));

  const cardShellStyle = useAnimatedStyle(() => {
    const dormant = dormantSize * 0.72;
    return {
      width: interpolate(disclosureAnim.value, [0, 1], [dormant, readingWidth]),
      height: interpolate(disclosureAnim.value, [0, 1], [dormant, cardHeight]),
      borderRadius: interpolate(disclosureAnim.value, [0, 1], [dormant / 2, 28]),
      borderColor: symbol.color,
      borderWidth: interpolate(disclosureAnim.value, [0, 1], [0, 1.5]),
    };
  });

  const frostStyle = useAnimatedStyle(() => ({
    opacity: interpolate(disclosureAnim.value, [0, 0.4], [0, 1], Extrapolation.CLAMP),
  }));

  const headerStyle = useAnimatedStyle(() => ({
    opacity: interpolate(disclosureAnim.value, [0.15, 0.5], [0, 1], Extrapolation.CLAMP),
  }));

  const headlineStyle = useAnimatedStyle(() => ({
    opacity: interpolate(disclosureAnim.value, [0.3, 0.65], [0, 1], Extrapolation.CLAMP),
  }));

  const detailStyle = useAnimatedStyle(() => ({
    opacity: interpolate(disclosureAnim.value, [0.55, 1], [0, 1], Extrapolation.CLAMP),
  }));

  const touchPad = Math.max(0, (MIN_TOUCH_TARGET - dormantSize * 0.72) / 2);

  return (
    <Animated.View
      style={[
        styles.host,
        {
          left: 0,
          top: 0,
          width: glowBoxSize,
          height: glowBoxSize,
        },
        containerStyle,
      ]}
      pointerEvents="box-none"
    >
      {/* The glow -- always present, never text-bearing. This is Logan
          reasoning about this entity whether or not it is being read. Stays
          at the vessel's natural field position even when the card (below)
          detaches for legibility.
          Sprint 3.6 (bubble-match pass, softened, then simplified back down
          -- see the constants block above): a soft volumetric bubble, built
          from the minimum number of distinct layers rather than several
          stacked translucent discs. Render order (back to front): one
          faint bloom, the interaction ripple, the single gradient shell
          (its own 5-stop curve carries transparent-center ->
          subtle-inner -> stronger-outer on its own), then the rim stroke
          on top. */}
      <View pointerEvents="none" style={styles.glowLayerHost}>
        <View
          style={[
            styles.glowRing,
            {
              width: bloom,
              height: bloom,
              borderRadius: bloom / 2,
              backgroundColor: symbol.color,
              opacity: bloomOpacity,
            },
          ]}
        />
        <Animated.View
          style={[
            styles.echoRing,
            {
              width: bubbleSize * 0.66,
              height: bubbleSize * 0.66,
              borderRadius: bubbleSize * 0.33,
              borderColor: symbol.color,
            },
            echoRingStyle,
          ]}
        />
        <Animated.View style={[{ width: bubbleSize, height: bubbleSize }, bubbleStyle]}>
          <Svg width={bubbleSize} height={bubbleSize}>
            <Defs>
              {/* Concentric, not off-center -- the reference reads as a
                  hollow, evenly transparent middle with a "smoke" ring
                  thickening toward the edge, not a directional highlight.
                  r="100%" (not a smaller fraction) so each Stop's offset
                  maps directly to a fraction of the bubble's true radius --
                  otherwise SVG pads the last stop's color flat across
                  whatever radius is left outside r, which would flatten
                  exactly the outer-third gradation this profile depends on. */}
              <RadialGradient id={gradientId} cx="50%" cy="50%" r="100%">
                <Stop offset="0" stopColor={symbol.color} stopOpacity={gradientCenterOpacity} />
                <Stop offset="0.35" stopColor={symbol.color} stopOpacity={gradientInnerOpacity} />
                <Stop
                  offset="0.6"
                  stopColor={symbol.color}
                  stopOpacity={gradientTransitionOpacity}
                />
                <Stop offset="0.8" stopColor={symbol.color} stopOpacity={gradientOuterOpacity} />
                <Stop offset="1" stopColor={symbol.color} stopOpacity={gradientRimFillOpacity} />
              </RadialGradient>
            </Defs>
            <Circle
              cx={bubbleSize / 2}
              cy={bubbleSize / 2}
              r={bubbleSize / 2 - 1}
              fill={`url(#${gradientId})`}
            />
            <Circle
              cx={bubbleSize / 2}
              cy={bubbleSize / 2}
              r={bubbleSize / 2 - 1}
              fill="none"
              stroke={symbol.color}
              strokeWidth={0.9}
              strokeOpacity={rimOpacity}
            />
          </Svg>
        </Animated.View>
      </View>

      {/* Persistent resting-state identity -- so the field never reads as a
          collection of anonymous glowing dots. V3.1.4.2 brand correction
          pass: dropped the descriptor line entirely (the reference shows no
          vessel, including the most prominent one, with descriptor text at
          rest) -- identity + confidence tier only. Prominence is carried by
          glow size/brightness alone, not by how much text a vessel gets.
          "none" is reserved for feed sizes well beyond what's been designed
          for. Fades out as this vessel grows into its own card.
          Sprint 3.6 (bubble-match pass): this used to sit just below the
          glow (`top` computed from dormantSize/glowBoxSize) -- the owner's
          reference shows it centered inside the bubble instead. Filling the
          whole host and centering with flexbox (rather than a fixed `top`
          offset) puts it at the host's true center, which is also the
          bubble's center, regardless of glowBoxSize's own padding. */}
      {layout.labelTier !== "none" && (
        <Animated.View pointerEvents="none" style={[styles.restLabel, restLabelStyle]}>
          {/* Owner reference (Field Bias mockup, Sprint 3.6): name + real
              confidence percentage + a short real-data reason tag. Sprint
              3.6 deliberately dropped a per-vessel icon badge here -- a
              ticker/name badge repeating the name text right next to it
              (the previous EntitySymbol-in-a-circle treatment) read as
              redundant. Bubble-polish pass (V3.1.4.3) reintroduced it
              inline before the name; Sprint 3.6.5 device-feedback pass
              moved it to its own centered row above the name instead (icon
              / name / confidence% / descriptor stack) and sized it up --
              on a physical device the inline treatment read as incidental
              rather than intentional. Still restrained: moderately larger
              and centered, but reduced-opacity (restLabelIconWrap) so it
              stays subordinate to the name below it, not a badge. `symbol`
              is computed once for the whole vessel (used by the glow/rim
              colors above and the opened card's header below too) and
              reused here, not re-resolved. `maxWidth` is derived from this
              vessel's own bubble diameter via LABEL_WIDTH_FRACTION -- the
              same fraction attentionLayout.ts's minDiameterForLabel used to
              grow this vessel's `size` in the first place, so ordinarily
              the text already fits with room to spare. numberOfLines/
              ellipsis below is only a last-resort safety net (e.g.
              unusually long real content beyond what the sizing heuristic
              estimated for), not the primary mechanism -- growing the
              bubble is. */}
          <View
            style={{
              maxWidth: Math.max(44, bubbleSize * LABEL_WIDTH_FRACTION),
              alignItems: "center",
            }}
          >
            <View style={styles.restLabelIconWrap}>
              <EntitySymbol
                symbol={symbol}
                size={layout.labelTier === "compact" ? COMPACT_NAME_ICON_SIZE : FULL_NAME_ICON_SIZE}
              />
            </View>
            <Text
              style={[
                styles.restLabelName,
                layout.labelTier === "compact" && styles.restLabelNameCompact,
              ]}
              numberOfLines={1}
            >
              {item.ticker ?? item.display_name}
            </Text>
            <Text
              style={[
                styles.restLabelPct,
                { color: symbol.color },
                layout.labelTier === "compact" && styles.restLabelPctCompact,
              ]}
            >
              {Math.round(item.confidence_score * 100)}%
            </Text>
            <Text
              style={[
                styles.restLabelDescriptor,
                layout.labelTier === "compact" && styles.restLabelDescriptorCompact,
              ]}
              numberOfLines={1}
            >
              {humanizeSignalType(item.signal_type)}
            </Text>
          </View>
        </Animated.View>
      )}

      <Animated.View style={cardPositionStyle}>
        {/* Sprint 3.6 device retest: this Pressable used to wrap the entire
            card, including the detail body's ScrollView below. An ancestor
            Pressable claims the JS touch responder on touch-down (so it can
            track its own press feedback) before a nested ScrollView's
            native scroll gesture recognizer ever gets a chance to activate
            -- a well-documented RN failure mode for "Touchable wraps
            ScrollView" (the mirror image of the PanResponder-wraps-
            Pressable fix already applied at the field level in
            AttentionField.tsx). The flex:1 sizing fix alone couldn't have
            fixed this: the ScrollView was correctly sized, it just never
            received the gesture.
            The fix: `disabled` while the card is open. A disabled Pressable
            doesn't attach its responder, so touches fall through to
            whatever's actually underneath -- the ScrollView included --
            instead of being intercepted here first. It stays enabled while
            dormant (disclosure 0) so tapping the small resting glow still
            opens the card; the header/headline Pressable just below takes
            over "tap to close" duty once open, since it never overlaps the
            scrollable area. */}
        <Pressable
          onPress={onPress}
          disabled={disclosure !== 0}
          hitSlop={{ top: touchPad, bottom: touchPad, left: touchPad, right: touchPad }}
          style={styles.pressable}
          accessibilityRole="button"
          accessibilityLabel={`${item.display_name}: ${item.delivered_item.headline}`}
          accessibilityHint="Opens the opportunity card"
          accessibilityState={{ expanded: disclosure > 0, selected: isFocused }}
        >
          <Animated.View style={[cardShellStyle, styles.cardShell]}>
            <Animated.View style={[StyleSheet.absoluteFill, frostStyle]}>
              <BlurView intensity={80} tint="dark" style={StyleSheet.absoluteFill} />
              {/* Solid scrim under a subtle color tint: round 2 (real-device
                  screenshots) found blur alone too transparent against a
                  moving Atmosphere behind it -- this guarantees a dark,
                  readable base regardless of what's behind it, while the
                  gradient still carries a whisper of the entity's color. */}
              <View style={[StyleSheet.absoluteFill, styles.scrim]} />
              <LinearGradient
                colors={[symbol.color + "14", "transparent"]}
                start={{ x: 0.1, y: 0.05 }}
                end={{ x: 0.7, y: 0.6 }}
                style={StyleSheet.absoluteFill}
              />
              <View style={styles.content}>
                <Pressable
                  onPress={onPress}
                  hitSlop={10}
                  style={styles.closeButton}
                  accessibilityRole="button"
                  accessibilityLabel="Close"
                >
                  <Ionicons name="close" size={16} color={theme.textSecondary} />
                </Pressable>

                {/* Sprint 3.6 device retest: takes over "tap to close" from
                    the outer Pressable once the card is open (disabled
                    while dormant, mirroring the outer one, so exactly one
                    of the two is ever active -- avoids two overlapping
                    tap targets with contradictory accessibility hints).
                    Deliberately stops at the headline, above
                    detailBodyWrap -- it must never extend over the
                    scrollable area below. */}
                <Pressable
                  onPress={onPress}
                  disabled={disclosure === 0}
                  accessibilityRole="button"
                  accessibilityLabel={`${item.display_name}: ${item.delivered_item.headline}`}
                  accessibilityHint="Closes the opportunity card"
                  accessibilityState={{ expanded: disclosure > 0, selected: isFocused }}
                >
                  <Animated.View style={[styles.headerRow, headerStyle]}>
                    <View style={styles.headerIdentity}>
                      {!!item.ticker && <Text style={styles.tickerLine}>{item.ticker}</Text>}
                      <View style={styles.headerNameRow}>
                        <EntitySymbol symbol={symbol} size={22} />
                        <Text style={styles.headerName} numberOfLines={1}>
                          {item.display_name}
                        </Text>
                      </View>
                      <View style={[styles.tierPill, { borderColor: symbol.color }]}>
                        <Text style={[styles.tierPillText, { color: symbol.color }]}>
                          CONFIDENCE · {Math.round(item.confidence_score * 100)}%
                        </Text>
                      </View>
                    </View>
                    <ConfidenceRing
                      score={item.confidence_score}
                      label={item.confidence_label}
                      color={symbol.color}
                      size={46}
                    />
                  </Animated.View>

                  <Animated.Text style={[styles.headline, headlineStyle]} numberOfLines={3}>
                    {item.delivered_item.headline}
                  </Animated.Text>
                </Pressable>

                {/* Sprint 3.6 (section 7 bug fix): this used to size the
                    ScrollView against a fixed estimate of the header/
                    headline's height (DETAIL_BODY_RESERVED). When real
                    content ran taller than that estimate, the ScrollView's
                    own rendered box extended past the card shell's clipped
                    bounds, cutting off the bottom of the scrollable area
                    itself -- not just scrolling past it. flex:1 always
                    fills exactly the real remaining space after the header/
                    headline lay out, however tall they actually are, so
                    every section stays reachable. The bottom fade is purely
                    a "there's more below" affordance, not scroll chrome. */}
                <View
                  style={styles.detailBodyWrap}
                  onLayout={(e) => setDetailContainerH(e.nativeEvent.layout.height)}
                >
                  <Animated.ScrollView
                    style={styles.detailBody}
                    showsVerticalScrollIndicator={false}
                    onContentSizeChange={(_, h) => setDetailContentH(h)}
                  >
                    <Animated.View style={detailStyle}>
                      {/* STRATUS TAKE / WHY IT MATTERS NOW / WHAT CHANGED (V3.1.4.2
                          brand pass): a "WATCH FOR" section -- 1-2 conditions that
                          would strengthen/weaken this opportunity -- was requested
                          too, but no field in the current DeliveredItem contract
                          backs it (confirmed against logan_core's actual schema,
                          not just the mobile type); omitted rather than fabricated.
                          See the completion report for the closest existing hook
                          (ConclusionConfidence.limiting_factors) that isn't wired
                          into this response yet. */}
                      {!!stratusTake && (
                        <View style={styles.section}>
                          <Text style={[styles.sectionLabel, { color: symbol.color }]}>
                            STRATUS TAKE
                          </Text>
                          <Text style={styles.sectionText}>{stratusTake}</Text>
                        </View>
                      )}

                      {!!item.delivered_item.why_now && (
                        <View style={styles.section}>
                          <Text style={[styles.sectionLabel, { color: symbol.color }]}>
                            WHY IT MATTERS NOW
                          </Text>
                          <Text style={styles.sectionText}>{item.delivered_item.why_now}</Text>
                        </View>
                      )}

                      {!!item.delivered_item.what_happened && (
                        <View style={styles.section}>
                          <Text style={[styles.sectionLabel, { color: symbol.color }]}>
                            WHAT CHANGED
                          </Text>
                          <Text style={styles.sectionText}>
                            {item.delivered_item.what_happened}
                          </Text>
                        </View>
                      )}

                      <RecommendationPanel
                        recommendation={item.delivered_item.recommendation}
                        color={symbol.color}
                      />

                      <View style={styles.metaRow}>
                        {relatedCount > 0 && (
                          <View style={styles.metaCell}>
                            <Text style={styles.metaLabel}>RELATED SIGNALS</Text>
                            <Text style={styles.metaValue}>{relatedCount}</Text>
                          </View>
                        )}
                        <View style={styles.metaCell}>
                          <Text style={styles.metaLabel}>LAST UPDATED</Text>
                          <Text style={styles.metaValue}>{lastUpdated}</Text>
                        </View>
                      </View>

                      {item.delivered_item.required_disclaimers.map((d) => (
                        <Text key={d} style={styles.disclaimerText}>
                          {d}
                        </Text>
                      ))}
                    </Animated.View>
                  </Animated.ScrollView>
                  {shouldShowOverflowFade(detailContentH, detailContainerH) && (
                    <LinearGradient
                      pointerEvents="none"
                      colors={["transparent", theme.background]}
                      style={styles.detailFade}
                    />
                  )}
                </View>
              </View>
            </Animated.View>
          </Animated.View>
        </Pressable>
      </Animated.View>
    </Animated.View>
  );
}

function stableDelay(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  return (hash % 900) + 60;
}

const styles = StyleSheet.create({
  host: { position: "absolute", alignItems: "center", justifyContent: "center" },
  glowLayerHost: { position: "absolute", alignItems: "center", justifyContent: "center" },
  glowRing: { position: "absolute" },
  echoRing: { position: "absolute", borderWidth: 1.5 },
  // V3.1.4.2 (real-device screenshot review): this relied on the parent
  // host's alignItems:"center" to horizontally center an absolutely
  // positioned child with no explicit `left`/`top` -- RN/Yoga does not
  // reliably apply cross-axis alignItems to position:"absolute" children
  // (CSS position:absolute is removed from flow and only respects
  // left/right/top/bottom/margin). Sprint 3.6 (bubble-match pass): the
  // label now sits centered *inside* the bubble (previously it hung just
  // below the glow) -- filling the host with inset 0 and centering via
  // flexbox on this (non-absolutely-positioned-relative-to-itself)
  // container works reliably, unlike the old single `left: "50%"` +
  // fixed-width + negative-margin approach, and needs no per-vessel size
  // constant to stay in sync with.
  restLabel: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: "center",
    justifyContent: "center",
  },
  // Owner reference (Field Bias mockup): name reads as the primary
  // identity, bold and legible, not the quiet instrument-label treatment
  // used for metadata elsewhere -- this is the one piece of vessel text
  // that's meant to be read at a glance, not just recognized peripherally.
  // Bubble-polish pass: fontSize 12 -> 14 and added tight `tracking.vessel`
  // letter-spacing (owner request: moderately larger resting-state name,
  // without competing with restLabelPct below it -- see that style's own
  // comment). Kept in sync with attentionLayout.ts's FULL_NAME_SIZE/
  // letter-spacing argument, which duplicates this on purpose (that file
  // can't measure real text, only estimate against these constants).
  restLabelName: {
    color: theme.text,
    fontSize: 14,
    fontFamily: font.heading,
    letterSpacing: tracking.vessel,
  },
  // fontSize 10 -> 11, not 12 -- see attentionLayout.ts's COMPACT_NAME_SIZE
  // comment for why 12 (the original bubble-polish spec value) was walked
  // back a point: it landed only 1pt under restLabelPctCompact's 13,
  // reading as ambiguous with the percentage that's meant to stay the
  // clear headline number. No letter-spacing at this size -- tight tracking
  // reads fine at 14px but starts to fight legibility this small.
  restLabelNameCompact: { fontSize: 11, opacity: 0.9 },
  // Sprint 3.6.5: the icon now sits in its own centered row above the name
  // (see the resting-label JSX above) rather than inline before it, so this
  // is just a bottom-margin wrapper, not a row layout -- the parent View's
  // own `alignItems: "center"` centers it horizontally. Opacity keeps it
  // visually subordinate to the name below -- size alone (FULL_NAME_ICON_SIZE/
  // COMPACT_NAME_ICON_SIZE above) wasn't enough on its own in earlier
  // per-vessel badge treatments (see the JSX comment above for why a badge
  // treatment was removed once already); slightly higher than the previous
  // inline treatment's 0.75 since the larger Sprint 3.6.5 icon size reads as
  // washed-out at that opacity, but still clearly quieter than the name.
  restLabelIconWrap: {
    marginBottom: ICON_NAME_GAP,
    opacity: 0.82,
  },
  // The confidence percentage is real data (confidence_score), shown
  // up-front on the field itself rather than only after opening the card --
  // large and in the vessel's category color so it reads as the headline
  // number, with tabular figures so the digit width doesn't shift as
  // different vessels show different values.
  restLabelPct: {
    fontSize: 17,
    fontFamily: font.heading,
    fontVariant: ["tabular-nums"],
    marginTop: 1,
  },
  restLabelPctCompact: { fontSize: 13 },
  // The reason tag: real signal_type (see lib/signalType.ts), not a
  // hand-authored phrase -- quietest text on the vessel, instrument-label
  // treatment (small, wide-tracked, muted), subordinate to both the name
  // and the percentage above it.
  restLabelDescriptor: {
    color: theme.muted,
    fontSize: 7.5,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
    marginTop: 2,
    opacity: 0.85,
  },
  restLabelDescriptorCompact: { fontSize: 6.5, opacity: 0.65 },
  pressable: { alignItems: "center", justifyContent: "center" },
  cardShell: { overflow: "hidden" },
  scrim: { backgroundColor: theme.background, opacity: 0.88 },
  content: { flex: 1, padding: 20, justifyContent: "flex-start" },
  closeButton: { position: "absolute", top: 12, right: 12, zIndex: 1, padding: 4 },
  headerRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    paddingRight: 24,
  },
  headerIdentity: { flexShrink: 1, gap: 6 },
  tickerLine: {
    color: theme.textSecondary,
    fontSize: 10,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
  },
  headerNameRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  headerName: { color: theme.text, fontFamily: font.heading, fontSize: 17, flexShrink: 1 },
  tierPill: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  tierPillText: { fontSize: 9, fontFamily: font.metadata, letterSpacing: tracking.metadata },
  headline: {
    color: theme.text,
    fontFamily: font.heading,
    fontSize: 20,
    lineHeight: 26,
    marginTop: 16,
  },
  // Sprint 3.6 (section 7 bug fix): flex:1 instead of a fixed maxHeight
  // computed from a header-height estimate -- see the call site's comment
  // for why the estimate could clip content on real devices.
  detailBodyWrap: { flex: 1, marginTop: 18 },
  detailBody: { flex: 1 },
  detailFade: { position: "absolute", left: 0, right: 0, bottom: 0, height: 28 },
  section: { marginBottom: 12 },
  sectionLabel: {
    fontSize: type.micro,
    fontFamily: font.metadata,
    letterSpacing: tracking.label,
    marginBottom: 4,
  },
  sectionText: { color: theme.textSecondary, fontSize: 13, fontFamily: font.body, lineHeight: 19 },
  metaRow: {
    flexDirection: "row",
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: theme.border,
    marginTop: 4,
    paddingTop: 12,
    gap: 22,
  },
  metaCell: { gap: 3 },
  metaLabel: {
    color: theme.muted,
    fontSize: 9,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
  },
  metaValue: { color: theme.textSecondary, fontSize: 12, fontFamily: font.bodyMedium },
  disclaimerText: {
    color: theme.muted,
    fontSize: type.micro,
    fontFamily: font.body,
    lineHeight: 15,
    marginTop: spacing.sm,
  },
});
