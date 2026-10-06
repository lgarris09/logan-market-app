// ADR-082 -- the Beta 1 contextual feedback control.
//
// One quiet control on the opportunity detail that opens a small sheet with
// the five governed reasons and an optional note. A report is tied to the
// opportunity and revision on screen and records what was displayed (see
// lib/opportunityFeedback.ts). It changes nothing the user sees.
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { font, radius, spacing, theme, type } from "../constants/theme";
import {
  FEEDBACK_NOTE_MAX_LENGTH,
  FEEDBACK_OPTIONS,
  submitOpportunityFeedback,
} from "../lib/opportunityFeedback";
import type { OpportunityFeedbackReason } from "../lib/telemetry";
import type { FeedItem } from "../types/loganFeed";

type Phase = "choosing" | "sending" | "sent" | "failed";

export function OpportunityFeedback({ item }: { item: FeedItem }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<OpportunityFeedbackReason | null>(null);
  const [note, setNote] = useState("");
  const [phase, setPhase] = useState<Phase>("choosing");

  // A report has to be tied to a revision to be investigable. Items without
  // one (lifecycle tracking not active) do not show the control at all.
  if (item.opportunity_revision == null) return null;

  const close = () => {
    setOpen(false);
    setReason(null);
    setNote("");
    setPhase("choosing");
  };

  const send = async () => {
    if (reason === null || phase === "sending") return;
    setPhase("sending");
    const result = await submitOpportunityFeedback(item, reason, note);
    setPhase(result === "sent" ? "sent" : "failed");
  };

  return (
    <>
      <Pressable
        style={styles.trigger}
        onPress={() => setOpen(true)}
        accessibilityRole="button"
        accessibilityLabel={`Report a problem with ${item.display_name}`}
        hitSlop={8}
      >
        <Ionicons name="flag-outline" size={12} color={theme.muted} />
        <Text style={styles.triggerText}>Something off?</Text>
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={close}>
        <KeyboardAvoidingView
          style={styles.backdrop}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <Pressable style={StyleSheet.absoluteFill} onPress={close} accessibilityLabel="Close" />
          <View style={styles.sheet} accessibilityViewIsModal>
            {phase === "sent" ? (
              <>
                <Text style={styles.title}>Thanks</Text>
                <Text style={styles.body}>
                  This report is attached to this opportunity so we can look into it.
                </Text>
                <Pressable style={styles.primary} onPress={close} accessibilityRole="button">
                  <Text style={styles.primaryText}>Done</Text>
                </Pressable>
              </>
            ) : (
              <>
                <Text style={styles.title}>What is off about this?</Text>
                <Text style={styles.body} numberOfLines={2}>
                  {item.delivered_item.headline}
                </Text>

                {FEEDBACK_OPTIONS.map((option) => {
                  const selected = option.reason === reason;
                  return (
                    <Pressable
                      key={option.reason}
                      style={[styles.option, selected && styles.optionSelected]}
                      onPress={() => setReason(option.reason)}
                      accessibilityRole="radio"
                      accessibilityState={{ selected }}
                      accessibilityLabel={option.label}
                    >
                      <Ionicons
                        name={selected ? "radio-button-on" : "radio-button-off"}
                        size={16}
                        color={selected ? theme.accent : theme.muted}
                      />
                      <Text style={[styles.optionText, selected && { color: theme.text }]}>
                        {option.label}
                      </Text>
                    </Pressable>
                  );
                })}

                <TextInput
                  style={styles.note}
                  value={note}
                  onChangeText={setNote}
                  placeholder="Add a note (optional)"
                  placeholderTextColor={theme.muted}
                  maxLength={FEEDBACK_NOTE_MAX_LENGTH}
                  multiline
                  accessibilityLabel="Optional note"
                />

                {phase === "failed" && (
                  <Text style={styles.error} accessibilityLiveRegion="polite">
                    That did not go through. Check your connection and try again.
                  </Text>
                )}

                <View style={styles.actions}>
                  <Pressable style={styles.secondary} onPress={close} accessibilityRole="button">
                    <Text style={styles.secondaryText}>Cancel</Text>
                  </Pressable>
                  <Pressable
                    style={[
                      styles.primary,
                      (reason === null || phase === "sending") && styles.disabled,
                    ]}
                    onPress={send}
                    disabled={reason === null || phase === "sending"}
                    accessibilityRole="button"
                    accessibilityState={{ disabled: reason === null || phase === "sending" }}
                  >
                    <Text style={styles.primaryText}>
                      {phase === "sending" ? "Sending" : phase === "failed" ? "Try again" : "Send"}
                    </Text>
                  </Pressable>
                </View>
              </>
            )}
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    alignSelf: "flex-start",
    paddingVertical: 8,
    marginTop: 6,
  },
  triggerText: { color: theme.muted, fontSize: 11.5, fontFamily: font.body },
  backdrop: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
    backgroundColor: "rgba(0,0,0,0.6)",
  },
  sheet: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.lg,
  },
  title: { color: theme.text, fontSize: type.body, fontFamily: font.bodyMedium, marginBottom: 6 },
  body: {
    color: theme.textSecondary,
    fontSize: 12.5,
    fontFamily: font.body,
    lineHeight: 18,
    marginBottom: spacing.md,
  },
  option: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 11,
    paddingHorizontal: 10,
    borderRadius: 10,
  },
  optionSelected: { backgroundColor: theme.surfaceSoft },
  optionText: { color: theme.textSecondary, fontSize: 13.5, fontFamily: font.body, flex: 1 },
  note: {
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 10,
    color: theme.text,
    fontFamily: font.body,
    fontSize: 13,
    minHeight: 64,
    maxHeight: 120,
    padding: 10,
    marginTop: spacing.sm,
    textAlignVertical: "top",
  },
  error: { color: theme.warning, fontSize: 12, fontFamily: font.body, marginTop: spacing.sm },
  actions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  primary: {
    backgroundColor: theme.accent,
    borderRadius: 10,
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    alignSelf: "flex-end",
  },
  primaryText: { color: theme.background, fontSize: 13, fontFamily: font.bodyMedium },
  secondary: { paddingHorizontal: spacing.md, paddingVertical: 10 },
  secondaryText: { color: theme.textSecondary, fontSize: 13, fontFamily: font.bodyMedium },
  disabled: { opacity: 0.4 },
});
