"""
Tool Schema Adapter for AI APIs

Converts between OpenAI function call format and Claude tool format.
Also handles tool call extraction and result formatting.

Format Comparison:

OpenAI Format:
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather info",
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    }

Claude Format:
    {
        "name": "get_weather",
        "description": "Get weather info",
        "input_schema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }

Usage:
    from reusable_lib.messages import (
        convert_openai_tools_to_claude,
        format_tool_result_for_claude,
        create_simple_tool_schema
    )

    # Convert existing OpenAI tools
    claude_tools = convert_openai_tools_to_claude(openai_tools)

    # Create a new tool schema
    tool = create_simple_tool_schema(
        name="add",
        description="Add two numbers",
        properties={
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
        },
        required=["a", "b"]
    )
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def convert_openai_tool_to_claude(openai_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single OpenAI tool schema to Claude format.

    Args:
        openai_tool: OpenAI tool schema with type="function"

    Returns:
        Claude tool schema

    Example:
        >>> openai_tool = {
        ...     "type": "function",
        ...     "function": {
        ...         "name": "add",
        ...         "description": "Add two numbers",
        ...         "parameters": {
        ...             "type": "object",
        ...             "properties": {
        ...                 "a": {"type": "number"},
        ...                 "b": {"type": "number"}
        ...             },
        ...             "required": ["a", "b"]
        ...         }
        ...     }
        ... }
        >>> convert_openai_tool_to_claude(openai_tool)
        {
            "name": "add",
            "description": "Add two numbers",
            "input_schema": {...}
        }
    """
    # Handle both wrapped and unwrapped formats
    if "type" in openai_tool and openai_tool["type"] == "function":
        func = openai_tool["function"]
    else:
        # Already in function format (no wrapper)
        func = openai_tool

    # Build Claude tool schema
    claude_tool = {
        "name": func["name"],
        "description": func.get("description", ""),
        "input_schema": func.get("parameters", {
            "type": "object",
            "properties": {},
            "required": []
        })
    }

    return claude_tool


def convert_openai_tools_to_claude(
    openai_tools: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Convert a list of OpenAI tools to Claude format.

    Args:
        openai_tools: List of OpenAI tool schemas

    Returns:
        List of Claude tool schemas
    """
    return [convert_openai_tool_to_claude(tool) for tool in openai_tools]


def convert_claude_tool_call_to_openai(
    tool_use_block: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert Claude's tool_use block to OpenAI tool_call format.

    Claude format (in message.content):
        {
            "type": "tool_use",
            "id": "toolu_123",
            "name": "get_weather",
            "input": {"city": "SF"}
        }

    OpenAI format:
        {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"city": "SF"}'
            }
        }

    Args:
        tool_use_block: Claude tool_use content block

    Returns:
        OpenAI tool_call dict
    """
    return {
        "id": tool_use_block["id"],
        "type": "function",
        "function": {
            "name": tool_use_block["name"],
            "arguments": json.dumps(tool_use_block.get("input", {}))
        }
    }


def extract_tool_calls_from_response(response: Any) -> List[Dict[str, Any]]:
    """
    Extract tool_use blocks from Claude response.

    Works with both Claude Message objects (from the SDK) and dict responses.

    Args:
        response: Claude Message object or dict

    Returns:
        List of tool_use blocks as dicts
    """
    tool_calls = []

    # Handle dict response
    if isinstance(response, dict):
        content = response.get("content", [])
    # Handle SDK Message object
    elif hasattr(response, "content"):
        content = response.content
    else:
        return tool_calls

    if not content:
        return tool_calls

    for block in content:
        # Check if this is a tool_use block (SDK object)
        if hasattr(block, 'type') and block.type == 'tool_use':
            tool_calls.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input if hasattr(block, 'input') else {}
            })
        # Handle dict format
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            tool_calls.append(block)

    return tool_calls


def format_tool_result_for_claude(
    tool_use_id: str,
    tool_result: Any,
    is_error: bool = False
) -> Dict[str, Any]:
    """
    Format a tool execution result for Claude.

    Claude expects tool results as user messages with tool_result content blocks:
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_123",
                    "content": "Result text"
                }
            ]
        }

    Args:
        tool_use_id: The tool_use.id from the request
        tool_result: The result (will be converted to string)
        is_error: Whether this is an error result

    Returns:
        Claude user message with tool_result
    """
    # Convert result to string
    if isinstance(tool_result, str):
        content_str = tool_result
    elif isinstance(tool_result, (dict, list)):
        content_str = json.dumps(tool_result, indent=2)
    else:
        content_str = str(tool_result)

    # Build tool_result block
    tool_result_block = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content_str
    }

    if is_error:
        tool_result_block["is_error"] = True

    return {
        "role": "user",
        "content": [tool_result_block]
    }


def format_multiple_tool_results_for_claude(
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Format multiple tool results into a single user message.

    Claude prefers all tool results in a single user message rather than
    multiple user messages.

    Args:
        results: List of dicts with keys: tool_use_id, result, is_error (optional)

    Returns:
        Single user message with multiple tool_result blocks

    Example:
        >>> results = [
        ...     {"tool_use_id": "toolu_1", "result": "42"},
        ...     {"tool_use_id": "toolu_2", "result": "Hello", "is_error": False}
        ... ]
        >>> format_multiple_tool_results_for_claude(results)
        {"role": "user", "content": [...]}
    """
    tool_result_blocks = []

    for result_info in results:
        tool_use_id = result_info["tool_use_id"]
        result = result_info["result"]
        is_error = result_info.get("is_error", False)

        # Convert result to string
        if isinstance(result, str):
            content_str = result
        elif isinstance(result, (dict, list)):
            content_str = json.dumps(result, indent=2)
        else:
            content_str = str(result)

        # Build tool_result block
        block = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content_str
        }

        if is_error:
            block["is_error"] = True

        tool_result_blocks.append(block)

    return {
        "role": "user",
        "content": tool_result_blocks
    }


def validate_claude_tool_schema(tool: Dict[str, Any]) -> bool:
    """
    Validate that a tool schema is valid for Claude.

    Args:
        tool: Tool schema to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["name", "description", "input_schema"]

    for field in required_fields:
        if field not in tool:
            logger.error(f"Tool schema missing required field: {field}")
            return False

    # Validate input_schema structure
    input_schema = tool["input_schema"]
    if not isinstance(input_schema, dict):
        logger.error("input_schema must be a dict")
        return False

    if "type" not in input_schema:
        logger.error("input_schema must have 'type' field")
        return False

    return True


def validate_claude_tool_schemas(tools: List[Dict[str, Any]]) -> bool:
    """
    Validate a list of tool schemas.

    Args:
        tools: List of tool schemas

    Returns:
        True if all valid, False if any invalid
    """
    return all(validate_claude_tool_schema(tool) for tool in tools)


def create_simple_tool_schema(
    name: str,
    description: str,
    properties: Dict[str, Any],
    required: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a simple Claude tool schema.

    This is a convenience function for creating tool schemas without
    manually constructing the full structure.

    Args:
        name: Tool name (lowercase, underscores for spaces)
        description: Tool description (what it does, when to use it)
        properties: Parameter properties dict
        required: List of required parameter names

    Returns:
        Claude tool schema

    Example:
        >>> tool = create_simple_tool_schema(
        ...     "add",
        ...     "Add two numbers together",
        ...     {
        ...         "a": {"type": "number", "description": "First number"},
        ...         "b": {"type": "number", "description": "Second number"}
        ...     },
        ...     ["a", "b"]
        ... )
    """
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required or []
        }
    }
