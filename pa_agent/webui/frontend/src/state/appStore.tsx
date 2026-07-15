import React, { createContext, useContext, useReducer, type Dispatch, type ReactNode } from "react";
import type { AnalysisRecord } from "../types/domain";

export interface StreamBuffers {
  stage1Reasoning: string;
  stage1Content: string;
  stage2Reasoning: string;
  stage2Content: string;
}

export interface AppState {
  source: string;
  symbol: string;
  timeframe: string;
  nBars: number;
  analysisInProgress: boolean;
  statusMessage: string;
  record: AnalysisRecord | null;
  streamBuffers: StreamBuffers;
  errorMessage: string | null;
}

const emptyStreamBuffers: StreamBuffers = {
  stage1Reasoning: "",
  stage1Content: "",
  stage2Reasoning: "",
  stage2Content: "",
};

export const defaultAppState: AppState = {
  // Left blank rather than defaulting to "mt5": MT5 requires a native,
  // logged-in terminal, so eagerly fetching its symbol list on page load
  // would surface a failed-request console entry whenever that terminal
  // isn't available (headless CI, or a desktop without MT5 running).
  source: "",
  symbol: "",
  timeframe: "",
  nBars: 100,
  analysisInProgress: false,
  statusMessage: "",
  record: null,
  streamBuffers: emptyStreamBuffers,
  errorMessage: null,
};

export type Action =
  | { type: "SET_SOURCE"; source: string }
  | { type: "SET_SYMBOL"; symbol: string }
  | { type: "SET_TIMEFRAME"; timeframe: string }
  | { type: "SET_N_BARS"; nBars: number }
  | { type: "ANALYSIS_SUBMITTED" }
  | { type: "ANALYSIS_STATUS"; message: string }
  | {
      type: "ANALYSIS_STREAM_CHUNK";
      stage: "stage1" | "stage2";
      kind: "reasoning" | "content";
      chunk: string;
    }
  | { type: "ANALYSIS_RECORD"; record: AnalysisRecord }
  | { type: "ANALYSIS_ERROR"; message: string };

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_SOURCE":
      return { ...state, source: action.source, symbol: "", timeframe: "" };
    case "SET_SYMBOL":
      return { ...state, symbol: action.symbol };
    case "SET_TIMEFRAME":
      return { ...state, timeframe: action.timeframe };
    case "SET_N_BARS":
      return { ...state, nBars: action.nBars };
    case "ANALYSIS_SUBMITTED":
      return {
        ...state,
        analysisInProgress: true,
        statusMessage: "",
        errorMessage: null,
        streamBuffers: emptyStreamBuffers,
      };
    case "ANALYSIS_STATUS":
      return { ...state, statusMessage: action.message };
    case "ANALYSIS_STREAM_CHUNK": {
      const key = `${action.stage}${action.kind === "reasoning" ? "Reasoning" : "Content"}` as keyof StreamBuffers;
      return {
        ...state,
        streamBuffers: {
          ...state.streamBuffers,
          [key]: state.streamBuffers[key] + action.chunk,
        },
      };
    }
    case "ANALYSIS_RECORD":
      return { ...state, analysisInProgress: false, record: action.record };
    case "ANALYSIS_ERROR":
      return { ...state, analysisInProgress: false, errorMessage: action.message };
    default:
      return state;
  }
}

const AppStateContext = createContext<{ state: AppState; dispatch: Dispatch<Action> } | null>(
  null,
);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, defaultAppState);
  return React.createElement(AppStateContext.Provider, { value: { state, dispatch } }, children);
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used inside AppStateProvider");
  return ctx;
}
