"""
String Manipulation Tools
=========================

String processing utilities for AI tool calling.

Tools:
- string_replace: Find and replace text
- string_split: Split text into parts
- string_join: Join list into string
- regex_match: Find regex matches
- regex_replace: Replace using regex
- string_case: Change text case
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


def string_replace(
    text: str,
    find: str,
    replace: str,
    count: int = -1,
    case_sensitive: bool = True
) -> Dict[str, Any]:
    """
    Find and replace text in a string.

    Args:
        text: The text to search in
        find: The substring to find
        replace: The replacement string
        count: Max replacements (-1 for all, default)
        case_sensitive: Whether to match case (default: True)

    Returns:
        Dict with result and count of replacements

    Example:
        >>> string_replace("Hello World", "World", "Python")
        {"result": "Hello Python", "replacements": 1}
    """
    try:
        if not case_sensitive:
            # Case-insensitive replacement using regex
            pattern = re.compile(re.escape(find), re.IGNORECASE)
            if count == -1:
                result = pattern.sub(replace, text)
                num_replacements = len(pattern.findall(text))
            else:
                result = pattern.sub(replace, text, count=count)
                num_replacements = min(count, len(pattern.findall(text)))
        else:
            if count == -1:
                num_replacements = text.count(find)
                result = text.replace(find, replace)
            else:
                num_replacements = min(count, text.count(find))
                result = text.replace(find, replace, count)

        return {
            "result": result,
            "replacements": num_replacements
        }
    except Exception as e:
        return {"error": str(e), "result": text, "replacements": 0}


def string_split(
    text: str,
    delimiter: str = None,
    max_splits: int = -1
) -> Dict[str, Any]:
    """
    Split text into a list of parts.

    Args:
        text: The text to split
        delimiter: What to split on (None = whitespace)
        max_splits: Max number of splits (-1 for all)

    Returns:
        Dict with parts list and count

    Example:
        >>> string_split("a,b,c", ",")
        {"parts": ["a", "b", "c"], "count": 3}
    """
    try:
        if max_splits == -1:
            parts = text.split(delimiter)
        else:
            parts = text.split(delimiter, max_splits)

        return {
            "parts": parts,
            "count": len(parts)
        }
    except Exception as e:
        return {"error": str(e), "parts": [text], "count": 1}


def string_join(
    parts: List[str],
    delimiter: str = ""
) -> Dict[str, Any]:
    """
    Join a list of strings into one string.

    Args:
        parts: List of strings to join
        delimiter: String to put between parts (default: "")

    Returns:
        Dict with joined result and part count

    Example:
        >>> string_join(["Hello", "World"], " ")
        {"result": "Hello World", "parts_joined": 2}
    """
    try:
        result = delimiter.join(str(p) for p in parts)
        return {
            "result": result,
            "parts_joined": len(parts)
        }
    except Exception as e:
        return {"error": str(e), "result": "", "parts_joined": 0}


def regex_match(
    text: str,
    pattern: str,
    flags: str = ""
) -> Dict[str, Any]:
    """
    Find all regex matches in text.

    Args:
        text: Text to search
        pattern: Regex pattern
        flags: Optional flags string (i=ignore case, m=multiline, s=dotall)

    Returns:
        Dict with matches list and count

    Example:
        >>> regex_match("Call 123-456 or 789-012", r"\\d{3}-\\d{3}")
        {"matches": ["123-456", "789-012"], "count": 2}
    """
    try:
        # Parse flags
        re_flags = 0
        if 'i' in flags:
            re_flags |= re.IGNORECASE
        if 'm' in flags:
            re_flags |= re.MULTILINE
        if 's' in flags:
            re_flags |= re.DOTALL

        matches = re.findall(pattern, text, re_flags)

        # Handle groups - flatten if single group
        if matches and isinstance(matches[0], tuple):
            matches = [m[0] if len(m) == 1 else list(m) for m in matches]

        return {
            "matches": matches,
            "count": len(matches)
        }
    except re.error as e:
        return {"error": f"Invalid regex: {e}", "matches": [], "count": 0}
    except Exception as e:
        return {"error": str(e), "matches": [], "count": 0}


def regex_replace(
    text: str,
    pattern: str,
    replacement: str,
    flags: str = "",
    count: int = 0
) -> Dict[str, Any]:
    """
    Replace text using regex pattern.

    Args:
        text: Text to search
        pattern: Regex pattern to find
        replacement: Replacement (can use \\1, \\2 for groups)
        flags: Optional flags (i=ignore case, m=multiline, s=dotall)
        count: Max replacements (0 = all)

    Returns:
        Dict with result and replacement count

    Example:
        >>> regex_replace("Hello 123 World 456", r"\\d+", "NUM")
        {"result": "Hello NUM World NUM", "replacements": 2}
    """
    try:
        re_flags = 0
        if 'i' in flags:
            re_flags |= re.IGNORECASE
        if 'm' in flags:
            re_flags |= re.MULTILINE
        if 's' in flags:
            re_flags |= re.DOTALL

        # Count matches first
        num_matches = len(re.findall(pattern, text, re_flags))
        num_replacements = num_matches if count == 0 else min(count, num_matches)

        result = re.sub(pattern, replacement, text, count=count, flags=re_flags)

        return {
            "result": result,
            "replacements": num_replacements
        }
    except re.error as e:
        return {"error": f"Invalid regex: {e}", "result": text, "replacements": 0}
    except Exception as e:
        return {"error": str(e), "result": text, "replacements": 0}


def string_case(
    text: str,
    case: str = "lower"
) -> Dict[str, Any]:
    """
    Change the case of text.

    Args:
        text: Text to transform
        case: Target case:
            - "lower": lowercase
            - "upper": UPPERCASE
            - "title": Title Case
            - "capitalize": Capitalize first letter
            - "swapcase": sWAP cASE

    Returns:
        Dict with transformed result

    Example:
        >>> string_case("hello world", "title")
        {"result": "Hello World"}
    """
    try:
        transformations = {
            "lower": text.lower,
            "upper": text.upper,
            "title": text.title,
            "capitalize": text.capitalize,
            "swapcase": text.swapcase,
        }

        if case not in transformations:
            return {
                "error": f"Unknown case '{case}'. Use: lower, upper, title, capitalize, swapcase",
                "result": text
            }

        return {"result": transformations[case]()}
    except Exception as e:
        return {"error": str(e), "result": text}


# =============================================================================
# Tool Schemas
# =============================================================================

STRING_TOOL_SCHEMAS = {
    "string_replace": {
        "name": "string_replace",
        "description": "Find and replace text in a string. Supports case-insensitive matching.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to search in"
                },
                "find": {
                    "type": "string",
                    "description": "The substring to find"
                },
                "replace": {
                    "type": "string",
                    "description": "The replacement string"
                },
                "count": {
                    "type": "integer",
                    "description": "Max replacements (-1 for all)",
                    "default": -1
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Whether to match case",
                    "default": True
                }
            },
            "required": ["text", "find", "replace"]
        }
    },
    "string_split": {
        "name": "string_split",
        "description": "Split text into a list of parts by delimiter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to split"
                },
                "delimiter": {
                    "type": "string",
                    "description": "What to split on (omit for whitespace)"
                },
                "max_splits": {
                    "type": "integer",
                    "description": "Max number of splits (-1 for all)",
                    "default": -1
                }
            },
            "required": ["text"]
        }
    },
    "string_join": {
        "name": "string_join",
        "description": "Join a list of strings into one string with a delimiter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of strings to join"
                },
                "delimiter": {
                    "type": "string",
                    "description": "String to put between parts",
                    "default": ""
                }
            },
            "required": ["parts"]
        }
    },
    "regex_match": {
        "name": "regex_match",
        "description": "Find all regex pattern matches in text. Returns list of matches.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to search"
                },
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern (e.g., '\\\\d+' for numbers)"
                },
                "flags": {
                    "type": "string",
                    "description": "Flags: i=ignore case, m=multiline, s=dotall",
                    "default": ""
                }
            },
            "required": ["text", "pattern"]
        }
    },
    "regex_replace": {
        "name": "regex_replace",
        "description": "Replace text using regex. Supports backreferences (\\\\1, \\\\2).",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to search"
                },
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to find"
                },
                "replacement": {
                    "type": "string",
                    "description": "Replacement (can use \\\\1, \\\\2 for groups)"
                },
                "flags": {
                    "type": "string",
                    "description": "Flags: i=ignore case, m=multiline, s=dotall",
                    "default": ""
                },
                "count": {
                    "type": "integer",
                    "description": "Max replacements (0 = all)",
                    "default": 0
                }
            },
            "required": ["text", "pattern", "replacement"]
        }
    },
    "string_case": {
        "name": "string_case",
        "description": "Change text case: lower, upper, title, capitalize, or swapcase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to transform"
                },
                "case": {
                    "type": "string",
                    "enum": ["lower", "upper", "title", "capitalize", "swapcase"],
                    "description": "Target case",
                    "default": "lower"
                }
            },
            "required": ["text"]
        }
    }
}
