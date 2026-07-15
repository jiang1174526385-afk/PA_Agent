import { get, post, put } from "./client";
import type {
  AnalysisRecord,
  ChatDebugContextResponse,
  DataSourceChoice,
  DemoRecordListResponse,
  FeishuRead,
  GeneralRead,
  KlineFrame,
  OKXRead,
  ProviderRead,
  PushPlusRead,
  SectionName,
} from "../types/domain";

export function fetchDataSources(): Promise<DataSourceChoice[]> {
  return get<DataSourceChoice[]>("/api/data-sources");
}

export function fetchSymbols(kind: string): Promise<string[]> {
  return get<{ symbols: string[] }>(`/api/data-sources/${kind}/symbols`).then((r) => r.symbols);
}

export function fetchTimeframes(kind: string): Promise<string[]> {
  return get<{ timeframes: string[] }>(`/api/data-sources/${kind}/timeframes`).then(
    (r) => r.timeframes,
  );
}

export function fetchKlineSnapshot(
  source: string,
  symbol: string,
  timeframe: string,
  n: number,
): Promise<KlineFrame> {
  const params = new URLSearchParams({ source, symbol, timeframe, n: String(n) });
  return get<KlineFrame>(`/api/kline/snapshot?${params.toString()}`);
}

export function fetchModels(): Promise<string[]> {
  return get<{ models: string[] }>("/api/ai/models").then((r) => r.models);
}

type SectionReadMap = {
  provider: ProviderRead;
  general: GeneralRead;
  feishu: FeishuRead;
  pushplus: PushPlusRead;
  okx: OKXRead;
};

export function fetchSettingsSection<S extends SectionName>(
  section: S,
): Promise<SectionReadMap[S]> {
  return get(`/api/settings/${section}`);
}

export function saveSettingsSection<S extends SectionName>(
  section: S,
  body: Record<string, unknown>,
): Promise<SectionReadMap[S]> {
  return put(`/api/settings/${section}`, body);
}

export function fetchChatDebugContext(record: AnalysisRecord): Promise<ChatDebugContextResponse> {
  return post<ChatDebugContextResponse>("/api/chat/debug-context", { record });
}

export function fetchDemoRecords(): Promise<DemoRecordListResponse> {
  return get<DemoRecordListResponse>("/api/demo/records");
}
