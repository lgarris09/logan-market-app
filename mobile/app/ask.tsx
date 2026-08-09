import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { font, theme, spacing, tracking, type } from "../constants/theme";
import { PressableScale } from "../components/PressableScale";
import { fetchJson } from "../lib/apiClient";

// Sprint 3.6 device retest: Ask STRATUS's first-run mark now renders the
// owner-approved horizon/sun artwork directly (see
// assets/images/stratus-horizon-mark.png) instead of the hand-coded
// HorizonMark.tsx arc. Unlike the wordmark asset, this source file already
// carried a real, correctly-varying alpha channel -- no matte synthesis was
// needed, just a crop to the real content bounds. The menu drawer footer
// (index.tsx) moved to the same asset in a later round -- HorizonMark.tsx
// itself is no longer imported anywhere in the app, left in place rather
// than deleted unasked.
const HORIZON_MARK_SOURCE = require("../assets/images/stratus-horizon-mark.png");
const HORIZON_MARK_ASPECT_RATIO = 1512 / 430;
const HORIZON_MARK_WIDTH = 140;

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  isError?: boolean;
  time: string;
};

const STARTER_PROMPTS = [
  "What's the most important signal right now?",
  "What changed since yesterday?",
  "What deserves my attention today?",
];

let messageCounter = 0;
function nextId(): string {
  messageCounter += 1;
  return `msg-${messageCounter}`;
}

