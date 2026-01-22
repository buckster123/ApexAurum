"""
Audio Editor Tools - Edit and manipulate audio files

Provides tools for:
- Trimming audio to specific timestamps
- Fade in/out effects
- Volume normalization
- Creating seamless loops
- Concatenating multiple clips
- Speed/pitch adjustment
- Audio analysis and info

Uses pydub for manipulation, librosa for analysis.
"""

import os
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Audio storage
AUDIO_FOLDER = Path("./sandbox/music")
EDITED_FOLDER = Path("./sandbox/music/edited")
EDITED_FOLDER.mkdir(parents=True, exist_ok=True)

# Try to import audio libraries
try:
    from pydub import AudioSegment
    from pydub.effects import normalize, compress_dynamic_range
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    AudioSegment = None

try:
    import librosa
    import numpy as np
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False
    librosa = None
    np = None

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False
    sf = None


def _check_pydub():
    """Check if pydub is available"""
    if not HAS_PYDUB:
        return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
    return None


def _resolve_audio_path(file_path: str) -> Path:
    """Resolve audio file path, checking common locations"""
    path = Path(file_path)

    # If absolute or exists as-is
    if path.is_absolute() or path.exists():
        return path

    # Check in sandbox/music
    music_path = AUDIO_FOLDER / file_path
    if music_path.exists():
        return music_path

    # Check in edited folder
    edited_path = EDITED_FOLDER / file_path
    if edited_path.exists():
        return edited_path

    return path  # Return original, let caller handle missing file


def _generate_output_name(input_path: Path, suffix: str) -> Path:
    """Generate output filename with suffix"""
    stem = input_path.stem
    ext = input_path.suffix or ".mp3"
    timestamp = datetime.now().strftime("%H%M%S")
    return EDITED_FOLDER / f"{stem}_{suffix}_{timestamp}{ext}"


def _ms_to_timestamp(ms: int) -> str:
    """Convert milliseconds to MM:SS.mmm format"""
    seconds = ms / 1000
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"


def _timestamp_to_ms(timestamp: str) -> int:
    """Convert MM:SS or MM:SS.mmm or seconds to milliseconds"""
    if isinstance(timestamp, (int, float)):
        return int(timestamp * 1000)

    timestamp = str(timestamp).strip()

    # Handle pure seconds (e.g., "5.5")
    if ':' not in timestamp:
        return int(float(timestamp) * 1000)

    # Handle MM:SS or MM:SS.mmm
    parts = timestamp.split(':')
    minutes = int(parts[0])
    seconds = float(parts[1])
    return int((minutes * 60 + seconds) * 1000)


# ═══════════════════════════════════════════════════════════════════════════════
# CORE AUDIO TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def audio_info(file_path: str) -> Dict[str, Any]:
    """
    Get detailed information about an audio file.

    Args:
        file_path: Path to the audio file

    Returns:
        Dict with duration, sample_rate, channels, format, file_size, etc.
    """
    err = _check_pydub()
    if err:
        return err

    try:
        path = _resolve_audio_path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        audio = AudioSegment.from_file(str(path))

        info = {
            "success": True,
            "file_path": str(path),
            "file_name": path.name,
            "duration_ms": len(audio),
            "duration_seconds": len(audio) / 1000,
            "duration_formatted": _ms_to_timestamp(len(audio)),
            "channels": audio.channels,
            "sample_rate": audio.frame_rate,
            "sample_width": audio.sample_width,
            "frame_count": audio.frame_count(),
            "file_size_bytes": path.stat().st_size,
            "file_size_mb": round(path.stat().st_size / 1048576, 2),
            "format": path.suffix.lstrip('.'),
            "dbfs": round(audio.dBFS, 2),  # Volume level
        }

        # Add librosa analysis if available
        if HAS_LIBROSA:
            try:
                y, sr = librosa.load(str(path), sr=None)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                info["estimated_bpm"] = round(float(tempo), 1)
            except Exception as e:
                logger.warning(f"Librosa analysis failed: {e}")

        return info

    except Exception as e:
        logger.error(f"audio_info failed: {e}")
        return {"success": False, "error": str(e)}


