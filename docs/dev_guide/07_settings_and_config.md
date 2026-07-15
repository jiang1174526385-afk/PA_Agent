# 07 — Settings API and the Settings Modal

> Router: `docs/dev_guide/webui.md`. Read this doc before adding/changing any `config/settings.json` field exposed through the web UI.

## 1. Architecture

- **Schema**: `pa_agent/webui/schemas/settings.py` — five sections, `SectionName = Literal["provider", "general", "feishu", "pushplus", "okx"]`. Each has a `*Read` (GET response) and `*Write` (PUT request) Pydantic model, plus a `*_to_read()`/`apply_*_write()` function pair. `general_to_read()` is the one exception that auto-derives from `GeneralRead.model_fields` (so `GeneralSettings` and `GeneralRead` field names must stay identical) rather than listing fields by hand like the other four sections do.
- **Route layer**: `pa_agent/webui/api/settings.py` — `GET`/`PUT /api/settings/{section}`.
- **Frontend**: `src/settings/SettingsModal.tsx` + one tab component per section: `ProviderTab.tsx`, `GeneralTab.tsx`, `FeishuTab.tsx`, `PushPlusTab.tsx`, `OKXTab.tsx`. `SecretInput.tsx` is the shared masked-input component used by every secret field.

## 2. Secret-Masking Pattern — Follow This For Any New Secret Field

Every secret field (`provider.api_key`, `feishu.secret`, `feishu.app_secret`, `pushplus.token`, `okx.api_key`/`api_secret`/`passphrase`) follows the same contract:

- **GET** returns `{field}_masked: str` (via `pa_agent.util.mask_secret.mask_secret`) + `{field}_set: bool` — **never** the plaintext value.
- **PUT** accepts the raw field name (e.g. `api_key: str | None`): `None` = leave unchanged, `""` = clear, non-empty = set to this new value.
- `apply_*_write()` functions implement this via `if write.field is not None: target.field = write.field` — copy this exact pattern for a new secret field, don't invent a different unset/clear convention.

## 3. `GeneralSettings` — Full Current Field List (as of phase 7)

`analysis_bar_count`, `refresh_interval_ms`, `context_warning_threshold_pct`, `last_data_source`, `kline_adjust`, `last_tradingview_exchange`, `last_symbol`, `last_timeframe`, `decision_flow_auto_play`, `decision_flow_play_seconds`, `alert_on_order_opportunity`, `incremental_max_new_bars`, `decision_stance`, `decision_flow_default_zoom_pct`, `stream_pane_font_pt`, `chart_seq_label_font_pt`, `auto_resume_chart_after_analysis`, `keep_analysis`, `cancel_keep_analysis_on_retry`, `decision_confidence_threshold`, `enable_next_bar_prediction`, `structure_flip_cooldown_bars`.

**Note the decision-flow field is named `decision_flow_play_seconds` ("播放秒数"), not "duration"/"时长".** A phase-7 review nearly logged this as a missing feature because it searched for the keyword "duration" and got no hits — **when checking whether some configurable value exists, grep multiple plausible names (seconds/duration/ms/时长/秒数), not just one**, before concluding it's missing.

## 4. Known Limitations (documented, not bugs to silently fix)

- **`GET /api/ai/models` (`pa_agent/webui/api/models.py`) is a hardcoded curated list** (`deepseek-v4-flash`/`deepseek-chat`/`deepseek-reasoner` at time of writing), not a real model-enumeration call — `pa_agent/ai/client_factory.py` has no such API. The frontend allows free-text entry as a fallback. If more providers are added, this list's maintenance approach may need revisiting, but that's a separate decision, not an implicit part of any feature work touching settings.
- **`notify_on_order_only` (Feishu section) has never been read/consumed by either the desktop GUI or the web layer** — see `05_demo_and_notify.md` §3 for the full context. Do not wire it up without asking the user first.
- **`decision_stance`'s allowed values are a fixed enum** (`conservative`/`balanced`/`aggressive`/`extreme_aggressive`) consumed by both stage-2 AI decision behavior and (separately) the `06_reports_dashboard.md` strategy filter dropdown — if this enum changes, both consumers need updating, they don't share a single source of truth beyond this Pydantic `Literal`.

## 5. Also Check

- `03_decision_tree_and_flow.md` — `decision_flow_auto_play`/`decision_flow_play_seconds`/`decision_flow_default_zoom_pct` consumption.
- `06_reports_dashboard.md` — the `okx` section (`api_key`/`api_secret`/`passphrase`) feeding the backfill pipeline.
- `01_kline_and_chart.md` — `refresh_interval_ms`.
