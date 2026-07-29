import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { API_BASE_URL } from "../constants/config";
import { theme } from "../constants/theme";

export default function AskScreen() {
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState(
    "Ask what changed, why something matters, or what deserves your attention."
  );
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    const clean = message.trim();
    if (!clean || loading) return;

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/v1/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: clean }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = (await response.json()) as { answer: string };
      setAnswer(data.answer);
      setMessage("");
    } catch (error) {
      setAnswer(
        error instanceof Error ? error.message : "Unable to reach Logan."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.answerCard}>
        <Text style={styles.label}>LOGAN</Text>
        <Text style={styles.answer}>{answer}</Text>
      </View>

      <View style={styles.composer}>
        <TextInput
          value={message}
          onChangeText={setMessage}
          placeholder="Ask Logan..."
          placeholderTextColor={theme.muted}
          multiline
          style={styles.input}
        />
        <Pressable style={styles.send} onPress={submit}>
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.sendText}>SEND</Text>
          )}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: theme.background,
    padding: 18,
    justifyContent: "space-between",
  },
  answerCard: {
    backgroundColor: theme.panel,
    borderRadius: 20,
    borderColor: theme.border,
    borderWidth: 1,
    padding: 18,
  },
  label: {
    color: theme.accent,
    fontWeight: "900",
    fontSize: 11,
    letterSpacing: 1.5,
    marginBottom: 10,
  },
  answer: {
    color: theme.text,
    fontSize: 17,
    lineHeight: 25,
  },
  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 10,
  },
  input: {
    flex: 1,
    minHeight: 52,
    maxHeight: 130,
    borderRadius: 16,
    backgroundColor: theme.panel,
    borderColor: theme.border,
    borderWidth: 1,
    color: theme.text,
    padding: 14,
    fontSize: 16,
  },
  send: {
    minWidth: 72,
    height: 52,
    borderRadius: 16,
    backgroundColor: theme.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  sendText: {
    color: "#FFFFFF",
    fontWeight: "900",
  },
});
