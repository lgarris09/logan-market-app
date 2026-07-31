import { Pressable, StyleSheet, Text, View } from "react-native";

import { EntitySymbol } from "./EntitySymbol";
import { theme } from "../constants/theme";
import { resolveSymbol } from "../lib/symbolResolver";
import { FeedItem } from "../types/loganFeed";

const NODE_SIZE = 66;

export function OpportunityNode({
  item,
  onPress,
  selected,
}: {
  item: FeedItem;
  onPress: () => void;
  selected: boolean;
}) {
  const symbol = resolveSymbol(item);

  return (
    <Pressable onPress={onPress} style={styles.wrapper} hitSlop={8}>
      <View
        style={[
          styles.ring,
          {
            width: NODE_SIZE,
            height: NODE_SIZE,
            borderRadius: NODE_SIZE / 2,
            borderColor: symbol.color,
            shadowColor: symbol.color,
            backgroundColor: theme.surface,
          },
          selected && styles.ringSelected,
        ]}
      >
        <EntitySymbol symbol={symbol} size={NODE_SIZE - 16} />
      </View>
      <Text style={styles.label} numberOfLines={1}>
        {item.display_name.toUpperCase()}
      </Text>
      <Text style={[styles.status, { color: symbol.color }]} numberOfLines={1}>
        {item.confidence_label}
      </Text>
    </Pressable>
  );
}

export { NODE_SIZE };

const styles = StyleSheet.create({
  wrapper: {
    alignItems: "center",
    width: 92,
  },
  ring: {
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    shadowOpacity: 0.6,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 0 },
    elevation: 6,
  },
  ringSelected: {
    borderWidth: 3,
  },
  label: {
    color: theme.text,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.6,
    marginTop: 6,
    textAlign: "center",
  },
  status: {
    fontSize: 9,
    fontWeight: "700",
    marginTop: 2,
    textAlign: "center",
  },
});
