import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Modal,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import Animated, {
  Easing,
  interpolate,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
} from "react-native-reanimated";

import { font, radius, spacing, theme, tracking, type } from "../constants/theme";
import { AttentionField, OpenRequest } from "../components/AttentionField";
import { FieldBiasControl } from "../components/FieldBiasControl";
import { PressableScale } from "../components/PressableScale";
import { fetchJson } from "../lib/apiClient";
import { FieldBias } from "../lib/fieldBias";
import { OpportunitiesResponse } from "../types/loganFeed";

// Sprint 3.6 device retest: the Attention Field header and the menu drawer
// header both now render the owner-approved STRATUS wordmark artwork
// directly (a cropped, alpha-matted PNG -- see
// assets/images/stratus-wordmark-header.png) instead of the hand-coded SVG
// letterforms StratusWordmark.tsx draws. The owner was explicit: stop
// approximating this through text/font/letter geometry and use the
// approved artwork as-is. The About screen moved to the same asset in a
// later round too (see about.tsx) -- StratusWordmark.tsx itself is no
// longer imported anywhere in the app, but left in place rather than
// deleted unasked.
const HEADER_LOGO_SOURCE = require("../assets/images/stratus-wordmark-header.png");
// Sized by width, not height: the asset's own glow/padding means driving it
// by a fixed height let the surrounding bloom dictate how big the mark felt,
// making it read as a glowing banner rather than a wordmark. Width is what
// actually communicates "how big is STRATUS" here -- height just follows
// whatever the artwork's real proportions require.
const HEADER_LOGO_WIDTH = 132;
// Device retest (round 2): the first crop (1536x480) kept a wide, faint
// outer bloom that read as "washed out" once actually on-screen -- retook
// the crop tighter (1536x310) and raised the alpha curve's black point so
// faint haze drops to fully transparent instead of a long soft gray tail.
// Aspect ratio must track the asset's real crop dimensions or `contain`
// will letterbox rather than fill the intended width.
const HEADER_LOGO_ASPECT_RATIO = 1536 / 310;

// The menu drawer footer's horizon/sun mark, above "POWERED BY LGI" -- the
// same approved artwork already shipped for Ask STRATUS's first-run state
// (see ask.tsx), not the hand-coded HorizonMark.tsx arc. First shipped at
// 30 (matching the previous HorizonMark size={30} footprint exactly), then
// bumped up twice on the owner's follow-up feedback -- "POWERED BY LGI"
// text below it is untouched, only the mark itself got bigger.
const MENU_HORIZON_MARK_SOURCE = require("../assets/images/stratus-horizon-mark.png");
const MENU_HORIZON_MARK_ASPECT_RATIO = 1512 / 430;
const MENU_HORIZON_MARK_WIDTH = 62;
const HEADER_LOGO_HEIGHT = HEADER_LOGO_WIDTH / HEADER_LOGO_ASPECT_RATIO;

type FeedState =
  | { kind: "loading" }
  | { kind: "loaded"; response: OpportunitiesResponse }
  | { kind: "empty" }
  | { kind: "timeout" }
  | { kind: "error"; message: string };

// The header dot's notification badge. Driven by the backend's real
// `is_new_for_user` field (see types/loganFeed.ts's FeedItem comment) --
// process-lifetime/in-memory on the server, not durable across a backend
// restart, but a genuine "is this new to this user" signal rather than the
// earlier client-side event_id-diffing workaround. Just enough shown here
// to say what changed: name and confidence, nothing fabricated.
type OpportunityNotification = {
  eventId: string;
  name: string;
  confidencePct: number;
};

const NOTIFICATION_POLL_INTERVAL_MS = 60000;

// The badge's width is computed here rather than left to flexbox: this
// absolutely-positioned, `right`-anchored box wasn't reliably auto-sizing
// to its Text content either direction (a fixed height clipped two-digit
// counts; removing it to let padding drive width instead made the digits
// wrap vertically in an unexpectedly narrow box). Computing an explicit
// width from the actual digit count sidesteps that entirely.
function notifBadgeWidth(count: number): number {
  const digits = String(count).length;
  return Math.max(16, 10 + digits * 6);
}

