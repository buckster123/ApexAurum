"""
Utility Tools for Claude

Simple utility tools that don't require external resources:
- get_current_time: Get current date/time
- calculator: Perform basic arithmetic
- reverse_string: Reverse a string
- count_words: Count words in text
- random_number: Generate random number
"""

import logging
from datetime import datetime
from typing import Union, Literal
import random

logger = logging.getLogger(__name__)


def get_current_time(format: str = "iso") -> str:
    """
    Get the current date and time.

    Args:
        format: Output format - "iso", "human", "date", "time", "timestamp"

    Returns:
        Current time in requested format

    Example:
        >>> get_current_time("human")
        "Monday, December 29, 2025 at 01:00:00 AM"
    """
    now = datetime.now()

    if format == "iso":
        return now.isoformat()
    elif format == "human":
        return now.strftime("%A, %B %d, %Y at %I:%M:%S %p")
    elif format == "date":
        return now.strftime("%Y-%m-%d")
    elif format == "time":
        return now.strftime("%H:%M:%S")
    elif format == "timestamp":
        return str(int(now.timestamp()))
    else:
        return now.isoformat()


def calculator(operation: str, a: float, b: float = 0) -> Union[float, str]:
    """
    Perform basic arithmetic operations.

    Args:
        operation: Operation to perform - add, subtract, multiply, divide, power, modulo
        a: First number
        b: Second number (default: 0)

    Returns:
        Result of the operation

    Example:
        >>> calculator("add", 5, 3)
        8.0
        >>> calculator("divide", 10, 2)
        5.0
    """
    try:
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                return "Error: Division by zero"
            return a / b
        elif operation == "power":
            return a ** b
        elif operation == "modulo":
            if b == 0:
                return "Error: Modulo by zero"
            return a % b
        else:
            return f"Error: Unknown operation '{operation}'"
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


def count_words(text: str) -> dict:
    """
    Count words, characters, and lines in text.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with counts

    Example:
        >>> count_words("Hello world\\nHow are you?")
        {"words": 5, "characters": 24, "lines": 2, "characters_no_spaces": 20}
    """
    words = len(text.split())
    characters = len(text)
    lines = len(text.splitlines())
    characters_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

    return {
        "words": words,
        "characters": characters,
        "lines": lines,
        "characters_no_spaces": characters_no_spaces
    }


def random_number(min_value: int = 0, max_value: int = 100) -> int:
    """
    Generate a random integer.

    Args:
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)

    Returns:
        Random integer between min and max

    Example:
        >>> random_number(1, 10)
        7
    """
    return random.randint(min_value, max_value)


def random_choice(choices: list) -> str:
    """
    Pick a random item from a list.

    Args:
        choices: List of options to choose from

    Returns:
        Random choice from the list

    Example:
        >>> random_choice(["apple", "banana", "cherry"])
        "banana"
    """
    if not choices:
        return "Error: Empty list provided"
    return random.choice(choices)


def session_info() -> dict:
    """
    Get operational context about the current session and system state.

    Helps agents understand their environment and available resources.

    Returns:
        Dictionary with session context:
        - timestamp: Current ISO timestamp
        - agent_id: Current agent ID if running as agent (or None)
        - preset: Active settings preset name
        - conversation_length: Number of messages in current conversation
        - tools_available: Total number of tools available
        - datasets: List of available dataset names
        - village_stats: Village memory statistics
        - agents: Recent agent activity summary
    """
    from datetime import datetime
    from pathlib import Path
    import json

    result = {
        "timestamp": datetime.now().isoformat(),
        "agent_id": None,
        "preset": None,
        "conversation_length": 0,
        "tools_available": 0,
        "datasets": [],
        "village_stats": {},
        "agents": {}
    }

    # Try to get context from multiple sources:
    # 1. Thread-local agent context (for spawned agents)
    # 2. Streamlit session state (for main chat)
    try:
        # First check thread-local context (spawned agents)
        from tools.agents import get_current_agent_context
        agent_context = get_current_agent_context()
        if agent_context and 'agent_id' in agent_context:
            result["agent_id"] = agent_context['agent_id']
        else:
            # Fallback to Streamlit session state
            import streamlit as st
            if hasattr(st, 'session_state'):
                # Agent ID
                result["agent_id"] = st.session_state.get("current_agent_id")

                # Active preset
                result["preset"] = st.session_state.get("active_preset", "Custom")

                # Conversation length
                messages = st.session_state.get("messages", [])
                result["conversation_length"] = len(messages)
    except:
        pass

    # Tool count (always available)
    try:
        from tools import ALL_TOOLS
        result["tools_available"] = len(ALL_TOOLS)
    except:
        result["tools_available"] = 50  # Fallback

    # Available datasets
    try:
        datasets_path = Path("sandbox/datasets")
        if datasets_path.exists():
            datasets = []
            for item in datasets_path.iterdir():
                if item.is_dir():
                    meta_path = item / "dataset_meta.json"
                    if meta_path.exists():
                        try:
                            meta = json.loads(meta_path.read_text())
                            datasets.append({
                                "name": item.name,
                                "description": meta.get("description", ""),
                                "chunks": meta.get("chunk_count", 0)
                            })
                        except:
                            datasets.append({"name": item.name, "description": "", "chunks": 0})
            result["datasets"] = datasets
    except Exception as e:
        result["datasets"] = []

    # Village stats
    try:
        import chromadb
        chroma_path = Path("sandbox/chroma_db")
        if chroma_path.exists():
            client = chromadb.PersistentClient(path=str(chroma_path))
            village_stats = {}

            for collection_name in ["knowledge_village", "knowledge_private", "knowledge_bridges"]:
                try:
                    col = client.get_collection(collection_name)
                    village_stats[collection_name] = col.count()
                except:
                    pass

            result["village_stats"] = village_stats
    except:
        pass

    # Agent activity
    try:
        agents_path = Path("sandbox/agents.json")
        if agents_path.exists():
            agents_data = json.loads(agents_path.read_text())

            # Summarize agent activity
            total = len(agents_data)
            running = sum(1 for a in agents_data.values() if a.get("status") == "running")
            completed = sum(1 for a in agents_data.values() if a.get("status") == "completed")
            failed = sum(1 for a in agents_data.values() if a.get("status") == "failed")

            result["agents"] = {
                "total": total,
                "running": running,
                "completed": completed,
                "failed": failed
            }
    except:
        result["agents"] = {"total": 0, "running": 0, "completed": 0, "failed": 0}

    return result


# Tool schemas for registration
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
                    "description": "Output format: 'iso' for ISO8601, 'human' for readable, 'date' for date only, 'time' for time only, 'timestamp' for Unix timestamp",
                    "default": "iso"
                }
            },
            "required": []
        }
    },
    "calculator": {
        "name": "calculator",
        "description": "Perform basic arithmetic operations (add, subtract, multiply, divide, power, modulo)",
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
                    "description": "Second number (optional for some operations)",
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
    "session_info": {
        "name": "session_info",
        "description": """Get operational context about the current session and system state.

Returns information to help understand the environment:
- timestamp: Current time
- agent_id: Your agent ID if running as an agent
- preset: Active settings preset name
- conversation_length: Messages in current conversation
- tools_available: Total tools in the system
- datasets: Available vector datasets (name, description, chunk count)
- village_stats: Memory counts per realm (village, private, bridges)
- agents: Agent activity summary (total, running, completed, failed)

Use this to understand your operating context and available resources.""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}
