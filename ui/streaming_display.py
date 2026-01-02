"""
Streaming Display Components for Streamlit

Provides UI components for displaying streaming content in real-time.

This module provides:
1. Streaming text display
2. Tool execution display
3. Status indicators
4. Progress tracking
"""

import time
import streamlit as st
from typing import Any, Dict, List, Optional
import json


class StreamingTextDisplay:
    """
    Display for streaming text content.

    Updates in real-time as text chunks arrive, with markdown rendering.
    """

    def __init__(self, container=None):
        """
        Initialize streaming text display.

        Args:
            container: Streamlit container to use (creates one if None)
        """
        self.container = container if container is not None else st.empty()
        self.text_buffer = ""
        self.finalized = False

    def append(self, text: str) -> None:
        """
        Append text to display.

        Args:
            text: Text chunk to append
        """
        if self.finalized:
            return

        self.text_buffer += text
        self.container.markdown(self.text_buffer)

    def set_text(self, text: str) -> None:
        """
        Set complete text (replace buffer).

        Args:
            text: Complete text to display
        """
        self.text_buffer = text
        self.container.markdown(self.text_buffer)

    def show_status(self, status: str) -> None:
        """
        Show temporary status message.

        Args:
            status: Status message
        """
        if not self.finalized:
            # Show status as italic text
            self.container.markdown(f"*{status}*")

    def finalize(self) -> str:
        """
        Mark display as complete and return final text.

        Returns:
            Final text buffer content
        """
        self.finalized = True
        # Final render with complete text
        if self.text_buffer:
            self.container.markdown(self.text_buffer)
        return self.text_buffer

    def clear(self) -> None:
        """Clear the display."""
        self.text_buffer = ""
        self.finalized = False
        self.container.empty()