def audio_trim(
    file_path: str,
    start: Union[str, float] = 0,
    end: Union[str, float] = None,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Trim audio to specified start and end times.

    Args:
        file_path: Path to the audio file
        start: Start time (seconds, or "MM:SS" format). Default: 0
        end: End time (seconds, or "MM:SS" format). Default: end of file
        output_path: Output file path. Default: auto-generated in edited folder

    Returns:
        Dict with success status and output file path

    Example:
        >>> audio_trim("mysong.mp3", start=5, end=10)  # Trim to 5s-10s
        >>> audio_trim("mysong.mp3", start="0:30", end="1:00")  # 30s to 1min
    """
    err = _check_pydub()
    if err:
        return err

    try:
        path = _resolve_audio_path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        audio = AudioSegment.from_file(str(path))
        original_duration = len(audio)

        # Convert timestamps to milliseconds
        start_ms = _timestamp_to_ms(start)
        end_ms = _timestamp_to_ms(end) if end is not None else original_duration

        # Validate
        if start_ms < 0:
            start_ms = 0
        if end_ms > original_duration:
            end_ms = original_duration
        if start_ms >= end_ms:
            return {"success": False, "error": f"Invalid range: start ({start_ms}ms) >= end ({end_ms}ms)"}

        # Trim
        trimmed = audio[start_ms:end_ms]

        # Output path
        if output_path:
            out_path = Path(output_path)
        else:
            out_path = _generate_output_name(path, "trim")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export
        format_type = out_path.suffix.lstrip('.') or 'mp3'
        trimmed.export(str(out_path), format=format_type)

        return {
            "success": True,
            "input_file": str(path),
            "output_file": str(out_path),
            "original_duration_ms": original_duration,
            "trimmed_duration_ms": len(trimmed),
            "trimmed_duration_formatted": _ms_to_timestamp(len(trimmed)),
            "start_ms": start_ms,
            "end_ms": end_ms,
        }

    except Exception as e:
        logger.error(f"audio_trim failed: {e}")
        return {"success": False, "error": str(e)}


def audio_fade(
    file_path: str,
    fade_in_ms: int = 0,
    fade_out_ms: int = 0,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Apply fade in and/or fade out to audio.

    Args:
        file_path: Path to the audio file
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
        output_path: Output file path. Default: auto-generated

    Returns:
        Dict with success status and output file path

    Example:
        >>> audio_fade("mysong.mp3", fade_in_ms=500, fade_out_ms=1000)
    """
    err = _check_pydub()
    if err:
        return err

    try:
        path = _resolve_audio_path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        audio = AudioSegment.from_file(str(path))

        # Apply fades
        if fade_in_ms > 0:
            audio = audio.fade_in(fade_in_ms)
        if fade_out_ms > 0:
            audio = audio.fade_out(fade_out_ms)

        # Output path
        if output_path:
            out_path = Path(output_path)
        else:
            out_path = _generate_output_name(path, "fade")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export
        format_type = out_path.suffix.lstrip('.') or 'mp3'
        audio.export(str(out_path), format=format_type)

        return {
            "success": True,
            "input_file": str(path),
            "output_file": str(out_path),
            "fade_in_ms": fade_in_ms,
            "fade_out_ms": fade_out_ms,
            "duration_ms": len(audio),
        }

    except Exception as e:
        logger.error(f"audio_fade failed: {e}")
        return {"success": False, "error": str(e)}


def audio_normalize(
    file_path: str,
    target_dbfs: float = -14.0,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Normalize audio volume to a target level.

    Args:
        file_path: Path to the audio file
        target_dbfs: Target volume in dBFS. Default: -14 (broadcast standard)
        output_path: Output file path. Default: auto-generated

    Returns:
        Dict with success status, output file, and volume change info

    Example:
        >>> audio_normalize("quiet_sound.mp3", target_dbfs=-12)
    """
    err = _check_pydub()
    if err:
        return err

    try:
        path = _resolve_audio_path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        audio = AudioSegment.from_file(str(path))
        original_dbfs = audio.dBFS

        # Calculate gain needed
        gain = target_dbfs - original_dbfs

        # Apply gain
        normalized = audio + gain

        # Output path
        if output_path:
            out_path = Path(output_path)
        else:
            out_path = _generate_output_name(path, "norm")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export
        format_type = out_path.suffix.lstrip('.') or 'mp3'
        normalized.export(str(out_path), format=format_type)

        return {
            "success": True,
            "input_file": str(path),
            "output_file": str(out_path),
            "original_dbfs": round(original_dbfs, 2),
            "target_dbfs": target_dbfs,
            "final_dbfs": round(normalized.dBFS, 2),
            "gain_applied": round(gain, 2),
        }

    except Exception as e:
        logger.error(f"audio_normalize failed: {e}")
        return {"success": False, "error": str(e)}


def audio_loop(
    file_path: str,
    loop_count: int = 2,
    crossfade_ms: int = 100,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Create a looped version of audio with optional crossfade.

    Args:
        file_path: Path to the audio file
        loop_count: Number of times to loop (2 = original + 1 repeat)
        crossfade_ms: Crossfade duration between loops for seamless transition
        output_path: Output file path. Default: auto-generated

    Returns:
        Dict with success status and output file path

    Example:
        >>> audio_loop("ambient.mp3", loop_count=4, crossfade_ms=500)
    """
    err = _check_pydub()
    if err:
        return err

    try:
        path = _resolve_audio_path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        audio = AudioSegment.from_file(str(path))
        original_duration = len(audio)

        if loop_count < 2:
            loop_count = 2

        # Create looped audio with crossfade
        looped = audio
        for _ in range(loop_count - 1):
            if crossfade_ms > 0 and crossfade_ms < len(audio):
                looped = looped.append(audio, crossfade=crossfade_ms)
            else:
                looped = looped + audio

        # Output path
        if output_path:
            out_path = Path(output_path)
        else:
            out_path = _generate_output_name(path, f"loop{loop_count}")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export
        format_type = out_path.suffix.lstrip('.') or 'mp3'
        looped.export(str(out_path), format=format_type)

        return {
            "success": True,
            "input_file": str(path),
            "output_file": str(out_path),
            "original_duration_ms": original_duration,
            "looped_duration_ms": len(looped),
            "looped_duration_formatted": _ms_to_timestamp(len(looped)),
            "loop_count": loop_count,
            "crossfade_ms": crossfade_ms,
        }

    except Exception as e:
        logger.error(f"audio_loop failed: {e}")
        return {"success": False, "error": str(e)}


def audio_concat(
    file_paths: List[str],
    crossfade_ms: int = 0,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Concatenate multiple audio files into one.

    Args:
        file_paths: List of audio file paths to concatenate (in order)
        crossfade_ms: Crossfade duration between clips
        output_path: Output file path. Default: auto-generated

    Returns:
        Dict with success status and output file path

    Example:
        >>> audio_concat(["intro.mp3", "main.mp3", "outro.mp3"], crossfade_ms=200)
    """
    err = _check_pydub()
    if err:
        return err

    try:
        if not file_paths or len(file_paths) < 2:
            return {"success": False, "error": "Need at least 2 files to concatenate"}

        # Load all audio files
        segments = []
        for fp in file_paths:
            path = _resolve_audio_path(fp)
            if not path.exists():
                return {"success": False, "error": f"File not found: {fp}"}
            segments.append(AudioSegment.from_file(str(path)))

        # Concatenate
        combined = segments[0]
        for seg in segments[1:]:
            if crossfade_ms > 0:
                combined = combined.append(seg, crossfade=crossfade_ms)
            else:
                combined = combined + seg

        # Output path
        if output_path:
            out_path = Path(output_path)
        else:
            out_path = EDITED_FOLDER / f"concat_{datetime.now().strftime('%H%M%S')}.mp3"

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export
        format_type = out_path.suffix.lstrip('.') or 'mp3'
        combined.export(str(out_path), format=format_type)

        return {
            "success": True,
            "input_files": file_paths,
            "output_file": str(out_path),
            "total_duration_ms": len(combined),
            "total_duration_formatted": _ms_to_timestamp(len(combined)),
            "file_count": len(file_paths),
            "crossfade_ms": crossfade_ms,
        }

    except Exception as e:
        logger.error(f"audio_concat failed: {e}")
        return {"success": False, "error": str(e)}


def audio_speed(
    file_path: str,
    speed_factor: float = 1.0,
    preserve_pitch: bool = True,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Change audio speed/tempo.

    Args:
        file_path: Path to the audio file
        speed_factor: Speed multiplier (0.5 = half speed, 2.0 = double speed)
        preserve_pitch: If True, pitch stays the same (time stretch).
                       If False, pitch changes with speed (chipmunk/slow-mo effect)
        output_path: Output file path. Default: auto-generated

    Returns:
        Dict with success status and output file path

    Example:
        >>> audio_speed("mysong.mp3", speed_factor=1.5)  # 50% faster
    """
    err = _check_pydub()
    if err:
        return err

    try:
        path = _resolve_audio_path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        if speed_factor <= 0:
            return {"success": False, "error": "Speed factor must be positive"}

        audio = AudioSegment.from_file(str(path))
        original_duration = len(audio)

        if preserve_pitch and HAS_LIBROSA:
            # Use librosa for time stretching (preserves pitch)
            y, sr = librosa.load(str(path), sr=None)
            y_stretched = librosa.effects.time_stretch(y, rate=speed_factor)

            # Convert back to AudioSegment
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                sf.write(tmp.name, y_stretched, sr)
                audio = AudioSegment.from_file(tmp.name)
                os.unlink(tmp.name)
        else:
            # Simple speed change (affects pitch)
            # Change frame rate to affect speed
            new_frame_rate = int(audio.frame_rate * speed_factor)
            audio = audio._spawn(audio.raw_data, overrides={
                "frame_rate": new_frame_rate
            }).set_frame_rate(audio.frame_rate)

        # Output path
        if output_path:
            out_path = Path(output_path)
        else:
            speed_str = f"{speed_factor:.1f}x".replace('.', '_')
            out_path = _generate_output_name(path, f"speed{speed_str}")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export
        format_type = out_path.suffix.lstrip('.') or 'mp3'
        audio.export(str(out_path), format=format_type)

        return {
            "success": True,
            "input_file": str(path),
            "output_file": str(out_path),
            "original_duration_ms": original_duration,
            "new_duration_ms": len(audio),
            "speed_factor": speed_factor,
            "pitch_preserved": preserve_pitch,
        }

    except Exception as e:
        logger.error(f"audio_speed failed: {e}")
        return {"success": False, "error": str(e)}


def audio_reverse(
    file_path: str,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Reverse an audio file.

    Args:
        file_path: Path to the audio file
        output_path: Output file path. Default: auto-generated

    Returns:
        Dict with success status and output file path
    """
    err = _check_pydub()
    if err:
        return err

    try:
        path = _resolve_audio_path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        audio = AudioSegment.from_file(str(path))
        reversed_audio = audio.reverse()

        # Output path
        if output_path:
            out_path = Path(output_path)
        else:
            out_path = _generate_output_name(path, "reversed")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export
        format_type = out_path.suffix.lstrip('.') or 'mp3'
        reversed_audio.export(str(out_path), format=format_type)

        return {
            "success": True,
            "input_file": str(path),
            "output_file": str(out_path),
            "duration_ms": len(reversed_audio),
        }

    except Exception as e:
        logger.error(f"audio_reverse failed: {e}")
        return {"success": False, "error": str(e)}


def audio_list_files(folder: str = None) -> Dict[str, Any]:
    """
    List audio files in the music folder.

    Args:
        folder: Specific folder to list. Default: sandbox/music

    Returns:
        Dict with list of audio files and their basic info
    """
    try:
        search_folder = Path(folder) if folder else AUDIO_FOLDER

        if not search_folder.exists():
            return {"success": False, "error": f"Folder not found: {search_folder}"}

        audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}
        files = []

        for f in sorted(search_folder.iterdir()):
            if f.is_file() and f.suffix.lower() in audio_extensions:
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size_mb": round(f.stat().st_size / 1048576, 2),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })

        return {
            "success": True,
            "folder": str(search_folder),
            "files": files,
            "count": len(files),
        }

    except Exception as e:
        logger.error(f"audio_list_files failed: {e}")
        return {"success": False, "error": str(e)}


def audio_get_waveform(
    file_path: str,
    num_points: int = 200
) -> Dict[str, Any]:
    """
    Get waveform data for visualization.

    Args:
        file_path: Path to the audio file
        num_points: Number of data points for the waveform. Default: 200

    Returns:
        Dict with waveform amplitude data and duration
    """
    if not HAS_LIBROSA:
        return {"success": False, "error": "librosa not installed"}

    try:
        path = _resolve_audio_path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        # Load audio
        y, sr = librosa.load(str(path), sr=None, mono=True)
        duration = len(y) / sr

        # Downsample for visualization
        hop_length = max(1, len(y) // num_points)

        # Get amplitude envelope
        envelope = []
        for i in range(0, len(y), hop_length):
            chunk = y[i:i+hop_length]
            if len(chunk) > 0:
                envelope.append(float(np.max(np.abs(chunk))))

        # Normalize to 0-1
        max_val = max(envelope) if envelope else 1
        if max_val > 0:
            envelope = [v / max_val for v in envelope]

        return {
            "success": True,
            "file_path": str(path),
            "duration_seconds": duration,
            "sample_rate": sr,
            "waveform": envelope,
            "num_points": len(envelope),
        }

    except Exception as e:
        logger.error(f"audio_get_waveform failed: {e}")
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

AUDIO_INFO_SCHEMA = {
    "name": "audio_info",
    "description": "Get detailed information about an audio file including duration, format, sample rate, and volume level.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file"
            }
        },
        "required": ["file_path"]
    }
}

AUDIO_TRIM_SCHEMA = {
    "name": "audio_trim",
    "description": "Trim audio to specified start and end times. Supports seconds (5.5) or timestamp format (1:30).",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file"
            },
            "start": {
                "type": ["string", "number"],
                "description": "Start time in seconds or MM:SS format. Default: 0",
                "default": 0
            },
            "end": {
                "type": ["string", "number"],
                "description": "End time in seconds or MM:SS format. Default: end of file"
            },
            "output_path": {
                "type": "string",
                "description": "Output file path. Default: auto-generated in edited folder"
            }
        },
        "required": ["file_path"]
    }
}

AUDIO_FADE_SCHEMA = {
    "name": "audio_fade",
    "description": "Apply fade in and/or fade out effects to audio.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file"
            },
            "fade_in_ms": {
                "type": "integer",
                "description": "Fade in duration in milliseconds",
                "default": 0
            },
            "fade_out_ms": {
                "type": "integer",
                "description": "Fade out duration in milliseconds",
                "default": 0
            },
            "output_path": {
                "type": "string",
                "description": "Output file path. Default: auto-generated"
            }
        },
        "required": ["file_path"]
    }
}

AUDIO_NORMALIZE_SCHEMA = {
    "name": "audio_normalize",
    "description": "Normalize audio volume to a target level in dBFS.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file"
            },
            "target_dbfs": {
                "type": "number",
                "description": "Target volume in dBFS. Default: -14 (broadcast standard)",
                "default": -14.0
            },
            "output_path": {
                "type": "string",
                "description": "Output file path. Default: auto-generated"
            }
        },
        "required": ["file_path"]
    }
}

AUDIO_LOOP_SCHEMA = {
    "name": "audio_loop",
    "description": "Create a looped version of audio with optional crossfade for seamless transitions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file"
            },
            "loop_count": {
                "type": "integer",
                "description": "Number of times to loop (2 = original + 1 repeat)",
                "default": 2
            },
            "crossfade_ms": {
                "type": "integer",
                "description": "Crossfade duration between loops in milliseconds",
                "default": 100
            },
            "output_path": {
                "type": "string",
                "description": "Output file path. Default: auto-generated"
            }
        },
        "required": ["file_path"]
    }
}

AUDIO_CONCAT_SCHEMA = {
    "name": "audio_concat",
    "description": "Concatenate multiple audio files into one.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of audio file paths to concatenate (in order)"
            },
            "crossfade_ms": {
                "type": "integer",
                "description": "Crossfade duration between clips in milliseconds",
                "default": 0
            },
            "output_path": {
                "type": "string",
                "description": "Output file path. Default: auto-generated"
            }
        },
        "required": ["file_paths"]
    }
}

AUDIO_SPEED_SCHEMA = {
    "name": "audio_speed",
    "description": "Change audio speed/tempo. Can preserve pitch (time stretch) or let pitch change with speed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file"
            },
            "speed_factor": {
                "type": "number",
                "description": "Speed multiplier (0.5 = half speed, 2.0 = double speed)",
                "default": 1.0
            },
            "preserve_pitch": {
                "type": "boolean",
                "description": "If true, pitch stays same. If false, pitch changes with speed.",
                "default": True
            },
            "output_path": {
                "type": "string",
                "description": "Output file path. Default: auto-generated"
            }
        },
        "required": ["file_path"]
    }
}

AUDIO_REVERSE_SCHEMA = {
    "name": "audio_reverse",
    "description": "Reverse an audio file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file"
            },
            "output_path": {
                "type": "string",
                "description": "Output file path. Default: auto-generated"
            }
        },
        "required": ["file_path"]
    }
}

AUDIO_LIST_FILES_SCHEMA = {
    "name": "audio_list_files",
    "description": "List audio files in the music folder.",
    "input_schema": {
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder to list. Default: sandbox/music"
            }
        }
    }
}

AUDIO_GET_WAVEFORM_SCHEMA = {
    "name": "audio_get_waveform",
    "description": "Get waveform amplitude data for visualization.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file"
            },
            "num_points": {
                "type": "integer",
                "description": "Number of data points for the waveform",
                "default": 200
            }
        },
        "required": ["file_path"]
    }
}


# Combined schemas dict
AUDIO_EDITOR_TOOL_SCHEMAS = {
    "audio_info": AUDIO_INFO_SCHEMA,
    "audio_trim": AUDIO_TRIM_SCHEMA,
    "audio_fade": AUDIO_FADE_SCHEMA,
    "audio_normalize": AUDIO_NORMALIZE_SCHEMA,
    "audio_loop": AUDIO_LOOP_SCHEMA,
    "audio_concat": AUDIO_CONCAT_SCHEMA,
    "audio_speed": AUDIO_SPEED_SCHEMA,
    "audio_reverse": AUDIO_REVERSE_SCHEMA,
    "audio_list_files": AUDIO_LIST_FILES_SCHEMA,
    "audio_get_waveform": AUDIO_GET_WAVEFORM_SCHEMA,
}
