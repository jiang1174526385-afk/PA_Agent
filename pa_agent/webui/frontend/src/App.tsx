import { useEffect, useState } from "react";
import { ChartView } from "./chart/ChartView";
import { ChatPanel } from "./chat/ChatPanel";
import { DecisionPanel } from "./decision/DecisionPanel";
import { FutureTrendPanel } from "./decision/FutureTrendPanel";
import { DecisionTreePanel } from "./decisionTree/DecisionTreePanel";
import { DecisionFlowPanel } from "./decisionFlow/DecisionFlowPanel";
import { DebugPanel } from "./debug/DebugPanel";
import { ValidationDialog } from "./debug/ValidationDialog";
import { fetchDataSources, fetchKlineSnapshot, fetchSymbols, fetchTimeframes } from "./api/paAgentApi";
import { useAnalysisSocket, useKlineSocket, type KlineSubscribeParams } from "./api/paAgentWs";
import { SettingsModal } from "./settings/SettingsModal";
import { useAppState } from "./state/appStore";
import { Toolbar } from "./toolbar/Toolbar";
import type { DataSourceChoice, KlineFrame } from "./types/domain";

export function App() {
  const { state, dispatch } = useAppState();
  const [dataSources, setDataSources] = useState<DataSourceChoice[]>([]);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [timeframes, setTimeframes] = useState<string[]>([]);
  const [klineParams, setKlineParams] = useState<KlineSubscribeParams | null>(null);
  const [snapshotFrame, setSnapshotFrame] = useState<KlineFrame | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [dismissedExceptionAt, setDismissedExceptionAt] = useState<number | null>(null);

  useEffect(() => {
    fetchDataSources().then(setDataSources);
  }, []);

  useEffect(() => {
    if (!state.source) return;
    // A data source can legitimately be unreachable (e.g. MT5 requires a
    // native terminal that isn't installed/logged in) -- surface it as a
    // status message instead of an unhandled rejection/console error.
    fetchSymbols(state.source)
      .then(setSymbols)
      .catch((err) => {
        setSymbols([]);
        dispatch({ type: "ANALYSIS_STATUS", message: `获取品种列表失败: ${err.message}` });
      });
    fetchTimeframes(state.source)
      .then(setTimeframes)
      .catch(() => setTimeframes([]));
  }, [state.source]);

  const kline = useKlineSocket(klineParams);
  const analysis = useAnalysisSocket((msg) => {
    switch (msg.type) {
      case "event":
        dispatch({ type: "ANALYSIS_STATUS", message: msg.message });
        break;
      case "stage1_reasoning":
        dispatch({ type: "ANALYSIS_STREAM_CHUNK", stage: "stage1", kind: "reasoning", chunk: msg.chunk });
        break;
      case "stage1_content":
        dispatch({ type: "ANALYSIS_STREAM_CHUNK", stage: "stage1", kind: "content", chunk: msg.chunk });
        break;
      case "stage2_reasoning":
        dispatch({ type: "ANALYSIS_STREAM_CHUNK", stage: "stage2", kind: "reasoning", chunk: msg.chunk });
        break;
      case "stage2_content":
        dispatch({ type: "ANALYSIS_STREAM_CHUNK", stage: "stage2", kind: "content", chunk: msg.chunk });
        break;
      case "record":
        dispatch({ type: "ANALYSIS_RECORD", record: msg.record });
        break;
      case "error":
        dispatch({ type: "ANALYSIS_ERROR", message: msg.message });
        break;
      default:
        break;
    }
  });

  function handleSourceChange(source: string) {
    dispatch({ type: "SET_SOURCE", source });
    setSymbols([]);
    setTimeframes([]);
    setKlineParams(null);
  }

  function handleFetchData() {
    if (!state.symbol || !state.timeframe) return;
    // Immediate one-shot snapshot for instant render; /ws/kline then takes
    // over for live refresh.
    fetchKlineSnapshot(state.source, state.symbol, state.timeframe, state.nBars).then(
      setSnapshotFrame,
    );
    setKlineParams({
      source: state.source,
      symbol: state.symbol,
      timeframe: state.timeframe,
      n_bars: state.nBars,
    });
  }

  function handleSubmitFull() {
    dispatch({ type: "ANALYSIS_SUBMITTED" });
    analysis.submit({ type: "submit", mode: "full" });
  }

  function handleSubmitIncremental() {
    dispatch({ type: "ANALYSIS_SUBMITTED" });
    analysis.submit({ type: "submit", mode: "incremental" });
  }

  const decision = state.record?.stage2_decision ?? null;
  const showValidationDialog =
    state.record !== null &&
    state.record.exception !== null &&
    dismissedExceptionAt !== state.record.meta.timestamp_local_ms;

  return (
    <div className="app-shell">
      <Toolbar
        dataSources={dataSources}
        symbols={symbols}
        timeframes={timeframes}
        source={state.source}
        symbol={state.symbol}
        timeframe={state.timeframe}
        nBars={state.nBars}
        hasFrame={kline.frame !== null}
        analysisInProgress={state.analysisInProgress}
        klineConnected={kline.connected}
        analysisConnected={analysis.connected}
        onSourceChange={handleSourceChange}
        onSymbolChange={(symbol) => dispatch({ type: "SET_SYMBOL", symbol })}
        onTimeframeChange={(timeframe) => dispatch({ type: "SET_TIMEFRAME", timeframe })}
        onNBarsChange={(nBars) => dispatch({ type: "SET_N_BARS", nBars })}
        onFetchData={handleFetchData}
        onSubmitFull={handleSubmitFull}
        onSubmitIncremental={handleSubmitIncremental}
        onCancelAnalysis={() => analysis.cancel()}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <div className="main-layout">
        <ChartView frame={kline.frame ?? snapshotFrame} decision={decision} />
        <div className="side-pane">
          {state.statusMessage && <div className="panel">{state.statusMessage}</div>}
          {state.errorMessage && (
            <div className="panel" style={{ color: "var(--danger)" }}>
              {state.errorMessage}
            </div>
          )}
          <DecisionPanel decision={decision} />
          <FutureTrendPanel decision={decision} />
          <DecisionTreePanel record={state.record} />
        </div>
      </div>

      <div className="flow-row">
        <DecisionFlowPanel record={state.record} />
      </div>

      <div className="chat-debug-row">
        <ChatPanel record={state.record} />
        <DebugPanel record={state.record} />
      </div>

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
      {showValidationDialog && state.record && (
        <ValidationDialog
          record={state.record}
          onClose={() => setDismissedExceptionAt(state.record!.meta.timestamp_local_ms)}
        />
      )}
    </div>
  );
}
