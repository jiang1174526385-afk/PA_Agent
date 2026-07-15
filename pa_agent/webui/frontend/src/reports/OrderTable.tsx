import { useEffect, useState } from "react";
import type { OrderRow } from "../types/domain";
import { fetchReportOrders } from "./reportsApi";
import { formatHoldingDuration } from "./format";

function toCsv(rows: OrderRow[]): string {
  const cols = [
    "record_time", "symbol", "order_direction", "entry_price", "actual_exit_price",
    "pnl_usd", "pnl_pips", "holding_duration_s", "decision_stance",
  ];
  const header = cols.join(",");
  const lines = rows.map((r) => cols.map((c) => JSON.stringify(r[c] ?? "")).join(","));
  return [header, ...lines].join("\n");
}

export function OrderTable({
  reportKey,
  filters,
}: {
  reportKey: string;
  filters: { from?: string; to?: string; strategy?: string };
}) {
  const [rows, setRows] = useState<OrderRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("record_time_desc");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchReportOrders(reportKey, { ...filters, search, sort, page, page_size: pageSize })
      .then((resp) => {
        setRows(resp.rows);
        setTotal(resp.total);
      })
      .finally(() => setLoading(false));
  }, [reportKey, filters.from, filters.to, filters.strategy, search, sort, page, pageSize]);

  function toggleSort(col: string) {
    setSort((prev) => (prev === `${col}_desc` ? `${col}_asc` : `${col}_desc`));
    setPage(1);
  }

  function exportAll() {
    fetchReportOrders(reportKey, { ...filters, search, sort, page: 1, page_size: total || 1 }).then((resp) => {
      const blob = new Blob([toCsv(resp.rows)], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${reportKey}_orders.csv`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="reports-card" data-testid="order-table">
      <div className="reports-order-toolbar">
        <strong>订单明细 共{total}笔</strong>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="品种、方向或备注"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
          <button className="reports-manage-btn" onClick={exportAll}>
            导出全部
          </button>
        </div>
      </div>
      <table className="reports-order-table">
        <thead>
          <tr>
            <th onClick={() => toggleSort("record_time")}>时间</th>
            <th>品种</th>
            <th>方向</th>
            <th>入场价</th>
            <th>出场价</th>
            <th onClick={() => toggleSort("pnl_usd")}>盈亏(USD)</th>
            <th onClick={() => toggleSort("pnl_pips")}>盈亏(点)</th>
            <th>持仓时长</th>
            <th>策略</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const pnl = parseFloat(r.pnl_usd || "0");
            return (
              <tr key={i}>
                <td>{r.record_time}</td>
                <td>{r.symbol}</td>
                <td>{r.order_direction}</td>
                <td>{r.entry_price}</td>
                <td>{r.actual_exit_price || "—"}</td>
                <td className={pnl > 0 ? "pnl-positive" : pnl < 0 ? "pnl-negative" : ""}>
                  {r.fill_status === "filled" ? r.pnl_usd : "—"}
                </td>
                <td>{r.fill_status === "filled" ? r.pnl_pips : "—"}</td>
                <td>{r.fill_status === "filled" ? formatHoldingDuration(r.holding_duration_s) : "—"}</td>
                <td>{r.decision_stance}</td>
                <td>{r.fill_status || "未回填"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {loading && <p className="reports-kpi-sub">加载中…</p>}
      <div className="reports-pagination">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
          上一页
        </button>
        <span>
          第 {page} / {totalPages} 页
        </span>
        <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
          下一页
        </button>
      </div>
    </div>
  );
}
