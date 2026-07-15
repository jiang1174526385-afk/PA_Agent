import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  LineSeries,
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from "lightweight-charts";
import type { KlineFrame } from "../types/domain";
import { priceLinesFromDecision, type PriceLineSpec } from "./decisionOverlay";
import type { StageDecision } from "../types/domain";

export interface ChartHandles {
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export function useLightweightChart(
  frame: KlineFrame | null,
  decision: StageDecision | null,
): ChartHandles {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ema20SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const atr14SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const priceLinesRef = useRef<ReturnType<ISeriesApi<"Candlestick">["createPriceLine"]>[]>([]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      layout: {
        background: { color: "#0a0e14" },
        textColor: "#e6edf3",
      },
      grid: {
        vertLines: { color: "#1c2128" },
        horzLines: { color: "#1c2128" },
      },
      rightPriceScale: { borderColor: "#30363d" },
      timeScale: { borderColor: "#30363d" },
      autoSize: true,
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });
    candleSeriesRef.current = candleSeries;

    const ema20Series = chart.addSeries(LineSeries, {
      color: "#fbbf24",
      lineWidth: 1,
      priceLineVisible: false,
    });
    ema20SeriesRef.current = ema20Series;

    const atr14Series = chart.addSeries(LineSeries, {
      color: "#7dd3fc",
      lineWidth: 1,
      priceLineVisible: false,
      priceScaleId: "atr14",
    });
    atr14Series.priceScale().applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
    atr14SeriesRef.current = atr14Series;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!frame || !candleSeriesRef.current || !ema20SeriesRef.current || !atr14SeriesRef.current) {
      return;
    }
    // bars[0] is the newest (K1); lightweight-charts wants ascending time order.
    const oldestFirst = [...frame.bars].reverse();
    const candles: CandlestickData[] = oldestFirst.map((bar) => ({
      time: Math.floor(bar.ts_open / 1000) as UTCTimestamp,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));
    candleSeriesRef.current.setData(candles);

    // Warm-up-period indicator values arrive as null (see
    // pa_agent/webui/schemas/kline.py::_nan_to_none); lightweight-charts wants
    // those points omitted entirely rather than passed as NaN/null.
    const ema20Asc = [...frame.indicators.ema20].reverse();
    const ema20Data: LineData[] = oldestFirst
      .map((bar, i) => ({ time: Math.floor(bar.ts_open / 1000) as UTCTimestamp, value: ema20Asc[i] }))
      .filter((p): p is { time: UTCTimestamp; value: number } => p.value !== null);
    ema20SeriesRef.current.setData(ema20Data);

    const atr14Asc = [...frame.indicators.atr14].reverse();
    const atr14Data: LineData[] = oldestFirst
      .map((bar, i) => ({ time: Math.floor(bar.ts_open / 1000) as UTCTimestamp, value: atr14Asc[i] }))
      .filter((p): p is { time: UTCTimestamp; value: number } => p.value !== null);
    atr14SeriesRef.current.setData(atr14Data);
  }, [frame]);

  useEffect(() => {
    const series = candleSeriesRef.current;
    if (!series) return;
    for (const line of priceLinesRef.current) {
      series.removePriceLine(line);
    }
    priceLinesRef.current = [];
    if (!decision) return;
    const specs: PriceLineSpec[] = priceLinesFromDecision(decision);
    priceLinesRef.current = specs.map((spec) =>
      series.createPriceLine({
        price: spec.price,
        color: spec.color,
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: spec.title,
      }),
    );
  }, [decision]);

  return { containerRef };
}
