// Hand-kept mirror of pa_agent/webui/schemas/*.py -- no auto-generation
// (see docs/webui_migration/README.md §7 global quality requirements).

export interface KlineBar {
  seq: number;
  ts_open: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
  pct_chg: number | null;
  closed: boolean;
}

export interface IndicatorBundle {
  ema20: (number | null)[];
  atr14: (number | null)[];
}

export interface KlineFrame {
  symbol: string;
  timeframe: string;
  bars: KlineBar[];
  indicators: IndicatorBundle;
  snapshot_ts_local_ms: number;
}

export interface DataSourceChoice {
  kind: string;
  label: string;
}

// -- WS /ws/kline messages --------------------------------------------------

export type KlineWsInbound =
  | { type: "subscribed"; epoch: number }
  | { type: "frame"; epoch: number; frame: KlineFrame }
  | { type: "status"; epoch: number; message: string }
  | { type: "error"; epoch: number; message: string };

export interface KlineWsSubscribe {
  type: "subscribe";
  source: string;
  symbol: string;
  timeframe: string;
  n_bars: number;
  interval_ms?: number;
}

// -- Decision / analysis result ----------------------------------------------

export interface NextBarPrediction {
  unpredictable?: boolean;
  probabilities?: { bullish: number; bearish: number; neutral: number };
  reasoning?: string;
}

export interface NextCyclePrediction {
  unpredictable?: boolean;
  direction?: "bullish" | "bearish" | "neutral";
  probabilities?: Record<string, number>;
  reasoning?: string;
}

export interface StageDecision {
  order_type?: string;
  reasoning?: string;
  brief_reasoning?: string;
  direction?: string;
  cycle_position?: string;
  alternative_cycle_position?: string;
  market_phase?: string;
  transition_risk?: string;
  diagnosis_confidence?: number;
  diagnosis_confidence_reasoning?: string;
  trade_confidence?: number;
  trade_confidence_reasoning?: string;
  order_direction?: string;
  entry_price?: number | null;
  take_profit_price?: number | null;
  take_profit_price_2?: number | null;
  stop_loss_price?: number | null;
  estimated_win_rate?: number | null;
  next_bar_prediction?: NextBarPrediction | null;
  next_cycle_prediction?: NextCyclePrediction | null;
}

export interface RecordMeta {
  timestamp_local_iso: string;
  timestamp_local_ms: number;
  symbol: string;
  timeframe: string;
  bar_count: number;
  ai_provider: Record<string, unknown>;
  decision_stance: string;
}

export interface AnalysisRecord {
  meta: RecordMeta;
  stage1_diagnosis: Record<string, unknown> | null;
  stage2_decision: StageDecision | null;
  exception: Record<string, unknown> | null;
  [key: string]: unknown;
}

// -- WS /ws/analysis messages -------------------------------------------------

export type AnalysisWsInbound =
  | { type: "event"; event: string; message: string }
  | { type: "stage1_reasoning"; chunk: string }
  | { type: "stage1_content"; chunk: string }
  | { type: "stage2_reasoning"; chunk: string }
  | { type: "stage2_content"; chunk: string }
  | { type: "stage_prompt"; stage: string; system: string; user: string }
  | { type: "stage2_files"; files: string[] }
  | { type: "record"; record: AnalysisRecord }
  | { type: "error"; message: string };

export interface AnalysisWsSubmit {
  type: "submit";
  mode: "full" | "incremental";
  n_bars?: number;
  incremental_new_bar_count?: number;
}

export type AnalysisWsCancel = { type: "cancel" };

// -- Settings ------------------------------------------------------------

export interface ProviderRead {
  model: string;
  base_url: string;
  api_key_masked: string;
  api_key_set: boolean;
  thinking: boolean;
  reasoning_effort: "low" | "medium" | "high" | "max";
  context_window: number;
}

export interface GeneralRead {
  analysis_bar_count: number;
  refresh_interval_ms: number;
  context_warning_threshold_pct: number;
  last_data_source: string;
  kline_adjust: "qfq" | "hfq" | "none";
  last_tradingview_exchange: string;
  last_symbol: string;
  last_timeframe: string;
  decision_flow_auto_play: boolean;
  decision_flow_play_seconds: number;
  alert_on_order_opportunity: boolean;
  incremental_max_new_bars: number;
  decision_stance: "conservative" | "balanced" | "aggressive" | "extreme_aggressive";
  decision_flow_default_zoom_pct: number;
  stream_pane_font_pt: number;
  chart_seq_label_font_pt: number;
  auto_resume_chart_after_analysis: boolean;
  keep_analysis: boolean;
  cancel_keep_analysis_on_retry: boolean;
  decision_confidence_threshold: number;
  enable_next_bar_prediction: boolean;
  structure_flip_cooldown_bars: number;
}

export interface FeishuRead {
  enabled: boolean;
  webhook_url: string;
  secret_masked: string;
  secret_set: boolean;
  app_id: string;
  app_secret_masked: string;
  app_secret_set: boolean;
  notify_on_order_only: boolean;
}

export interface PushPlusRead {
  enabled: boolean;
  token_masked: string;
  token_set: boolean;
}

export type SectionName = "provider" | "general" | "feishu" | "pushplus";
