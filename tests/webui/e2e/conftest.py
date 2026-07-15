"""Playwright e2e fixtures: a real uvicorn instance serving the built SPA,
backed by a real `AppContext.bootstrap()` (real OKX data source over the
network) but with `TwoStageOrchestrator.submit` monkeypatched to a fast,
deterministic fake -- driving the real DeepSeek API in e2e would need a paid
API key and be slow/non-deterministic, which is out of scope for a UI-wiring
smoke test. Settings/records paths are redirected to a tmp dir so the suite
never touches the real config/settings.json or records/pending/.
"""

from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn

from pa_agent.records.schema import AnalysisRecord, RecordMeta
from pa_agent.util.threading import OrchestratorEvent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _build_record(frame, previous_record, *, cancelled: bool) -> AnalysisRecord:
    meta = RecordMeta(
        timestamp_local_iso="2026-07-15T00:00:00",
        timestamp_local_ms=0,
        symbol=frame.symbol,
        timeframe=frame.timeframe,
        bar_count=len(frame.bars),
        ai_provider={"model": "e2e-fake"},
    )
    return AnalysisRecord(
        meta=meta,
        kline_data=[],
        htf_text="",
        stage1_messages=[],
        stage1_response=None,
        stage1_diagnosis=(
            None
            if cancelled
            else {
                "direction": "上涨",
                "market_phase": "stable",
                "gate_result": "proceed",
                "gate_trace": [
                    {
                        "node_id": "1.1",
                        "question": "[e2e] 是否存在明确趋势方向？（基于K10-K1判断）",
                        "answer": "是",
                        "reason": "[e2e] 趋势清晰",
                        "bar_range": "K10-K1",
                    },
                ],
            }
        ),
        stage2_messages=[],
        stage2_response=None,
        stage2_decision=(
            None
            if cancelled
            else {
                "order_type": "买入",
                "order_direction": "做多",
                "trade_confidence": 82,
                "diagnosis_confidence": 75,
                "entry_price": 100.0,
                "take_profit_price": 110.0,
                "stop_loss_price": 95.0,
                "reasoning": "E2E fake analysis result for smoke testing.",
                "estimated_win_rate": 60,
                "decision_trace": [
                    {
                        "node_id": "9.0",
                        "question": "[e2e] 是否存在有效入场信号？",
                        "answer": "是",
                        "reason": "[e2e] 信号有效",
                        "bar_range": "K1",
                    },
                    {
                        "node_id": "10.3",
                        "question": "[e2e] 交易者方程是否成立？",
                        "answer": "是",
                        "reason": "[e2e] 盈亏比达标",
                        "bar_range": "K1",
                    },
                ],
                "terminal": {"node_id": "10.3", "outcome": "trade", "label": "[e2e] 满足下单条件"},
                "gate_shortcircuited": False,
            }
        ),
        strategy_files_used=["e2e_strategy.txt"],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )


def _fake_submit(
    self,
    frame,
    cancel_token,
    on_event,
    *,
    on_stage1_reasoning=None,
    on_stage1_content=None,
    on_stage2_reasoning=None,
    on_stage2_content=None,
    on_stage_prompt=None,
    on_stage2_files=None,
    previous_record=None,
    incremental_new_bar_count=None,
):
    on_event(OrchestratorEvent.Stage1Started)
    if on_stage1_reasoning:
        on_stage1_reasoning("[e2e] stage1 reasoning...\n")
    if on_stage1_content:
        on_stage1_content('{"diagnosis": "e2e"}')

    for _ in range(60):
        if cancel_token.is_set():
            record = _build_record(frame, previous_record, cancelled=True)
            self._pending_writer.save_partial(record, "user_cancelled")
            on_event(OrchestratorEvent.Cancelled)
            return record
        time.sleep(0.05)

    on_event(OrchestratorEvent.Stage1Done)
    if on_stage_prompt:
        on_stage_prompt("stage2", "[e2e] system prompt", "[e2e] user prompt")
    if on_stage2_files:
        on_stage2_files(["e2e_strategy.txt"])
    on_event(OrchestratorEvent.Stage2Started)
    if on_stage2_reasoning:
        on_stage2_reasoning("[e2e] stage2 reasoning...\n")
    if on_stage2_content:
        on_stage2_content('{"order_type": "买入"}')
    on_event(OrchestratorEvent.Stage2Done)

    record = _build_record(frame, previous_record, cancelled=False)
    self._pending_writer.save_full(record)
    on_event(OrchestratorEvent.RecordSaved)
    return record


def _fake_chat_send(self, user_text, cancel_token, on_reasoning_token=None, on_content_token=None):
    """Fake `FreeChatSession.send()` -- mirrors `_fake_submit` above: driving
    the real DeepSeek API in e2e would need a paid key and be
    slow/non-deterministic (phase-5-execution-plan.md §7)."""
    from pa_agent.ai.deepseek_client import AIReply, AIUsage, CancelledError

    if cancel_token.is_set():
        raise CancelledError("e2e cancelled before call")
    if on_reasoning_token:
        on_reasoning_token(f"[e2e] 追问思考：{user_text}\n")
    if on_content_token:
        on_content_token(f"[e2e] 关于「{user_text}」的建议：维持当前止损位不变。")
    usage = AIUsage(prompt_tokens=120, cached_prompt_tokens=40, completion_tokens=30, total_tokens=150)
    self._ledger.add(usage)
    return AIReply(
        content=f"[e2e] 关于「{user_text}」的建议：维持当前止损位不变。",
        reasoning_content=f"[e2e] 追问思考：{user_text}\n",
        raw={"id": "e2e-chat", "model": "e2e-fake", "usage": {}},
        usage=usage,
        request_id="e2e-chat",
        latency_ms=5.0,
    )


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    from pa_agent.orchestrator.free_chat import FreeChatSession
    from pa_agent.orchestrator.two_stage import TwoStageOrchestrator

    monkeypatch.setattr(TwoStageOrchestrator, "submit", _fake_submit)
    monkeypatch.setattr(FreeChatSession, "send", _fake_chat_send)
    monkeypatch.setattr("pa_agent.config.paths.SETTINGS_JSON_PATH", tmp_path / "settings.json")
    records_dir = tmp_path / "records" / "pending"
    monkeypatch.setattr("pa_agent.config.paths.RECORDS_PENDING_DIR", records_dir)

    # Import after monkeypatching paths so a fresh `server` module state isn't required
    # (AppContext.bootstrap() re-imports paths lazily inside the classmethod body).
    import importlib

    from pa_agent.webui import server as server_module

    importlib.reload(server_module)

    port = _free_port()
    config = uvicorn.Config(server_module.app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            import urllib.request

            with urllib.request.urlopen(f"{base_url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.2)
    else:
        raise RuntimeError("webui server did not become healthy in time")

    yield {"base_url": base_url, "records_dir": records_dir}

    server.should_exit = True
    thread.join(timeout=10)
