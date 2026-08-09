import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle } from "react-native-svg";

import { font, theme, tracking } from "../constants/theme";

// A compact confidence readout for the expanded Opportunity Card. Reads only
// `confidence_score`/`confidence_label` (both already public per the data
// contract) -- this is presentation of an existing, permitted field, not a
// new sub-score. Static (no animated fill) by design: the rest of the field
// already carries a lot of concurrent motion, and this number should read as
// settled fact, not something still resolving.
export function ConfidenceRing({
  score,
  label,
  color,
  size = 60,
}: {
  score: number;
  label: string;
  color: string;
  size?: number;
}) {
  const stroke = 4;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, score));
  const filled = clamped * circumference;

  return (
    <View style={styles.wrap}>
      <View style={{ width: size, height: size }}>
        <Svg width={size} height={size}>
          <Circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke={theme.border}
            strokeWidth={stroke}
            fill="none"
          />
          <Circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke={color}
            strokeWidth={stroke}
            strokeDasharray={`${filled}, ${circumference}`}
            strokeLinecap="round"
            fill="none"
            rotation={-90}
            origin={`${size / 2}, ${size / 2}`}
          />
        </Svg>
        <View style={StyleSheet.absoluteFill} pointerEvents="none">
          <View style={styles.center}>
            <Text style={[styles.pct, { fontSize: size * 0.26 }]}>
              {Math.round(clamped * 100)}%
            </Text>
          </View>
        </View>
      </View>
      <Text style={styles.label}>{label.toUpperCase()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  // Tabular figures (reference typography panel: "Numbers: Tabular
  // Figures") so the percentage doesn't visibly shift width as it changes.
  pct: { color: theme.text, fontFamily: font.heading, fontVariant: ["tabular-nums"] },
  label: {
    color: theme.textSecondary,
    fontSize: 9,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
    marginTop: 6,
  },
});
