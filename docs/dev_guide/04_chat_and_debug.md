# 04 — Free Chat and Debug Panel

> Router: `docs/dev_guide/webui.md`. Read this doc for `/ws/chat`, `ChatRunner`, `ChatPanel.tsx` (timeline + raw-stream), `DebugPanel.tsx` (merged debug + prompt-files), `ValidationDialog.tsx`.

## 1. Architecture

- **Backend**: `pa_agent/webui/services/chat_runner.py::ChatRunner`/`build_chat_session()` — asyncio wrapper over `pa_agent/orchestrator/free_chat.py::FreeChatSession` (core logic, zero changes — only called). Reuses the same `asyncio.to_thread` + `run_coroutine_threadsafe` pattern as `AnalysisRunner`.
- **`/ws/chat` is a fully separate WebSocket from `/ws/analysis`**, not a mode flag on it — deliberate choice (confirmed with the user in phase 5): the desktop's `FreeChatSession` is rebuilt fresh after every completed analysis (`main_window.py:3750`) and depends on process-level singletons (`client`/`assembler`/`pending_writer`/`ledger`) with a different lifecycle than "one submit, one result." A user is very likely to still be typing follow-ups after the analysis WS connection itself has closed.
- **Client→server**: `{"type": "send", ...}`, `{"type": "cancel"}`. **Server→client**: `chat_reasoning`/`chat_content` (streamed chunks), `chat_done`, `chat_error` (with a `cancelled: bool` field distinguishing "you cancelled it" from "it actually failed").
- **Session rebuild trigger**: `pa_agent/webui/api/analysis.py::_run()` calls `build_chat_session()` right after a `record` is produced — the *only* natural rebuild point in the web architecture, mirroring the desktop's `_on_record_ready_impl` (a UI callback the web layer has no direct equivalent of).
- **Debug data**: `POST /api/chat/debug-context` — one call returns everything both `DebugPanel` and `ValidationDialog` need: formatted turns (Stage1/Stage2/exception — **never** follow-up/chat turns, matching the desktop's `DebugWidget.add_turn()` call sites, which never add chat turns either) + prompt-files info, with **server-side secret masking already applied** (`mask_secret`, same string-level API-key replacement as desktop `DebugWidget._mask()` — applies to `system_prompt`/`user_prompt`/`validation_info`/serialized `raw_response`). This combined "already-formatted + already-masked" response pattern means the frontend never touches raw secrets or does its own masking logic — reuse it for any future "show possibly-sensitive raw data" feature.

## 2. Frontend Component Merging (deliberate, not an oversight)

Three desktop widgets were deliberately **not** ported 1:1 — read this before "restoring" a 3-way split:

- **`ConversationWidget` (timeline) + `AiStreamWindow` (raw continuous stream)** → merged into one `ChatPanel.tsx` with a "时间线/原始流" toggle, backed by one `useChatSession.ts` engine and one send box. Both desktop widgets are just two different read-only views over the same `FreeChatSession.send()` calls, not two functionally distinct pieces — porting them separately would mean two independent send/cancel state machines in the web layer for no benefit.
- **`DebugWidget` + `PromptFilesPanel`** → merged into one `DebugPanel.tsx` (prompt-files list rendered inline at the bottom). Both derive from the same `/api/chat/debug-context` call keyed on the current record, and are adjacent in the desktop's "AI 侧边栏" layout anyway (`main_window.py:316-317`). Splitting them would mean either a duplicated network call or introducing a shared state layer this project's architecture doesn't otherwise have.
- **`ValidationDialog.tsx`** independently re-requests `/api/chat/debug-context` rather than sharing `DebugPanel`'s fetch — accepted as a small, rare (dialog only shows when `record.exception` is set and not yet dismissed) duplicate request rather than introducing cross-component request sharing.

## 3. Historical Pitfalls

- **Never `monkeypatch` `DeepSeekClient.stream_chat` (too low-level) in tests — patch `FreeChatSession.send()`** (the public entry point, already encapsulating usage/ledger accumulation), same principle as `TwoStageOrchestrator.submit` being the patch point for analysis tests. See `tests/webui/e2e/conftest.py::_fake_chat_send`.
- **No automated coverage of `/ws/chat`'s behavior against a real DeepSeek API** — pytest/e2e both use hand-constructed fakes; this is a known, standing gap (same category as decision-tree/flow's untested-against-real-model-output gap in `03_decision_tree_and_flow.md`).
- **Unhandled edge case, documented not fixed**: if the user triggers a new analysis while a `/ws/chat` follow-up (`send()`) is still running in its background thread, `state.chat_session` gets replaced by the new record's `build_chat_session()` call, but the *old* thread keeps running to completion and replies via its already-captured `websocket` reference — the reply the user sees may come from a session that's technically already been superseded. This matches the desktop's own behavior (old `_ChatWorker` QThread also runs to completion unblocked by a new `FreeChatSession`), so it's not a regression — but if you need stricter session-generation checking, it doesn't exist yet.

## 4. Also Check

- `02_analysis_and_decision.md` — the record that triggers `build_chat_session()`.
- `08_state_and_layout.md` — `.chat-debug-row`'s place in the `.app-shell` layout budget (this row, added in phase 5, is what first pushed total content height past one screen and forced `.app-shell` from fixed `100vh` to `min-height: 100vh` — see that doc's "layout budget history" section before adding yet another stacked block).
