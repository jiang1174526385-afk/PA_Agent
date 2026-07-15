import { describe, expect, it } from "vitest";
import { priceLinesFromDecision } from "./decisionOverlay";

describe("priceLinesFromDecision", () => {
  it("returns no lines when decision has no trade prices", () => {
    expect(priceLinesFromDecision({})).toEqual([]);
  });

  it("builds entry/TP1/TP2/SL lines with long-direction colors", () => {
    const lines = priceLinesFromDecision({
      order_direction: "做多",
      entry_price: 100,
      take_profit_price: 110,
      take_profit_price_2: 120,
      stop_loss_price: 90,
    });
    expect(lines).toEqual([
      { price: 100, color: "#22c55e", title: "入场" },
      { price: 110, color: "#22c55e", title: "TP1" },
      { price: 120, color: "#22c55e", title: "TP2" },
      { price: 90, color: "#ef4444", title: "止损" },
    ]);
  });

  it("colors the entry line red for a short direction", () => {
    const lines = priceLinesFromDecision({ order_direction: "做空", entry_price: 100 });
    expect(lines[0]).toEqual({ price: 100, color: "#ef4444", title: "入场" });
  });

  it("omits fields that are null/undefined", () => {
    const lines = priceLinesFromDecision({ entry_price: 100, stop_loss_price: null });
    expect(lines).toEqual([{ price: 100, color: "#ef4444", title: "入场" }]);
  });
});
