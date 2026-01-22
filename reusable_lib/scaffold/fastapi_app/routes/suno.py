"""
Suno Prompt Compiler Routes

API endpoints for the Suno Prompt Compiler - transforms high-level intent
into complex Suno AI prompts with kaomoji, symbols, and emotional cartography.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

# Add parent project to path for tool imports
lib_path = Path(__file__).parent.parent.parent.parent
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from tools.suno_compiler import (
    suno_prompt_build,
    suno_prompt_preset_save,
    suno_prompt_preset_load,
    suno_prompt_preset_list,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class CompileRequest(BaseModel):
    """Request to compile a Suno prompt."""
    intent: str = Field(..., description="High-level description of desired sound")
    mood: str = Field(default="mystical", description="Emotional mood (mystical, ethereal, dark, triumphant, etc.)")
    purpose: str = Field(default="song", description="Purpose: song, sfx, ambient, loop, jingle")
    genre: str = Field(default="", description="Optional genre tags")
    weirdness: int = Field(default=50, ge=0, le=100, description="Experimental factor 0-100")
    style_balance: int = Field(default=50, ge=0, le=100, description="Vocals vs instrumental balance")
    instrumental: bool = Field(default=True, description="Instrumental only (no vocals)")


class PresetSaveRequest(BaseModel):
    """Request to save a preset."""
    name: str = Field(..., description="Preset name (lowercase, underscores)")
    intent: str
    mood: str = "mystical"
    purpose: str = "sfx"
    genre: str = ""
    weirdness: int = 50
    style_balance: int = 50
    instrumental: bool = True


# =============================================================================
# Routes
# =============================================================================

@router.post("/compile")
async def compile_prompt(request: CompileRequest):
    """
    Compile a Suno prompt from high-level intent.

    Transforms simple descriptions into complex Suno prompts using:
    - Kaomoji and symbol injection for Bark/Chirp manipulation
    - Emotional cartography (mood percentage mappings)
    - Non-standard parameters (432Hz tuning, fractional BPM, etc.)
    - Purpose-based duration targeting

    Returns the compiled prompt and ready-to-use music_generate arguments.
    """
    try:
        result = suno_prompt_build(
            intent=request.intent,
            mood=request.mood,
            purpose=request.purpose,
            genre=request.genre,
            weirdness=request.weirdness,
            style_balance=request.style_balance,
            instrumental=request.instrumental,
        )
        return result
    except Exception as e:
        logger.error(f"Compile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def list_presets():
    """
    List all available Suno prompt presets.

    Returns preset names that can be loaded with /presets/{name}.
    """
    try:
        result = suno_prompt_preset_list()
        return result
    except Exception as e:
        logger.error(f"List presets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets/{name}")
async def load_preset(name: str):
    """
    Load a Suno prompt preset by name.

    Returns the preset configuration and compiled prompt ready for music_generate.
    """
    try:
        result = suno_prompt_preset_load(name)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Load preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/presets")
async def save_preset(request: PresetSaveRequest):
    """
    Save a new Suno prompt preset.

    The preset can later be loaded with /presets/{name}.
    """
    try:
        result = suno_prompt_preset_save(
            name=request.name,
            intent=request.intent,
            mood=request.mood,
            purpose=request.purpose,
            genre=request.genre,
            weirdness=request.weirdness,
            style_balance=request.style_balance,
            instrumental=request.instrumental,
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/moods")
async def list_moods():
    """
    List available mood presets with their emotional cartography.
    """
    from tools.suno_compiler import EMOTIONAL_CARTOGRAPHY
    return {
        "moods": list(EMOTIONAL_CARTOGRAPHY.keys()),
        "details": {k: v for k, v in EMOTIONAL_CARTOGRAPHY.items()}
    }


@router.get("/purposes")
async def list_purposes():
    """
    List available purpose types with duration targets.
    """
    from tools.suno_compiler import PURPOSE_DURATION
    return {
        "purposes": list(PURPOSE_DURATION.keys()),
        "durations": PURPOSE_DURATION
    }