function timeNow(): string {
  return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// V3.1.4.2 (real-device brand pass): the working keyboard-safe flow and
// scrolling conversation from the previous round are preserved untouched
// (own header, KeyboardAvoidingView, fetchJson round-trip). What changed is
// visual identity -- a deliberate first state instead of a large empty chat
// void, and assistant responses presented as bordered "intelligence panels"
// (STRATUS label + timestamp header, like a compact Opportunity Card)
// rather than SMS-style bubbles, so this reads as "the intelligence behind
// STRATUS," not a generic chat app. User messages stay distinct but
// restrained (tinted outline, not a solid color block).
export default function AskScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const controllerRef = useRef<AbortController | null>(null);
  useEffect(() => () => controllerRef.current?.abort(), []);

  const scrollRef = useRef<ScrollView>(null);

  const submit = async (overrideText?: string) => {
    const clean = (overrideText ?? input).trim();
    if (!clean || loading) return;

    setMessages((prev) => [...prev, { id: nextId(), role: "user", text: clean, time: timeNow() }]);
    setInput("");
    setLoading(true);

    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    const result = await fetchJson<{ answer: string }>("/v1/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: clean }),
      signal: controller.signal,
      // Non-idempotent request -- don't auto-retry a POST, matching
      // fetchJson's own documented convention for this case.
      retries: 0,
    });

    switch (result.status) {
      case "success":
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", text: result.data.answer, time: timeNow() },
        ]);
        break;
      case "timeout":
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            isError: true,
            text: "STRATUS didn't respond in time. Check your connection and try again.",
            time: timeNow(),
          },
        ]);
        break;
      case "error":
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            isError: true,
            text: result.message || "Unable to reach STRATUS.",
            time: timeNow(),
          },
        ]);
        break;
      case "aborted":
        // Superseded by a newer submission or the screen unmounted -- no UI update.
        return;
    }

    setLoading(false);
  };

  const hasConversation = messages.length > 0;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.topbar}>
        <Pressable
          onPress={() => router.back()}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel="Back"
        >
          <Ionicons name="chevron-back" size={22} color={theme.textSecondary} />
        </Pressable>
        <View style={styles.topbarTitle}>
          <Text style={styles.wordmark}>ASK STRATUS</Text>
          <View style={styles.titleUnderline} />
        </View>
        <View style={styles.spacer} />
      </View>

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={0}
      >
        <ScrollView
          ref={scrollRef}
          style={styles.flex}
          contentContainerStyle={styles.messages}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
          keyboardShouldPersistTaps="handled"
        >
          {!hasConversation && (
            <View style={styles.firstState}>
              <Image
                source={HORIZON_MARK_SOURCE}
                resizeMode="contain"
                accessibilityElementsHidden
                importantForAccessibility="no"
                style={styles.horizonMark}
              />
              <Text style={styles.firstStatePoweredBy}>POWERED BY LGI</Text>
              <Text style={styles.firstStateHeadline}>
                I&apos;m STRATUS.{"\n"}Your personal opportunity intelligence.
              </Text>
              <Text style={styles.firstStateSubtext}>
                Ask what changed. Why it matters. What deserves your attention.
              </Text>

              <View style={styles.starterList}>
                {STARTER_PROMPTS.map((prompt) => (
                  <Pressable
                    key={prompt}
                    style={styles.starterRow}
                    onPress={() => submit(prompt)}
                    accessibilityRole="button"
                    accessibilityLabel={prompt}
                  >
                    <Text style={styles.starterText}>{prompt}</Text>
                    <Ionicons name="chevron-forward" size={15} color={theme.textSecondary} />
                  </Pressable>
                ))}
              </View>
            </View>
          )}

          {hasConversation && (
            <View style={styles.todayDivider}>
              <View style={styles.todayLine} />
              <Text style={styles.todayText}>TODAY</Text>
              <View style={styles.todayLine} />
            </View>
          )}

          {messages.map((message) =>
            message.role === "user" ? (
              <View key={message.id} style={styles.userRow}>
                <Text style={styles.userText}>{message.text}</Text>
              </View>
            ) : (
              <View key={message.id} style={[styles.panel, message.isError && styles.panelError]}>
                <View style={styles.panelHeader}>
                  <View style={styles.panelHeaderLeft}>
                    <View style={styles.panelDot} />
                    <Text style={styles.panelLabel}>STRATUS</Text>
                  </View>
                  <Text style={styles.panelTime}>{message.time}</Text>
                </View>
                <Text style={styles.panelText}>{message.text}</Text>
              </View>
            )
          )}

          {loading && (
            <View style={styles.panel}>
              <View style={styles.panelHeader}>
                <View style={styles.panelHeaderLeft}>
                  <View style={styles.panelDot} />
                  <Text style={styles.panelLabel}>STRATUS</Text>
                </View>
              </View>
              <ActivityIndicator
                color={theme.textSecondary}
                size="small"
                style={styles.panelLoading}
              />
            </View>
          )}
        </ScrollView>

        <View style={styles.composer}>
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Ask STRATUS..."
            placeholderTextColor={theme.muted}
            multiline
            style={styles.input}
            accessibilityLabel="Message to STRATUS"
          />
          <PressableScale
            style={styles.send}
            onPress={() => submit()}
            disabled={loading || !input.trim()}
            accessibilityLabel="Send"
            accessibilityHint="Sends your message to STRATUS"
            accessibilityState={{ disabled: loading, busy: loading }}
          >
            <Ionicons name="arrow-up" size={13} color={theme.background} />
          </PressableScale>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.background },
  flex: { flex: 1 },
  topbar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: spacing.xs,
    paddingBottom: spacing.sm,
  },
  topbarTitle: { alignItems: "center" },
  wordmark: {
    color: theme.textSecondary,
    fontSize: 12,
    fontFamily: font.metadata,
    letterSpacing: tracking.label,
  },
  titleUnderline: {
    width: 22,
    height: 1.5,
    backgroundColor: theme.accent,
    marginTop: 6,
    borderRadius: 1,
  },
  spacer: { width: 22 },
  messages: { padding: 20, gap: 18, flexGrow: 1, justifyContent: "flex-end" },
  firstState: { alignItems: "center", paddingTop: spacing.xxl, paddingBottom: spacing.xl },
  horizonMark: {
    width: HORIZON_MARK_WIDTH,
    height: HORIZON_MARK_WIDTH / HORIZON_MARK_ASPECT_RATIO,
  },
  firstStatePoweredBy: {
    color: theme.muted,
    fontSize: 9,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
    marginTop: 8,
  },
  // Sprint 3.6 (section 16): "too heavy/generic compared with the precision
  // language of the rest of the product" -- InterTight Medium (not the
  // heavier SemiBold used for card headlines) plus a lighter line height,
  // so the hero reads as restrained/engineered rather than a generic app
  // welcome banner, while staying clearly the largest text on the screen.
  firstStateHeadline: {
    color: theme.text,
    fontSize: 21,
    fontFamily: font.headingMedium,
    lineHeight: 27,
    textAlign: "center",
    marginTop: spacing.lg,
  },
  firstStateSubtext: {
    color: theme.textSecondary,
    fontSize: type.body,
    fontFamily: font.body,
    lineHeight: 21,
    textAlign: "center",
    marginTop: spacing.sm,
    marginBottom: spacing.xl,
  },
  starterList: { width: "100%", gap: 8 },
  starterRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: spacing.md,
    paddingVertical: 11,
  },
  starterText: {
    color: theme.textSecondary,
    fontSize: 12.5,
    fontFamily: font.bodyMedium,
    flexShrink: 1,
    marginRight: spacing.sm,
  },
  todayDivider: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 4 },
  todayLine: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: theme.border },
  todayText: {
    color: theme.muted,
    fontSize: 9,
    fontFamily: font.metadata,
    letterSpacing: tracking.label,
  },
  userRow: { alignSelf: "flex-end", maxWidth: "82%" },
  userText: {
    color: theme.text,
    fontSize: type.body,
    fontFamily: font.body,
    lineHeight: 20,
    backgroundColor: theme.accentSoft,
    borderColor: theme.accent + "40",
    borderWidth: 1,
    borderRadius: 14,
    borderBottomRightRadius: 3,
    paddingHorizontal: 14,
    paddingVertical: 10,
    overflow: "hidden",
  },
  panel: {
    backgroundColor: theme.panel,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 14,
    padding: spacing.lg,
  },
  panelError: { borderColor: theme.accent },
  panelHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  panelHeaderLeft: { flexDirection: "row", alignItems: "center", gap: 6 },
  panelDot: { width: 5, height: 5, borderRadius: 2.5, backgroundColor: theme.accent },
  panelLabel: {
    color: theme.accent,
    fontSize: 10,
    fontFamily: font.metadata,
    letterSpacing: tracking.label,
  },
  panelTime: { color: theme.muted, fontSize: 10, fontFamily: font.body },
  panelText: { color: theme.text, fontSize: type.body, fontFamily: font.body, lineHeight: 21 },
  panelLoading: { alignSelf: "flex-start", marginTop: 2 },
  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 10,
    paddingHorizontal: 18,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  input: {
    flex: 1,
    minHeight: 46,
    maxHeight: 130,
    borderRadius: 14,
    backgroundColor: theme.background,
    borderColor: theme.border,
    borderWidth: 1,
    color: theme.text,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    fontFamily: font.body,
  },
  // Sprint 3.6 (section 17): "among the most visually dominant elements on
  // the screen" -- shrunk (36 -> 32) while staying comfortably above the
  // platform's ~28px minimum practical tap size (the surrounding 10px gap
  // and row padding keep the real hit area generous).
  send: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: theme.accent,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "center",
  },
});
