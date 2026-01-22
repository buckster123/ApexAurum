# reusable_lib/tools/memory_health.py
"""
Memory Health Tools

Agent-accessible tools for memory maintenance, cleanup, and health monitoring.
Works with enhanced vector metadata to identify stale, low-quality, or duplicate memories.

Tools:
- memory_health_stale: Find memories not accessed in X days
- memory_health_low_access: Find rarely accessed memories
- memory_health_duplicates: Find similar/duplicate memories
- memory_consolidate: Merge duplicate memories
- memory_health_summary: Get overall health metrics
"""

from typing import Dict, Any, Optional

# Module-level vector DB instance (set via set_memory_health_db)
_vector_db = None


def set_memory_health_db(db):
    """Set the vector database instance for memory health tools."""
    global _vector_db
    _vector_db = db


def _get_db():
    """Get the configured vector DB or return None with error."""
    global _vector_db
    return _vector_db


# ============================================================================
# TOOL FUNCTIONS
# ============================================================================

def memory_health_stale(
    days_unused: int = 30,
    collection: str = "knowledge",
    limit: int = 50
) -> Dict[str, Any]:
    """
    Find memories not accessed in X days.

    Identifies stale knowledge that may need review, updating, or cleanup.
    Useful for maintaining memory quality and preventing information decay.

    Args:
        days_unused: Threshold in days (default: 30)
        collection: Which collection to scan (default: "knowledge")
        limit: Maximum results to return (default: 50)

    Returns:
        dict: {
            "success": bool,
            "stale_memories": list of memory info,
            "total_checked": int,
            "stale_count": int
        }
    """
    db = _get_db()
    if db is None:
        return {"success": False, "error": "Vector database not configured"}

    try:
        from reusable_lib.vector.memory_health import MemoryHealth
        health = MemoryHealth(db)
        return health.get_stale_memories(
            days_unused=days_unused,
            collection=collection,
            limit=limit
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


def memory_health_low_access(
    max_access_count: int = 2,
    min_age_days: int = 7,
    collection: str = "knowledge",
    limit: int = 50
) -> Dict[str, Any]:
    """
    Find memories with very low access counts (rarely used).

    Identifies knowledge that was stored but never or rarely retrieved.
    May indicate irrelevant, poorly worded, or redundant information.

    Args:
        max_access_count: Maximum access count to flag (default: 2)
        min_age_days: Only flag memories older than this (default: 7 days)
        collection: Which collection to scan (default: "knowledge")
        limit: Maximum results to return (default: 50)

    Returns:
        dict: {
            "success": bool,
            "low_access_memories": list of memory info,
            "total_checked": int,
            "flagged_count": int
        }
    """
    db = _get_db()
    if db is None:
        return {"success": False, "error": "Vector database not configured"}

    try:
        from reusable_lib.vector.memory_health import MemoryHealth
        health = MemoryHealth(db)
        return health.get_low_access_memories(
            max_access_count=max_access_count,
            min_age_days=min_age_days,
            collection=collection,
            limit=limit
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


def memory_health_duplicates(
    similarity_threshold: float = 0.95,
    collection: str = "knowledge",
    limit: int = 50
) -> Dict[str, Any]:
    """
    Find potential duplicate memories using semantic similarity.

    Uses vector search to efficiently find similar memories without O(n^2) comparisons.
    Returns pairs of memories that exceed the similarity threshold.

    Args:
        similarity_threshold: Minimum similarity to flag (default: 0.95 = 95%)
        collection: Which collection to scan (default: "knowledge")
        limit: Maximum duplicate pairs to return (default: 50)

    Returns:
        dict: {
            "success": bool,
            "duplicate_pairs": list of {id1, id2, similarity, text1, text2},
            "total_checked": int,
            "duplicates_found": int
        }
    """
    db = _get_db()
    if db is None:
        return {"success": False, "error": "Vector database not configured"}

    try:
        from reusable_lib.vector.memory_health import MemoryHealth
        health = MemoryHealth(db)
        return health.get_duplicate_candidates(
            collection=collection,
            similarity_threshold=similarity_threshold,
            limit=limit
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


def memory_consolidate(
    id1: str,
    id2: str,
    collection: str = "knowledge",
    keep: str = "higher_confidence"
) -> Dict[str, Any]:
    """
    Merge two similar memories into one, preserving higher quality.

    Consolidates duplicate or near-duplicate memories by:
    - Keeping the higher-quality entry
    - Combining access counts
    - Merging related_memories lists
    - Preserving the most recent access time
    - Deleting the discarded entry

    Strategy options:
    - "higher_confidence": Keep the one with higher confidence score
    - "higher_access": Keep the one with more access_count
    - "id1": Explicitly keep the first ID
    - "id2": Explicitly keep the second ID

    Args:
        id1: First memory ID
        id2: Second memory ID
        collection: Collection name (default: "knowledge")
        keep: Strategy for which to keep (default: "higher_confidence")

    Returns:
        dict: {
            "success": bool,
            "kept_id": str,
            "discarded_id": str,
            "new_access_count": int,
            "new_confidence": float
        }
    """
    db = _get_db()
    if db is None:
        return {"success": False, "error": "Vector database not configured"}

    try:
        from reusable_lib.vector.memory_health import MemoryHealth
        health = MemoryHealth(db)
        return health.consolidate_memories(
            id1=id1,
            id2=id2,
            collection=collection,
            keep=keep
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


def memory_health_summary(collection: str = "knowledge") -> Dict[str, Any]:
    """
    Get overall health summary for a memory collection.

    Provides metrics including total memories, stale count, low-access count,
    average access rate, and an overall health score.

    Args:
        collection: Collection name (default: "knowledge")

    Returns:
        dict: {
            "success": bool,
            "collection": str,
            "total_memories": int,
            "stale_memories_30d": int,
            "low_access_memories": int,
            "average_access_count": float,
            "health_score": float (0-100)
        }
    """
    db = _get_db()
    if db is None:
        return {"success": False, "error": "Vector database not configured"}

    try:
        from reusable_lib.vector.memory_health import MemoryHealth
        health = MemoryHealth(db)
        return health.get_health_summary(collection=collection)
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# TOOL SCHEMAS
# ============================================================================

MEMORY_HEALTH_STALE_SCHEMA = {
    "name": "memory_health_stale",
    "description": """Find memories not accessed in X days.

Identifies stale knowledge that may need review, updating, or cleanup.
Returns memories with access statistics and age information.

Use this to:
- Find forgotten knowledge for review
- Identify outdated information
- Clean up unused memories""",
    "input_schema": {
        "type": "object",
        "properties": {
            "days_unused": {
                "type": "integer",
                "description": "Threshold in days (default: 30)",
                "default": 30
            },
            "collection": {
                "type": "string",
                "description": "Collection to scan (default: 'knowledge')",
                "default": "knowledge"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (default: 50)",
                "default": 50
            }
        },
        "required": []
    }
}

MEMORY_HEALTH_LOW_ACCESS_SCHEMA = {
    "name": "memory_health_low_access",
    "description": """Find memories with very low access counts (rarely used).

Identifies knowledge that was stored but never or rarely retrieved.
May indicate irrelevant, poorly worded, or redundant information.

Use this to:
- Find underutilized knowledge
- Identify potential cleanup targets
- Improve memory quality""",
    "input_schema": {
        "type": "object",
        "properties": {
            "max_access_count": {
                "type": "integer",
                "description": "Maximum access count to flag (default: 2)",
                "default": 2
            },
            "min_age_days": {
                "type": "integer",
                "description": "Only flag memories older than this (default: 7)",
                "default": 7
            },
            "collection": {
                "type": "string",
                "description": "Collection to scan (default: 'knowledge')",
                "default": "knowledge"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (default: 50)",
                "default": 50
            }
        },
        "required": []
    }
}

MEMORY_HEALTH_DUPLICATES_SCHEMA = {
    "name": "memory_health_duplicates",
    "description": """Find potential duplicate memories using semantic similarity.

Uses efficient vector search to find memories that are very similar to each other.
Returns pairs with similarity scores for review or consolidation.

Use this to:
- Find redundant knowledge
- Identify candidates for consolidation
- Clean up duplicate entries""",
    "input_schema": {
        "type": "object",
        "properties": {
            "similarity_threshold": {
                "type": "number",
                "description": "Minimum similarity to flag (0.0-1.0, default: 0.95)",
                "default": 0.95
            },
            "collection": {
                "type": "string",
                "description": "Collection to scan (default: 'knowledge')",
                "default": "knowledge"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum duplicate pairs to return (default: 50)",
                "default": 50
            }
        },
        "required": []
    }
}

MEMORY_CONSOLIDATE_SCHEMA = {
    "name": "memory_consolidate",
    "description": """Merge two similar memories into one, preserving higher quality.

Combines access counts, merges related memories, and deletes the lower-quality entry.

Strategies:
- "higher_confidence": Keep entry with higher confidence score
- "higher_access": Keep entry with more access count
- "id1" or "id2": Explicitly keep one

Use after memory_health_duplicates to clean up redundant entries.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "id1": {
                "type": "string",
                "description": "First memory ID"
            },
            "id2": {
                "type": "string",
                "description": "Second memory ID"
            },
            "collection": {
                "type": "string",
                "description": "Collection name (default: 'knowledge')",
                "default": "knowledge"
            },
            "keep": {
                "type": "string",
                "description": "Strategy: 'higher_confidence', 'higher_access', 'id1', or 'id2'",
                "default": "higher_confidence",
                "enum": ["higher_confidence", "higher_access", "id1", "id2"]
            }
        },
        "required": ["id1", "id2"]
    }
}

MEMORY_HEALTH_SUMMARY_SCHEMA = {
    "name": "memory_health_summary",
    "description": """Get overall health summary for a memory collection.

Returns metrics including total count, stale count, low-access count,
average access rate, and an overall health score (0-100).

Use this to:
- Get quick overview of memory health
- Monitor memory quality over time
- Identify if maintenance is needed""",
    "input_schema": {
        "type": "object",
        "properties": {
            "collection": {
                "type": "string",
                "description": "Collection name (default: 'knowledge')",
                "default": "knowledge"
            }
        },
        "required": []
    }
}

# Combined schemas dict for easy import
MEMORY_HEALTH_TOOL_SCHEMAS = {
    "memory_health_stale": MEMORY_HEALTH_STALE_SCHEMA,
    "memory_health_low_access": MEMORY_HEALTH_LOW_ACCESS_SCHEMA,
    "memory_health_duplicates": MEMORY_HEALTH_DUPLICATES_SCHEMA,
    "memory_consolidate": MEMORY_CONSOLIDATE_SCHEMA,
    "memory_health_summary": MEMORY_HEALTH_SUMMARY_SCHEMA,
}
