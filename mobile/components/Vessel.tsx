import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";
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
import { VesselLayout } from "../lib/attentionLayout";
import { FeedItem } from "../types/loganFeed";

const MIN_TOUCH_TARGET = 44;
// Shared with AttentionField.tsx's viewport-clamp math (round 2, real-device
// screenshot review: the card could render partially off-screen for vessels
// near the field's edges since it grew symmetrically from the vessel's own
// anchor). Exported so both files stay in sync instead of duplicating magic
// numbers.
export const CARD_HEIGHT = 372;
export const CARD_SAFE_MARGIN = 16;

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

  const entrance = useSharedValue(0);
  const drift = useSharedValue(0);
  const breath = useSharedValue(0);
  const pulse = useSharedValue(0);
  const disclosureAnim = useSharedValue(0);
  const focusAnim = useSharedValue(isFocused ? 1 : 0);
  const dimAnim = useSharedValue(0);

  // Condensation: this vessel did not simply appear -- it accreted, starting
  // diffuse and settling. Staggered per entity so the whole field doesn't
  // form in unison.
  useEffect(() => {
    if (reducedMotion) {
      entrance.value = 1;
      return;
    }
    const delay = stableDelay(item.event_id);
    entrance.value = withDelay(delay, withSpring(1, { damping: 11, stiffness: 90 }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reducedMotion]);

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
  // radius) already scales down for them. Opacity and outer-ring radius now
  // both scale with `prominence` (0..1, rank-derived, already computed by
  // attentionLayout.ts) so the strongest bloom is reserved for the
  // highest-attention vessels and secondary vessels recede toward true
  // negative space instead of contributing an equally-bright halo.
  const outer = dormantSize * (1.0 + prominence * 0.3);
  const mid = dormantSize * (0.5 + prominence * 0.16);
  const core = dormantSize * 0.3;
  const outerOpacity = 0.05 + prominence * 0.13;
  const midOpacity = 0.18 + prominence * 0.32;
  const coreOpacityBase = 0.26 + prominence * 0.2;
  const glowBoxSize = Math.max(outer, readingWidth) + 40;

  const relatedCount = item.connected_event_ids.length;
  // STRATUS's own interpretation, not a second copy of "what happened" --
  // why_it_matters is a template concatenation of why_it_matters_to_me and
  // what_happened server-side, so it's deliberately not used here; using it
  // would just repeat WHAT CHANGED below.
  const stratusTake =
    item.delivered_item.why_it_matters_to_me?.trim() || item.delivered_item.why_it_matters?.trim();
  const lastUpdated = relativeTimeFrom(item.delivered_item.delivered_at);

  const containerStyle = useAnimatedStyle(() => {
    const translateX = interpolate(drift.value, [-1, 1], [-5, 5]);
    const translateY = interpolate(drift.value, [-1, 1], [-7, 7]);
    return {
      opacity: entrance.value * (1 - dimAnim.value * 0.85),
      transform: [{ translateX }, { translateY }],
    };
  });

  const coreStyle = useAnimatedStyle(() => {
    const coreOpacity = interpolate(
      breath.value,
      [0, 1],
      [coreOpacityBase * (1 - instability * 0.45), coreOpacityBase * (1 + instability * 0.45)]
    );
    const pulseScale = interpolate(pulse.value, [0, 1], [1, 1 + 0.05 + prominence * 0.14]);
    const focusScale = interpolate(focusAnim.value, [0, 1], [1, 1.14]);
    const entranceScale = interpolate(entrance.value, [0, 0.6, 1], [0.3, 1.12, 1]);
    return {
      opacity: coreOpacity,
      transform: [{ scale: entranceScale }, { scale: pulseScale }, { scale: focusScale }],
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
          left: `${layout.x * 100}%`,
          top: `${layout.y * 100}%`,
          width: glowBoxSize,
          height: glowBoxSize,
          marginLeft: -glowBoxSize / 2,
          marginTop: -glowBoxSize / 2,
        },
        containerStyle,
      ]}
      pointerEvents="box-none"
    >
      {/* The glow -- always present, never text-bearing. This is Logan
          reasoning about this entity whether or not it is being read. Stays
          at the vessel's natural field position even when the card (below)
          detaches for legibility. */}
      <View pointerEvents="none" style={styles.glowLayerHost}>
        <View
          style={[
            styles.glowRing,
            {
              width: outer,
              height: outer,
              borderRadius: outer / 2,
              backgroundColor: symbol.color,
              opacity: outerOpacity,
            },
          ]}
        />
        <View
          style={[
            styles.glowRing,
            {
              width: mid,
              height: mid,
              borderRadius: mid / 2,
              backgroundColor: symbol.color,
              opacity: midOpacity,
            },
          ]}
        />
        <Animated.View
          style={[
            styles.echoRing,
            {
              width: core * 2.2,
              height: core * 2.2,
              borderRadius: core * 1.1,
              borderColor: symbol.color,
            },
            echoRingStyle,
          ]}
        />
        <Animated.View
          style={[
            styles.glowCore,
            {
              width: core,
              height: core,
              borderRadius: core / 2,
              backgroundColor: symbol.color,
              shadowColor: symbol.color,
              shadowRadius: core,
            },
            coreStyle,
          ]}
        />
      </View>

      {/* Persistent resting-state identity -- so the field never reads as a
          collection of anonymous glowing dots. V3.1.4.2 brand correction
          pass: dropped the descriptor line entirely (the reference shows no
          vessel, including the most prominent one, with descriptor text at
          rest) -- identity + confidence tier only. Prominence is carried by
          glow size/brightness alone, not by how much text a vessel gets.
          "none" is reserved for feed sizes well beyond what's been designed
          for. Fades out as this vessel grows into its own card. */}
      {layout.labelTier !== "none" && (
        <Animated.View
          pointerEvents="none"
          style={[
            styles.restLabel,
            { top: `${50 + (dormantSize * 0.72 * 50) / glowBoxSize}%` },
            restLabelStyle,
          ]}
        >
          {/* Owner reference (Field Bias mockup, Sprint 3.6): name + real
              confidence percentage + a short real-data reason tag, no icon
              badge -- a ticker/name badge repeating the name text right
              next to it (the previous EntitySymbol-in-a-circle treatment)
              was redundant, and the reference's own cleanest vessels show
              plain text with no icon at all. EntitySymbol itself is
              untouched and still used in the opened card's header below. */}
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
  glowCore: {
    position: "absolute",
    shadowOpacity: 0.9,
    shadowOffset: { width: 0, height: 0 },
    elevation: 1,
  },
  // V3.1.4.2 (real-device screenshot review): this relied on the parent
  // host's alignItems:"center" to horizontally center an absolutely
  // positioned child with no explicit `left` -- RN/Yoga does not reliably
  // apply cross-axis alignItems to position:"absolute" children (CSS
  // position:absolute is removed from flow and only respects left/right/
  // margin), so the label centered inconsistently depending on host width.
  // `left: "50%"` makes centering on the host's true center explicit.
  // Widened (100 -> 118) for the new three-line content (name, percentage,
  // descriptor) -- trimmed down from an initial 132 estimate; that didn't
  // leave the highest-priority vessels' tightly-packed inner radius band
  // (large glows, close together by design) enough room to also satisfy
  // this much label footprint. Must stay in sync with
  // lib/attentionLayout.ts's LABEL_WIDTH/FULL_LABEL_HEIGHT/
  // COMPACT_LABEL_HEIGHT or the collision math under-reserves real space.
  restLabel: {
    position: "absolute",
    left: "50%",
    alignItems: "center",
    width: 118,
    marginLeft: -59,
  },
  // Owner reference (Field Bias mockup): name reads as the primary
  // identity, bold and legible, not the quiet instrument-label treatment
  // used for metadata elsewhere -- this is the one piece of vessel text
  // that's meant to be read at a glance, not just recognized peripherally.
  restLabelName: {
    color: theme.text,
    fontSize: 12,
    fontFamily: font.heading,
  },
  restLabelNameCompact: { fontSize: 10, opacity: 0.9 },
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
