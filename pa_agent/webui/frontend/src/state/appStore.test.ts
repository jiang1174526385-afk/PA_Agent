import { describe, expect, it } from "vitest";
import { defaultAppState, reducer, type AppState } from "./appStore";

describe("appStore reducer", () => {
  it("resets symbol/timeframe when the data source changes", () => {
    const state = { ...defaultAppState, symbol: "BTC-USDT-SWAP", timeframe: "15m" };
    const next = reducer(state, { type: "SET_SOURCE", source: "okx" });
    expect(next.source).toBe("okx");
    expect(next.symbol).toBe("");
    expect(next.timeframe).toBe("");
  });

  it("accumulates stream chunks per stage/kind independently", () => {
    let state = defaultAppState;
    state = reducer(state, { type: "ANALYSIS_STREAM_CHUNK", stage: "stage1", kind: "reasoning", chunk: "a" });
    state = reducer(state, { type: "ANALYSIS_STREAM_CHUNK", stage: "stage1", kind: "reasoning", chunk: "b" });
    state = reducer(state, { type: "ANALYSIS_STREAM_CHUNK", stage: "stage2", kind: "content", chunk: "x" });
    expect(state.streamBuffers.stage1Reasoning).toBe("ab");
    expect(state.streamBuffers.stage2Content).toBe("x");
    expect(state.streamBuffers.stage1Content).toBe("");
  });

  it("clears stream buffers and errors on a new submission", () => {
    let state: AppState = { ...defaultAppState, errorMessage: "boom" };
    state = reducer(state, {
      type: "ANALYSIS_STREAM_CHUNK",
      stage: "stage1",
      kind: "content",
      chunk: "leftover",
    });
    state = reducer(state, { type: "ANALYSIS_SUBMITTED" });
    expect(state.analysisInProgress).toBe(true);
    expect(state.errorMessage).toBeNull();
    expect(state.streamBuffers.stage1Content).toBe("");
  });

  it("marks analysis finished on record and on error", () => {
    let state = { ...defaultAppState, analysisInProgress: true };
    const withRecord = reducer(state, {
      type: "ANALYSIS_RECORD",
      record: {
        meta: {} as never,
        stage1_messages: [],
        stage1_response: null,
        stage1_diagnosis: null,
        stage2_messages: [],
        stage2_response: null,
        stage2_decision: null,
        strategy_files_used: [],
        experience_loaded: [],
        exception: null,
      },
    });
    expect(withRecord.analysisInProgress).toBe(false);

    state = reducer(state, { type: "ANALYSIS_ERROR", message: "网络错误" });
    expect(state.analysisInProgress).toBe(false);
    expect(state.errorMessage).toBe("网络错误");
  });
});
