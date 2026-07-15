"""Read/Write DTOs for the four settings sections exposed to the web UI.

Secret fields (`provider.api_key`, `feishu.secret`, `feishu.app_secret`,
`pushplus.token`) are never echoed in plaintext: GET responses carry a masked
value (`pa_agent.util.mask_secret.mask_secret`) plus an `*_set` boolean, and PUT
requests use `None` = "leave unchanged", `""` = "clear", non-empty = "set new
value" (per phase-1-execution-plan.md §5.4).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from pa_agent.config.settings import (
    FeishuSettings,
    GeneralSettings,
    PushPlusSettings,
    Settings,
)
from pa_agent.util.mask_secret import mask_secret

SectionName = Literal["provider", "general", "feishu", "pushplus"]


class ProviderRead(BaseModel):
    model: str
    base_url: str
    api_key_masked: str
    api_key_set: bool
    thinking: bool
    reasoning_effort: Literal["low", "medium", "high", "max"]
    context_window: int


class ProviderWrite(BaseModel):
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    thinking: bool | None = None
    reasoning_effort: Literal["low", "medium", "high", "max"] | None = None
    context_window: int | None = None


class GeneralRead(BaseModel):
    analysis_bar_count: int
    refresh_interval_ms: int
    context_warning_threshold_pct: float
    last_data_source: str
    kline_adjust: Literal["qfq", "hfq", "none"]
    last_tradingview_exchange: str
    last_symbol: str
    last_timeframe: str
    decision_flow_auto_play: bool
    decision_flow_play_seconds: int
    alert_on_order_opportunity: bool
    incremental_max_new_bars: int
    decision_stance: Literal["conservative", "balanced", "aggressive", "extreme_aggressive"]
    decision_flow_default_zoom_pct: int
    stream_pane_font_pt: int
    chart_seq_label_font_pt: int
    auto_resume_chart_after_analysis: bool
    keep_analysis: bool
    cancel_keep_analysis_on_retry: bool
    decision_confidence_threshold: int
    enable_next_bar_prediction: bool
    structure_flip_cooldown_bars: int


class GeneralWrite(BaseModel):
    analysis_bar_count: int | None = None
    refresh_interval_ms: int | None = None
    context_warning_threshold_pct: float | None = None
    last_data_source: str | None = None
    kline_adjust: Literal["qfq", "hfq", "none"] | None = None
    last_tradingview_exchange: str | None = None
    last_symbol: str | None = None
    last_timeframe: str | None = None
    decision_flow_auto_play: bool | None = None
    decision_flow_play_seconds: int | None = None
    alert_on_order_opportunity: bool | None = None
    incremental_max_new_bars: int | None = None
    decision_stance: (
        Literal["conservative", "balanced", "aggressive", "extreme_aggressive"] | None
    ) = None
    decision_flow_default_zoom_pct: int | None = None
    stream_pane_font_pt: int | None = None
    chart_seq_label_font_pt: int | None = None
    auto_resume_chart_after_analysis: bool | None = None
    keep_analysis: bool | None = None
    cancel_keep_analysis_on_retry: bool | None = None
    decision_confidence_threshold: int | None = None
    enable_next_bar_prediction: bool | None = None
    structure_flip_cooldown_bars: int | None = None


class FeishuRead(BaseModel):
    enabled: bool
    webhook_url: str
    secret_masked: str
    secret_set: bool
    app_id: str
    app_secret_masked: str
    app_secret_set: bool
    notify_on_order_only: bool


class FeishuWrite(BaseModel):
    enabled: bool | None = None
    webhook_url: str | None = None
    secret: str | None = None
    app_id: str | None = None
    app_secret: str | None = None
    notify_on_order_only: bool | None = None


class PushPlusRead(BaseModel):
    enabled: bool
    token_masked: str
    token_set: bool


class PushPlusWrite(BaseModel):
    enabled: bool | None = None
    token: str | None = None


def provider_to_read(p) -> ProviderRead:
    return ProviderRead(
        model=p.model,
        base_url=p.base_url,
        api_key_masked=mask_secret(p.api_key),
        api_key_set=bool(p.api_key.strip()),
        thinking=p.thinking,
        reasoning_effort=p.reasoning_effort,
        context_window=p.context_window,
    )


def general_to_read(g: GeneralSettings) -> GeneralRead:
    return GeneralRead(**{k: getattr(g, k) for k in GeneralRead.model_fields})


def feishu_to_read(f: FeishuSettings) -> FeishuRead:
    return FeishuRead(
        enabled=f.enabled,
        webhook_url=f.webhook_url,
        secret_masked=mask_secret(f.secret),
        secret_set=bool(f.secret.strip()),
        app_id=f.app_id,
        app_secret_masked=mask_secret(f.app_secret),
        app_secret_set=bool(f.app_secret.strip()),
        notify_on_order_only=f.notify_on_order_only,
    )


def pushplus_to_read(pp: PushPlusSettings) -> PushPlusRead:
    return PushPlusRead(
        enabled=pp.enabled,
        token_masked=mask_secret(pp.token),
        token_set=bool(pp.token.strip()),
    )


def apply_provider_write(settings: Settings, write: ProviderWrite) -> None:
    p = settings.provider
    if write.model is not None:
        p.model = write.model
    if write.base_url is not None:
        p.base_url = write.base_url
    if write.api_key is not None:
        p.api_key = write.api_key
    if write.thinking is not None:
        p.thinking = write.thinking
    if write.reasoning_effort is not None:
        p.reasoning_effort = write.reasoning_effort
    if write.context_window is not None:
        p.context_window = write.context_window


def apply_general_write(settings: Settings, write: GeneralWrite) -> None:
    g = settings.general
    for field in GeneralWrite.model_fields:
        value = getattr(write, field)
        if value is not None:
            setattr(g, field, value)


def apply_feishu_write(settings: Settings, write: FeishuWrite) -> None:
    f = settings.feishu
    if write.enabled is not None:
        f.enabled = write.enabled
    if write.webhook_url is not None:
        f.webhook_url = write.webhook_url
    if write.secret is not None:
        f.secret = write.secret
    if write.app_id is not None:
        f.app_id = write.app_id
    if write.app_secret is not None:
        f.app_secret = write.app_secret
    if write.notify_on_order_only is not None:
        f.notify_on_order_only = write.notify_on_order_only


def apply_pushplus_write(settings: Settings, write: PushPlusWrite) -> None:
    pp = settings.pushplus
    if write.enabled is not None:
        pp.enabled = write.enabled
    if write.token is not None:
        pp.token = write.token
