import { get, post } from "../api/client";
import type {
  BackfillResponse,
  OrdersResponse,
  ReportListItem,
  ReportSummaryResponse,
} from "../types/domain";

export function fetchReportsList(): Promise<ReportListItem[]> {
  return get<ReportListItem[]>("/api/reports");
}

export function triggerBackfill(key: string, kind: "mt5" | "okx"): Promise<BackfillResponse> {
  const params = new URLSearchParams({ kind });
  return post<BackfillResponse>(`/api/reports/${encodeURIComponent(key)}/backfill?${params}`, {});
}

export interface ReportFilters {
  from?: string;
  to?: string;
  strategy?: string;
}

export function fetchReportSummary(
  key: string,
  filters: ReportFilters = {},
): Promise<ReportSummaryResponse> {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.strategy) params.set("strategy", filters.strategy);
  const qs = params.toString();
  return get<ReportSummaryResponse>(`/api/reports/${encodeURIComponent(key)}/summary${qs ? `?${qs}` : ""}`);
}

export interface OrdersQuery extends ReportFilters {
  search?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export function fetchPnlCalendar(
  key: string,
  year: number,
  month: number,
  strategy?: string,
): Promise<Record<string, number>> {
  const params = new URLSearchParams({ year: String(year), month: String(month) });
  if (strategy) params.set("strategy", strategy);
  return get<Record<string, number>>(`/api/reports/${encodeURIComponent(key)}/calendar?${params}`);
}

export function fetchReportOrders(key: string, query: OrdersQuery = {}): Promise<OrdersResponse> {
  const params = new URLSearchParams();
  if (query.from) params.set("from", query.from);
  if (query.to) params.set("to", query.to);
  if (query.strategy) params.set("strategy", query.strategy);
  if (query.search) params.set("search", query.search);
  if (query.sort) params.set("sort", query.sort);
  params.set("page", String(query.page ?? 1));
  params.set("page_size", String(query.page_size ?? 10));
  return get<OrdersResponse>(`/api/reports/${encodeURIComponent(key)}/orders?${params}`);
}