class ToolExecutionDisplay:
    """
    Display for tool execution progress.

    Shows currently executing and completed tools with status indicators.
    Phase 2B Enhanced: Animated spinners, color-coded status, better formatting.
    """

    # Animated spinner frames
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    # Tool category icons
    TOOL_ICONS = {
        "file": "📁",
        "web": "🌐",
        "agent": "🤖",
        "code": "💻",
        "memory": "🧠",
        "vector": "🔍",
        "time": "⏰",
        "calc": "🔢",
        "string": "📝",
        "default": "🛠️"
    }

    def __init__(self, container=None):
        """
        Initialize tool execution display.

        Args:
            container: Streamlit container to use (creates one if None)
        """
        self.container = container if container is not None else st.empty()
        self.active_tools: Dict[str, Dict[str, Any]] = {}
        self.completed_tools: Dict[str, Dict[str, Any]] = {}
        self.tool_order: List[str] = []  # Track display order
        self.spinner_index = 0  # For animated spinners

    def start_tool(self, tool_id: str, tool_name: str, tool_input: Optional[Dict] = None) -> None:
        """
        Show tool starting.

        Args:
            tool_id: Tool execution ID
            tool_name: Name of the tool
            tool_input: Tool input parameters (optional)
        """
        self.active_tools[tool_id] = {
            "name": tool_name,
            "input": tool_input or {},
            "status": "running",
            "start_time": time.time()
        }
        if tool_id not in self.tool_order:
            self.tool_order.append(tool_id)
        self._render()

    def complete_tool(
        self,
        tool_id: str,
        result: Any,
        is_error: bool = False,
        duration: Optional[float] = None
    ) -> None:
        """
        Mark tool as complete.

        Args:
            tool_id: Tool execution ID
            result: Tool result
            is_error: Whether result is an error
            duration: Execution duration in seconds
        """
        if tool_id in self.active_tools:
            tool_data = self.active_tools.pop(tool_id)
            tool_data["status"] = "error" if is_error else "complete"
            tool_data["result"] = result
            tool_data["is_error"] = is_error
            tool_data["end_time"] = time.time()
            if duration is not None:
                tool_data["duration"] = duration
            else:
                tool_data["duration"] = tool_data["end_time"] - tool_data["start_time"]

            self.completed_tools[tool_id] = tool_data
            self._render()

    def _get_tool_category(self, tool_name: str) -> str:
        """
        Detect tool category from name.

        Args:
            tool_name: Tool name

        Returns:
            Category string (file/web/agent/code/memory/vector/time/calc/string/default)
        """
        name_lower = tool_name.lower()

        # File operations
        if any(x in name_lower for x in ["file", "read", "write", "list", "delete", "move", "copy"]):
            return "file"

        # Web operations
        if any(x in name_lower for x in ["web", "fetch", "search", "http", "url"]):
            return "web"

        # Agent operations
        if any(x in name_lower for x in ["agent", "spawn", "council", "socratic"]):
            return "agent"

        # Code execution
        if any(x in name_lower for x in ["code", "execute", "python", "run"]):
            return "code"

        # Memory operations
        if any(x in name_lower for x in ["memory", "store", "recall", "forget"]):
            return "memory"

        # Vector/search operations
        if any(x in name_lower for x in ["vector", "search", "knowledge", "semantic", "embed"]):
            return "vector"

        # Time operations
        if any(x in name_lower for x in ["time", "date", "clock"]):
            return "time"

        # Calculator
        if any(x in name_lower for x in ["calc", "math", "add", "subtract", "multiply"]):
            return "calc"

        # String operations
        if any(x in name_lower for x in ["string", "text", "concat", "split", "length"]):
            return "string"

        return "default"

    def _render(self) -> None:
        """Render current tool states."""
        with self.container.container():
            # Increment spinner for animated effect
            self.spinner_index = (self.spinner_index + 1) % len(self.SPINNER_FRAMES)

            # Render tools in order
            for tool_id in self.tool_order:
                tool_data = None

                if tool_id in self.active_tools:
                    tool_data = self.active_tools[tool_id]
                elif tool_id in self.completed_tools:
                    tool_data = self.completed_tools[tool_id]

                if tool_data:
                    self._render_tool(tool_id, tool_data)

    def _render_tool(self, tool_id: str, tool_data: Dict[str, Any]) -> None:
        """
        Render a single tool with enhanced visual feedback.

        Args:
            tool_id: Tool execution ID
            tool_data: Tool data dict
        """
        status = tool_data["status"]
        name = tool_data["name"]
        tool_input = tool_data.get("input", {})

        # Get tool category icon
        category = self._get_tool_category(name)
        category_icon = self.TOOL_ICONS.get(category, self.TOOL_ICONS["default"])

        # Status emoji and timing
        elapsed = None
        if status == "running":
            # Animated spinner
            spinner = self.SPINNER_FRAMES[self.spinner_index]
            elapsed = time.time() - tool_data["start_time"]
            time_str = f"⏱️ {elapsed:.1f}s"
            status_text = "Running"
        elif status == "complete":
            spinner = "✅"
            time_str = f"✓ {tool_data.get('duration', 0):.2f}s"
            status_text = "Complete"
        else:  # error
            spinner = "❌"
            time_str = f"✗ {tool_data.get('duration', 0):.2f}s"
            status_text = "Error"

        # Format tool call
        if tool_input:
            # Smart truncation of input parameters
            input_parts = []
            for k, v in tool_input.items():
                v_repr = repr(v)
                if len(v_repr) > 40:
                    v_repr = v_repr[:37] + "..."
                input_parts.append(f"{k}={v_repr}")
            input_str = ", ".join(input_parts)
            tool_call = f"{name}({input_str})"
        else:
            tool_call = f"{name}()"

        # Color-coded container based on status
        if status == "running":
            # Running tools in info container
            with st.container():
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    st.markdown(f"{spinner} {category_icon} **{tool_call}**")
                with col2:
                    st.caption(time_str)

                # Progress bar for long-running tools (>2s)
                if elapsed is not None and elapsed > 2.0:
                    # Pulse effect (indeterminate progress)
                    progress_value = (elapsed % 2) / 2  # Oscillates 0-1
                    st.progress(progress_value)

        elif status == "complete":
            # Completed tools in success container
            with st.success(f"{spinner} {category_icon} **{tool_call}**", icon="✅"):
                st.caption(f"{status_text} • {time_str}")

        else:  # error
            # Error tools in error container
            with st.error(f"{spinner} {category_icon} **{tool_call}**", icon="❌"):
                st.caption(f"{status_text} • {time_str}")

        # Show result if complete or error
        if status in ["complete", "error"] and "result" in tool_data:
            result = tool_data["result"]

            # Detect result type for smart formatting
            expander_label = "View Result" if status == "complete" else "View Error"

            with st.expander(expander_label, expanded=False):
                # JSON/dict/list formatting
                if isinstance(result, (dict, list)):
                    st.json(result)

                # String results - detect language for syntax highlighting
                elif isinstance(result, str):
                    result_str = result

                    # Detect code/structured content
                    language = "text"
                    if result_str.strip().startswith(("{", "[")):
                        language = "json"
                    elif result_str.strip().startswith("```"):
                        language = "markdown"
                    elif any(x in result_str for x in ["def ", "class ", "import ", "return "]):
                        language = "python"

                    # Truncate very long results
                    if len(result_str) > 1000:
                        st.code(result_str[:1000] + f"\n\n... ({len(result_str) - 1000} more characters)", language=language)
                    else:
                        st.code(result_str, language=language)

                # Other types
                else:
                    st.code(str(result), language="text")

    def clear(self) -> None:
        """Clear all tool displays."""
        self.active_tools.clear()
        self.completed_tools.clear()
        self.tool_order.clear()
        self.container.empty()

    def get_summary(self) -> Dict[str, int]:
        """
        Get summary of tool executions.

        Returns:
            Dict with counts of active, completed, and failed tools
        """
        failed = sum(1 for t in self.completed_tools.values() if t.get("is_error", False))
        completed = len(self.completed_tools) - failed

        return {
            "active": len(self.active_tools),
            "completed": completed,
            "failed": failed,
            "total": len(self.tool_order)
        }


