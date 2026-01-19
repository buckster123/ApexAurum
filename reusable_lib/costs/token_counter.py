"""
Token Counter for AI APIs

Estimates token usage for requests to help with rate limiting and cost tracking.
Works with any LLM API that uses similar token-based pricing.

Approximations (since exact counting requires the actual tokenizer):
- Text: ~1 token per 4 characters (conservative estimate)
- Images: ~170 tokens per image (Claude average)
- Tools: ~50-200 tokens per tool schema (average: 100)

Usage:
    from reusable_lib.costs import count_tokens, estimate_text_tokens

    # Quick text estimate
    tokens = estimate_text_tokens("Hello, world!")  # ~3 tokens

    # Full request estimate
    result = count_tokens(
        messages=[{"role": "user", "content": "Hello!"}],
        system="You are a helpful assistant.",
        tools=[{...}]
    )
    print(result["input_tokens"])  # Estimated input tokens
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def estimate_text_tokens(text: str) -> int:
    """
    Estimate tokens in a text string.

    Uses conservative estimate of 1 token per 4 characters.
    Claude's actual tokenizer may vary, but this is a safe approximation.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Conservative estimate: 1 token ~= 4 characters
    return max(1, len(text) // 4)


def estimate_image_tokens(image_count: int = 1) -> int:
    """
    Estimate tokens for images.

    Claude uses ~85-170 tokens per image depending on size.
    We use 170 as a safe upper bound.

    Args:
        image_count: Number of images

    Returns:
        Estimated token count
    """
    TOKENS_PER_IMAGE = 170
    return image_count * TOKENS_PER_IMAGE


def estimate_tool_tokens(tools: Optional[List[Dict[str, Any]]]) -> int:
    """
    Estimate tokens for tool schemas.

    Tool schemas add overhead. Estimate based on schema complexity:
    - Simple tools: ~50 tokens
    - Complex tools: ~200 tokens
    - Average: ~100 tokens per tool

    Args:
        tools: List of tool schemas

    Returns:
        Estimated token count
    """
    if not tools:
        return 0

    TOKENS_PER_TOOL = 100
    return len(tools) * TOKENS_PER_TOOL


def estimate_message_tokens(message: Dict[str, Any]) -> int:
    """
    Estimate tokens in a single message.

    Handles both simple string content and complex array content
    (text blocks, images, tool results, etc.)

    Args:
        message: Message dict with role and content

    Returns:
        Estimated token count
    """
    content = message.get("content", "")
    tokens = 0

    # Handle array content (with text and images)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text = item.get("text", "")
                    tokens += estimate_text_tokens(text)
                elif item.get("type") == "image":
                    tokens += estimate_image_tokens(1)
                elif item.get("type") == "tool_result":
                    # Tool results can contain text
                    result_content = item.get("content", "")
                    if isinstance(result_content, str):
                        tokens += estimate_text_tokens(result_content)
                    elif isinstance(result_content, list):
                        for sub_item in result_content:
                            if isinstance(sub_item, dict) and sub_item.get("type") == "text":
                                tokens += estimate_text_tokens(sub_item.get("text", ""))
            elif isinstance(item, str):
                tokens += estimate_text_tokens(item)

    # Handle simple string content
    elif isinstance(content, str):
        tokens += estimate_text_tokens(content)

    # Add overhead for message structure (~10 tokens for role, formatting, etc.)
    tokens += 10

    return tokens


def count_tokens(
    messages: List[Dict[str, Any]],
    system: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    model: Optional[str] = None
) -> Dict[str, int]:
    """
    Estimate total token count for an API request.

    Args:
        messages: List of conversation messages
        system: System prompt (optional)
        tools: Tool schemas (optional)
        model: Model name (optional, for future model-specific estimates)

    Returns:
        Dictionary with token estimates:
        - input_tokens: Estimated input tokens
        - output_tokens: Estimated output tokens (default estimate)
        - total_tokens: Total estimated tokens
    """
    input_tokens = 0

    # Count system prompt
    if system:
        input_tokens += estimate_text_tokens(system)

    # Count messages
    for message in messages:
        input_tokens += estimate_message_tokens(message)

    # Count tool schemas
    if tools:
        input_tokens += estimate_tool_tokens(tools)

    # Estimate output tokens (conservative)
    # Typical response is 100-500 tokens, we'll estimate 300 as average
    output_tokens = 300

    total_tokens = input_tokens + output_tokens

    logger.debug(
        f"Token estimate: {input_tokens} input + {output_tokens} output "
        f"= {total_tokens} total"
    )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens
    }


def count_images_in_messages(messages: List[Dict[str, Any]]) -> int:
    """
    Count number of images in messages.

    Args:
        messages: List of messages

    Returns:
        Total number of images
    """
    image_count = 0

    for message in messages:
        content = message.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image":
                    image_count += 1

    return image_count
