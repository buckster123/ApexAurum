"""
Streaming Infrastructure for Claude API

Handles real-time streaming of responses, tool execution tracking,
and event emission for UI updates.

This module provides:
1. Streaming response handler
2. Tool execution tracker
3. Stream event system
4. Progress indicators
"""

import time
import logging
from typing import Any, Dict, List, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime
from anthropic.types import ContentBlock

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """
    Event emitted during streaming operations.

    Event types:
    - text_delta: Text chunk received
    - tool_start: Tool execution started
    - tool_complete: Tool execution completed
    - thinking: Processing status update
    - error: Error occurred
    - done: Stream complete
    """
    event_type: str
    data: Any
    timestamp: float = field(default_factory=time.time)

    def __repr__(self):
        return f"StreamEvent(type={self.event_type}, data={self.data})"


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

    def start_tool(self, tool_id: str, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """
        Mark a tool as started.

        Args:
            tool_id: Unique tool execution ID
            tool_name: Name of the tool
            tool_input: Tool input parameters
        """
        self.active_tools[tool_id] = {
            "name": tool_name,
            "input": tool_input,
            "status": "running",
            "start_time": time.time(),
        }
        logger.info(f"Tool started: {tool_name} (ID: {tool_id})")

    def complete_tool(
        self,
        tool_id: str,
        result: Any,
        is_error: bool = False
    ) -> None:
        """
        Mark a tool as completed.

        Args:
            tool_id: Tool execution ID
            result: Tool execution result
            is_error: Whether the result is an error
        """
        if tool_id not in self.active_tools:
            logger.warning(f"Attempted to complete unknown tool: {tool_id}")
            return

        tool_data = self.active_tools.pop(tool_id)
        tool_data["status"] = "error" if is_error else "complete"
        tool_data["result"] = result
        tool_data["end_time"] = time.time()
        tool_data["duration"] = tool_data["end_time"] - tool_data["start_time"]
        tool_data["is_error"] = is_error

        self.completed_tools[tool_id] = tool_data

        status = "with error" if is_error else "successfully"
        logger.info(f"Tool completed {status}: {tool_data['name']} (ID: {tool_id}, {tool_data['duration']:.2f}s)")

    def get_active_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of currently executing tools.

        Returns:
            List of active tool data dicts
        """
        return list(self.active_tools.values())

    def get_completed_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of completed tools.

        Returns:
            List of completed tool data dicts
        """
        return list(self.completed_tools.values())

    def get_tool_status(self, tool_id: str) -> Optional[str]:
        """
        Get status of a specific tool.

        Args:
            tool_id: Tool execution ID

        Returns:
            Status string or None if not found
        """
        if tool_id in self.active_tools:
            return self.active_tools[tool_id]["status"]
        elif tool_id in self.completed_tools:
            return self.completed_tools[tool_id]["status"]
        return None

    def get_elapsed_time(self, tool_id: str) -> Optional[float]:
        """
        Get elapsed time for a tool.

        Args:
            tool_id: Tool execution ID

        Returns:
            Elapsed time in seconds, or None if not found
        """
        if tool_id in self.active_tools:
            return time.time() - self.active_tools[tool_id]["start_time"]
        elif tool_id in self.completed_tools:
            return self.completed_tools[tool_id]["duration"]
        return None

    def clear(self) -> None:
        """Clear all tool tracking data."""
        self.active_tools.clear()
        self.completed_tools.clear()


class StreamingResponseHandler:
    """
    Handles streaming responses from Claude API.

    Processes stream chunks, buffers text, detects tool use,
    and emits events for UI updates.
    """

    def __init__(self, api_client: Any):
        """
        Initialize streaming response handler.

        Args:
            api_client: Claude API client instance
        """
        self.api_client = api_client
        self.text_buffer = ""
        self.current_tool_use = None

    def stream_message(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 64000,
        temperature: float = 1.0,
        top_p: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Generator[StreamEvent, None, None]:
        """
        Stream a message and yield events.

        Args:
            messages: Conversation messages
            system: System prompt
            model: Model to use
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            tools: Tool schemas
            **kwargs: Additional API parameters

        Yields:
            StreamEvent objects for text deltas and tool use
        """
        try:
            # Build API parameters, excluding None values
            api_params = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # Add optional parameters only if not None
            if system is not None:
                api_params["system"] = system
            if model is not None:
                api_params["model"] = model
            if top_p is not None:
                api_params["top_p"] = top_p
            if tools is not None:
                api_params["tools"] = tools

            # Add any additional kwargs
            api_params.update(kwargs)

            # Create streaming message
            with self.api_client.client.messages.stream(**api_params) as stream:

                # Process stream chunks
                for event in stream:
                    # Get event type
                    event_type = event.type if hasattr(event, 'type') else str(type(event))

                    # Text delta events
                    if event_type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, 'type') and delta.type == 'text_delta':
                            text = delta.text
                            self.text_buffer += text
                            yield StreamEvent(
                                event_type="text_delta",
                                data=text,
                                timestamp=time.time()
                            )

                    # Content block start (could be text or tool_use)
                    elif event_type == "content_block_start":
                        content_block = event.content_block
                        if hasattr(content_block, 'type'):
                            if content_block.type == 'tool_use':
                                # Tool use started
                                self.current_tool_use = {
                                    "id": content_block.id,
                                    "name": content_block.name,
                                    "input": {}
                                }
                                yield StreamEvent(
                                    event_type="tool_start",
                                    data={
                                        "id": content_block.id,
                                        "name": content_block.name
                                    },
                                    timestamp=time.time()
                                )

                    # Input delta for tool use
                    elif event_type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, 'type') and delta.type == 'input_json_delta':
                            # Tool input is being streamed
                            # We'll accumulate and emit on block stop
                            pass

                    # Content block stop
                    elif event_type == "content_block_stop":
                        if self.current_tool_use:
                            # Tool use complete (input received)
                            yield StreamEvent(
                                event_type="tool_input_complete",
                                data=self.current_tool_use,
                                timestamp=time.time()
                            )
                            self.current_tool_use = None

                    # Message complete
                    elif event_type == "message_stop":
                        yield StreamEvent(
                            event_type="done",
                            data={"text": self.text_buffer},
                            timestamp=time.time()
                        )

                # Get final message
                final_message = stream.get_final_message()

                yield StreamEvent(
                    event_type="final_message",
                    data=final_message,
                    timestamp=time.time()
                )

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield StreamEvent(
                event_type="error",
                data={"error": str(e), "type": type(e).__name__},
                timestamp=time.time()
            )

    def reset(self) -> None:
        """Reset handler state for new stream."""
        self.text_buffer = ""
        self.current_tool_use = None


