import { useEffect, useMemo, useRef } from "react";
import { Animated, StyleSheet, View, useWindowDimensions } from "react-native";
import Svg, { Circle, Line } from "react-native-svg";

import { LoganCore } from "./LoganCore";
import { NODE_SIZE, OpportunityNode } from "./OpportunityNode";
import { FeedItem } from "../types/loganFeed";

const NODE_WRAPPER_WIDTH = 92;

export function OpportunityField({
  items,
  selectedId,
  onSelect,
}: {
  items: FeedItem[];
  selectedId: string | null;
  onSelect: (item: FeedItem) => void;
}) {
  const { width } = useWindowDimensions();
  const fieldSize = Math.min(width - 24, 420);
  const center = fieldSize / 2;
  const innerRadius = 92;
  const outerRadius = fieldSize / 2 - NODE_SIZE / 2 - 10;

  // Radial position: higher priority_score -> smaller radius -> closer to the
  // Logan core. Angle: evenly distributed, starting at the top, going clockwise.
  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    if (items.length === 0) return map;

    const scores = items.map((i) => i.priority_score);
    const min = Math.min(...scores);
    const max = Math.max(...scores);
    const range = max - min || 1;

    items.forEach((item, index) => {
      const t = (item.priority_score - min) / range;
      const radius = outerRadius - t * (outerRadius - innerRadius);
      const angle = -Math.PI / 2 + (index / items.length) * Math.PI * 2;
      map.set(item.event_id, {
        x: center + radius * Math.cos(angle),
        y: center + radius * Math.sin(angle),
      });
    });
    return map;
  }, [items, center, innerRadius, outerRadius]);

  // Ripple connections between related entities, deduped so each pair draws once.
  const connectionPairs = useMemo(() => {
    const seen = new Set<string>();
    const pairs: [string, string][] = [];
    items.forEach((item) => {
      item.connected_event_ids.forEach((otherId) => {
        const key = [item.event_id, otherId].sort().join("|");
        if (!seen.has(key) && positions.has(otherId)) {
          seen.add(key);
          pairs.push([item.event_id, otherId]);
        }
      });
    });
    return pairs;
  }, [items, positions]);

  const entrance = useRef<Animated.Value[]>([]).current;
  while (entrance.length < items.length) entrance.push(new Animated.Value(0));

  useEffect(() => {
    Animated.stagger(
      70,
      entrance.slice(0, items.length).map((value) =>
        Animated.spring(value, { toValue: 1, useNativeDriver: true, friction: 7, tension: 40 })
      )
    ).start();
    // Only replay the entrance animation when the item set actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.length]);

  return (
    <View style={{ width: fieldSize, height: fieldSize }}>
      <Svg width={fieldSize} height={fieldSize} style={StyleSheet.absoluteFill}>
        <Circle cx={center} cy={center} r={innerRadius} stroke="#232B36" strokeWidth={1} fill="none" />
        <Circle
          cx={center}
          cy={center}
          r={(innerRadius + outerRadius) / 2}
          stroke="#1A2028"
          strokeWidth={1}
          fill="none"
        />
        <Circle cx={center} cy={center} r={outerRadius} stroke="#1A2028" strokeWidth={1} fill="none" />

        {items.map((item) => {
          const pos = positions.get(item.event_id);
          if (!pos) return null;
          return (
            <Line
              key={`core-${item.event_id}`}
              x1={center}
              y1={center}
              x2={pos.x}
              y2={pos.y}
              stroke="#3A3220"
              strokeWidth={1}
              opacity={0.5}
            />
          );
        })}

        {connectionPairs.map(([a, b]) => {
          const posA = positions.get(a);
          const posB = positions.get(b);
          if (!posA || !posB) return null;
          return (
            <Line
              key={`${a}-${b}`}
              x1={posA.x}
              y1={posA.y}
              x2={posB.x}
              y2={posB.y}
              stroke="#E8B95C"
              strokeWidth={1.5}
              opacity={0.4}
            />
          );
        })}
      </Svg>

      <View style={[StyleSheet.absoluteFill, styles.centerWrap]} pointerEvents="none">
        <LoganCore />
      </View>

      {items.map((item, index) => {
        const pos = positions.get(item.event_id);
        if (!pos) return null;
        const anim = entrance[index];
        return (
          <Animated.View
            key={item.event_id}
            style={{
              position: "absolute",
              left: pos.x - NODE_WRAPPER_WIDTH / 2,
              top: pos.y - NODE_SIZE / 2,
              opacity: anim,
              transform: [{ scale: anim }],
            }}
          >
            <OpportunityNode
              item={item}
              selected={selectedId === item.event_id}
              onPress={() => onSelect(item)}
            />
          </Animated.View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  centerWrap: {
    alignItems: "center",
    justifyContent: "center",
  },
});
