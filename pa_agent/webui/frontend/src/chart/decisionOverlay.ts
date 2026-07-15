// Mirrors the price fields pa_agent/gui/chart_decision_overlay.py enriches onto
// a decision dict for the desktop chart widget (entry/TP1/TP2/SL price lines).
import type { StageDecision } from "../types/domain";

export interface PriceLineSpec {
  price: number;
  color: string;
  title: string;
}

function isLongDirection(direction: string | undefined): boolean {
  return !!direction && direction.includes("多");
}

export function priceLinesFromDecision(decision: StageDecision): PriceLineSpec[] {
  const long = isLongDirection(decision.order_direction);
  const entryColor = long ? "#22c55e" : "#ef4444";
  const specs: PriceLineSpec[] = [];

  if (typeof decision.entry_price === "number") {
    specs.push({ price: decision.entry_price, color: entryColor, title: "入场" });
  }
  if (typeof decision.take_profit_price === "number") {
    specs.push({ price: decision.take_profit_price, color: "#22c55e", title: "TP1" });
  }
  if (typeof decision.take_profit_price_2 === "number") {
    specs.push({ price: decision.take_profit_price_2, color: "#22c55e", title: "TP2" });
  }
  if (typeof decision.stop_loss_price === "number") {
    specs.push({ price: decision.stop_loss_price, color: "#ef4444", title: "止损" });
  }
  return specs;
}
