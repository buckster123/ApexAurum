"""
Streaming Infrastructure for AI APIs

Handles real-time streaming of responses, tool execution tracking,
and event emission for UI updates.

Components:
1. StreamEvent - Event objects for stream processing
2. ToolExecutionTracker - Track tool execution status and timing
3. ProgressIndicator - Animated spinner and progress display
4. format_tool_display - Format tool calls for UI

Usage:
    from reusable_lib.streaming import (
        StreamEvent,
        ToolExecutionTracker,
        ProgressIndicator,
        format_tool_display
    )

    # Track tool execution
    tracker = ToolExecutionTracker()
    tracker.start_tool("toolu_123", "calculator", {"a": 5, "b": 3})
    # ... execute tool ...
    tracker.complete_tool("toolu_123", result=8)

    # Progress indicator
    progress = ProgressIndicator()
    while working:
        print(progress.format_status("Processing..."))
        time.sleep(0.1)

    # Format for display
    display = format_tool_display(
        "calculator",
        {"a": 5, "b": 3},
        status="complete",
        duration=0.5,
        result=8
    )
"""

import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """
    Event emitted during streaming operations.

    Event types:
    - text_delta: Text chunk received
    - thinking_delta: Extended thinking content chunk
    - thinking_start: Extended thinking block started
    - thinking_end: Extended thinking block ended
    - tool_start: Tool execution started
    - tool_input_complete: Tool input fully received
    - tool_complete: Tool execution completed
    - error: Error occurred
    - done: Stream complete
    - final_message: Complete message object
    """
    event_type: str
    data: Any
    timestamp: float = field(default_factory=time.time)

    def __repr__(self):
        return f"StreamEvent(type={self.event_type}, data={self.data})"

    def is_text(self) -> bool:
        """Check if this is a text content event."""
        return self.event_type in ("text_delta", "thinking_delta")

    def is_tool_event(self) -> bool:
        """Check if this is a tool-related event."""
        return self.event_type in ("tool_start", "tool_input_complete", "tool_complete")

    def is_terminal(self) -> bool:
        """Check if this is a terminal event (done or error)."""
        return self.event_type in ("done", "error", "final_message")


