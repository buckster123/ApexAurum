"""
Audio Editor Routes

API endpoints for audio manipulation - trim, fade, normalize, loop, speed, etc.
Used by the DJ Booth for post-processing generated music.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

# Add parent project to path for tool imports
lib_path = Path(__file__).parent.parent.parent.parent
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from tools.audio_editor import (
    audio_info,
    audio_trim,
    audio_fade,
    audio_normalize,
    audio_loop,
    audio_concat,
    audio_speed,
    audio_reverse,
    audio_list_files,
    audio_get_waveform,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class TrimRequest(BaseModel):
    """Request to trim audio."""
    file_path: str = Field(..., description="Path to audio file")
    start: Union[str, float] = Field(default=0, description="Start time (seconds or MM:SS)")
    end: Optional[Union[str, float]] = Field(default=None, description="End time (seconds or MM:SS)")
    output_path: Optional[str] = Field(default=None, description="Output path (auto-generated if not provided)")


class FadeRequest(BaseModel):
    """Request to add fades."""
    file_path: str = Field(..., description="Path to audio file")
    fade_in_ms: int = Field(default=0, ge=0, description="Fade in duration in milliseconds")
    fade_out_ms: int = Field(default=0, ge=0, description="Fade out duration in milliseconds")
    output_path: Optional[str] = Field(default=None)


class NormalizeRequest(BaseModel):
    """Request to normalize audio."""
    file_path: str = Field(..., description="Path to audio file")
    target_dbfs: float = Field(default=-14.0, description="Target loudness in dBFS")
    output_path: Optional[str] = Field(default=None)


class LoopRequest(BaseModel):
    """Request to loop audio."""
    file_path: str = Field(..., description="Path to audio file")
    loop_count: int = Field(default=2, ge=1, le=10, description="Number of loops")
    crossfade_ms: int = Field(default=100, ge=0, description="Crossfade duration between loops")
    output_path: Optional[str] = Field(default=None)


class ConcatRequest(BaseModel):
    """Request to concatenate audio files."""
    file_paths: List[str] = Field(..., description="List of audio file paths to concatenate")
    crossfade_ms: int = Field(default=0, ge=0, description="Crossfade duration between files")
    output_path: Optional[str] = Field(default=None)


class SpeedRequest(BaseModel):
    """Request to change audio speed."""
    file_path: str = Field(..., description="Path to audio file")
    speed_factor: float = Field(default=1.0, gt=0.25, le=4.0, description="Speed multiplier (0.25-4.0)")
    preserve_pitch: bool = Field(default=True, description="Preserve pitch when changing speed")
    output_path: Optional[str] = Field(default=None)


class ReverseRequest(BaseModel):
    """Request to reverse audio."""
    file_path: str = Field(..., description="Path to audio file")
    output_path: Optional[str] = Field(default=None)


class WaveformRequest(BaseModel):
    """Request for waveform data."""
    file_path: str = Field(..., description="Path to audio file")
    num_points: int = Field(default=200, ge=50, le=1000, description="Number of waveform points")


# =============================================================================
# Routes
# =============================================================================

@router.get("/list")
async def list_audio_files(
    folder: Optional[str] = None,
    pattern: str = "*.mp3"
):
    """
    List audio files in a directory.

    Defaults to the sandbox/music directory.
    """
    try:
        result = audio_list_files(folder=folder)
        return result
    except Exception as e:
        logger.error(f"List files error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_audio_info(file_path: str):
    """
    Get information about an audio file.

    Returns duration, format, channels, sample rate, etc.
    """
    try:
        result = audio_info(file_path)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/waveform")
async def get_waveform(request: WaveformRequest):
    """
    Get waveform data for visualization.

    Returns array of amplitude values for drawing waveform.
    """
    try:
        result = audio_get_waveform(request.file_path, request.num_points)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Waveform error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trim")
async def trim_audio(request: TrimRequest):
    """
    Trim audio to specified start and end times.

    Times can be specified as:
    - Seconds (float): 5.5, 10.0
    - MM:SS format: "1:30", "0:45"
    """
    try:
        result = audio_trim(
            file_path=request.file_path,
            start=request.start,
            end=request.end,
            output_path=request.output_path
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trim error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fade")
async def fade_audio(request: FadeRequest):
    """
    Add fade in and/or fade out to audio.
    """
    try:
        result = audio_fade(
            file_path=request.file_path,
            fade_in_ms=request.fade_in_ms,
            fade_out_ms=request.fade_out_ms,
            output_path=request.output_path
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fade error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/normalize")
async def normalize_audio(request: NormalizeRequest):
    """
    Normalize audio to target loudness level.

    Standard targets:
    - Streaming: -14 dBFS
    - Broadcast: -23 dBFS
    - CD: -9 dBFS
    """
    try:
        result = audio_normalize(
            file_path=request.file_path,
            target_dbfs=request.target_dbfs,
            output_path=request.output_path
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Normalize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/loop")
async def loop_audio(request: LoopRequest):
    """
    Create a looped version of audio with crossfade.
    """
    try:
        result = audio_loop(
            file_path=request.file_path,
            loop_count=request.loop_count,
            crossfade_ms=request.crossfade_ms,
            output_path=request.output_path
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Loop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/concat")
async def concat_audio(request: ConcatRequest):
    """
    Concatenate multiple audio files.
    """
    try:
        result = audio_concat(
            file_paths=request.file_paths,
            crossfade_ms=request.crossfade_ms,
            output_path=request.output_path
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Concat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speed")
async def change_speed(request: SpeedRequest):
    """
    Change audio playback speed.

    With preserve_pitch=True, pitch stays the same.
    Without it, pitch changes with speed (chipmunk/slowed effect).
    """
    try:
        result = audio_speed(
            file_path=request.file_path,
            speed_factor=request.speed_factor,
            preserve_pitch=request.preserve_pitch,
            output_path=request.output_path
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reverse")
async def reverse_audio(request: ReverseRequest):
    """
    Reverse audio playback.
    """
    try:
        result = audio_reverse(
            file_path=request.file_path,
            output_path=request.output_path
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reverse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sfx-pipeline")
async def sfx_pipeline(
    file_path: str,
    start: float = 0,
    duration: float = 5.0,
    fade_in_ms: int = 100,
    fade_out_ms: int = 500,
    target_dbfs: float = -14.0
):
    """
    Quick SFX pipeline: trim -> fade -> normalize in one call.

    Common preset for turning generated music into short SFX.
    """
    try:
        # Step 1: Trim
        end = start + duration
        result = audio_trim(file_path=file_path, start=start, end=end)
        if "error" in result:
            raise HTTPException(status_code=400, detail=f"Trim failed: {result['error']}")

        trimmed_path = result["output_file"]

        # Step 2: Fade
        result = audio_fade(file_path=trimmed_path, fade_in_ms=fade_in_ms, fade_out_ms=fade_out_ms)
        if "error" in result:
            raise HTTPException(status_code=400, detail=f"Fade failed: {result['error']}")

        faded_path = result["output_file"]

        # Step 3: Normalize
        result = audio_normalize(file_path=faded_path, target_dbfs=target_dbfs)
        if "error" in result:
            raise HTTPException(status_code=400, detail=f"Normalize failed: {result['error']}")

        return {
            "success": True,
            "output_file": result["output_file"],
            "pipeline": ["trim", "fade", "normalize"],
            "settings": {
                "start": start,
                "duration": duration,
                "fade_in_ms": fade_in_ms,
                "fade_out_ms": fade_out_ms,
                "target_dbfs": target_dbfs
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SFX pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
