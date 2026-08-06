// Symbol resolution pipeline: Canonical Entity -> Symbol Resolver -> ResolvedSymbol.
// Every Opportunity Node renders through this same lookup -- no per-entity
// components. When Logan encounters a new entity_id, this file (a data lookup, not
// new UI code) is the only thing that would ever need an entry, and even without
// one it degrades gracefully through the fallback chain below.
//
// Fallback order: known logo -> ticker -> known category icon -> initials.
// (Category icon is placed ahead of initials for entities like "NFL" or "FED" --
// their entity_id already reads like an acronym, so initials would just repeat the
// label under the node. A category icon carries more information in that case.)

export type ResolvedSymbol =
  | { kind: "logo"; iconName: string; color: string }
  | { kind: "ticker"; text: string; color: string }
  | { kind: "category"; iconName: string; color: string }
  | { kind: "initials"; text: string; color: string };

// FontAwesome5 brand icon names, for entities with a recognizable public logo.
const KNOWN_LOGOS: Record<string, string> = {
  AAPL: "apple",
  BTC: "bitcoin",
};

// FontAwesome5 solid icon names, one per category.
const CATEGORY_ICONS: Record<string, string> = {
  stocks: "chart-line",
  markets: "chart-line",
  commodities: "oil-can",
  crypto: "coins",
  macro: "university",
  sports: "football-ball",
  culture: "music",
  "prediction-markets": "balance-scale",
  technology: "microchip",
};

// Per-entity accent colors (mirrors the reference render's per-entity coloring,
// not a flat per-category palette -- three "stocks" entities look distinct).
const ENTITY_COLORS: Record<string, string> = {
  TSLA: "#F04444",
  NVDA: "#4FD1A5",
  AAPL: "#E8E8E8",
  MARKETS: "#2DD4BF",
  OIL: "#F0B64A",
  BTC: "#F7931A",
  FED: "#4A90D9",
  NFL: "#3B82F6",
  MUSIC: "#A78BFA",
  POLY: "#A78BFA",
  AI_SECTOR: "#4FD1A5",
};

// Stable fallback palette for entities with no explicit color, keyed by a cheap
// hash of entity_id so the same unknown entity always gets the same color.
const FALLBACK_PALETTE = ["#F04444", "#4FD1A5", "#2DD4BF", "#F0B64A", "#A78BFA", "#4A90D9"];

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function colorFor(entityId: string): string {
  return (
    ENTITY_COLORS[entityId] ?? FALLBACK_PALETTE[hashString(entityId) % FALLBACK_PALETTE.length]
  );
}

function initialsFor(displayName: string): string {
  const words = displayName.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

export function resolveSymbol(entity: {
  entity_id: string;
  display_name: string;
  category: string;
  ticker: string | null;
}): ResolvedSymbol {
  const color = colorFor(entity.entity_id);

  const logo = KNOWN_LOGOS[entity.entity_id];
  if (logo) return { kind: "logo", iconName: logo, color };

  if (entity.ticker) return { kind: "ticker", text: entity.ticker, color };

  const categoryIcon = CATEGORY_ICONS[entity.category];
  if (categoryIcon) return { kind: "category", iconName: categoryIcon, color };

  return { kind: "initials", text: initialsFor(entity.display_name), color };
}