// V3.1.4.1 (Sprint 3.5 usability pass): the menu used to be a flat list of
// legacy/prototype screens with no consumer-facing structure. Split into a
// small, honest consumer menu (only real destinations, or destinations
// clearly marked not-yet-available -- never a fake link that goes nowhere)
// and a single __DEV__-gated "Developer / Diagnostics" row, which opens its
// own dedicated screen (app/dev-diagnostics.tsx) rather than inlining
// legacy screens/backend status directly in the drawer (round 2, real-
// device screenshot review: that inline content dominated the menu).
type ConsumerItem = {
  label: string;
  href?: "/ask" | "/about";
  soon?: boolean;
};

const ATTENTION_ITEMS: ConsumerItem[] = [
  { label: "Saved", soon: true },
  { label: "Reminders", soon: true },
];

const YOUR_STRATUS_ITEMS: ConsumerItem[] = [
  { label: "Ask STRATUS", href: "/ask" },
  { label: "About STRATUS", href: "/about" },
  { label: "Settings", soon: true },
];

function MenuRow({ item, onNavigate }: { item: ConsumerItem; onNavigate: () => void }) {
  return (
    <Pressable
      style={styles.menuItem}
      disabled={item.soon}
      onPress={() => {
        if (!item.href) return;
        onNavigate();
        router.push(item.href);
      }}
      accessibilityRole="button"
      accessibilityLabel={item.soon ? `${item.label}, coming soon` : item.label}
      accessibilityState={{ disabled: item.soon }}
    >
      <Text style={[styles.menuItemText, item.soon && styles.menuItemTextSoon]}>{item.label}</Text>
      {item.soon ? (
        <View style={styles.soonPill}>
          <Text style={styles.soonPillText}>SOON</Text>
        </View>
      ) : (
        <Ionicons name="chevron-forward" size={16} color={theme.textSecondary} />
      )}
    </Pressable>
  );
}

