"""
Memory Tools for AI Applications

Simple key-value memory storage using JSON files. Perfect for persisting
information across conversations or sessions without requiring a database.

Features:
- Store any JSON-serializable value
- Automatic timestamps
- Prefix-based filtering
- Simple keyword search
- Configurable storage path

Usage:
    from reusable_lib.tools import memory_store, memory_retrieve, MEMORY_TOOL_SCHEMAS

    # Store a value
    memory_store("user_name", "Alice")

    # Retrieve later
    result = memory_retrieve("user_name")
    print(result["value"])  # "Alice"

    # Search memory
    results = memory_search("Alice")

    # Register with AI API
    tools = list(MEMORY_TOOL_SCHEMAS.values())

Advanced Usage:
    from reusable_lib.tools import SimpleMemory

    # Custom storage path
    memory = SimpleMemory(storage_file=Path("./data/memory.json"))
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class SimpleMemory:
    """
    Simple JSON-based memory storage.

    Thread-safe for basic operations. For high-concurrency applications,
    consider using a proper database.
    """

    def __init__(self, storage_file: Optional[Path] = None):
        """
        Initialize memory storage.

        Args:
            storage_file: Path to JSON storage file.
                         Defaults to ./memory.json in current directory.
        """
        self.storage_file = storage_file or Path("./memory.json")
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Create storage file and directory if needed."""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_file.exists():
            self._save_data({})

    def _load_data(self) -> Dict[str, Any]:
        """Load memory data from file."""
        try:
            with open(self.storage_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Corrupted memory file, starting fresh")
            return {}
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return {}

    def _save_data(self, data: Dict[str, Any]):
        """Save memory data to file."""
        try:
            with open(self.storage_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")

    def store(self, key: str, value: Any, metadata: Optional[Dict] = None) -> Dict:
        """Store a value in memory."""
        data = self._load_data()
        entry = {
            "value": value,
            "stored_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        data[key] = entry
        self._save_data(data)
        return {"success": True, "key": key, "stored_at": entry["stored_at"]}

    def retrieve(self, key: str) -> Dict:
        """Retrieve a value from memory."""
        data = self._load_data()
        if key not in data:
            return {"found": False, "error": f"Key not found: {key}"}
        entry = data[key]
        return {
            "found": True,
            "key": key,
            "value": entry["value"],
            "stored_at": entry["stored_at"],
            "metadata": entry.get("metadata", {})
        }

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all memory keys, optionally filtered by prefix."""
        data = self._load_data()
        keys = list(data.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    def delete(self, key: str) -> Dict:
        """Delete a key from memory."""
        data = self._load_data()
        if key not in data:
            return {"success": False, "error": f"Key not found: {key}"}
        del data[key]
        self._save_data(data)
        return {"success": True, "key": key}

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search memory by keyword."""
        data = self._load_data()
        query_lower = query.lower()
        results = []

        for key, entry in data.items():
            value_str = str(entry["value"]).lower()
            if query_lower in key.lower() or query_lower in value_str:
                results.append({
                    "key": key,
                    "value": entry["value"],
                    "stored_at": entry["stored_at"],
                    "metadata": entry.get("metadata", {})
                })
                if len(results) >= limit:
                    break

        return results

    def clear(self):
        """Clear all memory entries."""
        self._save_data({})


# Default global memory instance
_default_memory: Optional[SimpleMemory] = None


def _get_memory() -> SimpleMemory:
    """Get or create the default memory instance."""
    global _default_memory
    if _default_memory is None:
        _default_memory = SimpleMemory()
    return _default_memory


def set_memory_path(path: Path):
    """
    Set the storage path for the default memory instance.

    Args:
        path: Path to JSON storage file

    Example:
        >>> set_memory_path(Path("./data/memory.json"))
    """
    global _default_memory
    _default_memory = SimpleMemory(storage_file=path)


def memory_store(key: str, value: Any, metadata: Optional[Dict] = None) -> Dict:
    """
    Store a value in memory.

    Args:
        key: Memory key (identifier)
        value: Value to store (can be string, number, list, dict)
        metadata: Optional metadata dict

    Returns:
        Status dict with success, key, stored_at

    Example:
        >>> memory_store("user_name", "Alice")
        {"success": True, "key": "user_name", "stored_at": "2026-01-15T10:30:00"}
    """
    try:
        return _get_memory().store(key, value, metadata)
    except Exception as e:
        logger.error(f"Error storing memory {key}: {e}")
        return {"success": False, "error": str(e)}


def memory_retrieve(key: str) -> Dict:
    """
    Retrieve a value from memory.

    Args:
        key: Memory key

    Returns:
        Dict with found, value, stored_at, metadata (or error if not found)

    Example:
        >>> memory_retrieve("user_name")
        {"found": True, "key": "user_name", "value": "Alice", "stored_at": "..."}
    """
    try:
        return _get_memory().retrieve(key)
    except Exception as e:
        logger.error(f"Error retrieving memory {key}: {e}")
        return {"found": False, "error": str(e)}


def memory_list(prefix: Optional[str] = None) -> Union[List[str], Dict]:
    """
    List all memory keys.

    Args:
        prefix: Optional prefix filter (e.g., "user_" to get all user keys)

    Returns:
        List of keys, or error dict

    Example:
        >>> memory_list()
        ["user_name", "user_age", "settings"]
        >>> memory_list("user_")
        ["user_name", "user_age"]
    """
    try:
        return _get_memory().list_keys(prefix)
    except Exception as e:
        logger.error(f"Error listing memory: {e}")
        return {"error": str(e)}


def memory_delete(key: str) -> Dict:
    """
    Delete a key from memory.

    Args:
        key: Memory key to delete

    Returns:
        Status dict

    Example:
        >>> memory_delete("old_key")
        {"success": True, "key": "old_key"}
    """
    try:
        return _get_memory().delete(key)
    except Exception as e:
        logger.error(f"Error deleting memory {key}: {e}")
        return {"success": False, "error": str(e)}


def memory_search(query: str, limit: int = 10) -> Union[List[Dict], Dict]:
    """
    Search memory by keyword (simple text search).

    Searches both keys and values for the query string.

    Args:
        query: Search query
        limit: Maximum results to return

    Returns:
        List of matching entries, or error dict

    Example:
        >>> memory_search("Alice")
        [{"key": "user_name", "value": "Alice", ...}]
    """
    try:
        return _get_memory().search(query, limit)
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        return {"error": str(e)}


# Tool schemas for AI API registration
MEMORY_TOOL_SCHEMAS = {
    "memory_store": {
        "name": "memory_store",
        "description": (
            "Store a value in memory with a key for later retrieval. "
            "Use this to remember information across conversations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": (
                        "Unique key to identify this memory "
                        "(e.g., 'user_name', 'user_preferences')"
                    )
                },
                "value": {
                    "description": "Value to store (can be string, number, array, or object)"
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata about this memory",
                    "default": {}
                }
            },
            "required": ["key", "value"]
        }
    },
    "memory_retrieve": {
        "name": "memory_retrieve",
        "description": "Retrieve a previously stored value from memory by its key",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key of the memory to retrieve"
                }
            },
            "required": ["key"]
        }
    },
    "memory_list": {
        "name": "memory_list",
        "description": "List all stored memory keys, optionally filtered by prefix",
        "input_schema": {
            "type": "object",
            "properties": {
                "prefix": {
                    "type": "string",
                    "description": (
                        "Optional prefix to filter keys "
                        "(e.g., 'user_' to get all user-related keys)"
                    )
                }
            },
            "required": []
        }
    },
    "memory_delete": {
        "name": "memory_delete",
        "description": "Delete a memory by its key",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key of the memory to delete"
                }
            },
            "required": ["key"]
        }
    },
    "memory_search": {
        "name": "memory_search",
        "description": "Search memory entries by keyword (searches both keys and values)",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
}
