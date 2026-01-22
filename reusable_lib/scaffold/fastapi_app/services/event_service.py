"""
Event Broadcasting Service

Manages WebSocket connections and broadcasts tool events to connected clients.
Used by Village GUI for real-time agent visualization.
"""

import asyncio
import json
import logging
import time
from typing import Set, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events broadcast to frontend."""
    TOOL_START = "tool_start"
    TOOL_COMPLETE = "tool_complete"
    TOOL_ERROR = "tool_error"
    AGENT_THINKING = "agent_thinking"
    AGENT_IDLE = "agent_idle"
    CONNECTION = "connection"


# Zone mapping - which tools belong to which zone
TOOL_ZONE_MAP = {
    # DJ Booth - Music tools
    "music_generate": "dj_booth",
    "music_status": "dj_booth",
    "music_result": "dj_booth",
    "music_list": "dj_booth",
    "music_favorite": "dj_booth",
    "music_library": "dj_booth",
    "music_search": "dj_booth",
    "music_play": "dj_booth",
    "midi_create": "dj_booth",
    "music_compose": "dj_booth",

    # DJ Booth - Suno Prompt Compiler
    "suno_prompt_build": "dj_booth",
    "suno_prompt_preset_save": "dj_booth",
    "suno_prompt_preset_load": "dj_booth",
    "suno_prompt_preset_list": "dj_booth",

    # DJ Booth - Audio Editor
    "audio_info": "dj_booth",
    "audio_trim": "dj_booth",
    "audio_fade": "dj_booth",
    "audio_normalize": "dj_booth",
    "audio_loop": "dj_booth",
    "audio_concat": "dj_booth",
    "audio_speed": "dj_booth",
    "audio_reverse": "dj_booth",
    "audio_list_files": "dj_booth",
    "audio_get_waveform": "dj_booth",

    # Memory Garden - Vector and memory tools
    "vector_add": "memory_garden",
    "vector_search": "memory_garden",
    "vector_delete": "memory_garden",
    "vector_list_collections": "memory_garden",
    "vector_get_stats": "memory_garden",
    "vector_add_knowledge": "memory_garden",
    "vector_search_knowledge": "memory_garden",
    "memory_store": "memory_garden",
    "memory_retrieve": "memory_garden",
    "memory_search": "memory_garden",
    "memory_delete": "memory_garden",
    "memory_list": "memory_garden",
    "memory_health_stale": "memory_garden",
    "memory_health_low_access": "memory_garden",
    "memory_health_duplicates": "memory_garden",
    "memory_consolidate": "memory_garden",
    "memory_health_summary": "memory_garden",

    # File Shed - Filesystem tools
    "fs_read_file": "file_shed",
    "fs_write_file": "file_shed",
    "fs_list_files": "file_shed",
    "fs_mkdir": "file_shed",
    "fs_delete": "file_shed",
    "fs_exists": "file_shed",
    "fs_get_info": "file_shed",
    "fs_read_lines": "file_shed",
    "fs_edit": "file_shed",

    # Workshop - Code execution
    "execute_python": "workshop",

    # Bridge Portal - Agent and village tools
    "agent_spawn": "bridge_portal",
    "agent_status": "bridge_portal",
    "agent_result": "bridge_portal",
    "agent_list": "bridge_portal",
    "socratic_council": "bridge_portal",
    "village_post": "bridge_portal",
    "village_search": "bridge_portal",
    "village_get_thread": "bridge_portal",
    "village_list_agents": "bridge_portal",
    "summon_ancestor": "bridge_portal",
    "introduction_ritual": "bridge_portal",
    "village_detect_convergence": "bridge_portal",
    "village_get_stats": "bridge_portal",

    # Dataset tools - Memory Garden (knowledge-related)
    "dataset_list": "memory_garden",
    "dataset_query": "memory_garden",
}


@dataclass
class VillageEvent:
    """Event to be broadcast to frontend."""
    type: EventType
    agent_id: str
    tool: Optional[str] = None
    zone: str = "village_square"
    arguments: Optional[Dict] = None
    result_preview: Optional[str] = None
    success: Optional[bool] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    timestamp: int = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(time.time() * 1000)

    def to_json(self) -> str:
        """Convert to JSON string for WebSocket."""
        data = {k: v for k, v in asdict(self).items() if v is not None}
        data["type"] = self.type.value  # Convert enum to string
        return json.dumps(data)


class EventBroadcaster:
    """
    Singleton service for broadcasting events to WebSocket clients.

    Usage:
        broadcaster = get_event_broadcaster()
        await broadcaster.broadcast_tool_start("AZOTH", "music_generate", {"prompt": "..."})
    """

    _instance: Optional['EventBroadcaster'] = None

    def __init__(self):
        self.connections: Set = set()
        self._current_agent: str = "CLAUDE"  # Default agent
        self._tool_start_times: Dict[str, float] = {}

    @classmethod
    def get_instance(cls) -> 'EventBroadcaster':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_current_agent(self, agent_id: str):
        """Set the current active agent for events."""
        self._current_agent = agent_id

    def get_zone_for_tool(self, tool_name: str) -> str:
        """Get the zone a tool belongs to."""
        return TOOL_ZONE_MAP.get(tool_name, "village_square")

    async def connect(self, websocket):
        """Register a new WebSocket connection."""
        self.connections.add(websocket)
        logger.info(f"Village GUI connected. Total connections: {len(self.connections)}")

        # Send welcome event
        event = VillageEvent(
            type=EventType.CONNECTION,
            agent_id="SYSTEM",
            zone="village_square"
        )
        await websocket.send_text(event.to_json())

    def disconnect(self, websocket):
        """Remove a WebSocket connection."""
        self.connections.discard(websocket)
        logger.info(f"Village GUI disconnected. Total connections: {len(self.connections)}")

    async def broadcast(self, event: VillageEvent):
        """Broadcast event to all connected clients."""
        if not self.connections:
            return

        message = event.to_json()
        disconnected = set()

        for connection in self.connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected
        self.connections -= disconnected

    async def broadcast_tool_start(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_id: Optional[str] = None
    ):
        """Broadcast tool execution start."""
        agent = agent_id or self._current_agent
        zone = self.get_zone_for_tool(tool_name)

        # Track start time for duration calculation
        key = f"{agent}:{tool_name}"
        self._tool_start_times[key] = time.time()

        event = VillageEvent(
            type=EventType.TOOL_START,
            agent_id=agent,
            tool=tool_name,
            zone=zone,
            arguments=arguments
        )
        await self.broadcast(event)
        logger.debug(f"Broadcast tool_start: {agent} -> {tool_name} @ {zone}")

    async def broadcast_tool_complete(
        self,
        tool_name: str,
        result: Any,
        success: bool = True,
        agent_id: Optional[str] = None
    ):
        """Broadcast tool execution complete."""
        agent = agent_id or self._current_agent
        zone = self.get_zone_for_tool(tool_name)

        # Calculate duration
        key = f"{agent}:{tool_name}"
        start_time = self._tool_start_times.pop(key, None)
        duration_ms = int((time.time() - start_time) * 1000) if start_time else None

        # Create result preview (truncated)
        result_str = str(result)
        result_preview = result_str[:100] + "..." if len(result_str) > 100 else result_str

        event = VillageEvent(
            type=EventType.TOOL_COMPLETE,
            agent_id=agent,
            tool=tool_name,
            zone=zone,
            result_preview=result_preview,
            success=success,
            duration_ms=duration_ms
        )
        await self.broadcast(event)
        logger.debug(f"Broadcast tool_complete: {agent} <- {tool_name} ({duration_ms}ms)")

    async def broadcast_tool_error(
        self,
        tool_name: str,
        error: str,
        agent_id: Optional[str] = None
    ):
        """Broadcast tool execution error."""
        agent = agent_id or self._current_agent
        zone = self.get_zone_for_tool(tool_name)

        # Clean up start time
        key = f"{agent}:{tool_name}"
        self._tool_start_times.pop(key, None)

        event = VillageEvent(
            type=EventType.TOOL_ERROR,
            agent_id=agent,
            tool=tool_name,
            zone=zone,
            error=error[:200],
            success=False
        )
        await self.broadcast(event)

    # Synchronous versions for non-async contexts
    def broadcast_sync(self, event: VillageEvent):
        """Synchronous broadcast - works from any context."""
        if not self.connections:
            return  # No connections, skip

        message = event.to_json()
        disconnected = set()

        # Direct sync send to all connections
        for connection in list(self.connections):
            try:
                # Use the connection's underlying send - this works because
                # FastAPI/Starlette WebSocket has sync-compatible internals
                import anyio
                anyio.from_thread.run_sync(
                    lambda: None  # Dummy to check if we're in async context
                )
            except Exception:
                pass

        # Schedule on the event loop if available
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're being called from a sync context but there's a running loop
                # Use run_coroutine_threadsafe for proper scheduling
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(self.broadcast(event), loop)
                # Don't wait for result - fire and forget
                logger.debug(f"Scheduled broadcast: {event.type.value} - {event.tool}")
            else:
                # No running loop, run directly
                loop.run_until_complete(self.broadcast(event))
        except RuntimeError as e:
            # No event loop at all - try to get the running one differently
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self.broadcast(event))
            except RuntimeError:
                logger.debug(f"No event loop for broadcast: {event.type.value} - {event.tool}")

    def tool_start_sync(self, tool_name: str, arguments: Dict, agent_id: Optional[str] = None):
        """Synchronous tool start broadcast."""
        agent = agent_id or self._current_agent
        zone = self.get_zone_for_tool(tool_name)
        key = f"{agent}:{tool_name}"
        self._tool_start_times[key] = time.time()

        event = VillageEvent(
            type=EventType.TOOL_START,
            agent_id=agent,
            tool=tool_name,
            zone=zone,
            arguments=arguments
        )
        self.broadcast_sync(event)

    def tool_complete_sync(self, tool_name: str, result: Any, success: bool = True, agent_id: Optional[str] = None):
        """Synchronous tool complete broadcast."""
        agent = agent_id or self._current_agent
        zone = self.get_zone_for_tool(tool_name)

        key = f"{agent}:{tool_name}"
        start_time = self._tool_start_times.pop(key, None)
        duration_ms = int((time.time() - start_time) * 1000) if start_time else None

        result_str = str(result)
        result_preview = result_str[:100] + "..." if len(result_str) > 100 else result_str

        event = VillageEvent(
            type=EventType.TOOL_COMPLETE,
            agent_id=agent,
            tool=tool_name,
            zone=zone,
            result_preview=result_preview,
            success=success,
            duration_ms=duration_ms
        )
        self.broadcast_sync(event)


# Module-level singleton accessor
def get_event_broadcaster() -> EventBroadcaster:
    """Get the global event broadcaster instance."""
    return EventBroadcaster.get_instance()