class StatusIndicator:
    """
    Animated status indicator with spinner and elapsed time.
    """

    # Spinner frames
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, container=None):
        """
        Initialize status indicator.

        Args:
            container: Streamlit container to use
        """
        self.container = container if container is not None else st.empty()
        self.frame_index = 0
        self.start_time = time.time()
        self.message = ""

    def update(self, message: str) -> None:
        """
        Update status message.

        Args:
            message: Status message
        """
        self.message = message
        elapsed = time.time() - self.start_time
        spinner = self._next_frame()
        self.container.markdown(f"{spinner} {message} ({elapsed:.1f}s)")

    def _next_frame(self) -> str:
        """Get next spinner frame."""
        frame = self.SPINNER_FRAMES[self.frame_index]
        self.frame_index = (self.frame_index + 1) % len(self.SPINNER_FRAMES)
        return frame

    def done(self, message: Optional[str] = None) -> None:
        """
        Mark as complete.

        Args:
            message: Optional completion message
        """
        if message:
            self.container.markdown(f"✅ {message}")
        else:
            self.container.empty()

    def error(self, message: str) -> None:
        """
        Show error.

        Args:
            message: Error message
        """
        self.container.markdown(f"❌ {message}")

    def clear(self) -> None:
        """Clear the indicator."""
        self.container.empty()


class StreamingProgressBar:
    """
    Progress bar for long-running operations.
    """

    def __init__(self, container=None):
        """
        Initialize progress bar.

        Args:
            container: Streamlit container
        """
        self.container = container if container is not None else st.empty()
        self.progress_value = 0.0

    def update(self, progress: float, message: Optional[str] = None) -> None:
        """
        Update progress.

        Args:
            progress: Progress value (0.0 to 1.0)
            message: Optional status message
        """
        self.progress_value = max(0.0, min(1.0, progress))

        with self.container.container():
            st.progress(self.progress_value)
            if message:
                st.caption(message)

    def complete(self) -> None:
        """Mark as complete and remove."""
        self.container.empty()

    def clear(self) -> None:
        """Clear the progress bar."""
        self.container.empty()


def format_tool_for_display(
    tool_name: str,
    tool_input: Dict[str, Any],
    status: str = "running"
) -> str:
    """
    Format tool call for display.

    Args:
        tool_name: Tool name
        tool_input: Tool input parameters
        status: Status (running, complete, error)

    Returns:
        Formatted markdown string
    """
    emoji = {"running": "🔄", "complete": "✅", "error": "❌"}.get(status, "⏳")

    if tool_input:
        input_str = ", ".join(
            f"{k}={repr(v)[:30]}" + ("..." if len(repr(v)) > 30 else "")
            for k, v in tool_input.items()
        )
        return f"{emoji} **{tool_name}({input_str})**"
    else:
        return f"{emoji} **{tool_name}()**"


def create_streaming_container():
    """
    Create a container setup for streaming display.

    Returns:
        Tuple of (text_container, tool_container, status_container)
    """
    # Create placeholders
    status_container = st.empty()
    tool_container = st.empty()
    text_container = st.empty()

    return text_container, tool_container, status_container


def estimate_completion_time(
    start_time: float,
    progress: float
) -> Optional[str]:
    """
    Estimate completion time based on progress.

    Args:
        start_time: Operation start time
        progress: Current progress (0.0 to 1.0)

    Returns:
        Formatted ETA string or None
    """
    if progress <= 0.0:
        return None

    elapsed = time.time() - start_time
    if progress >= 1.0:
        return "Complete"

    total_estimated = elapsed / progress
    remaining = total_estimated - elapsed

    if remaining < 1:
        return "< 1s"
    elif remaining < 60:
        return f"{int(remaining)}s"
    else:
        minutes = int(remaining / 60)
        seconds = int(remaining % 60)
        return f"{minutes}m {seconds}s"
