import { useEffect, useMemo, useRef } from "react";
import { Animated, StyleSheet, View, useWindowDimensions } from "react-native";
import Svg, { Circle, Line } from "react-native-svg";

import { LoganCore } from "./LoganCore";
import { NODE_SIZE, NodeEmphasis, OpportunityNode } from "./OpportunityNode";
import { clusterMembersOf, computeFieldLayout } from "../lib/fieldLayout";
import { FeedItem } from "../types/loganFeed";

const NODE_WRAPPER_WIDTH = 92;
const AnimatedCircle = Animated.createAnimatedComponent(Circle);

function ConnectionPulse({
  from,
  to,
  delay,
}: {
  from: { x: number; y: number };
  to: { x: number; y: number };
  delay: number;
}) {
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(progress, { toValue: 1, duration: 1600, delay, useNativeDriver: false }),
        Animated.timing(progress, { toValue: 0, duration: 0, useNativeDriver: false }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [progress, delay]);

  const cx = progress.interpolate({ inputRange: [0, 1], outputRange: [from.x, to.x] });
  const cy = progress.interpolate({ inputRange: [0, 1], outputRange: [from.y, to.y] });
  const opacity = progress.interpolate({
    inputRange: [0, 0.1, 0.9, 1],
    outputRange: [0, 0.85, 0.85, 0],
  });

  return <AnimatedCircle cx={cx} cy={cy} r={2.6} fill="#E8B95C" opacity={opacity} />;
}

export function OpportunityField({
  items,
  selectedId,
  onSelect,
  pulseKey,
}: {
  items: FeedItem[];
  selectedId: string | null;
  onSelect: (item: FeedItem) => void;
  pulseKey?: string | number;
}) {
  const { width } = useWindowDimensions();
  const fieldSize = Math.min(width - 24, 420);
  const center = fieldSize / 2;
  const innerRadius = 92;
  const outerRadius = fieldSize / 2 - NODE_SIZE / 2 - 10;

  const positions = useMemo(
    () => computeFieldLayout(items, center, innerRadius, outerRadius),
    [items, center, innerRadius, outerRadius]
  );

  const clusterMembers = useMemo(
    () => (selectedId ? clusterMembersOf(items, selectedId) : null),
    [items, selectedId]
  );

  const directEdgesOfSelected = useMemo(() => {
    if (!selectedId) return new Set<string>();
    const selectedItem = items.find((i) => i.event_id === selectedId);
    return new Set(selectedItem?.connected_event_ids ?? []);
  }, [items, selectedId]);

  const emphasisFor = (item: FeedItem): NodeEmphasis => {
    if (!selectedId || !clusterMembers) return "related";
    if (item.event_id === selectedId) return "focused";
    return clusterMembers.has(item.event_id) ? "related" : "dimmed";
  };

  // Ripple connections, deduped so each pair draws once.
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
      entrance
        .slice(0, items.length)
        .map((value) =>
          Animated.spring(value, { toValue: 1, useNativeDriver: true, friction: 7, tension: 40 })
        )
    ).start();
    // Only replay the entrance animation when the item set actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.length]);

  return (
    <View style={{ width: fieldSize, height: fieldSize }}>
      <Svg width={fieldSize} height={fieldSize} style={StyleSheet.absoluteFill}>
        {items.map((item) => {
          const pos = positions.get(item.event_id);
          if (!pos) return null;
          const emphasis = emphasisFor(item);
          const opacity = emphasis === "focused" ? 0.55 : emphasis === "related" ? 0.32 : 0.1;
          return (
            <Line
              key={`core-${item.event_id}`}
              x1={center}
              y1={center}
              x2={pos.x}
              y2={pos.y}
              stroke="#3A3220"
              strokeWidth={1}
              opacity={opacity}
            />
          );
        })}

        {connectionPairs.map(([a, b]) => {
          const posA = positions.get(a);
          const posB = positions.get(b);
          if (!posA || !posB) return null;

          const isDirect =
            !!selectedId &&
            ((a === selectedId && directEdgesOfSelected.has(b)) ||
              (b === selectedId && directEdgesOfSelected.has(a)));
          const touchesCluster = !!clusterMembers && clusterMembers.has(a) && clusterMembers.has(b);

          const opacity = isDirect ? 0.55 : touchesCluster ? 0.22 : 0.08;
          const strokeWidth = isDirect ? 1.6 : 1;

          return (
            <Line
              key={`${a}-${b}`}
              x1={posA.x}
              y1={posA.y}
              x2={posB.x}
              y2={posB.y}
              stroke="#E8B95C"
              strokeWidth={strokeWidth}
              opacity={opacity}
            />
          );
        })}

        {Array.from(directEdgesOfSelected).map((otherId, index) => {
          if (!selectedId) return null;
          const from = positions.get(selectedId);
          const to = positions.get(otherId);
          if (!from || !to) return null;
          return (
            <ConnectionPulse
              key={`pulse-${selectedId}-${otherId}`}
              from={from}
              to={to}
              delay={index * 220}
            />
          );
        })}
      </Svg>

      <View style={[StyleSheet.absoluteFill, styles.centerWrap]} pointerEvents="none">
        <LoganCore pulseKey={pulseKey} />
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
              emphasis={emphasisFor(item)}
              onPress={() => onSelect(item)}
              floatPhase={pos.floatPhase}
              floatFreq={pos.floatFreq}
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
