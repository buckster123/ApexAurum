"""
Presets Routes

API endpoints for managing settings presets.
"""

import logging
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from services.presets_service import get_presets_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class CreatePresetRequest(BaseModel):
    """Request to create a new preset."""
    name: str
    description: str = ""
    provider: str = "ollama"
    model: str = "qwen2.5:3b"
    temperature: float = 0.7
    max_tokens: int = 2048
    use_tools: bool = True
    context_strategy: str = "adaptive"
    context_max_messages: int = 20


class UpdatePresetRequest(BaseModel):
    """Request to update a preset."""
    name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    use_tools: Optional[bool] = None
    context_strategy: Optional[str] = None
    context_max_messages: Optional[int] = None


class DuplicatePresetRequest(BaseModel):
    """Request to duplicate a preset."""
    new_name: str


class ImportPresetsRequest(BaseModel):
    """Request to import presets."""
    presets: dict


# =============================================================================
# Routes
# =============================================================================

@router.get("")
async def list_presets():
    """
    List all available presets.

    Returns both built-in and custom presets.
    """
    service = get_presets_service()
    return {
        "presets": service.list_presets(),
        "active_preset_id": service.active_preset_id
    }


@router.get("/active")
async def get_active_preset():
    """
    Get the currently active preset.
    """
    service = get_presets_service()
    preset = service.get_active_preset()
    if not preset:
        return {"preset": None, "message": "No active preset"}
    return {"preset": preset}


@router.get("/{preset_id}")
async def get_preset(preset_id: str):
    """
    Get a specific preset by ID.
    """
    service = get_presets_service()
    preset = service.get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset


@router.post("")
async def create_preset(request: CreatePresetRequest):
    """
    Create a new custom preset.
    """
    service = get_presets_service()
    preset = service.create_preset(
        name=request.name,
        description=request.description,
        provider=request.provider,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        use_tools=request.use_tools,
        context_strategy=request.context_strategy,
        context_max_messages=request.context_max_messages
    )
    return preset


@router.put("/{preset_id}")
async def update_preset(preset_id: str, request: UpdatePresetRequest):
    """
    Update an existing preset.

    Only custom presets can be updated.
    """
    service = get_presets_service()

    # Build update dict from non-None values
    updates = {k: v for k, v in request.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    preset = service.update_preset(preset_id, **updates)
    if not preset:
        raise HTTPException(
            status_code=404,
            detail="Preset not found or is a built-in preset (cannot modify)"
        )
    return preset


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str):
    """
    Delete a custom preset.

    Built-in presets cannot be deleted.
    """
    service = get_presets_service()
    if not service.delete_preset(preset_id):
        raise HTTPException(
            status_code=404,
            detail="Preset not found or is a built-in preset (cannot delete)"
        )
    return {"success": True, "deleted": preset_id}


@router.post("/{preset_id}/activate")
async def activate_preset(preset_id: str):
    """
    Set a preset as active.

    The active preset's settings will be used as defaults.
    """
    service = get_presets_service()
    preset = service.activate_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"success": True, "activated": preset}


@router.post("/{preset_id}/duplicate")
async def duplicate_preset(preset_id: str, request: DuplicatePresetRequest):
    """
    Duplicate an existing preset with a new name.
    """
    service = get_presets_service()
    preset = service.duplicate_preset(preset_id, request.new_name)
    if not preset:
        raise HTTPException(status_code=404, detail="Source preset not found")
    return preset


@router.get("/export/all")
async def export_presets():
    """
    Export all custom presets for backup.
    """
    service = get_presets_service()
    return {
        "presets": service.export_presets(),
        "count": len(service.export_presets())
    }


@router.post("/import")
async def import_presets(request: ImportPresetsRequest):
    """
    Import presets from backup.
    """
    service = get_presets_service()
    result = service.import_presets(request.presets)
    return result
