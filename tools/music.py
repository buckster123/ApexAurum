"""
Agentic Music Pipeline - Phase 1

Suno AI music generation tools with non-blocking spawn+poll pattern:
- music_generate: Start music generation (returns task_id immediately)
- music_status: Check generation progress
- music_result: Get completed audio file
- music_list: List recent music tasks

Follows the agent_spawn/status/result pattern for consistent UX.
"""

import logging
import json
import threading
import time
import os
import re
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv

# Try to import tenacity for retry logic
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False
    RetryError = Exception

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
MUSIC_FOLDER = Path("./sandbox/music")
TASKS_FILE = Path("./sandbox/music_tasks.json")
CONFIG_FILE = Path("./sandbox/music_config.json")
LATEST_TRACK_FILE = Path("./sandbox/music_latest.json")  # For sidebar auto-load
SUNO_API_KEY = os.getenv("SUNO_API_KEY", "")
SUNO_API_BASE = "https://api.sunoapi.org/api/v1"


def _get_config() -> Dict[str, Any]:
    """Load music configuration from file"""
    defaults = {"blocking_mode": True}
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return {**defaults, **config}
    except Exception:
        pass
    return defaults


def _save_config(config: Dict[str, Any]):
    """Save music configuration to file"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving music config: {e}")


def _set_latest_track(track_info: Dict[str, Any]):
    """Save latest track info for sidebar auto-load"""
    try:
        LATEST_TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        track_info["timestamp"] = datetime.now().isoformat()
        with open(LATEST_TRACK_FILE, 'w') as f:
            json.dump(track_info, f, indent=2)
        logger.info(f"Set latest track: {track_info.get('title')}")
    except Exception as e:
        logger.error(f"Error saving latest track: {e}")


def _get_latest_track() -> Optional[Dict[str, Any]]:
    """Get latest track info for sidebar"""
    try:
        if LATEST_TRACK_FILE.exists():
            with open(LATEST_TRACK_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None

# Model character limits
MODEL_LIMITS = {
    "V3_5": {"prompt": 3000, "style": 200, "title": 80},
    "V4": {"prompt": 3000, "style": 200, "title": 80},
    "V4_5": {"prompt": 5000, "style": 1000, "title": 100},
    "V5": {"prompt": 5000, "style": 1000, "title": 100},
}


class MusicTaskStatus(Enum):
    """Music generation task status"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MusicTask:
    """Represents a music generation task"""
    task_id: str
    prompt: str
    style: str = ""
    title: str = ""
    model: str = "V5"
    is_instrumental: bool = True
    status: MusicTaskStatus = MusicTaskStatus.PENDING
    progress: str = "Queued"
    suno_task_id: Optional[str] = None
    audio_url: Optional[str] = None
    audio_file: Optional[str] = None
    duration: float = 0.0
    clip_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "style": self.style,
            "title": self.title,
            "model": self.model,
            "is_instrumental": self.is_instrumental,
            "status": self.status.value,
            "progress": self.progress,
            "suno_task_id": self.suno_task_id,
            "audio_url": self.audio_url,
            "audio_file": self.audio_file,
            "duration": self.duration,
            "clip_id": self.clip_id,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MusicTask":
        """Create task from dictionary"""
        status_str = data.get("status", "pending")
        try:
            status = MusicTaskStatus(status_str)
        except ValueError:
            status = MusicTaskStatus.PENDING

        return cls(
            task_id=data["task_id"],
            prompt=data.get("prompt", ""),
            style=data.get("style", ""),
            title=data.get("title", ""),
            model=data.get("model", "V5"),
            is_instrumental=data.get("is_instrumental", True),
            status=status,
            progress=data.get("progress", "Queued"),
            suno_task_id=data.get("suno_task_id"),
            audio_url=data.get("audio_url"),
            audio_file=data.get("audio_file"),
            duration=data.get("duration", 0.0),
            clip_id=data.get("clip_id"),
            error=data.get("error"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


class MusicTaskManager:
    """Manages music generation tasks"""

    def __init__(self):
        """Initialize task manager"""
        self.tasks: Dict[str, MusicTask] = {}
        self._ensure_directories()
        self._load_tasks()

    def _ensure_directories(self):
        """Ensure storage directories exist"""
        MUSIC_FOLDER.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not TASKS_FILE.exists():
            self._save_tasks()

    def _load_tasks(self):
        """Load tasks from storage"""
        try:
            if TASKS_FILE.exists():
                with open(TASKS_FILE, 'r') as f:
                    data = json.load(f)
                    for task_id, task_data in data.items():
                        self.tasks[task_id] = MusicTask.from_dict(task_data)
                logger.info(f"Loaded {len(self.tasks)} music tasks")
        except Exception as e:
            logger.error(f"Error loading music tasks: {e}")

    def _save_tasks(self):
        """Save tasks to storage"""
        try:
            data = {
                task_id: task.to_dict()
                for task_id, task in self.tasks.items()
            }
            with open(TASKS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving music tasks: {e}")

    def create_task(
        self,
        prompt: str,
        style: str = "",
        title: str = "",
        model: str = "V5",
        is_instrumental: bool = True
    ) -> MusicTask:
        """Create a new music task"""
        task_id = f"music_{int(datetime.now().timestamp() * 1000)}"
        task = MusicTask(
            task_id=task_id,
            prompt=prompt,
            style=style,
            title=title,
            model=model,
            is_instrumental=is_instrumental
        )
        self.tasks[task_id] = task
        self._save_tasks()
        logger.info(f"Created music task {task_id}: {prompt[:50]}...")
        return task

    def get_task(self, task_id: str) -> Optional[MusicTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def list_tasks(self, limit: int = 10) -> List[MusicTask]:
        """List recent tasks"""
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )
        return sorted_tasks[:limit]

    def run_task(self, task_id: str) -> Dict[str, Any]:
        """
        Run a music generation task (blocking).
        Called in a background thread.
        Downloads ALL tracks from Suno (typically 2).
        """
        task = self.get_task(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}

        task.status = MusicTaskStatus.GENERATING
        task.started_at = datetime.now().isoformat()
        task.progress = "Starting generation..."
        self._save_tasks()

        try:
            # Check API key
            if not SUNO_API_KEY:
                raise ValueError("SUNO_API_KEY not configured in .env")

            # Submit to Suno API
            task.progress = "Submitting to Suno API..."
            self._save_tasks()

            suno_task_id = self._submit_generation(task)
            task.suno_task_id = suno_task_id
            task.progress = "Queued at Suno..."
            self._save_tasks()

            # Poll for completion
            result = self._poll_completion(task)

            if result.get("success"):
                tracks = result.get("tracks", [])
                track_count = len(tracks)

                task.progress = f"Downloading {track_count} track(s)..."
                self._save_tasks()

                # Download ALL tracks
                downloaded_files = []
                all_tracks_info = []

                for i, track_info in enumerate(tracks):
                    try:
                        logger.info(f"Downloading track {i+1}/{track_count}: {track_info.get('title')}")
                        audio_file = self._download_audio(task, track_info, track_num=i+1)
                        downloaded_files.append(audio_file)
                        all_tracks_info.append({
                            "file": audio_file,
                            "title": track_info.get("title"),
                            "duration": track_info.get("duration", 0),
                            "clip_id": track_info.get("clip_id"),
                            "audio_url": track_info.get("audio_url")
                        })
                        logger.info(f"SUCCESS: Track {i+1} saved to {audio_file}")
                    except Exception as e:
                        logger.error(f"Failed to download track {i+1}: {e}")

                if not downloaded_files:
                    raise Exception("Failed to download any tracks")

                # Store first track as primary (for backward compatibility)
                first_track = all_tracks_info[0]
                task.audio_file = first_track["file"]
                task.audio_url = first_track.get("audio_url")
                task.duration = first_track.get("duration", 0.0)
                task.clip_id = first_track.get("clip_id")
                task.title = first_track.get("title", task.title) or f"Track_{task_id[-8:]}"
                task.status = MusicTaskStatus.COMPLETED
                task.progress = f"Complete ({track_count} tracks)"
                task.completed_at = datetime.now().isoformat()
                self._save_tasks()

                # Set latest track for sidebar auto-load
                _set_latest_track({
                    "filepath": first_track["file"],
                    "title": first_track["title"],
                    "duration": first_track["duration"],
                    "task_id": task_id
                })

                logger.info(f"Music task {task_id} completed: {track_count} tracks downloaded")
                return {
                    "success": True,
                    "audio_file": first_track["file"],
                    "audio_files": downloaded_files,
                    "tracks": all_tracks_info,
                    "track_count": track_count
                }
            else:
                raise Exception(result.get("error", "Unknown error"))

        except Exception as e:
            logger.error(f"Music task {task_id} failed: {e}")
            task.status = MusicTaskStatus.FAILED
            task.error = str(e)
            task.progress = f"Failed: {str(e)[:100]}"
            task.completed_at = datetime.now().isoformat()
            self._save_tasks()
            return {"success": False, "error": str(e)}

    def _submit_generation(self, task: MusicTask) -> str:
        """Submit generation request to Suno API"""
        headers = {
            "Authorization": f"Bearer {SUNO_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": task.model,
            "instrumental": task.is_instrumental,
            "customMode": True,
            "prompt": task.prompt,
            # Callback URL is required by API but we poll instead of using webhooks
            # Using placeholder - doesn't need to be reachable since we poll
            "callBackUrl": "https://localhost/callback",
        }

        if task.title:
            payload["title"] = task.title
        if task.style:
            payload["style"] = task.style

        logger.info(f"Submitting to Suno: {task.model}, instrumental={task.is_instrumental}")

        # Use retry if available
        if HAS_TENACITY:
            response = self._api_call_with_retry(
                "POST",
                f"{SUNO_API_BASE}/generate",
                headers=headers,
                json=payload
            )
        else:
            response = requests.post(
                f"{SUNO_API_BASE}/generate",
                headers=headers,
                json=payload,
                timeout=30
            )

        if response.status_code != 200:
            raise Exception(f"Suno API error: HTTP {response.status_code}: {response.text[:200]}")

        result = response.json()
        if result.get("code") != 200:
            raise Exception(f"Suno API error: {result.get('msg', 'Unknown error')}")

        suno_task_id = result.get("data", {}).get("taskId")
        if not suno_task_id:
            raise Exception("No taskId in Suno response")

        logger.info(f"Suno task submitted: {suno_task_id}")
        return suno_task_id

    def _poll_completion(self, task: MusicTask, max_wait: int = 600) -> Dict[str, Any]:
        """Poll Suno API for completion"""
        headers = {"Authorization": f"Bearer {SUNO_API_KEY}"}
        start_time = time.time()
        poll_interval = 5  # seconds

        while time.time() - start_time < max_wait:
            try:
                if HAS_TENACITY:
                    response = self._api_call_with_retry(
                        "GET",
                        f"{SUNO_API_BASE}/generate/record-info",
                        headers=headers,
                        params={"taskId": task.suno_task_id}
                    )
                else:
                    response = requests.get(
                        f"{SUNO_API_BASE}/generate/record-info",
                        headers=headers,
                        params={"taskId": task.suno_task_id},
                        timeout=10
                    )

                if response.status_code != 200:
                    logger.warning(f"Status check HTTP {response.status_code}")
                    time.sleep(poll_interval)
                    continue

                result = response.json()
                if result.get("code") != 200:
                    logger.warning(f"Status API error: {result.get('msg')}")
                    time.sleep(poll_interval)
                    continue

                data = result.get("data", {})
                status = data.get("status", "UNKNOWN")

                if status == "PENDING":
                    task.progress = "In queue..."
                    self._save_tasks()
                elif status == "GENERATING":
                    task.progress = "Generating audio..."
                    self._save_tasks()
                elif status == "SUCCESS":
                    suno_data = data.get("response", {}).get("sunoData", [])
                    if suno_data:
                        # Return ALL tracks (Suno typically returns 2)
                        tracks = []
                        for track in suno_data:
                            tracks.append({
                                "audio_url": track.get("audioUrl"),
                                "title": track.get("title"),
                                "duration": track.get("duration", 0),
                                "clip_id": track.get("id")
                            })
                        return {
                            "success": True,
                            "tracks": tracks,
                            "track_count": len(tracks)
                        }
                    else:
                        return {"success": False, "error": "No audio data in response"}
                elif status == "ERROR":
                    return {"success": False, "error": data.get("error", "Generation failed")}

                time.sleep(poll_interval)

            except Exception as e:
                logger.warning(f"Poll error: {e}")
                time.sleep(poll_interval)

        return {"success": False, "error": f"Timeout after {max_wait}s"}

    def _download_audio(self, task: MusicTask, result: Dict[str, Any], track_num: int = 1) -> str:
        """Download audio file from URL"""
        audio_url = result.get("audio_url")
        if not audio_url:
            raise Exception("No audio URL to download")

        # Sanitize filename
        title = result.get("title", task.title) or f"track_{task.task_id[-8:]}"
        safe_title = re.sub(r'[^a-zA-Z0-9\s\-_]', '', title)[:60].strip() or "untitled"
        clip_id = result.get("clip_id", "")[-8:] or task.task_id[-8:]
        # Include track number in filename for multi-track downloads
        filename = f"{safe_title}_v{track_num}_{clip_id}.mp3"
        filepath = MUSIC_FOLDER / filename

        logger.info(f"Downloading audio (track {track_num}) to: {filepath}")

        # Download with retry if available
        if HAS_TENACITY:
            response = self._api_call_with_retry("GET", audio_url, stream=True)
        else:
            response = requests.get(audio_url, stream=True, timeout=60)

        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        file_size = filepath.stat().st_size
        logger.info(f"Downloaded: {filepath} ({file_size} bytes)")
        return str(filepath)

    def _api_call_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make API call with retry logic"""
        if HAS_TENACITY:
            @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
            def _call():
                if method == "GET":
                    return requests.get(url, **kwargs, timeout=kwargs.pop("timeout", 30))
                elif method == "POST":
                    return requests.post(url, **kwargs, timeout=kwargs.pop("timeout", 30))
                else:
                    raise ValueError(f"Unknown method: {method}")
            return _call()
        else:
            # No retry, just make the call
            if method == "GET":
                return requests.get(url, **kwargs, timeout=kwargs.pop("timeout", 30))
            elif method == "POST":
                return requests.post(url, **kwargs, timeout=kwargs.pop("timeout", 30))
            else:
                raise ValueError(f"Unknown method: {method}")


# Global manager instance (singleton)
_manager: Optional[MusicTaskManager] = None


def _get_manager() -> MusicTaskManager:
    """Get or create the music task manager"""
    global _manager
    if _manager is None:
        _manager = MusicTaskManager()
    return _manager


# ============================================================================
# TOOL FUNCTIONS
# ============================================================================

def music_generate(
    prompt: str,
    style: str = "",
    title: str = "",
    model: str = "V5",
    is_instrumental: bool = True,
    blocking: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Start AI music generation via Suno.

    Args:
        prompt: Music description or lyrics. Be specific about mood, genre, instruments.
        style: Style tags (e.g., 'electronic ambient', 'jazz piano')
        title: Song title (optional)
        model: Suno model version - V3_5, V4, V4_5, V5 (newest/best)
        is_instrumental: True for instrumental, False for vocals
        blocking: If True, waits until complete and returns audio file.
                  If False, returns immediately with task_id for polling.
                  If None (default), uses setting from Music Player sidebar.

    Returns:
        If blocking=True: Dict with audio_file path when complete
        If blocking=False: Dict with task_id. Use music_status(task_id) to check progress.

    Example:
        >>> music_generate("ambient electronic meditation", blocking=True)
        {"success": True, "audio_file": "sandbox/music/...", "duration": 120.5, ...}

        >>> music_generate("ambient electronic meditation", blocking=False)
        {"success": True, "task_id": "music_17...", "status": "pending", ...}
    """
    try:
        # Use config default if blocking not explicitly set
        if blocking is None:
            config = _get_config()
            blocking = config.get("blocking_mode", True)

        # Validate API key
        if not SUNO_API_KEY:
            return {
                "success": False,
                "error": "SUNO_API_KEY not configured in .env. Add your API key from sunoapi.org."
            }

        # Validate model
        if model not in MODEL_LIMITS:
            model = "V5"

        # Validate prompt length
        limits = MODEL_LIMITS[model]
        if len(prompt) > limits["prompt"]:
            return {
                "success": False,
                "error": f"Prompt too long ({len(prompt)} chars). Max for {model}: {limits['prompt']}"
            }

        manager = _get_manager()
        task = manager.create_task(prompt, style, title, model, is_instrumental)

        if blocking:
            # Synchronous: wait for completion (polls API)
            logger.info(f"Starting blocking music generation: {task.task_id}")
            result = manager.run_task(task.task_id)

            if result.get("success"):
                # Reload task to get updated fields
                task = manager.get_task(task.task_id)
                track_count = result.get("track_count", 1)
                all_files = result.get("audio_files", [task.audio_file])
                all_tracks = result.get("tracks", [])

                return {
                    "success": True,
                    "task_id": task.task_id,
                    "status": "completed",
                    "audio_file": task.audio_file,  # Primary (first) track
                    "audio_files": all_files,  # All tracks
                    "tracks": all_tracks,  # Full track info
                    "track_count": track_count,
                    "audio_url": task.audio_url,
                    "title": task.title,
                    "duration": task.duration,
                    "model": model,
                    "is_instrumental": is_instrumental,
                    "message": f"Music generated! {track_count} track(s) saved. Primary: {task.audio_file}"
                }
            else:
                return {
                    "success": False,
                    "task_id": task.task_id,
                    "status": "failed",
                    "error": result.get("error", "Unknown error"),
                    "message": "Music generation failed."
                }
        else:
            # Async: run in background thread
            thread = threading.Thread(
                target=manager.run_task,
                args=(task.task_id,),
                daemon=True
            )
            thread.start()

            logger.info(f"Started async music generation: {task.task_id}")

            return {
                "success": True,
                "task_id": task.task_id,
                "status": "pending",
                "model": model,
                "is_instrumental": is_instrumental,
                "message": f"Music generation started. Use music_status('{task.task_id}') to check progress. Takes 2-4 minutes."
            }

    except Exception as e:
        logger.error(f"Error starting music generation: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def music_status(task_id: str) -> Dict[str, Any]:
    """
    Check music generation progress.

    Args:
        task_id: The task ID from music_generate()

    Returns:
        Dict with status, progress, and timing info.

    Example:
        >>> music_status("music_1704067200000")
        {"found": True, "status": "generating", "progress": "Generating audio...", ...}
    """
    try:
        manager = _get_manager()
        task = manager.get_task(task_id)

        if not task:
            return {
                "found": False,
                "error": f"Task {task_id} not found"
            }

        result = {
            "found": True,
            "task_id": task_id,
            "status": task.status.value,
            "progress": task.progress,
            "prompt": task.prompt[:100] + ("..." if len(task.prompt) > 100 else ""),
            "model": task.model,
            "created_at": task.created_at,
        }

        if task.started_at:
            result["started_at"] = task.started_at
        if task.completed_at:
            result["completed_at"] = task.completed_at
        if task.error:
            result["error"] = task.error

        # Add completion hint
        if task.status == MusicTaskStatus.COMPLETED:
            result["message"] = f"Generation complete! Use music_result('{task_id}') to get the audio file."
        elif task.status == MusicTaskStatus.FAILED:
            result["message"] = f"Generation failed: {task.error}"
        elif task.status == MusicTaskStatus.GENERATING:
            result["message"] = "Still generating... Check again in 30 seconds."

        return result

    except Exception as e:
        logger.error(f"Error checking music status: {e}")
        return {"error": str(e)}


def music_result(task_id: str) -> Dict[str, Any]:
    """
    Get the result of a completed music generation.

    Args:
        task_id: The task ID from music_generate()

    Returns:
        Dict with audio file path, URL, title, and duration.

    Example:
        >>> music_result("music_1704067200000")
        {"success": True, "audio_file": "sandbox/music/Meditation_abc12345.mp3", ...}
    """
    try:
        manager = _get_manager()
        task = manager.get_task(task_id)

        if not task:
            return {
                "found": False,
                "error": f"Task {task_id} not found"
            }

        if task.status == MusicTaskStatus.COMPLETED:
            return {
                "found": True,
                "success": True,
                "task_id": task_id,
                "audio_file": task.audio_file,
                "audio_url": task.audio_url,
                "title": task.title,
                "duration": task.duration,
                "model": task.model,
                "is_instrumental": task.is_instrumental,
                "prompt": task.prompt,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "message": f"Audio saved to: {task.audio_file}"
            }
        elif task.status == MusicTaskStatus.FAILED:
            return {
                "found": True,
                "success": False,
                "task_id": task_id,
                "status": "failed",
                "error": task.error,
                "prompt": task.prompt
            }
        else:
            return {
                "found": True,
                "success": False,
                "task_id": task_id,
                "status": task.status.value,
                "progress": task.progress,
                "message": f"Generation still in progress. Current status: {task.progress}"
            }

    except Exception as e:
        logger.error(f"Error getting music result: {e}")
        return {"error": str(e)}


def music_list(limit: int = 10) -> Dict[str, Any]:
    """
    List recent music generation tasks.

    Args:
        limit: Maximum number of tasks to return (default 10)

    Returns:
        Dict with list of recent tasks and count.

    Example:
        >>> music_list(5)
        {"tasks": [...], "count": 5}
    """
    try:
        manager = _get_manager()
        tasks = manager.list_tasks(limit)

        return {
            "tasks": [
                {
                    "task_id": t.task_id,
                    "title": t.title or "Untitled",
                    "status": t.status.value,
                    "model": t.model,
                    "duration": t.duration,
                    "audio_file": t.audio_file,
                    "created_at": t.created_at
                }
                for t in tasks
            ],
            "count": len(tasks),
            "total_in_storage": len(manager.tasks)
        }

    except Exception as e:
        logger.error(f"Error listing music tasks: {e}")
        return {"error": str(e)}


# ============================================================================
# TOOL SCHEMAS
# ============================================================================

MUSIC_TOOL_SCHEMAS = {
    "music_generate": {
        "name": "music_generate",
        "description": (
            "Generate AI music via Suno. By default (blocking=True), waits until complete and returns "
            "the audio file path directly. Set blocking=False to return immediately with task_id for polling. "
            "Generation takes 2-4 minutes. Use when user asks for music, wants a soundtrack, "
            "or when !MUSIC trigger is detected."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Music description or lyrics. Be specific about mood, genre, instruments, tempo."
                },
                "style": {
                    "type": "string",
                    "description": "Style tags (e.g., 'electronic ambient', 'jazz piano', 'epic orchestral')",
                    "default": ""
                },
                "title": {
                    "type": "string",
                    "description": "Song title (optional, auto-generated if empty)",
                    "default": ""
                },
                "model": {
                    "type": "string",
                    "enum": ["V3_5", "V4", "V4_5", "V5"],
                    "description": "Suno model version. V5 is newest and best quality.",
                    "default": "V5"
                },
                "is_instrumental": {
                    "type": "boolean",
                    "description": "True for instrumental (no vocals), False to include AI vocals",
                    "default": True
                },
                "blocking": {
                    "type": "boolean",
                    "description": "If True (default), waits for completion and returns audio file. If False, returns task_id immediately for polling with music_status().",
                    "default": True
                }
            },
            "required": ["prompt"]
        }
    },
    "music_status": {
        "name": "music_status",
        "description": (
            "Check the progress of a music generation task. "
            "Returns status (pending/generating/completed/failed), progress message, and timing info."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID returned by music_generate()"
                }
            },
            "required": ["task_id"]
        }
    },
    "music_result": {
        "name": "music_result",
        "description": (
            "Get the result of a completed music generation. "
            "Returns the audio file path, URL, title, and duration. "
            "Only works after status is 'completed'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID returned by music_generate()"
                }
            },
            "required": ["task_id"]
        }
    },
    "music_list": {
        "name": "music_list",
        "description": (
            "List recent music generation tasks. "
            "Shows task_id, title, status, model, and file path for each."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tasks to return",
                    "default": 10
                }
            },
            "required": []
        }
    }
}
