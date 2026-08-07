import { useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { API_BASE_URL } from "../constants/config";
import { theme } from "../constants/theme";
import { OpportunityCard } from "../components/OpportunityCard";
import { FadeIn } from "../components/FadeIn";
import { PressableScale } from "../components/PressableScale";
import { TeslaDemoResponse } from "../types/loganDemo";

export default function DemoScreen() {
  const [result, setResult] = useState<TeslaDemoResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const runDemo = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/v1/demo/tesla`, { method: "POST" });
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      setResult((await response.json()) as TeslaDemoResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach Logan.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.kicker}>LOGAN INTELLIGENCE SYSTEM</Text>
      <Text style={styles.title}>Pipeline demo</Text>
      <Text style={styles.subtitle}>
        Runs the &ldquo;Tesla announces a major AI chip partnership&rdquo; scenario through the full
        18-layer logan_core pipeline on simulated data, live against the backend.
      </Text>

      <PressableScale style={styles.button} onPress={runDemo} disabled={loading}>
        {loading ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.buttonText}>Run Logan Demo</Text>
        )}
      </PressableScale>

      {!!error && (
        <FadeIn>
          <View style={styles.error}>
            <Text style={styles.errorTitle}>Backend not connected</Text>
            <Text style={styles.errorText}>{error}</Text>
            <Text style={styles.errorText}>
              Start FastAPI and set your computer IP in constants/config.ts.
            </Text>
          </View>
        </FadeIn>
      )}

      {result && (
        <FadeIn distance={14}>
          <OpportunityCard item={result.delivered_item} />

          <View style={styles.detailsCard}>
            <Text style={styles.detailsLabel}>CONCLUSION CONFIDENCE</Text>
            <Text style={styles.detailsText}>
              {result.confidence.classification} ·{" "}
              {Math.round(result.confidence.confidence_score * 100)}%
            </Text>
            {result.confidence.limiting_factors.map((factor) => (
              <Text key={factor} style={styles.detailsSubtext}>
                • {factor}
              </Text>
            ))}

            <Text style={[styles.detailsLabel, styles.spaced]}>POLICY</Text>
            <Text style={styles.detailsText}>
              {result.policy_result.permitted ? "permitted" : "suppressed"} ·{" "}
              {result.policy_result.communication_mode}
            </Text>
            <Text style={styles.detailsSubtext}>
              rules: {result.policy_result.policy_rules_applied.join(", ")}
            </Text>

            <Text style={[styles.detailsLabel, styles.spaced]}>EXECUTION TRACE</Text>
            <Text style={styles.detailsText}>
              {result.execution_trace.status} · {result.execution_trace.total_layers} layers ·{" "}
              {result.execution_trace.all_succeeded ? "all succeeded" : "some failed"}
            </Text>
            <Text style={styles.detailsSubtext}>{result.execution_trace.layers.join(" -> ")}</Text>
          </View>
        </FadeIn>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background },
  content: { paddingHorizontal: 18, paddingTop: 18, paddingBottom: 42 },
  kicker: { color: theme.accent, fontSize: 10, fontWeight: "900", letterSpacing: 1.4 },
  title: { color: theme.text, fontSize: 26, fontWeight: "900", marginTop: 8 },
  subtitle: {
    color: theme.textSecondary,
    fontSize: 14,
    lineHeight: 20,
    marginTop: 10,
    marginBottom: 20,
  },
  button: {
    backgroundColor: theme.accent,
    borderRadius: 16,
    alignItems: "center",
    paddingVertical: 16,
    marginBottom: 18,
  },
  buttonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "900" },
  error: {
    backgroundColor: theme.accentSoft,
    borderColor: theme.accent,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 14,
  },
  errorTitle: { color: theme.text, fontWeight: "900", marginBottom: 7 },
  errorText: { color: theme.textSecondary, lineHeight: 20, marginBottom: 4 },
  detailsCard: {
    backgroundColor: theme.surfaceSoft,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 18,
  },
  detailsLabel: {
    color: theme.textSecondary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.1,
    marginBottom: 6,
  },
  spaced: { marginTop: 16 },
  detailsText: { color: theme.text, fontSize: 14, fontWeight: "700" },
  detailsSubtext: { color: theme.textSecondary, fontSize: 12, lineHeight: 18, marginTop: 4 },
});
