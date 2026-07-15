import { useEffect, useState } from "react";
import { fetchPnlCalendar } from "../reportsApi";
import { formatUsd } from "../format";

const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];

export function PnlCalendar({ reportKey, strategy }: { reportKey: string; strategy?: string }) {
  const now = new Date();
  const [year, setYear] = useState(now.getUTCFullYear());
  const [month, setMonth] = useState(now.getUTCMonth() + 1);
  const [byDay, setByDay] = useState<Record<string, number>>({});

  useEffect(() => {
    fetchPnlCalendar(reportKey, year, month, strategy).then(setByDay);
  }, [reportKey, year, month, strategy]);

  function shiftMonth(delta: number) {
    let m = month + delta;
    let y = year;
    if (m < 1) {
      m = 12;
      y -= 1;
    } else if (m > 12) {
      m = 1;
      y += 1;
    }
    setMonth(m);
    setYear(y);
  }

  const firstOfMonth = new Date(Date.UTC(year, month - 1, 1));
  const startWeekday = firstOfMonth.getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const cells: (number | null)[] = [
    ...Array(startWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  return (
    <div className="reports-card" data-testid="pnl-calendar">
      <div className="reports-card-header">
        <span>盈亏日历</span>
        <span>
          <button onClick={() => shiftMonth(-1)}>‹</button>
          {" "}
          {year} 年 {month} 月
          {" "}
          <button onClick={() => shiftMonth(1)}>›</button>
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2, fontSize: 11 }}>
        {WEEKDAYS.map((w) => (
          <div key={w} style={{ textAlign: "center", color: "var(--report-fg-muted)" }}>
            {w}
          </div>
        ))}
        {cells.map((day, i) => {
          if (day === null) return <div key={i} />;
          const key = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
          const pnl = byDay[key];
          const bg = pnl === undefined ? "transparent" : pnl > 0 ? "#dcfce7" : pnl < 0 ? "#fee2e2" : "#f3f4f6";
          return (
            <div
              key={i}
              style={{
                border: "1px solid var(--report-border)",
                borderRadius: 6,
                padding: 4,
                minHeight: 40,
                background: bg,
              }}
            >
              <div>{day}</div>
              {pnl !== undefined && (
                <div style={{ fontSize: 10, color: pnl >= 0 ? "#16a34a" : "#dc2626" }}>{formatUsd(pnl)}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