class ProgressIndicator:
    """
    Generates animated progress indicators.

    Provides spinner animations and status messages for
    long-running operations.
    """

    # Spinner frames (Unicode Braille patterns)
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self):
        """Initialize progress indicator."""
        self.frame_index = 0
        self.start_time = time.time()

    def next_frame(self) -> str:
        """
        Get next spinner frame.

        Returns:
            Spinner character
        """
        frame = self.SPINNER_FRAMES[self.frame_index]
        self.frame_index = (self.frame_index + 1) % len(self.SPINNER_FRAMES)
        return frame

    def get_elapsed(self) -> float:
        """
        Get elapsed time since start.

        Returns:
            Elapsed time in seconds
        """
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

    def reset(self) -> None:
        """Reset indicator state."""
        self.frame_index = 0
        self.start_time = time.time()


def format_tool_display(
    tool_name: str,
    tool_input: Dict[str, Any],
    status: str = "running",
    duration: Optional[float] = None,
    result: Optional[Any] = None
) -> str:
    """
    Format tool execution for display.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters
        status: Tool status (running, complete, error)
        duration: Execution duration in seconds
        result: Tool result (if complete)

    Returns:
        Formatted display string
    """
    # Status emoji
    status_emoji = {
        "running": "🔄",
        "complete": "✅",
        "error": "❌"
    }.get(status, "⏳")

    # Format tool call
    input_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in tool_input.items())
    tool_call = f"{tool_name}({input_str})"

    # Add duration if available
    if duration is not None:
        tool_call += f"  [{duration:.2f}s]"

    # Add result preview if complete
    if status == "complete" and result is not None:
        result_str = str(result)[:100]
        if len(str(result)) > 100:
            result_str += "..."
        tool_call += f"\n   └─ {result_str}"
    elif status == "error" and result is not None:
        tool_call += f"\n   └─ Error: {result}"

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

    progress = min(tokens_generated / estimated_total, 1.0)
    return progress
