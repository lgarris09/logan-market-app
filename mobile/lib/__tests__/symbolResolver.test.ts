import { resolveSymbol } from "../symbolResolver";

// V3.1.4.2 brand correction pass: color follows the owner's reference
// image's actual "Markets / Odds / Trends" taxonomy (exact hex values from
// its color palette panel), not an invented wider category set. These
// tests pin that mapping down so it can't silently drift.

describe("resolveSymbol color", () => {
  it("gives same-category entities the same color family", () => {
    const nvda = resolveSymbol({
      entity_id: "NVDA",
      display_name: "NVIDIA",
      category: "stocks",
      ticker: "NVDA",
    });
    const tsla = resolveSymbol({
      entity_id: "TSLA",
      display_name: "Tesla",
      category: "stocks",
      ticker: "TSLA",
    });
    expect(nvda.color).toBe(tsla.color);
  });

  it("groups crypto under Markets green, matching the reference (BTC shown as MARKETS, not a separate hue)", () => {
    const btc = resolveSymbol({
      entity_id: "BTC",
      display_name: "Bitcoin",
      category: "crypto",
      ticker: "BTC",
    });
    const stock = resolveSymbol({
      entity_id: "X",
      display_name: "X",
      category: "stocks",
      ticker: "X",
    });
    expect(btc.color).toBe(stock.color);
    expect(btc.color.toUpperCase()).toBe("#22C55E");
  });

  it("gives sports/prediction-markets the Odds red, distinct from Markets", () => {
    const nfl = resolveSymbol({
      entity_id: "NFL",
      display_name: "NFL",
      category: "sports",
      ticker: null,
    });
    const poly = resolveSymbol({
      entity_id: "POLY",
      display_name: "Polymarket",
      category: "prediction-markets",
      ticker: null,
    });
    const stock = resolveSymbol({
      entity_id: "X",
      display_name: "X",
      category: "stocks",
      ticker: "X",
    });
    expect(nfl.color).toBe(poly.color);
    expect(nfl.color.toUpperCase()).toBe("#EF4444");
    expect(nfl.color).not.toBe(stock.color);
  });

  it("falls back to a neutral color for categories with no reference mapping", () => {
    const fed = resolveSymbol({
      entity_id: "FED",
      display_name: "Federal Reserve",
      category: "macro",
      ticker: null,
    });
    const unknown = resolveSymbol({
      entity_id: "X",
      display_name: "X",
      category: "some-future-category",
      ticker: null,
    });
    expect(fed.color).toBe(unknown.color);
  });

  it("never resolves the STRATUS brand accent orange for an entity glow", () => {
    const categories = [
      "stocks",
      "markets",
      "commodities",
      "crypto",
      "macro",
      "sports",
      "culture",
      "prediction-markets",
      "technology",
      "unknown-future-category",
    ];
    for (const category of categories) {
      const symbol = resolveSymbol({ entity_id: "X", display_name: "X", category, ticker: null });
      expect(symbol.color.toUpperCase()).not.toBe("#F47A2A");
    }
  });
});
