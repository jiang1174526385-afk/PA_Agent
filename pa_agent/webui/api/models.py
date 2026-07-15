"""AI model listing.

`pa_agent/ai/client_factory.py` has no `list_models`/enumeration API -- model
IDs are free-text (`AIProviderSettings.model`). This endpoint returns a curated
list to prefill the settings form's dropdown; the frontend must still allow
free-text entry since arbitrary provider-compatible model IDs are valid.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_CURATED_MODELS = [
    "deepseek-v4-flash",
    "deepseek-chat",
    "deepseek-reasoner",
]


class ModelsResponse(BaseModel):
    models: list[str]


@router.get("/ai/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    return ModelsResponse(models=_CURATED_MODELS)
