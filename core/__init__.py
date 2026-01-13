"""
Core API Module

Provides Claude API client, model configuration, and message conversion utilities.
"""

from .api_client import (
    ClaudeAPIClient,
    ClaudeAPIClientWithRetry,
    test_connection,
)

from .models import (
    ClaudeModels,
    ModelSelector,
    ModelCapabilities,
    resolve_model,
    get_model_list,
    DEFAULT_MODEL,
    DEFAULT_MAX_TOKENS,
)

from .message_converter import (
    extract_system_prompt,
    prepare_messages_for_claude,
    convert_tool_result_to_claude,
    validate_claude_messages,
    merge_consecutive_tool_results,
)

from .tool_adapter import (
    convert_openai_tool_to_claude,
    convert_openai_tools_to_claude,
    convert_claude_tool_call_to_openai,
    extract_tool_calls_from_response,
    format_tool_result_for_claude,
    format_multiple_tool_results_for_claude,
    validate_claude_tool_schema,
    validate_claude_tool_schemas,
    create_simple_tool_schema,
)

from .tool_processor import (
    ToolRegistry,
    ToolExecutor,
    ToolCallLoop,
    get_global_registry,
    register_tool,
)

from .streaming import (
    StreamEvent,
    StreamingResponseHandler,
    ToolExecutionTracker,
    ProgressIndicator,
    format_tool_display,
    estimate_stream_progress,
)

from .sandbox_manager import (
    SandboxManager,
    SandboxConfig,
    ExecutionMode,
    ExecutionResult,
    get_sandbox_manager,
)

__all__ = [
    # API Client
    "ClaudeAPIClient",
    "ClaudeAPIClientWithRetry",
    "test_connection",
    # Models
    "ClaudeModels",
    "ModelSelector",
    "ModelCapabilities",
    "resolve_model",
    "get_model_list",
    "DEFAULT_MODEL",
    "DEFAULT_MAX_TOKENS",
    # Message Conversion
    "extract_system_prompt",
    "prepare_messages_for_claude",
    "convert_tool_result_to_claude",
    "validate_claude_messages",
    "merge_consecutive_tool_results",
    # Tool Adapter
    "convert_openai_tool_to_claude",
    "convert_openai_tools_to_claude",
    "convert_claude_tool_call_to_openai",
    "extract_tool_calls_from_response",
    "format_tool_result_for_claude",
    "format_multiple_tool_results_for_claude",
    "validate_claude_tool_schema",
    "validate_claude_tool_schemas",
    "create_simple_tool_schema",
    # Tool Processor
    "ToolRegistry",
    "ToolExecutor",
    "ToolCallLoop",
    "get_global_registry",
    "register_tool",
    # Streaming
    "StreamEvent",
    "StreamingResponseHandler",
    "ToolExecutionTracker",
    "ProgressIndicator",
    "format_tool_display",
    "estimate_stream_progress",
    # Sandbox
    "SandboxManager",
    "SandboxConfig",
    "ExecutionMode",
    "ExecutionResult",
    "get_sandbox_manager",
]
