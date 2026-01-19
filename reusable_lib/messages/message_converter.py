"""
Message Format Converter

Converts between OpenAI/Moonshot message format and Claude/Anthropic format.
Useful when building applications that need to work with multiple AI providers
or when migrating between APIs.

Key Differences:
- OpenAI: System prompt in messages array with role="system"
- Claude: System prompt as separate parameter, NOT in messages array
- OpenAI: Tool results as role="tool" messages
- Claude: Tool results as role="user" messages with tool_result content blocks

Usage:
    from reusable_lib.messages import prepare_messages_for_claude

    # Convert OpenAI-style messages to Claude format
    openai_messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    system_prompt, claude_messages = prepare_messages_for_claude(openai_messages)
    # system_prompt = "You are helpful."
    # claude_messages = [
    #     {"role": "user", "content": "Hello!"},
    #     {"role": "assistant", "content": "Hi there!"},
    # ]
"""

from typing import List, Dict, Any, Tuple
import json
import logging

logger = logging.getLogger(__name__)


def extract_system_prompt(
    messages: List[Dict[str, Any]]
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extract system prompt from OpenAI-style messages array.

    OpenAI places system prompts in the messages array with role="system".
    Claude requires them as a separate parameter.

    Args:
        messages: List of message dicts (OpenAI format)

    Returns:
        Tuple of (system_prompt, remaining_messages)
        - system_prompt: Extracted system content (empty string if none)
        - remaining_messages: Messages without system message
    """
    system_prompt = ""
    user_messages = []

    for msg in messages:
        if msg.get("role") == "system":
            # Concatenate multiple system messages if present
            if system_prompt:
                system_prompt += "\n\n" + msg["content"]
            else:
                system_prompt = msg["content"]
        else:
            user_messages.append(msg)

    return system_prompt, user_messages


def add_system_to_messages(
    system_prompt: str,
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Add system prompt back to messages (for converting Claude -> OpenAI).

    Args:
        system_prompt: System prompt string
        messages: List of user/assistant messages

    Returns:
        Messages list with system message prepended
    """
    if not system_prompt:
        return messages

    return [{"role": "system", "content": system_prompt}] + messages


def convert_openai_to_claude_messages(
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Convert OpenAI-style messages to Claude format.

    Changes:
    - Removes system messages (should be extracted first)
    - Converts tool messages to user messages with tool_result blocks
    - Handles image_url format differences

    Args:
        messages: OpenAI-format messages

    Returns:
        Claude-format messages
    """
    claude_messages = []

    for msg in messages:
        role = msg.get("role")

        # Skip system messages (should be extracted separately)
        if role == "system":
            logger.warning(
                "System message found in messages array - should be extracted first"
            )
            continue

        # Convert tool messages to user messages with tool_result
        if role == "tool":
            claude_messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id", "unknown"),
                    "content": msg.get("content", "")
                }]
            })
            continue

        # Handle regular messages
        content = msg.get("content")

        # Handle content array (for images, etc.)
        if isinstance(content, list):
            converted_content = []
            for item in content:
                if item.get("type") == "text":
                    converted_content.append(item)
                elif item.get("type") == "image_url":
                    # Convert OpenAI image format to Claude format
                    converted_content.append(_convert_image_format(item))
                else:
                    converted_content.append(item)
            claude_messages.append({
                "role": role,
                "content": converted_content
            })
        else:
            # Simple text content
            claude_messages.append({
                "role": role,
                "content": content
            })

    return claude_messages


def _convert_image_format(openai_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert OpenAI image_url format to Claude image format.

    OpenAI: {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    Claude: {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}}

    Args:
        openai_image: OpenAI image_url object

    Returns:
        Claude image object
    """
    url = openai_image.get("image_url", {}).get("url", "")

    # Parse data URL format: data:image/jpeg;base64,<data>
    if url.startswith("data:"):
        parts = url.split(",", 1)
        if len(parts) == 2:
            # Extract media type
            media_info = parts[0].replace("data:", "").split(";")
            media_type = media_info[0] if media_info else "image/jpeg"
            base64_data = parts[1]

            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data
                }
            }

    # Fallback for non-data URLs (Claude doesn't support URL images directly)
    logger.warning(f"Cannot convert image URL to Claude format: {url[:50]}...")
    return {
        "type": "text",
        "text": f"[Image URL: {url[:100]}]"
    }


