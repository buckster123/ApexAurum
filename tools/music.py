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


def _post_to_village(task: "MusicTask") -> bool:
    """
    Post completed song to village knowledge for cultural memory.
    Non-blocking, errors logged but don't affect task completion.
    """
    try:
        # Import here to avoid circular imports
        from tools.vector_search import vector_add_knowledge

        # Build song description for knowledge base
        style_info = f", style: {task.style}" if task.style else ""
        vocal_type = "instrumental" if task.is_instrumental else "with vocals"

        fact = (
            f"🎵 SONG CREATED: \"{task.title}\" ({vocal_type}{style_info})\n"
            f"Duration: {task.duration:.1f}s | Model: {task.model}\n"
            f"Prompt: {task.prompt[:200]}{'...' if len(task.prompt) > 200 else ''}\n"
            f"File: {task.audio_file}"
        )

        result = vector_add_knowledge(
            fact=fact,
            category="cultural",  # Fits village protocol's cultural transmission
            confidence=1.0,
            source="music_generation",
            visibility="village",  # Shared in village square
            agent_id=task.agent_id or "MUSIC_PIPELINE",
            conversation_thread="music_creations"
        )

        if result.get("success"):
            logger.info(f"Posted song '{task.title}' to village knowledge")
            return True
        else:
            logger.warning(f"Failed to post song to village: {result.get('error')}")
            return False

    except Exception as e:
        logger.warning(f"Error posting song to village (non-fatal): {e}")
        return False

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
    # Phase 1.5: Curation & Memory
    agent_id: Optional[str] = None  # Creator agent
    favorite: bool = False  # Favorited by user
    play_count: int = 0  # Times played
    tags: List[str] = field(default_factory=list)  # User tags
    posted_to_village: bool = False  # Memory integration flag

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
            # Phase 1.5 fields
            "agent_id": self.agent_id,
            "favorite": self.favorite,
            "play_count": self.play_count,
            "tags": self.tags,
            "posted_to_village": self.posted_to_village,
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
            # Phase 1.5 fields
            agent_id=data.get("agent_id"),
            favorite=data.get("favorite", False),
            play_count=data.get("play_count", 0),
            tags=data.get("tags", []),
            posted_to_village=data.get("posted_to_village", False),
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
        is_instrumental: bool = True,
        agent_id: Optional[str] = None
    ) -> MusicTask:
        """Create a new music task"""
        task_id = f"music_{int(datetime.now().timestamp() * 1000)}"
        task = MusicTask(
            task_id=task_id,
            prompt=prompt,
            style=style,
            title=title,
            model=model,
            is_instrumental=is_instrumental,
            agent_id=agent_id
        )
        self.tasks[task_id] = task
        self._save_tasks()
        logger.info(f"Created music task {task_id} by {agent_id or 'unknown'}: {prompt[:50]}...")
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

                # Post to village knowledge (non-blocking, errors don't fail task)
                if _post_to_village(task):
                    task.posted_to_village = True
                    self._save_tasks()

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
    blocking: Optional[bool] = None,
    agent_id: Optional[str] = None
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
        agent_id: ID of the agent creating this song (for village memory attribution).

    Returns:
        If blocking=True: Dict with audio_file path when complete
        If blocking=False: Dict with task_id. Use music_status(task_id) to check progress.

    Note:
        Completed songs are automatically posted to village knowledge for cultural memory.

    Example:
        >>> music_generate("ambient electronic meditation", blocking=True)
        {"success": True, "audio_file": "sandbox/music/...", "duration": 120.5, ...}

        >>> music_generate("ambient electronic meditation", blocking=False, agent_id="AZOTH")
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
        task = manager.create_task(prompt, style, title, model, is_instrumental, agent_id)

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
                    "agent_id": task.agent_id,
                    "posted_to_village": task.posted_to_village,
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
# CURATION TOOLS (Phase 1.5)
# ============================================================================