class ToolExecutionTracker:
    """
    Tracks tool execution status and provides progress updates.

    Maintains state for all tools currently executing or completed
    within a single request.
    """

    def __init__(self):
        """Initialize tool execution tracker."""
        self.active_tools: Dict[str, Dict[str, Any]] = {}
        self.completed_tools: Dict[str, Dict[str, Any]] = {}

    def start_tool(
        self,
        tool_id: str,
        tool_name: str,
        tool_input: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark a tool as started.

        Args:
            tool_id: Unique tool execution ID
            tool_name: Name of the tool
            tool_input: Tool input parameters
        """
        self.active_tools[tool_id] = {
            "name": tool_name,
            "input": tool_input or {},
            "status": "running",
            "start_time": time.time(),
        }
        logger.info(f"Tool started: {tool_name} (ID: {tool_id})")

    def complete_tool(
        self,
        tool_id: str,
        result: Any,
        is_error: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Mark a tool as completed.

        Args:
            tool_id: Tool execution ID
            result: Tool execution result
            is_error: Whether the result is an error

        Returns:
            Completed tool data, or None if tool not found
        """
        if tool_id not in self.active_tools:
            logger.warning(f"Attempted to complete unknown tool: {tool_id}")
            return None

        tool_data = self.active_tools.pop(tool_id)
        tool_data["status"] = "error" if is_error else "complete"
        tool_data["result"] = result
        tool_data["end_time"] = time.time()
        tool_data["duration"] = tool_data["end_time"] - tool_data["start_time"]
        tool_data["is_error"] = is_error

        self.completed_tools[tool_id] = tool_data

        status = "with error" if is_error else "successfully"
        logger.info(
            f"Tool completed {status}: {tool_data['name']} "
            f"(ID: {tool_id}, {tool_data['duration']:.2f}s)"
        )

        return tool_data

    def get_active_tools(self) -> List[Dict[str, Any]]:
        """Get list of currently executing tools."""
        return list(self.active_tools.values())

    def get_completed_tools(self) -> List[Dict[str, Any]]:
        """Get list of completed tools."""
        return list(self.completed_tools.values())

    def get_tool_status(self, tool_id: str) -> Optional[str]:
        """Get status of a specific tool."""
        if tool_id in self.active_tools:
            return self.active_tools[tool_id]["status"]
        elif tool_id in self.completed_tools:
            return self.completed_tools[tool_id]["status"]
        return None

    def get_elapsed_time(self, tool_id: str) -> Optional[float]:
        """Get elapsed time for a tool."""
        if tool_id in self.active_tools:
            return time.time() - self.active_tools[tool_id]["start_time"]
        elif tool_id in self.completed_tools:
            return self.completed_tools[tool_id]["duration"]
        return None

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get tool data by ID (active or completed)."""
        return self.active_tools.get(tool_id) or self.completed_tools.get(tool_id)

    def clear(self) -> None:
        """Clear all tool tracking data."""
        self.active_tools.clear()
        self.completed_tools.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all tool executions."""
        total_duration = sum(
            t["duration"] for t in self.completed_tools.values()
        )
        error_count = sum(
            1 for t in self.completed_tools.values() if t.get("is_error")
        )

        return {
            "active_count": len(self.active_tools),
            "completed_count": len(self.completed_tools),
            "error_count": error_count,
            "total_duration": total_duration,
            "tools": [t["name"] for t in self.completed_tools.values()]
        }


class ProgressIndicator:
    """
    Generates animated progress indicators.

    Provides spinner animations and status messages for
    long-running operations.
    """

    # Spinner frames (Unicode Braille patterns)
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    # Alternative spinners
    DOTS_FRAMES = ["⠋", "⠙", "⠚", "⠞", "⠖", "⠦", "⠴", "⠲", "⠳", "⠓"]
    SIMPLE_FRAMES = ["|", "/", "-", "\\"]
    CLOCK_FRAMES = ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"]

    def __init__(self, style: str = "braille"):
        """
        Initialize progress indicator.

        Args:
            style: Spinner style - "braille", "dots", "simple", "clock"
        """
        styles = {
            "braille": self.SPINNER_FRAMES,
            "dots": self.DOTS_FRAMES,
            "simple": self.SIMPLE_FRAMES,
            "clock": self.CLOCK_FRAMES
        }
        self.frames = styles.get(style, self.SPINNER_FRAMES)
        self.frame_index = 0
        self.start_time = time.time()

    def next_frame(self) -> str:
        """Get next spinner frame."""
        frame = self.frames[self.frame_index]
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        return frame

    def get_elapsed(self) -> float:
        """Get elapsed time since start."""
        return time.time() - self.start_time

    def format_status(self, message: str) -> str:
        """
        Format status message with spinner and time.

        Args:
            message: Status message

        Returns:
            Formatted status string
        """
        elapsed = self.get_elapsed()
        spinner = self.next_frame()
        return f"{spinner} {message} ({elapsed:.1f}s)"

    def format_progress(self, message: str, progress: float) -> str:
        """
        Format status with progress bar.

        Args:
            message: Status message
            progress: Progress ratio (0.0 to 1.0)

        Returns:
            Formatted progress string
        """
        bar_width = 20
        filled = int(bar_width * min(progress, 1.0))
        bar = "█" * filled + "░" * (bar_width - filled)
        pct = progress * 100

        spinner = self.next_frame()
        elapsed = self.get_elapsed()

        return f"{spinner} {message} [{bar}] {pct:.0f}% ({elapsed:.1f}s)"

    def reset(self) -> None:
        """Reset indicator state."""
        self.frame_index = 0
        self.start_time = time.time()


def format_tool_display(
    tool_name: str,
    tool_input: Dict[str, Any],
    status: str = "running",
    duration: Optional[float] = None,
    result: Optional[Any] = None,
    max_input_length: int = 50,
    max_result_length: int = 100
) -> str:
    """
    Format tool execution for display.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters
        status: Tool status (running, complete, error)
        duration: Execution duration in seconds
        result: Tool result (if complete)
        max_input_length: Max chars per input value
        max_result_length: Max chars for result

    Returns:
        Formatted display string
    """
    # Status emoji
    status_emoji = {
        "running": "🔄",
        "complete": "✅",
        "error": "❌",
        "pending": "⏳"
    }.get(status, "⏳")

    # Format tool call
    input_parts = []
    for k, v in tool_input.items():
        v_str = repr(v)
        if len(v_str) > max_input_length:
            v_str = v_str[:max_input_length] + "..."
        input_parts.append(f"{k}={v_str}")

    input_str = ", ".join(input_parts)
    tool_call = f"{tool_name}({input_str})"

    # Add duration if available
    if duration is not None:
        tool_call += f"  [{duration:.2f}s]"

    # Add result preview if complete
    if status == "complete" and result is not None:
        result_str = str(result)
        if len(result_str) > max_result_length:
            result_str = result_str[:max_result_length] + "..."
        tool_call += f"\n   └─ {result_str}"
    elif status == "error" and result is not None:
        result_str = str(result)
        if len(result_str) > max_result_length:
            result_str = result_str[:max_result_length] + "..."
        tool_call += f"\n   └─ Error: {result_str}"

    return f"{status_emoji} **{tool_call}**"


def estimate_stream_progress(
    tokens_generated: int,
    estimated_total: int
) -> float:
    """
    Estimate streaming progress.

    Args:
        tokens_generated: Number of tokens generated so far
        estimated_total: Estimated total tokens

    Returns:
        Progress ratio (0.0 to 1.0)
    """
    if estimated_total <= 0:
        return 0.0

    return min(tokens_generated / estimated_total, 1.0)


def format_elapsed_time(seconds: float) -> str:
    """
    Format elapsed time for display.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string
    """
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
