"""
Utility Tools for AI Applications

Simple, zero-dependency utility tools ready for AI function calling.
Each tool comes with a Claude-compatible schema for easy registration.

Tools included:
- get_current_time: Get current date/time in various formats
- calculator: Basic arithmetic operations
- reverse_string: Reverse a string
- count_words: Count words, characters, lines in text
- random_number: Generate random integers
- random_choice: Pick random item from list

Usage:
    from reusable_lib.tools import calculator, UTILITY_TOOL_SCHEMAS

    # Use directly
    result = calculator("add", 5, 3)  # 8.0

    # Register with AI API
    tools = list(UTILITY_TOOL_SCHEMAS.values())
"""

import logging
import random
from datetime import datetime
from typing import Union, List, Dict, Any

logger = logging.getLogger(__name__)


def get_current_time(format: str = "iso") -> str:
    """
    Get the current date and time.

    Args:
        format: Output format
            - "iso": ISO8601 format (default)
            - "human": Human-readable (e.g., "Monday, January 1, 2025 at 12:00:00 PM")
            - "date": Date only (YYYY-MM-DD)
            - "time": Time only (HH:MM:SS)
            - "timestamp": Unix timestamp

    Returns:
        Current time in requested format

    Example:
        >>> get_current_time("human")
        "Monday, January 15, 2026 at 10:30:00 AM"
    """
    now = datetime.now()

    formats = {
        "iso": lambda: now.isoformat(),
        "human": lambda: now.strftime("%A, %B %d, %Y at %I:%M:%S %p"),
        "date": lambda: now.strftime("%Y-%m-%d"),
        "time": lambda: now.strftime("%H:%M:%S"),
        "timestamp": lambda: str(int(now.timestamp())),
    }

    return formats.get(format, formats["iso"])()


def calculator(operation: str, a: float, b: float = 0) -> Union[float, str]:
    """
    Perform basic arithmetic operations.

    Args:
        operation: Operation to perform
            - "add": a + b
            - "subtract": a - b
            - "multiply": a * b
            - "divide": a / b
            - "power": a ^ b
            - "modulo": a % b
        a: First number
        b: Second number (default: 0)

    Returns:
        Result of the operation, or error message string

    Example:
        >>> calculator("add", 5, 3)
        8.0
        >>> calculator("divide", 10, 0)
        "Error: Division by zero"
    """
    operations = {
        "add": lambda: a + b,
        "subtract": lambda: a - b,
        "multiply": lambda: a * b,
        "divide": lambda: "Error: Division by zero" if b == 0 else a / b,
        "power": lambda: a ** b,
        "modulo": lambda: "Error: Modulo by zero" if b == 0 else a % b,
    }

    try:
        if operation not in operations:
            return f"Error: Unknown operation '{operation}'"
        return operations[operation]()
    except Exception as e:
        return f"Error: {str(e)}"


def reverse_string(text: str) -> str:
    """
    Reverse a string.

    Args:
        text: Text to reverse

    Returns:
        Reversed text

    Example:
        >>> reverse_string("hello")
        "olleh"
    """
    return text[::-1]


def count_words(text: str) -> Dict[str, int]:
    """
    Count words, characters, and lines in text.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with counts:
        - words: Number of words
        - characters: Total characters (including whitespace)
        - lines: Number of lines
        - characters_no_spaces: Characters excluding whitespace

    Example:
        >>> count_words("Hello world\\nHow are you?")
        {"words": 5, "characters": 24, "lines": 2, "characters_no_spaces": 20}
    """
    return {
        "words": len(text.split()),
        "characters": len(text),
        "lines": len(text.splitlines()) or 1,
        "characters_no_spaces": len(
            text.replace(" ", "").replace("\n", "").replace("\t", "")
        )
    }


def random_number(min_value: int = 0, max_value: int = 100) -> int:
    """
    Generate a random integer within a range.

    Args:
        min_value: Minimum value (inclusive, default: 0)
        max_value: Maximum value (inclusive, default: 100)

    Returns:
        Random integer between min and max

    Example:
        >>> random_number(1, 10)
        7
    """
    return random.randint(min_value, max_value)


def random_choice(choices: List[Any]) -> Union[Any, str]:
    """
    Pick a random item from a list.

    Args:
        choices: List of options to choose from

    Returns:
        Random choice from the list, or error message if empty

    Example:
        >>> random_choice(["apple", "banana", "cherry"])
        "banana"
    """
    if not choices:
        return "Error: Empty list provided"
    return random.choice(choices)


# Tool schemas for AI API registration
UTILITY_TOOL_SCHEMAS = {
    "get_current_time": {
        "name": "get_current_time",
        "description": "Get the current date and time in various formats",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["iso", "human", "date", "time", "timestamp"],
                    "description": (
                        "Output format: 'iso' for ISO8601, 'human' for readable, "
                        "'date' for date only, 'time' for time only, "
                        "'timestamp' for Unix timestamp"
                    ),
                    "default": "iso"
                }
            },
            "required": []
        }
    },
    "calculator": {
        "name": "calculator",
        "description": (
            "Perform basic arithmetic operations "
            "(add, subtract, multiply, divide, power, modulo)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide", "power", "modulo"],
                    "description": "The arithmetic operation to perform"
                },
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number",
                    "default": 0
                }
            },
            "required": ["operation", "a"]
        }
    },
    "reverse_string": {
        "name": "reverse_string",
        "description": "Reverse a string (e.g., 'hello' becomes 'olleh')",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to reverse"
                }
            },
            "required": ["text"]
        }
    },
    "count_words": {
        "name": "count_words",
        "description": "Count words, characters, and lines in text",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to analyze"
                }
            },
            "required": ["text"]
        }
    },
    "random_number": {
        "name": "random_number",
        "description": "Generate a random integer within a range",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_value": {
                    "type": "integer",
                    "description": "Minimum value (inclusive)",
                    "default": 0
                },
                "max_value": {
                    "type": "integer",
                    "description": "Maximum value (inclusive)",
                    "default": 100
                }
            },
            "required": []
        }
    },
    "random_choice": {
        "name": "random_choice",
        "description": "Pick a random item from a list of choices",
        "input_schema": {
            "type": "object",
            "properties": {
                "choices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of options to choose from"
                }
            },
            "required": ["choices"]
        }
    }
}
