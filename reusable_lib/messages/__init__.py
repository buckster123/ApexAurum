# Messages - Message format conversion for AI APIs
# Extracted from ApexAurum - Claude Edition
# Handles conversion between OpenAI and Claude message formats

from .message_converter import (
    extract_system_prompt,
    add_system_to_messages,
    convert_openai_to_claude_messages,
    prepare_messages_for_claude,
    convert_tool_result_to_claude,
    validate_claude_messages,
    merge_consecutive_tool_results,
    format_tool_results_for_display,
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

__all__ = [
    # Message conversion
    'extract_system_prompt',
    'add_system_to_messages',
    'convert_openai_to_claude_messages',
    'prepare_messages_for_claude',
    'convert_tool_result_to_claude',
    'validate_claude_messages',
    'merge_consecutive_tool_results',
    'format_tool_results_for_display',
    # Tool adaptation
    'convert_openai_tool_to_claude',
    'convert_openai_tools_to_claude',
    'convert_claude_tool_call_to_openai',
    'extract_tool_calls_from_response',
    'format_tool_result_for_claude',
    'format_multiple_tool_results_for_claude',
    'validate_claude_tool_schema',
    'validate_claude_tool_schemas',
    'create_simple_tool_schema',
]