// STRATUS's home screen (the Attention Field, powered by LGI). One opportunity
// held in clear focus, everything else STRATUS is tracking present only as
// soft, ambient light around it. Swipe, or touch a glow directly, to bring
// something else into focus.
export default function AttentionFieldScreen() {
  const [state, setState] = useState<FeedState>({ kind: "loading" });
  const [menuOpen, setMenuOpen] = useState(false);
  // FIELD BIAS: a temporary presentation lens over the Attention Field, not
  // a filter/screen/permanent preference -- see lib/fieldBias.ts and
  // FieldBiasControl.tsx. Local UI state only, never persisted; resets to
  // "all" on a fresh screen mount by design.
  const [fieldBias, setFieldBias] = useState<FieldBias>("all");

  // Header "live" dot: a slow, constant size pulse -- purely decorative
  // (see liveDot's own accessibility props below), same breathing sine-ease
  // pattern Vessel.tsx uses elsewhere in the app rather than a new motion
  // language. Skips animating entirely under the OS's Reduce Motion setting.
  const liveDotPulse = useSharedValue(0);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (reducedMotion) {
      liveDotPulse.value = 0;
      return;
    }
    const ease = Easing.inOut(Easing.sin);
    // Slowed from 1600ms/leg (3.2s full cycle) to 2600ms/leg (5.2s) -- the
    // faster version read as a glitch/flicker rather than a calm pulse.
    // Was a manually chained withSequence(grow, shrink) repeated via
    // withRepeat(..., false) -- that combination snapped back to "large" at
    // the loop boundary instead of continuing the shrink smoothly.
    // withRepeat's own `reverse: true` ping-pongs a single withTiming back
    // to its start automatically, which is the idiomatic way to avoid that
    // seam.
    liveDotPulse.value = withRepeat(withTiming(1, { duration: 2600, easing: ease }), -1, true);
  }, [liveDotPulse, reducedMotion]);

  const liveDotStyle = useAnimatedStyle(() => ({
    transform: [{ scale: interpolate(liveDotPulse.value, [0, 1], [1, 1.5]) }],
  }));

  const loadFeed = useCallback(async (signal: AbortSignal) => {
    setState({ kind: "loading" });
    const result = await fetchJson<OpportunitiesResponse>("/v1/opportunities", { signal });
    switch (result.status) {
      case "success":
        setState(
          result.data.items.length > 0
            ? { kind: "loaded", response: result.data }
            : { kind: "empty" }
        );
        return;
      case "timeout":
        setState({ kind: "timeout" });
        return;
      case "aborted":
        // Screen unmounted or a new load superseded this one -- no state update.
        return;
      case "error":
        setState({ kind: "error", message: result.message });
        return;
    }
  }, []);

  // Cancels the in-flight request if the screen unmounts before it resolves,
  // instead of calling setState on an unmounted component.
  const controllerRef = useRef<AbortController | null>(null);

  const startLoad = useCallback(() => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    loadFeed(controller.signal);
  }, [loadFeed]);

  useEffect(() => {
    startLoad();
    return () => controllerRef.current?.abort();
  }, [startLoad]);

  // Background poll so new opportunities can actually be noticed while the
  // screen is open -- without this, the feed only ever loads once (or on
  // manual retry). Deliberately quiet: a failed/timed-out poll is ignored
  // rather than surfacing an error state (that's the manual loader's job,
  // on initial load and explicit retry), so a transient network hiccup here
  // never disrupts what's on screen.
  useEffect(() => {
    let cancelled = false;
    const interval = setInterval(async () => {
      const controller = new AbortController();
      const result = await fetchJson<OpportunitiesResponse>("/v1/opportunities", {
        signal: controller.signal,
      });
      if (cancelled || result.status !== "success") return;
      setState(
        result.data.items.length > 0 ? { kind: "loaded", response: result.data } : { kind: "empty" }
      );
    }, NOTIFICATION_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Notification badge: `unread` is derived directly from the backend's
  // `is_new_for_user` flag on each currently-fetched item (see
  // types/loganFeed.ts) -- no client-side ID-diffing/accumulation anymore.
  // `locallyReviewedIds` is a purely optimistic overlay: opening the
  // dropdown marks its contents reviewed with the backend (POST
  // /v1/notifications/review), but that only takes effect on the *next*
  // poll (up to 60s later); without this overlay the badge would
  // incorrectly reappear/stay visible until then. `devForcedIds` lets the
  // __DEV__ test button force a real, currently-displayed item to read as
  // unread on demand, without waiting on real backend timing (repeated
  // requests for the same underlying opportunity correctly stay quiet now
  // that the backend fix landed, so there's rarely a *naturally occurring*
  // new notification to test against during a short session).
  const [locallyReviewedIds, setLocallyReviewedIds] = useState<Set<string>>(new Set());
  const [devForcedIds, setDevForcedIds] = useState<Set<string>>(new Set());
  const [panelItems, setPanelItems] = useState<OpportunityNotification[] | null>(null);

  const unread = useMemo<OpportunityNotification[]>(() => {
    if (state.kind !== "loaded") return [];
    return state.response.items
      .filter(
        (item) =>
          (item.is_new_for_user || devForcedIds.has(item.event_id)) &&
          !locallyReviewedIds.has(item.event_id)
      )
      .map((item) => ({
        eventId: item.event_id,
        name: item.ticker ?? item.display_name,
        confidencePct: Math.round(item.confidence_score * 100),
      }));
  }, [state, devForcedIds, locallyReviewedIds]);

  const openNotifications = useCallback(() => {
    setPanelItems(unread);
    const eventIds = unread.map((n) => n.eventId);
    setLocallyReviewedIds((prev) => new Set([...prev, ...eventIds]));
    if (eventIds.length === 0) return;
    // Fire-and-forget: the optimistic local clear above already updated the
    // UI; if this fails, the badge may reappear on the next poll (the
    // backend never learned these were reviewed) -- acceptable for this
    // stage's in-memory backend state, not worth a retry/queue mechanism.
    // fetchJson never throws (see lib/apiClient.ts), so no catch needed.
    fetchJson("/v1/notifications/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_ids: eventIds }),
      retries: 0,
    });
  }, [unread]);

  // Tapping a notification closes the dropdown and asks the Attention
  // Field to open that vessel's card -- the same focus/disclosure state a
  // direct tap on the vessel itself would set (see AttentionField.tsx's
  // openRequest effect), so it's the identical open animation/position, not
  // a second card implementation.
  const [openRequest, setOpenRequest] = useState<OpenRequest | null>(null);
  const openNotificationCard = useCallback((eventId: string) => {
    setPanelItems(null);
    setOpenRequest({ eventId, token: Date.now() });
  }, []);

  // Dev-only test hook (__DEV__ -- stripped from production/TestFlight
  // builds, same gating as the existing Developer/Diagnostics menu row).
  // Forces a real, currently-displayed item to read as unread, rather than
  // inventing a fake event_id the way the pre-fix version of this button
  // had to -- so it exercises the actual open-card flow too, not just the
  // badge/dropdown chrome.
  const injectTestNotification = useCallback(() => {
    if (state.kind !== "loaded" || state.response.items.length === 0) return;
    const candidates = state.response.items.filter(
      (item) => !devForcedIds.has(item.event_id) && !unread.some((n) => n.eventId === item.event_id)
    );
    const pool = candidates.length > 0 ? candidates : state.response.items;
    const pick = pool[Math.floor(Math.random() * pool.length)];
    setDevForcedIds((prev) => new Set(prev).add(pick.event_id));
    setLocallyReviewedIds((prev) => {
      if (!prev.has(pick.event_id)) return prev;
      const next = new Set(prev);
      next.delete(pick.event_id);
      return next;
    });
  }, [state, devForcedIds, unread]);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.topbar}>
        {/* Sprint 3.6 device retest (round 2): the logo now sits truly
            centered in the header, with the live dot pinned to the right
            edge -- not grouped next to the hamburger as the previous round
            had it. `justifyContent:"space-between"` alone won't center the
            middle item precisely unless both bookends are the same width
            (the 22px hamburger icon and 5px dot aren't), so both sides use
            a fixed-width `topbarSide` column instead -- the center column's
            true midpoint then always lands on the row's true midpoint,
            regardless of how big the icon or dot are. */}
        <View style={styles.topbarSide}>
          <Pressable
            onPress={() => setMenuOpen(true)}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel="Menu"
            accessibilityHint="Opens the list of preserved screens"
          >
            <Ionicons name="menu" size={22} color={theme.textSecondary} />
          </Pressable>
        </View>
        <View style={styles.topbarCenter}>
          <Image
            source={HEADER_LOGO_SOURCE}
            resizeMode="contain"
            accessibilityRole="image"
            accessibilityLabel="STRATUS"
            style={styles.headerLogo}
          />
        </View>
        <View style={[styles.topbarSide, styles.topbarSideRight]}>
          <Pressable
            onPress={openNotifications}
            disabled={unread.length === 0}
            hitSlop={12}
            accessibilityRole="button"
            accessibilityLabel={
              unread.length > 0
                ? `${unread.length} new opportunity notification${unread.length === 1 ? "" : "s"}`
                : "No new opportunities"
            }
            accessibilityHint={unread.length > 0 ? "Opens the new opportunities list" : undefined}
          >
            <Animated.View style={[styles.liveDot, liveDotStyle]} />
            {unread.length > 0 && (
              <View
                style={[styles.notifBadge, { width: notifBadgeWidth(unread.length) }]}
                pointerEvents="none"
              >
                <Text style={styles.notifBadgeText} numberOfLines={1}>
                  {unread.length}
                </Text>
              </View>
            )}
          </Pressable>
        </View>
      </View>

      {state.kind === "loading" && (
        <View style={styles.centerFill} accessibilityLabel="Loading opportunities">
          <ActivityIndicator color={theme.accent} size="large" />
        </View>
      )}

      {state.kind === "error" && (
        <View style={styles.centerFill}>
          <View style={styles.error} accessibilityLiveRegion="polite">
            <Text style={styles.errorTitle}>Backend not connected</Text>
            <Text style={styles.errorText}>{state.message}</Text>
            <Text style={styles.errorText}>
              Start FastAPI and set your computer IP in constants/config.ts (or
              EXPO_PUBLIC_API_BASE_URL).
            </Text>
            <PressableScale
              style={styles.retryButton}
              onPress={startLoad}
              accessibilityLabel="Retry"
              accessibilityHint="Tries loading opportunities again"
            >
              <Text style={styles.retryText}>Retry</Text>
            </PressableScale>
          </View>
        </View>
      )}

      {state.kind === "timeout" && (
        <View style={styles.centerFill}>
          <View style={styles.error} accessibilityLiveRegion="polite">
            <Text style={styles.errorTitle}>Taking longer than expected</Text>
            <Text style={styles.errorText}>
              STRATUS didn&apos;t respond in time. Check that the backend is running and reachable.
            </Text>
            <PressableScale
              style={styles.retryButton}
              onPress={startLoad}
              accessibilityLabel="Retry"
              accessibilityHint="Tries loading opportunities again"
            >
              <Text style={styles.retryText}>Retry</Text>
            </PressableScale>
          </View>
        </View>
      )}

      {state.kind === "empty" && (
        <View style={styles.centerFill}>
          <View style={styles.error} accessibilityLiveRegion="polite">
            <Text style={styles.errorTitle}>Nothing to show yet</Text>
            <Text style={styles.errorText}>
              STRATUS isn&apos;t tracking any opportunities right now.
            </Text>
            <PressableScale
              style={styles.retryButton}
              onPress={startLoad}
              accessibilityLabel="Refresh"
              accessibilityHint="Checks again for opportunities"
            >
              <Text style={styles.retryText}>Refresh</Text>
            </PressableScale>
          </View>
        </View>
      )}

      {state.kind === "loaded" && (
        // FieldBiasControl is a fixed-height flex sibling *after* the field,
        // not an absolute overlay on top of it -- this way AttentionField's
        // own viewport-measurement/edge-padding logic (already height-
        // driven, see attentionLayout.ts's EDGE_PADDING) naturally keeps
        // vessels clear of the control with zero changes to that (locked)
        // layout solver.
        <View style={styles.fieldColumn}>
          <AttentionField
            items={state.response.items}
            openRequest={openRequest}
            fieldBias={fieldBias}
          />
          <FieldBiasControl value={fieldBias} onChange={setFieldBias} />
        </View>
      )}

      {__DEV__ && (
        <Pressable
          onPress={injectTestNotification}
          style={styles.devNotifButton}
          accessibilityRole="button"
          accessibilityLabel="Dev: inject a test notification"
        >
          <Text style={styles.devNotifButtonText}>DEV +1 NOTIF</Text>
        </Pressable>
      )}

      <Modal
        visible={menuOpen}
        animationType="fade"
        transparent
        onRequestClose={() => setMenuOpen(false)}
      >
        <Pressable
          style={styles.menuBackdrop}
          onPress={() => setMenuOpen(false)}
          accessibilityRole="button"
          accessibilityLabel="Close menu"
        >
          <View style={styles.menuCard}>
            <View style={styles.menuHeaderRow}>
              <Image
                source={HEADER_LOGO_SOURCE}
                resizeMode="contain"
                accessibilityRole="image"
                accessibilityLabel="STRATUS"
                style={styles.headerLogo}
              />
              <Pressable
                onPress={() => setMenuOpen(false)}
                hitSlop={10}
                accessibilityRole="button"
                accessibilityLabel="Close menu"
              >
                <Ionicons name="close" size={18} color={theme.textSecondary} />
              </Pressable>
            </View>

            <Text style={styles.menuSectionLabel}>ATTENTION</Text>
            <Pressable
              style={styles.menuItem}
              onPress={() => setMenuOpen(false)}
              accessibilityRole="button"
              accessibilityLabel="Home / Attention Field"
              accessibilityHint="Closes the menu -- you're already here"
            >
              <View style={styles.menuItemLabelRow}>
                <View style={styles.currentDot} />
                <Text style={styles.menuItemText}>Home / Attention Field</Text>
              </View>
            </Pressable>
            {ATTENTION_ITEMS.map((item) => (
              <MenuRow key={item.label} item={item} onNavigate={() => setMenuOpen(false)} />
            ))}

            <Text style={styles.menuSectionLabel}>YOUR STRATUS</Text>
            {YOUR_STRATUS_ITEMS.map((item) => (
              <MenuRow key={item.label} item={item} onNavigate={() => setMenuOpen(false)} />
            ))}

            {__DEV__ && (
              <>
                <Text style={styles.menuSectionLabel}>SYSTEM</Text>
                <Pressable
                  style={[styles.menuItem, styles.devMenuItem]}
                  onPress={() => {
                    setMenuOpen(false);
                    router.push("/dev-diagnostics");
                  }}
                  accessibilityRole="button"
                  accessibilityLabel="Developer / Diagnostics"
                >
                  <Text style={styles.devMenuItemText}>Developer / Diagnostics</Text>
                  <View style={styles.devPill}>
                    <Text style={styles.devPillText}>DEV</Text>
                  </View>
                </Pressable>
              </>
            )}

            <View style={styles.menuFooter}>
              <Image
                source={MENU_HORIZON_MARK_SOURCE}
                resizeMode="contain"
                accessibilityElementsHidden
                importantForAccessibility="no"
                style={styles.menuHorizonMark}
              />
              <Text style={styles.menuFooterText}>POWERED BY LGI</Text>
            </View>
          </View>
        </Pressable>
      </Modal>

      <Modal
        visible={panelItems !== null}
        animationType="fade"
        transparent
        onRequestClose={() => setPanelItems(null)}
      >
        <Pressable
          style={styles.notifBackdrop}
          onPress={() => setPanelItems(null)}
          accessibilityRole="button"
          accessibilityLabel="Close notifications"
        >
          {/* Inert Pressable, not a plain View: without something here to
              claim the touch, tapping empty space inside the panel (not on
              a row) would bubble to the backdrop above and close it. */}
          <Pressable style={styles.notifPanel} onPress={() => {}}>
            <Text style={styles.notifPanelTitle}>NEW OPPORTUNITIES</Text>
            {panelItems?.map((n) => (
              <Pressable
                key={n.eventId}
                style={styles.notifRow}
                onPress={() => openNotificationCard(n.eventId)}
                accessibilityRole="button"
                accessibilityLabel={`${n.name}, ${n.confidencePct} percent confidence`}
                accessibilityHint="Opens this opportunity's card"
              >
                <Text style={styles.notifRowName} numberOfLines={1}>
                  {n.name}
                </Text>
                <Text style={styles.notifRowPct}>{n.confidencePct}%</Text>
              </Pressable>
            ))}
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.background },
  // Column wrapping the Attention Field + FieldBiasControl -- see the JSX
  // comment at the call site for why this (not a position:absolute overlay)
  // is what lets the field's own edge-padding logic naturally clear the
  // control.
  fieldColumn: { flex: 1 },
  topbar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: spacing.xs,
    paddingBottom: spacing.sm,
  },
  // Equal-width bookend columns -- see the JSX comment above for why this
  // (rather than space-between on 3 unequal children) is what actually
  // centers the logo precisely.
  topbarSide: { width: 22, flexDirection: "row", alignItems: "center" },
  topbarSideRight: { alignItems: "flex-end" },
  topbarCenter: { flex: 1, alignItems: "center" },
  headerLogo: { width: HEADER_LOGO_WIDTH, height: HEADER_LOGO_HEIGHT },
  // Base size up 5 -> 7 (min ~7px at rest) with the 1.5x pulse peak (~10.5px
  // at max) -- both ends of the pulse bigger, not just the resting size.
  liveDot: { width: 7, height: 7, borderRadius: 3.5, backgroundColor: theme.accent },
  notifBadge: {
    position: "absolute",
    // Pushed further up/right (was -6/-8) -- at the old offsets the badge
    // sat almost entirely on top of the dot instead of just touching its
    // top-right edge.
    top: -12,
    right: -14,
    // Width is set inline per-render via notifBadgeWidth(unread.length) --
    // this absolutely-positioned, `right`-anchored box wasn't reliably
    // auto-sizing to its Text content in either direction (a fixed height
    // clipped two-digit counts; padding-driven auto-width instead wrapped
    // them vertically), so width is computed explicitly rather than left
    // to flexbox. Height stays fixed here since that's never ambiguous.
    height: 16,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.text,
    borderWidth: 1.5,
    borderColor: theme.background,
  },
  notifBadgeText: { color: theme.background, fontSize: 9, fontFamily: font.metadata },
  notifBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
    alignItems: "flex-end",
    paddingTop: 64,
    paddingRight: 20,
  },
  notifPanel: {
    minWidth: 220,
    maxWidth: 280,
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: spacing.lg,
  },
  notifPanelTitle: {
    color: theme.muted,
    fontSize: 10,
    fontFamily: font.metadata,
    letterSpacing: tracking.label,
    marginBottom: spacing.sm,
  },
  notifRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: spacing.xs,
  },
  notifRowName: {
    color: theme.text,
    fontSize: type.body,
    fontFamily: font.bodyMedium,
    flexShrink: 1,
    marginRight: spacing.sm,
  },
  notifRowPct: { color: theme.accent, fontSize: type.body, fontFamily: font.bodyMedium },
  // Dev-only (__DEV__) -- deliberately utilitarian/dashed rather than
  // matching the app's polished chrome, so it reads as a debug tool, not a
  // real feature. Never present in a production/TestFlight build.
  // Sprint 3.6.5 device-feedback pass: moved from bottom-right (where it
  // sat just above FieldBiasControl, visually competing with it during
  // physical-device review of the production-facing FIELD BIAS chrome) to
  // top-right, clear of both the Attention Field and the header's own
  // live-dot/notification-badge area. Purely a position change -- the
  // button's function (forcing a real, currently-displayed item to read as
  // unread) is untouched.
  devNotifButton: {
    position: "absolute",
    top: 52,
    right: 20,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: theme.muted,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: theme.background + "CC",
  },
  devNotifButtonText: {
    color: theme.muted,
    fontSize: 9,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
  },
  centerFill: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
  },
  error: {
    backgroundColor: theme.accentSoft,
    borderColor: theme.accent,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: 16,
    width: "100%",
  },
  errorTitle: { color: theme.text, fontFamily: font.heading, marginBottom: 7 },
  errorText: { color: theme.textSecondary, fontFamily: font.body, lineHeight: 20, marginBottom: 4 },
  retryButton: {
    backgroundColor: theme.accent,
    borderRadius: radius.sm,
    alignItems: "center",
    paddingVertical: spacing.md,
    marginTop: spacing.sm,
  },
  retryText: { color: theme.text, fontFamily: font.heading },
  menuBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.72)", justifyContent: "flex-end" },
  menuCard: {
    backgroundColor: theme.surface,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderTopWidth: 1,
    borderColor: theme.border,
    padding: 26,
    paddingBottom: 44,
  },
  menuHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.xl,
  },
  menuSectionLabel: {
    color: theme.muted,
    fontSize: 10,
    fontFamily: font.metadata,
    letterSpacing: tracking.label,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  menuItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: spacing.md + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: theme.border,
  },
  menuItemLabelRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  currentDot: { width: 5, height: 5, borderRadius: 2.5, backgroundColor: theme.accent },
  menuItemText: { color: theme.text, fontSize: type.body, fontFamily: font.bodyMedium },
  // 60-70% opacity for inactive/not-yet-available items, per the reference's
  // own inactive-state spec -- quieter than a plain muted color alone.
  menuItemTextSoon: { color: theme.muted, fontFamily: font.body, opacity: 0.65 },
  soonPill: {
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: 6,
    paddingVertical: 2,
    opacity: 0.65,
  },
  soonPillText: {
    color: theme.muted,
    fontSize: 8,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
  },
  devMenuItem: { marginTop: spacing.xs, borderBottomWidth: 0 },
  devMenuItemText: { color: theme.textSecondary, fontSize: type.body, fontFamily: font.bodyMedium },
  devPill: {
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  devPillText: {
    color: theme.muted,
    fontSize: 8,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
  },
  menuFooter: {
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: spacing.xxl + spacing.md,
    paddingTop: spacing.lg,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: theme.border,
  },
  menuHorizonMark: {
    width: MENU_HORIZON_MARK_WIDTH,
    height: MENU_HORIZON_MARK_WIDTH / MENU_HORIZON_MARK_ASPECT_RATIO,
  },
  menuFooterText: {
    color: theme.muted,
    fontSize: 10,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
  },
});
