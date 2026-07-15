import { formatDemoRecordLabel } from "../demo/demoFormat";
import type { DataSourceChoice, DemoRecordSummary } from "../types/domain";

export interface ToolbarProps {
  dataSources: DataSourceChoice[];
  symbols: string[];
  timeframes: string[];
  source: string;
  symbol: string;
  timeframe: string;
  nBars: number;
  hasFrame: boolean;
  analysisInProgress: boolean;
  klineConnected: boolean;
  analysisConnected: boolean;
  onSourceChange: (source: string) => void;
  onSymbolChange: (symbol: string) => void;
  onTimeframeChange: (timeframe: string) => void;
  onNBarsChange: (nBars: number) => void;
  onFetchData: () => void;
  onSubmitFull: () => void;
  onSubmitIncremental: () => void;
  onCancelAnalysis: () => void;
  onOpenSettings: () => void;
  // -- Phase 6: demo replay ---------------------------------------------------
  demoRecords: DemoRecordSummary[];
  demoRecordId: string;
  demoRunning: boolean;
  onDemoRecordChange: (recordId: string) => void;
  onPlayDemo: () => void;
  onPlayRandomDemo: () => void;
}


export function Toolbar(props: ToolbarProps) {
  return (
    <div className="toolbar" data-testid="toolbar">
      <select
        aria-label="数据源"
        value={props.source}
        onChange={(e) => props.onSourceChange(e.target.value)}
      >
        <option value="" disabled>
          选择数据源
        </option>
        {props.dataSources.map((ds) => (
          <option key={ds.kind} value={ds.kind}>
            {ds.label}
          </option>
        ))}
      </select>

      <select
        aria-label="品种"
        value={props.symbol}
        onChange={(e) => props.onSymbolChange(e.target.value)}
      >
        <option value="" disabled>
          选择品种
        </option>
        {props.symbols.map((sym) => (
          <option key={sym} value={sym}>
            {sym}
          </option>
        ))}
      </select>

      <select
        aria-label="周期"
        value={props.timeframe}
        onChange={(e) => props.onTimeframeChange(e.target.value)}
      >
        <option value="" disabled>
          选择周期
        </option>
        {props.timeframes.map((tf) => (
          <option key={tf} value={tf}>
            {tf}
          </option>
        ))}
      </select>

      <input
        aria-label="K线数量"
        type="number"
        min={2}
        max={5000}
        value={props.nBars}
        onChange={(e) => props.onNBarsChange(Number(e.target.value))}
        style={{ width: 72 }}
      />

      <button onClick={props.onFetchData} disabled={!props.symbol || !props.timeframe}>
        获取数据
      </button>

      <button
        onClick={props.onSubmitFull}
        disabled={props.analysisInProgress || !props.hasFrame}
      >
        提交分析
      </button>

      <button
        onClick={props.onSubmitIncremental}
        disabled={props.analysisInProgress || !props.hasFrame}
      >
        增量分析
      </button>

      {props.analysisInProgress && (
        <button onClick={props.onCancelAnalysis}>取消分析</button>
      )}

      <select
        aria-label="演示记录"
        data-testid="demo-record-select"
        value={props.demoRecordId}
        onChange={(e) => props.onDemoRecordChange(e.target.value)}
        disabled={props.demoRecords.length === 0}
      >
        <option value="" disabled>
          {props.demoRecords.length === 0 ? "暂无演示记录" : "选择演示记录"}
        </option>
        {props.demoRecords.map((r) => (
          <option key={r.record_id} value={r.record_id}>
            {formatDemoRecordLabel(r)}
          </option>
        ))}
      </select>

      <button
        data-testid="demo-play-button"
        onClick={props.onPlayDemo}
        disabled={props.analysisInProgress || !props.demoRecordId}
      >
        {props.demoRunning ? "演示回放中…" : "演示模式"}
      </button>

      <button
        data-testid="demo-random-button"
        onClick={props.onPlayRandomDemo}
        disabled={props.analysisInProgress || props.demoRecords.length === 0}
        title="随机播放一条演示记录"
      >
        随机演示
      </button>

      <div className="spacer" />

      <span className={`status-pill ${props.klineConnected ? "connected" : "disconnected"}`}>
        K线 {props.klineConnected ? "已连接" : "未连接"}
      </span>
      <span className={`status-pill ${props.analysisConnected ? "connected" : "disconnected"}`}>
        分析 {props.analysisConnected ? "已连接" : "未连接"}
      </span>

      <button onClick={props.onOpenSettings}>设置</button>
    </div>
  );
}
