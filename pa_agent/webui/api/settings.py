"""Settings CRUD (AI provider / general / feishu / pushplus). No notification
triggering here -- see phase-1 execution plan §2 non-goals.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from pa_agent.config.settings import load_settings, save_settings
from pa_agent.webui.schemas.settings import (
    FeishuWrite,
    GeneralWrite,
    ProviderWrite,
    PushPlusWrite,
    apply_feishu_write,
    apply_general_write,
    apply_provider_write,
    apply_pushplus_write,
    feishu_to_read,
    general_to_read,
    provider_to_read,
    pushplus_to_read,
)

router = APIRouter()

_READERS = {
    "provider": lambda s: provider_to_read(s.provider),
    "general": lambda s: general_to_read(s.general),
    "feishu": lambda s: feishu_to_read(s.feishu),
    "pushplus": lambda s: pushplus_to_read(s.pushplus),
}

_WRITE_MODELS = {
    "provider": ProviderWrite,
    "general": GeneralWrite,
    "feishu": FeishuWrite,
    "pushplus": PushPlusWrite,
}

_APPLIERS = {
    "provider": apply_provider_write,
    "general": apply_general_write,
    "feishu": apply_feishu_write,
    "pushplus": apply_pushplus_write,
}


@router.get("/settings/{section}")
async def get_settings_section(section: str) -> Any:
    if section not in _READERS:
        raise HTTPException(status_code=404, detail=f"未知设置分区: {section}")
    settings = load_settings()
    return _READERS[section](settings)


@router.put("/settings/{section}")
async def put_settings_section(section: str, body: dict[str, Any]) -> Any:
    if section not in _WRITE_MODELS:
        raise HTTPException(status_code=404, detail=f"未知设置分区: {section}")
    write = _WRITE_MODELS[section].model_validate(body)
    settings = load_settings()
    _APPLIERS[section](settings, write)
    save_settings(settings)
    return _READERS[section](settings)
