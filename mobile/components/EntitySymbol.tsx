import { FontAwesome5 } from "@expo/vector-icons";
import { StyleSheet, Text, View } from "react-native";

import { ResolvedSymbol } from "../lib/symbolResolver";

// The one reusable component every Opportunity Node renders its icon through.
// Never create a per-entity component -- add an entry to symbolResolver.ts instead.
export function EntitySymbol({ symbol, size }: { symbol: ResolvedSymbol; size: number }) {
  const iconSize = Math.round(size * 0.5);

  if (symbol.kind === "logo" || symbol.kind === "category") {
    return (
      <View style={[styles.container, { width: size, height: size, borderRadius: size / 2 }]}>
        <FontAwesome5 name={symbol.iconName} size={iconSize} color={symbol.color} solid />
      </View>
    );
  }

  const text = symbol.kind === "ticker" ? symbol.text : symbol.text;
  return (
    <View style={[styles.container, { width: size, height: size, borderRadius: size / 2 }]}>
      <Text
        style={[styles.text, { color: symbol.color, fontSize: Math.round(size * 0.3) }]}
        numberOfLines={1}
        adjustsFontSizeToFit
      >
        {text}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
  },
  text: {
    fontWeight: "700",
    letterSpacing: 0.5,
  },
});