def convert_tool_result_to_claude(
    tool_call_id: str,
    tool_name: str,
    result: str
) -> Dict[str, Any]:
    """
    Convert tool execution result to Claude's format.

    Args:
        tool_call_id: ID of the tool call
        tool_name: Name of the tool
        result: Tool execution result (as string)

    Returns:
        Claude-format user message with tool_result
    """
    return {
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": result
        }]
    }


def prepare_messages_for_claude(
    messages: List[Dict[str, Any]]
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Complete conversion from OpenAI format to Claude format.

    This is the main function to use for conversion. It:
    1. Extracts system prompt
    2. Converts message format
    3. Validates result

    Args:
        messages: OpenAI-format messages (may include system messages)

    Returns:
        Tuple of (system_prompt, claude_messages)
    """
    # Extract system prompt
    system_prompt, remaining_messages = extract_system_prompt(messages)

    # Convert to Claude format
    claude_messages = convert_openai_to_claude_messages(remaining_messages)

    # Validate: Claude requires alternating user/assistant messages
    if claude_messages:
        if claude_messages[0].get("role") != "user":
            logger.warning(
                "First message is not from user - Claude may reject this"
            )

    return system_prompt, claude_messages


def validate_claude_messages(messages: List[Dict[str, Any]]) -> bool:
    """
    Validate that messages conform to Claude's requirements.

    Claude requires:
    - Messages must alternate between user and assistant
    - First message must be from user
    - Last message should be from user (for continuation)
    - No consecutive messages from same role

    Args:
        messages: Claude-format messages

    Returns:
        True if valid, False otherwise
    """
    if not messages:
        return True

    # First message must be from user
    if messages[0].get("role") != "user":
        logger.error("First message must be from user")
        return False

    # Check alternating roles
    for i in range(len(messages) - 1):
        current_role = messages[i].get("role")
        next_role = messages[i + 1].get("role")

        if current_role == next_role:
            logger.error(f"Consecutive messages from {current_role} at index {i}")
            return False

    return True


def merge_consecutive_tool_results(
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge consecutive tool result messages into a single user message.

    Claude allows multiple tool_result blocks in one user message.
    This is useful when multiple tools are called at once.

    Args:
        messages: Messages that may have consecutive tool results

    Returns:
        Messages with merged tool results
    """
    merged = []
    tool_results_buffer = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        # Check if this is a tool result message
        is_tool_result = (
            role == "user" and
            isinstance(content, list) and
            len(content) > 0 and
            content[0].get("type") == "tool_result"
        )

        if is_tool_result:
            # Add to buffer
            if isinstance(content, list):
                tool_results_buffer.extend(content)
            else:
                tool_results_buffer.append(content)
        else:
            # Flush buffer if we have accumulated tool results
            if tool_results_buffer:
                merged.append({
                    "role": "user",
                    "content": tool_results_buffer.copy()
                })
                tool_results_buffer = []

            # Add current message
            merged.append(msg)

    # Flush any remaining tool results
    if tool_results_buffer:
        merged.append({
            "role": "user",
            "content": tool_results_buffer
        })

    return merged


def format_tool_results_for_display(content: List[Dict[str, Any]]) -> str:
    """
    Format tool results for display to user.

    Args:
        content: Content array from user message (may contain tool_result blocks)

    Returns:
        Formatted string for display
    """
    if not isinstance(content, list):
        return str(content)

    display_parts = []
    for item in content:
        if item.get("type") == "tool_result":
            tool_id = item.get("tool_use_id", "unknown")
            result = item.get("content", "")
            display_parts.append(f"**Tool Result** ({tool_id}):\n```\n{result}\n```")
        elif item.get("type") == "text":
            display_parts.append(item.get("text", ""))
        else:
            display_parts.append(str(item))

    return "\n\n".join(display_parts)
