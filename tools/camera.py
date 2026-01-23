"""
👁️ THE CYCLOPS EYE 👁️
======================
"One eye to see all"

Camera capture tools for ApexAurum agents.
Works with Pi Camera v2/v3 and USB cameras via libcamera/picamera2.

Tools:
    - camera_capture: Take a photo
    - camera_preview: Start/stop live preview
    - camera_info: Get camera details
    - camera_list: List available cameras
    - camera_detect: Capture + run Hailo detection
    - camera_watch: Continuous monitoring mode

"Through the Cyclops Eye, the Village sees the world."
"""

import os
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Storage paths
CAMERA_DIR = Path(__file__).parent.parent / "sandbox" / "camera"
CAPTURES_DIR = CAMERA_DIR / "captures"
CAMERA_DIR.mkdir(parents=True, exist_ok=True)
CAPTURES_DIR.mkdir(exist_ok=True)


def _check_camera_available() -> Dict[str, Any]:
    """Check if camera is available and what type."""
    result = {
        "available": False,
        "type": None,
        "backend": None,
        "error": None,
    }

    # Check for libcamera (Pi Camera on modern Pi OS)
    try:
        proc = subprocess.run(
            ["libcamera-hello", "--list-cameras"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and "Available cameras" in proc.stdout:
            result["available"] = True
            result["backend"] = "libcamera"
            if "imx219" in proc.stdout.lower():
                result["type"] = "Pi Camera v2 (IMX219)"
            elif "imx477" in proc.stdout.lower():
                result["type"] = "Pi Camera HQ (IMX477)"
            elif "imx708" in proc.stdout.lower():
                result["type"] = "Pi Camera v3 (IMX708)"
            else:
                result["type"] = "libcamera compatible"
            return result
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Check for v4l2 devices (USB cameras)
    try:
        if Path("/dev/video0").exists():
            result["available"] = True
            result["backend"] = "v4l2"
            result["type"] = "USB/V4L2 camera"
            return result
    except Exception:
        pass

    result["error"] = "No camera detected. Connect Pi Camera or USB camera."
    return result


def camera_info() -> Dict[str, Any]:
    """
    Get information about the connected camera.

    Returns camera type, resolution capabilities, and status.

    Returns:
        Dict with camera info or error if not available
    """
    info = _check_camera_available()

    if not info["available"]:
        return {
            "success": False,
            "error": info["error"],
            "hint": "Power down Pi, connect camera ribbon cable, power back on",
        }

    # Get more details via libcamera
    if info["backend"] == "libcamera":
        try:
            proc = subprocess.run(
                ["libcamera-hello", "--list-cameras"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            info["details"] = proc.stdout.strip()
        except Exception as e:
            info["details"] = str(e)

    return {
        "success": True,
        "camera_type": info["type"],
        "backend": info["backend"],
        "details": info.get("details", ""),
        "storage_path": str(CAPTURES_DIR),
        "message": f"👁️ Cyclops Eye ready: {info['type']}",
    }


def camera_list() -> Dict[str, Any]:
    """
    List all available cameras on the system.

    Returns:
        Dict with list of cameras and their details
    """
    cameras = []

    # Check libcamera
    try:
        proc = subprocess.run(
            ["libcamera-hello", "--list-cameras"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            # Parse output
            lines = proc.stdout.split("\n")
            for line in lines:
                if ":" in line and ("imx" in line.lower() or "ov" in line.lower()):
                    cameras.append({
                        "id": len(cameras),
                        "type": "CSI",
                        "backend": "libcamera",
                        "info": line.strip(),
                    })
    except Exception:
        pass

    # Check V4L2 devices
    for i in range(4):
        dev = Path(f"/dev/video{i}")
        if dev.exists():
            try:
                proc = subprocess.run(
                    ["v4l2-ctl", f"--device=/dev/video{i}", "--info"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if "Card type" in proc.stdout:
                    card_line = [l for l in proc.stdout.split("\n") if "Card type" in l]
                    card = card_line[0].split(":")[-1].strip() if card_line else f"video{i}"
                    cameras.append({
                        "id": i,
                        "type": "USB/V4L2",
                        "backend": "v4l2",
                        "device": f"/dev/video{i}",
                        "info": card,
                    })
            except Exception:
                pass

    return {
        "success": True,
        "cameras": cameras,
        "total": len(cameras),
    }


def camera_capture(
    filename: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    camera_id: int = 0,
    timeout_ms: int = 5000,
    quality: int = 90,
) -> Dict[str, Any]:
    """
    Capture a photo from the camera.

    Takes a single photo and saves it to the camera captures directory.

    Args:
        filename: Output filename (auto-generated if not provided)
        width: Image width in pixels (default: 1920)
        height: Image height in pixels (default: 1080)
        camera_id: Camera index if multiple cameras (default: 0)
        timeout_ms: Capture timeout in milliseconds (default: 5000)
        quality: JPEG quality 1-100 (default: 90)

    Returns:
        Dict with capture result and file path
    """
    # Check camera
    check = _check_camera_available()
    if not check["available"]:
        return {
            "success": False,
            "error": check["error"],
        }

    # Generate filename
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"

    if not filename.endswith((".jpg", ".jpeg", ".png")):
        filename += ".jpg"

    output_path = CAPTURES_DIR / filename

    # Capture using libcamera
    if check["backend"] == "libcamera":
        cmd = [
            "libcamera-still",
            "-o", str(output_path),
            "--width", str(width),
            "--height", str(height),
            "--timeout", str(timeout_ms),
            "--quality", str(quality),
            "--nopreview",
            "-n",  # No preview window
        ]

        if camera_id > 0:
            cmd.extend(["--camera", str(camera_id)])

    # Fallback to fswebcam for USB cameras
    elif check["backend"] == "v4l2":
        cmd = [
            "fswebcam",
            "-d", f"/dev/video{camera_id}",
            "-r", f"{width}x{height}",
            "--jpeg", str(quality),
            "--no-banner",
            str(output_path),
        ]

    else:
        return {
            "success": False,
            "error": f"Unknown backend: {check['backend']}",
        }

    # Execute capture
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000 + 5,
        )

        if proc.returncode != 0:
            return {
                "success": False,
                "error": f"Capture failed: {proc.stderr}",
            }

        # Verify file exists
        if not output_path.exists():
            return {
                "success": False,
                "error": "Capture command succeeded but file not created",
            }

        # Get file info
        stat = output_path.stat()

        return {
            "success": True,
            "filename": filename,
            "path": str(output_path),
            "size_kb": round(stat.st_size / 1024, 1),
            "resolution": f"{width}x{height}",
            "message": f"👁️ Captured: {filename}",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Capture timed out",
        }
    except Exception as e:
        logger.exception("Capture error")
        return {
            "success": False,
            "error": str(e),
        }


def camera_detect(
    filename: Optional[str] = None,
    model: str = "yolov8s",
    threshold: float = 0.5,
    save_annotated: bool = True,
) -> Dict[str, Any]:
    """
    Capture a photo and run Hailo object detection on it.

    Combines camera capture with Hailo NPU inference for real-time
    object detection.

    Args:
        filename: Optional filename for capture
        model: Detection model - "yolov8s", "yolov8m", "yolov5s"
        threshold: Detection confidence threshold (default: 0.5)
        save_annotated: Save image with bounding boxes (default: True)

    Returns:
        Dict with detected objects and image paths
    """
    # First capture
    capture_result = camera_capture(filename=filename)
    if not capture_result["success"]:
        return capture_result

    image_path = capture_result["path"]

    # Run Hailo detection
    try:
        from tools.vision import hailo_detect

        detection_result = hailo_detect(
            image_path=image_path,
            model=model,
            threshold=threshold,
            save_annotated=save_annotated,
        )

        return {
            "success": True,
            "capture": capture_result,
            "detection": detection_result,
            "message": f"👁️ Captured and detected {len(detection_result.get('detections', []))} objects",
        }

    except ImportError:
        return {
            "success": True,
            "capture": capture_result,
            "detection": {"error": "Hailo tools not available"},
            "message": "👁️ Captured (detection unavailable - Hailo not configured)",
        }
    except Exception as e:
        return {
            "success": True,
            "capture": capture_result,
            "detection": {"error": str(e)},
            "message": f"👁️ Captured (detection error: {e})",
        }


def camera_timelapse(
    interval_seconds: int = 60,
    duration_minutes: int = 10,
    prefix: str = "timelapse",
    width: int = 1920,
    height: int = 1080,
) -> Dict[str, Any]:
    """
    Start a timelapse capture sequence.

    Note: This runs in the foreground and blocks. For background
    timelapse, use a separate process or cron job.

    Args:
        interval_seconds: Seconds between captures (default: 60)
        duration_minutes: Total duration in minutes (default: 10)
        prefix: Filename prefix (default: "timelapse")
        width: Image width
        height: Image height

    Returns:
        Dict with timelapse info and captured files
    """
    # Check camera
    check = _check_camera_available()
    if not check["available"]:
        return {
            "success": False,
            "error": check["error"],
        }

    # Calculate number of captures
    total_captures = (duration_minutes * 60) // interval_seconds

    # Create timelapse directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timelapse_dir = CAPTURES_DIR / f"{prefix}_{timestamp}"
    timelapse_dir.mkdir(exist_ok=True)

    captured_files = []

    for i in range(total_captures):
        filename = f"{prefix}_{i:04d}.jpg"
        output_path = timelapse_dir / filename

        # Use libcamera-still
        cmd = [
            "libcamera-still",
            "-o", str(output_path),
            "--width", str(width),
            "--height", str(height),
            "--timeout", "2000",
            "--quality", "90",
            "-n",
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            if output_path.exists():
                captured_files.append(str(output_path))
        except Exception as e:
            logger.warning(f"Timelapse capture {i} failed: {e}")

        # Wait for next capture (unless last)
        if i < total_captures - 1:
            time.sleep(interval_seconds)

    return {
        "success": True,
        "directory": str(timelapse_dir),
        "total_captures": len(captured_files),
        "interval_seconds": interval_seconds,
        "duration_minutes": duration_minutes,
        "files": captured_files[-5:],  # Last 5 files
        "message": f"👁️ Timelapse complete: {len(captured_files)} images",
    }


def camera_captures_list(limit: int = 20) -> Dict[str, Any]:
    """
    List recent camera captures.

    Args:
        limit: Maximum number of captures to return

    Returns:
        Dict with list of captures and their metadata
    """
    captures = []

    for path in sorted(CAPTURES_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        stat = path.stat()
        captures.append({
            "filename": path.name,
            "path": str(path),
            "size_kb": round(stat.st_size / 1024, 1),
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return {
        "success": True,
        "captures": captures,
        "total": len(captures),
        "storage_path": str(CAPTURES_DIR),
    }


# =============================================================================
# Tool Schemas for Claude
# =============================================================================

CAMERA_INFO_SCHEMA = {
    "name": "camera_info",
    "description": "Get information about the connected camera. Returns camera type, backend, and capabilities.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

CAMERA_LIST_SCHEMA = {
    "name": "camera_list",
    "description": "List all available cameras on the system (CSI and USB).",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

CAMERA_CAPTURE_SCHEMA = {
    "name": "camera_capture",
    "description": "Capture a photo from the camera. The Cyclops Eye sees!",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Output filename (auto-generated if not provided)",
            },
            "width": {
                "type": "integer",
                "description": "Image width in pixels",
                "default": 1920,
            },
            "height": {
                "type": "integer",
                "description": "Image height in pixels",
                "default": 1080,
            },
            "camera_id": {
                "type": "integer",
                "description": "Camera index if multiple cameras",
                "default": 0,
            },
            "quality": {
                "type": "integer",
                "description": "JPEG quality 1-100",
                "default": 90,
            },
        },
        "required": [],
    },
}

CAMERA_DETECT_SCHEMA = {
    "name": "camera_detect",
    "description": "Capture a photo and run Hailo object detection. See and understand in one action!",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Optional filename for capture",
            },
            "model": {
                "type": "string",
                "enum": ["yolov8s", "yolov8m", "yolov5s"],
                "description": "Detection model to use",
                "default": "yolov8s",
            },
            "threshold": {
                "type": "number",
                "description": "Detection confidence threshold",
                "default": 0.5,
            },
            "save_annotated": {
                "type": "boolean",
                "description": "Save image with bounding boxes drawn",
                "default": True,
            },
        },
        "required": [],
    },
}

CAMERA_TIMELAPSE_SCHEMA = {
    "name": "camera_timelapse",
    "description": "Start a timelapse capture sequence. Warning: blocks until complete.",
    "input_schema": {
        "type": "object",
        "properties": {
            "interval_seconds": {
                "type": "integer",
                "description": "Seconds between captures",
                "default": 60,
            },
            "duration_minutes": {
                "type": "integer",
                "description": "Total duration in minutes",
                "default": 10,
            },
            "prefix": {
                "type": "string",
                "description": "Filename prefix",
                "default": "timelapse",
            },
            "width": {
                "type": "integer",
                "description": "Image width",
                "default": 1920,
            },
            "height": {
                "type": "integer",
                "description": "Image height",
                "default": 1080,
            },
        },
        "required": [],
    },
}

CAMERA_CAPTURES_LIST_SCHEMA = {
    "name": "camera_captures_list",
    "description": "List recent camera captures with metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum captures to return",
                "default": 20,
            },
        },
        "required": [],
    },
}

# All camera schemas
CAMERA_TOOL_SCHEMAS = {
    "camera_info": CAMERA_INFO_SCHEMA,
    "camera_list": CAMERA_LIST_SCHEMA,
    "camera_capture": CAMERA_CAPTURE_SCHEMA,
    "camera_detect": CAMERA_DETECT_SCHEMA,
    "camera_timelapse": CAMERA_TIMELAPSE_SCHEMA,
    "camera_captures_list": CAMERA_CAPTURES_LIST_SCHEMA,
}