def music_favorite(task_id: str, favorite: Optional[bool] = None) -> Dict[str, Any]:
    """
    Toggle or set favorite status for a song.

    Args:
        task_id: The task ID of the song
        favorite: True to favorite, False to unfavorite, None to toggle

    Returns:
        Dict with updated favorite status.

    Example:
        >>> music_favorite("music_1704067200000")
        {"success": True, "task_id": "...", "favorite": True}
    """
    try:
        manager = _get_manager()
        task = manager.get_task(task_id)

        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        # Toggle if not specified
        if favorite is None:
            task.favorite = not task.favorite
        else:
            task.favorite = favorite

        manager._save_tasks()

        return {
            "success": True,
            "task_id": task_id,
            "title": task.title,
            "favorite": task.favorite,
            "message": f"{'Added to' if task.favorite else 'Removed from'} favorites: {task.title}"
        }

    except Exception as e:
        logger.error(f"Error updating favorite status: {e}")
        return {"success": False, "error": str(e)}


def music_library(
    agent_id: Optional[str] = None,
    favorites_only: bool = False,
    status: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Browse music library with filters.

    Args:
        agent_id: Filter by creator agent (e.g., "AZOTH", "ELYSIAN")
        favorites_only: Only show favorited songs
        status: Filter by status (completed, failed, pending, generating)
        limit: Maximum songs to return (default 20)

    Returns:
        Dict with filtered songs and statistics.

    Example:
        >>> music_library(agent_id="AZOTH", favorites_only=True)
        {"songs": [...], "count": 3, "total_duration": 360.5}
    """
    try:
        manager = _get_manager()

        # Get all tasks sorted by date
        all_tasks = sorted(
            manager.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )

        # Apply filters
        filtered = []
        for task in all_tasks:
            # Agent filter
            if agent_id and task.agent_id != agent_id:
                continue
            # Favorites filter
            if favorites_only and not task.favorite:
                continue
            # Status filter
            if status and task.status.value != status:
                continue

            filtered.append(task)

            if len(filtered) >= limit:
                break

        # Calculate stats
        total_duration = sum(t.duration for t in filtered if t.duration)
        completed_count = sum(1 for t in filtered if t.status == MusicTaskStatus.COMPLETED)

        # Build response
        songs = []
        for t in filtered:
            songs.append({
                "task_id": t.task_id,
                "title": t.title or "Untitled",
                "agent_id": t.agent_id,
                "status": t.status.value,
                "favorite": t.favorite,
                "play_count": t.play_count,
                "duration": t.duration,
                "audio_file": t.audio_file,
                "is_instrumental": t.is_instrumental,
                "created_at": t.created_at,
                "posted_to_village": t.posted_to_village
            })

        return {
            "songs": songs,
            "count": len(songs),
            "completed_count": completed_count,
            "total_duration": total_duration,
            "total_in_library": len(manager.tasks),
            "filters_applied": {
                "agent_id": agent_id,
                "favorites_only": favorites_only,
                "status": status
            }
        }

    except Exception as e:
        logger.error(f"Error browsing music library: {e}")
        return {"error": str(e)}


def music_search(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search songs by title, prompt, or style.

    Args:
        query: Search text (matches title, prompt, or style)
        limit: Maximum results (default 10)

    Returns:
        Dict with matching songs.

    Example:
        >>> music_search("ambient meditation")
        {"results": [...], "count": 2, "query": "ambient meditation"}
    """
    try:
        manager = _get_manager()
        query_lower = query.lower()

        # Search all tasks
        matches = []
        for task in manager.tasks.values():
            # Search in title, prompt, and style
            searchable = f"{task.title} {task.prompt} {task.style}".lower()
            if query_lower in searchable:
                matches.append((task, searchable.count(query_lower)))

        # Sort by relevance (match count) then by date
        matches.sort(key=lambda x: (-x[1], x[0].created_at), reverse=True)

        # Limit results
        results = []
        for task, _score in matches[:limit]:
            results.append({
                "task_id": task.task_id,
                "title": task.title or "Untitled",
                "agent_id": task.agent_id,
                "status": task.status.value,
                "favorite": task.favorite,
                "duration": task.duration,
                "audio_file": task.audio_file,
                "prompt_preview": task.prompt[:100] + ("..." if len(task.prompt) > 100 else ""),
                "created_at": task.created_at
            })

        return {
            "results": results,
            "count": len(results),
            "query": query,
            "total_searched": len(manager.tasks)
        }

    except Exception as e:
        logger.error(f"Error searching music: {e}")
        return {"error": str(e)}


def music_play(task_id: str) -> Dict[str, Any]:
    """
    Mark a song as played (increments play count) and return file path.

    Args:
        task_id: The task ID of the song to play

    Returns:
        Dict with audio file path and updated stats.

    Example:
        >>> music_play("music_1704067200000")
        {"success": True, "audio_file": "...", "play_count": 3}
    """
    try:
        manager = _get_manager()
        task = manager.get_task(task_id)

        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        if task.status != MusicTaskStatus.COMPLETED:
            return {
                "success": False,
                "error": f"Song not ready. Status: {task.status.value}",
                "status": task.status.value
            }

        # Increment play count
        task.play_count += 1
        manager._save_tasks()

        # Update latest track for sidebar
        _set_latest_track({
            "filepath": task.audio_file,
            "title": task.title,
            "duration": task.duration,
            "task_id": task_id
        })

        # Try to set Streamlit session state directly for immediate update
        try:
            import streamlit as st
            if hasattr(st, 'session_state'):
                st.session_state.music_current_track = {
                    "filepath": task.audio_file,
                    "title": task.title,
                    "duration": task.duration,
                    "task_id": task_id
                }
                st.session_state.music_player_expanded = True
                st.session_state.music_needs_refresh = True
                logger.info(f"Set session state for music_play: {task.title}")
        except Exception as e:
            logger.debug(f"Could not set session state directly: {e}")

        return {
            "success": True,
            "task_id": task_id,
            "title": task.title,
            "audio_file": task.audio_file,
            "duration": task.duration,
            "play_count": task.play_count,
            "agent_id": task.agent_id,
            "message": f"Now playing: {task.title}"
        }

    except Exception as e:
        logger.error(f"Error playing music: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# TOOL SCHEMAS
# ============================================================================

MUSIC_TOOL_SCHEMAS = {
    "music_generate": {
        "name": "music_generate",
        "description": (
            "Generate AI music via Suno. By default (blocking=True), waits until complete and returns "
            "the audio file path directly. Set blocking=False to return immediately with task_id for polling. "
            "Generation takes 2-4 minutes. Completed songs are automatically posted to village knowledge "
            "for cultural memory. Use when user asks for music, wants a soundtrack, or when !MUSIC trigger is detected."
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
                },
                "agent_id": {
                    "type": "string",
                    "description": "ID of the creating agent (e.g., 'AZOTH', 'ELYSIAN'). Used for village memory attribution.",
                    "default": ""
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
    },
    # Curation Tools (Phase 1.5)
    "music_favorite": {
        "name": "music_favorite",
        "description": (
            "Toggle or set favorite status for a song. "
            "Use to mark songs you or the user particularly enjoy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID of the song to favorite"
                },
                "favorite": {
                    "type": "boolean",
                    "description": "True to favorite, False to unfavorite. Omit to toggle."
                }
            },
            "required": ["task_id"]
        }
    },
    "music_library": {
        "name": "music_library",
        "description": (
            "Browse the music library with filters. "
            "Filter by agent, favorites, or status. Shows play counts and durations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Filter by creator agent (e.g., 'AZOTH', 'ELYSIAN')"
                },
                "favorites_only": {
                    "type": "boolean",
                    "description": "Only show favorited songs",
                    "default": False
                },
                "status": {
                    "type": "string",
                    "enum": ["completed", "failed", "pending", "generating"],
                    "description": "Filter by status"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum songs to return",
                    "default": 20
                }
            },
            "required": []
        }
    },
    "music_search": {
        "name": "music_search",
        "description": (
            "Search songs by title, prompt, or style text. "
            "Returns matching songs sorted by relevance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search text to find in title, prompt, or style"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    "music_play": {
        "name": "music_play",
        "description": (
            "Play a song - increments play count and loads to sidebar player. "
            "Returns the audio file path for playback."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID of the song to play"
                }
            },
            "required": ["task_id"]
        }
    }
}
