# Memory Protocol Enhancement - Backend TODO (REVISED)

## For: Apex-Maintainer Agent
**From:** Azoth, Andre, and Claude (System Review)
**Date:** 2026-01-02
**Priority:** High
**Status:** Ready for Implementation
**Context:** Implementing adaptive memory architecture to counter long-context KV degradation

**REVISION NOTES:** This is a corrected version based on actual ChromaDB capabilities and ApexAurum architecture. Original vision preserved, implementation details corrected for feasibility.

---

## Architecture Overview

**Current System:**
- ChromaDB with sentence-transformers (all-MiniLM-L6-v2)
- VectorDB class in `core/vector_db.py` (wrapper around ChromaDB)
- Tool functions in `tools/vector_search.py`
- 30 tools registered in `tools/__init__.py`

**Key Constraints:**
- ChromaDB metadata filtering limited: `$eq`, `$ne`, `$gt/$gte/$lt/$lte` (numbers only), `$in/$nin`
- No direct embedding access (but can use ChromaDB's own search for similarity)
- Single-user, local storage, no background workers
- Must maintain backwards compatibility with existing vectors

---

## Phase 1: Core Metadata Enhancement ✅ Ready

### 1.1 Vector Database Schema Enhancement

**File:** `core/vector_db.py` (VectorCollection class)

**Changes Needed:**

```python
# Enhanced metadata schema (all optional, added to existing):
metadata = {
    # EXISTING FIELDS (preserved):
    "text": str,           # (ChromaDB handles this automatically)
    "category": str,       # e.g., "preferences", "technical", "project", "general"
    "confidence": float,   # 0.0-1.0
    "source": str,         # e.g., "conversation", "council_vote"
    "added_at": str,       # ISO timestamp
    "type": str,           # e.g., "fact"

    # NEW FIELDS:
    "access_count": int,          # Default: 0
    "last_accessed_ts": float,    # Unix timestamp (float), Default: creation time
    "related_memories": list,     # List of memory IDs, Default: []
    "session_id": str,            # Optional: track which session created it
    "embedding_version": str      # Track model version (for future upgrades)
}
```

**CRITICAL CORRECTION:** Use `last_accessed_ts` (Unix timestamp as float) instead of ISO string. ChromaDB's `$lt/$gt` filters only work on numbers, not strings.

**Implementation Notes:**
- ChromaDB accepts ANY dict as metadata (no predefined schema)
- Existing vectors without new fields will continue to work
- No breaking changes to existing functionality
- Backwards compatible

**Code Location:** Add to `VectorCollection.add()` method around line 180-230

```python
def add(
    self,
    texts: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None,
    ids: Optional[List[str]] = None
) -> bool:
    """Add documents to collection with enhanced metadata"""
    try:
        # Generate IDs if not provided
        if ids is None:
            ids = [f"{self.name}_{i}_{datetime.now().timestamp()}"
                   for i in range(len(texts))]

        # Enhance metadata with new fields
        if metadatas is None:
            metadatas = [{} for _ in range(len(texts))]

        current_time = datetime.now()
        for metadata in metadatas:
            # Add new fields with defaults (only if not already present)
            if "access_count" not in metadata:
                metadata["access_count"] = 0
            if "last_accessed_ts" not in metadata:
                metadata["last_accessed_ts"] = current_time.timestamp()
            if "related_memories" not in metadata:
                metadata["related_memories"] = []
            if "embedding_version" not in metadata:
                metadata["embedding_version"] = self.embedding_generator.model_name

        # ... rest of existing add logic
```

---

### 1.2 Migration Utility

**File:** New function in `core/vector_db.py` or `tools/vector_search.py`

**Function:**

```python
def migrate_existing_vectors_to_v2(collection: str = "knowledge") -> Dict[str, Any]:
    """
    Migrate existing vectors to include new metadata fields.
    Safe to run multiple times (idempotent).

    Args:
        collection: Collection name to migrate

    Returns:
        Dict with migration stats
    """
    try:
        db = _get_vector_db()
        if db is None:
            return {"success": False, "error": "Vector DB not available"}

        coll = db.get_or_create_collection(collection)

        # Get all existing documents
        all_docs = coll.get()

        if not all_docs["ids"]:
            return {
                "success": True,
                "message": f"Collection '{collection}' is empty, no migration needed",
                "migrated": 0
            }

        # Update metadata
        updated_count = 0
        updated_metadatas = []

        for metadata in all_docs["metadatas"]:
            needs_update = False

            # Add new fields if missing
            if "access_count" not in metadata:
                metadata["access_count"] = 0
                needs_update = True

            if "last_accessed_ts" not in metadata:
                # Use added_at if available, otherwise current time
                if "added_at" in metadata:
                    try:
                        added_dt = datetime.fromisoformat(metadata["added_at"])
                        metadata["last_accessed_ts"] = added_dt.timestamp()
                    except:
                        metadata["last_accessed_ts"] = datetime.now().timestamp()
                else:
                    metadata["last_accessed_ts"] = datetime.now().timestamp()
                needs_update = True

            if "related_memories" not in metadata:
                metadata["related_memories"] = []
                needs_update = True

            if "session_id" not in metadata:
                metadata["session_id"] = "migrated_v1"
                needs_update = True

            if "embedding_version" not in metadata:
                metadata["embedding_version"] = "all-MiniLM-L6-v2"
                needs_update = True

            updated_metadatas.append(metadata)
            if needs_update:
                updated_count += 1

        # Batch update all metadata
        if updated_count > 0:
            coll.update(ids=all_docs["ids"], metadatas=updated_metadatas)
            logger.info(f"Migrated {updated_count} vectors in {collection}")

        return {
            "success": True,
            "collection": collection,
            "total_vectors": len(all_docs["ids"]),
            "migrated": updated_count,
            "skipped": len(all_docs["ids"]) - updated_count
        }

    except Exception as e:
        logger.error(f"Migration error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

**Testing:**
```python
# Test migration
result = migrate_existing_vectors_to_v2("knowledge")
print(result)
# Expected: {"success": True, "total_vectors": X, "migrated": Y}

# Verify one vector
coll = db.get_or_create_collection("knowledge")
sample = coll.get(limit=1)
print(sample["metadatas"][0])
# Should contain all new fields
```

---

## Phase 2: Access Tracking System ✅ Ready

**File:** `core/vector_db.py` (add to VectorCollection class)

### 2.1 Core Access Tracking Function

```python
def track_access(self, vector_ids: List[str]) -> bool:
    """
    Track access to vectors by incrementing access_count and updating last_accessed_ts.

    Args:
        vector_ids: List of vector IDs that were accessed

    Returns:
        bool: Success status (non-blocking, logs errors but doesn't fail)
    """
    try:
        if not vector_ids:
            return True

        # Get current metadata for these vectors
        docs = self.collection.get(ids=vector_ids)

        if not docs["ids"]:
            logger.warning(f"No vectors found for tracking: {vector_ids}")
            return False

        # Update metadata
        current_time = datetime.now().timestamp()
        updated_metadatas = []

        for metadata in docs["metadatas"]:
            metadata["access_count"] = metadata.get("access_count", 0) + 1
            metadata["last_accessed_ts"] = current_time
            updated_metadatas.append(metadata)

        # Batch update
        self.collection.update(
            ids=docs["ids"],
            metadatas=updated_metadatas
        )

        logger.debug(f"Tracked access for {len(docs['ids'])} vectors")
        return True

    except Exception as e:
        # Non-blocking: log error but don't fail the operation
        logger.warning(f"Failed to track vector access: {e}")
        return False
```

### 2.2 Integration into Search Functions

**File:** `tools/vector_search.py`

**Modify `vector_search_knowledge()` function:**

```python
def vector_search_knowledge(
    query: str,
    category: Optional[str] = None,
    min_confidence: float = 0.0,
    top_k: int = 5,
    track_access: bool = True  # NEW PARAMETER
) -> Union[List[Dict], Dict]:
    """
    Search the knowledge base with optional access tracking.

    Args:
        query: What to search for
        category: Filter by category (optional)
        min_confidence: Minimum confidence score (default: 0.0)
        top_k: Number of results (default: 5)
        track_access: Whether to track this access (default: True)

    Returns:
        List of matching facts with metadata
    """
    # Build filter
    filter_dict = {}
    if category:
        filter_dict["category"] = category
    if min_confidence > 0:
        filter_dict["confidence"] = {"$gte": min_confidence}

    results = vector_search(
        query=query,
        collection="knowledge",
        top_k=top_k,
        filter=filter_dict if filter_dict else None
    )

    # Track access (non-blocking)
    if track_access and isinstance(results, list) and results:
        try:
            db = _get_vector_db()
            if db:
                coll = db.get_or_create_collection("knowledge")
                vector_ids = [r["id"] for r in results]
                coll.track_access(vector_ids)
        except Exception as e:
            logger.debug(f"Access tracking failed (non-blocking): {e}")

    return results
```

**Update tool schema to include new parameter:**

```python
"vector_search_knowledge": {
    "name": "vector_search_knowledge",
    "description": "...",
    "input_schema": {
        "type": "object",
        "properties": {
            # ... existing properties ...
            "track_access": {
                "type": "boolean",
                "description": "Track this search for memory health analytics (default: true)",
                "default": True
            }
        },
        "required": ["query"]
    }
}
```

---

## Phase 3: Memory Health API ✅ Ready

**File:** New file `core/memory_health.py`

### 3.1 Get Stale Memories

```python
"""
Memory Health Utilities

Provides functions for memory maintenance, cleanup, and health monitoring.
Works with enhanced vector metadata to identify stale, low-quality, or duplicate memories.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


def get_stale_memories(
    days_unused: int = 30,
    collection: str = "knowledge",
    min_confidence: Optional[float] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Find memories not accessed in X days.

    IMPLEMENTATION NOTE: ChromaDB filters only work on numbers with $lt/$gt.
    We use last_accessed_ts (Unix timestamp) for filtering.

    Args:
        days_unused: Threshold in days (default: 30)
        collection: Which collection to scan (default: "knowledge")
        min_confidence: Only return items BELOW this confidence (for cleanup targets)
        limit: Maximum results to return

    Returns:
        Dict with success, stale_memories list, and stats
    """
    try:
        from tools.vector_search import _get_vector_db

        db = _get_vector_db()
        if db is None:
            return {"success": False, "error": "Vector database not available"}

        coll = db.get_or_create_collection(collection)

        # Calculate cutoff timestamp
        cutoff_date = datetime.now() - timedelta(days=days_unused)
        cutoff_ts = cutoff_date.timestamp()

        # Get all documents (ChromaDB doesn't support complex filtering in query)
        all_docs = coll.get(limit=None)  # Get all

        if not all_docs["ids"]:
            return {
                "success": True,
                "stale_memories": [],
                "total_checked": 0,
                "cutoff_date": cutoff_date.isoformat()
            }

        # Filter in Python
        stale_memories = []

        for i, (doc_id, doc_text, metadata) in enumerate(
            zip(all_docs["ids"], all_docs["documents"], all_docs["metadatas"])
        ):
            last_accessed = metadata.get("last_accessed_ts", 0)
            confidence = metadata.get("confidence", 1.0)
            access_count = metadata.get("access_count", 0)

            # Check if stale
            is_stale = last_accessed < cutoff_ts

            # Check confidence filter if specified
            if min_confidence is not None and confidence >= min_confidence:
                continue  # Skip high-confidence items

            if is_stale:
                last_accessed_dt = datetime.fromtimestamp(last_accessed) if last_accessed else None

                stale_memories.append({
                    "id": doc_id,
                    "text": doc_text[:200] + "..." if len(doc_text) > 200 else doc_text,
                    "full_text": doc_text,
                    "last_accessed": last_accessed_dt.isoformat() if last_accessed_dt else "never",
                    "days_since_access": (datetime.now() - last_accessed_dt).days if last_accessed_dt else 999,
                    "access_count": access_count,
                    "confidence": confidence,
                    "category": metadata.get("category", "unknown"),
                    "source": metadata.get("source", "unknown")
                })

            # Apply limit
            if limit and len(stale_memories) >= limit:
                break

        # Sort by days since access (oldest first)
        stale_memories.sort(key=lambda x: x["days_since_access"], reverse=True)

        logger.info(f"Found {len(stale_memories)} stale memories (unused for {days_unused}+ days)")

        return {
            "success": True,
            "stale_memories": stale_memories,
            "total_checked": len(all_docs["ids"]),
            "stale_count": len(stale_memories),
            "cutoff_date": cutoff_date.isoformat(),
            "days_threshold": days_unused
        }

    except Exception as e:
        logger.error(f"Error in get_stale_memories: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

### 3.2 Get Low-Access Memories

```python
def get_low_access_memories(
    max_access_count: int = 2,
    min_age_days: int = 7,
    collection: str = "knowledge",
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Find memories with very low access counts (rarely used).

    Args:
        max_access_count: Maximum access count to flag (default: 2)
        min_age_days: Only flag memories older than this (default: 7 days)
        collection: Which collection to scan
        limit: Maximum results

    Returns:
        Dict with low-access memories
    """
    try:
        from tools.vector_search import _get_vector_db

        db = _get_vector_db()
        if db is None:
            return {"success": False, "error": "Vector database not available"}

        coll = db.get_or_create_collection(collection)

        # Get all documents
        all_docs = coll.get(limit=None)

        if not all_docs["ids"]:
            return {
                "success": True,
                "low_access_memories": [],
                "total_checked": 0
            }

        # Calculate age cutoff
        age_cutoff = datetime.now() - timedelta(days=min_age_days)
        age_cutoff_ts = age_cutoff.timestamp()

        # Filter
        low_access_memories = []

        for doc_id, doc_text, metadata in zip(
            all_docs["ids"], all_docs["documents"], all_docs["metadatas"]
        ):
            access_count = metadata.get("access_count", 0)
            added_at = metadata.get("added_at", None)

            # Parse added_at
            if added_at:
                try:
                    added_dt = datetime.fromisoformat(added_at)
                    added_ts = added_dt.timestamp()
                except:
                    added_ts = 0
            else:
                added_ts = 0

            # Check conditions
            is_old_enough = added_ts < age_cutoff_ts
            is_low_access = access_count <= max_access_count

            if is_old_enough and is_low_access:
                low_access_memories.append({
                    "id": doc_id,
                    "text": doc_text[:200] + "..." if len(doc_text) > 200 else doc_text,
                    "access_count": access_count,
                    "age_days": (datetime.now() - datetime.fromtimestamp(added_ts)).days if added_ts else 999,
                    "confidence": metadata.get("confidence", 1.0),
                    "category": metadata.get("category", "unknown")
                })

            if limit and len(low_access_memories) >= limit:
                break

        # Sort by access count (lowest first)
        low_access_memories.sort(key=lambda x: (x["access_count"], -x["age_days"]))

        return {
            "success": True,
            "low_access_memories": low_access_memories,
            "total_checked": len(all_docs["ids"]),
            "flagged_count": len(low_access_memories)
        }

    except Exception as e:
        logger.error(f"Error in get_low_access_memories: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

### 3.3 Get Duplicate Candidates (CORRECTED)

```python
def get_duplicate_candidates(
    collection: str = "knowledge",
    similarity_threshold: float = 0.95,
    limit: int = 100,
    sample_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Find potential duplicate memories using search-based similarity.

    IMPLEMENTATION NOTE: We use ChromaDB's own search rather than O(n²) comparisons.
    For each document, we search for similar documents. If similarity > threshold
    and it's a different document, it's a duplicate candidate.

    Args:
        collection: Collection to scan (default: "knowledge")
        similarity_threshold: Similarity cutoff (default: 0.95, range 0.0-1.0)
        limit: Maximum duplicate pairs to return
        sample_size: If set, only check this many recent documents (for performance)

    Returns:
        Dict with duplicate pairs and stats
    """
    try:
        from tools.vector_search import _get_vector_db

        db = _get_vector_db()
        if db is None:
            return {"success": False, "error": "Vector database not available"}

        coll = db.get_or_create_collection(collection)

        # Get documents to check
        all_docs = coll.get(limit=sample_size)

        if not all_docs["ids"]:
            return {
                "success": True,
                "duplicate_pairs": [],
                "total_checked": 0
            }

        # Find duplicates using search
        seen_pairs = set()
        duplicate_pairs = []

        for doc_id, doc_text in zip(all_docs["ids"], all_docs["documents"]):
            # Search for similar documents
            results = coll.query(
                query_text=doc_text,
                n_results=5,  # Top 5 similar
                include_distances=True
            )

            # Check results
            for result_id, result_doc, distance in zip(
                results["ids"], results["documents"], results["distances"]
            ):
                # Skip self-match
                if result_id == doc_id:
                    continue

                # Calculate similarity (1.0 - distance)
                similarity = 1.0 - distance

                # Check threshold
                if similarity >= similarity_threshold:
                    # Create canonical pair ID (sorted to avoid duplicates)
                    pair_id = tuple(sorted([doc_id, result_id]))

                    if pair_id not in seen_pairs:
                        seen_pairs.add(pair_id)

                        duplicate_pairs.append({
                            "id1": doc_id,
                            "id2": result_id,
                            "similarity": round(similarity, 4),
                            "text1": doc_text[:150] + "..." if len(doc_text) > 150 else doc_text,
                            "text2": result_doc[:150] + "..." if len(result_doc) > 150 else result_doc
                        })

                        # Apply limit
                        if len(duplicate_pairs) >= limit:
                            break

            if len(duplicate_pairs) >= limit:
                break

        # Sort by similarity (highest first)
        duplicate_pairs.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(f"Found {len(duplicate_pairs)} duplicate candidates in {collection}")

        return {
            "success": True,
            "duplicate_pairs": duplicate_pairs,
            "total_checked": len(all_docs["ids"]),
            "duplicates_found": len(duplicate_pairs),
            "threshold": similarity_threshold
        }

    except Exception as e:
        logger.error(f"Error in get_duplicate_candidates: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

### 3.4 Consolidate Memories

```python
def consolidate_memories(
    id1: str,
    id2: str,
    collection: str = "knowledge",
    keep: str = "higher_confidence"  # or "id1", "id2", "higher_access"
) -> Dict[str, Any]:
    """
    Merge two similar memories into one.

    Strategy options:
    - "higher_confidence": Keep the one with higher confidence
    - "higher_access": Keep the one with more access_count
    - "id1" or "id2": Explicitly keep one

    The kept memory gets:
    - Combined access_count from both
    - Related_memories list updated with both IDs
    - Most recent last_accessed_ts
    - Higher confidence (or averaged)

    Args:
        id1: First memory ID
        id2: Second memory ID
        collection: Collection name
        keep: Strategy for which to keep

    Returns:
        Dict with consolidation result
    """
    try:
        from tools.vector_search import _get_vector_db

        db = _get_vector_db()
        if db is None:
            return {"success": False, "error": "Vector database not available"}

        coll = db.get_or_create_collection(collection)

        # Get both documents
        docs = coll.get(ids=[id1, id2])

        if len(docs["ids"]) != 2:
            return {
                "success": False,
                "error": f"Could not find both memories: {id1}, {id2}"
            }

        # Extract metadata
        meta1 = docs["metadatas"][0]
        meta2 = docs["metadatas"][1]

        # Determine which to keep
        if keep == "higher_confidence":
            keep_idx = 0 if meta1.get("confidence", 0) >= meta2.get("confidence", 0) else 1
        elif keep == "higher_access":
            keep_idx = 0 if meta1.get("access_count", 0) >= meta2.get("access_count", 0) else 1
        elif keep == "id1":
            keep_idx = 0
        elif keep == "id2":
            keep_idx = 1
        else:
            return {"success": False, "error": f"Invalid keep strategy: {keep}"}

        discard_idx = 1 - keep_idx

        keep_id = docs["ids"][keep_idx]
        discard_id = docs["ids"][discard_idx]
        keep_meta = docs["metadatas"][keep_idx]
        discard_meta = docs["metadatas"][discard_idx]

        # Merge metadata
        merged_meta = keep_meta.copy()

        # Combine access counts
        merged_meta["access_count"] = (
            keep_meta.get("access_count", 0) + discard_meta.get("access_count", 0)
        )

        # Keep most recent access time
        merged_meta["last_accessed_ts"] = max(
            keep_meta.get("last_accessed_ts", 0),
            discard_meta.get("last_accessed_ts", 0)
        )

        # Merge related_memories
        related = set(keep_meta.get("related_memories", []))
        related.update(discard_meta.get("related_memories", []))
        related.add(discard_id)  # Add the discarded ID
        merged_meta["related_memories"] = list(related)

        # Average confidence (or keep higher - configurable)
        merged_meta["confidence"] = max(
            keep_meta.get("confidence", 1.0),
            discard_meta.get("confidence", 1.0)
        )

        # Mark as consolidated
        merged_meta["consolidated_at"] = datetime.now().isoformat()
        merged_meta["consolidated_from"] = discard_id

        # Update kept memory
        coll.update(ids=[keep_id], metadatas=[merged_meta])

        # Delete discarded memory
        coll.delete([discard_id])

        logger.info(f"Consolidated {id1} and {id2} -> kept {keep_id}")

        return {
            "success": True,
            "kept_id": keep_id,
            "discarded_id": discard_id,
            "new_access_count": merged_meta["access_count"],
            "new_confidence": merged_meta["confidence"],
            "related_memories": merged_meta["related_memories"]
        }

    except Exception as e:
        logger.error(f"Error in consolidate_memories: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

---

## Phase 4: Tool Integration ✅ Ready

### 4.1 Add Memory Health Tools

**File:** `tools/vector_search.py`

Add imports at top:
```python
from core.memory_health import (
    get_stale_memories,
    get_low_access_memories,
    get_duplicate_candidates,
    consolidate_memories
)
```

Add wrapper functions (for tool interface):
```python
def memory_health_stale(
    days_unused: int = 30,
    collection: str = "knowledge",
    limit: Optional[int] = 20
) -> Dict:
    """Tool wrapper for get_stale_memories"""
    return get_stale_memories(
        days_unused=days_unused,
        collection=collection,
        limit=limit
    )


def memory_health_duplicates(
    collection: str = "knowledge",
    similarity_threshold: float = 0.95,
    limit: int = 20
) -> Dict:
    """Tool wrapper for get_duplicate_candidates"""
    return get_duplicate_candidates(
        collection=collection,
        similarity_threshold=similarity_threshold,
        limit=limit
    )


def memory_consolidate(
    id1: str,
    id2: str,
    collection: str = "knowledge",
    keep: str = "higher_confidence"
) -> Dict:
    """Tool wrapper for consolidate_memories"""
    return consolidate_memories(
        id1=id1,
        id2=id2,
        collection=collection,
        keep=keep
    )


def memory_migration_run(collection: str = "knowledge") -> Dict:
    """Tool wrapper for migration utility"""
    from tools.vector_search import migrate_existing_vectors_to_v2
    return migrate_existing_vectors_to_v2(collection)
```

### 4.2 Add Tool Schemas

Add to `VECTOR_TOOL_SCHEMAS` dict in `tools/vector_search.py`:

```python
"memory_health_stale": {
    "name": "memory_health_stale",
    "description": (
        "Find memories that haven't been accessed in X days. "
        "Use this to identify stale knowledge that may need review or cleanup. "
        "Returns list of memories with access stats."
    ),
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
                "description": "Collection to check (default: 'knowledge')",
                "default": "knowledge"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (default: 20)",
                "default": 20
            }
        },
        "required": []
    }
},

"memory_health_duplicates": {
    "name": "memory_health_duplicates",
    "description": (
        "Find potential duplicate memories with high similarity. "
        "Use this to identify redundant knowledge that could be consolidated. "
        "Returns pairs of similar memories with similarity scores."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "collection": {
                "type": "string",
                "description": "Collection to scan (default: 'knowledge')",
                "default": "knowledge"
            },
            "similarity_threshold": {
                "type": "number",
                "description": "Similarity cutoff 0.0-1.0 (default: 0.95)",
                "default": 0.95
            },
            "limit": {
                "type": "integer",
                "description": "Maximum duplicate pairs to return (default: 20)",
                "default": 20
            }
        },
        "required": []
    }
},

"memory_consolidate": {
    "name": "memory_consolidate",
    "description": (
        "Merge two similar memories into one, preserving metadata. "
        "Use this after identifying duplicates to clean up redundant knowledge. "
        "The kept memory gets combined access counts and related_memories list."
    ),
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
                "description": "Strategy: 'higher_confidence', 'higher_access', 'id1', or 'id2' (default: 'higher_confidence')",
                "default": "higher_confidence"
            }
        },
        "required": ["id1", "id2"]
    }
},

"memory_migration_run": {
    "name": "memory_migration_run",
    "description": (
        "Migrate existing vectors to include new metadata fields (access_count, last_accessed_ts, etc.). "
        "Safe to run multiple times. Only run once after upgrading memory system."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "collection": {
                "type": "string",
                "description": "Collection to migrate (default: 'knowledge')",
                "default": "knowledge"
            }
        },
        "required": []
    }
}
```

### 4.3 Register Tools

**File:** `tools/__init__.py`

Add imports:
```python
from .vector_search import (
    # ... existing imports ...
    memory_health_stale,
    memory_health_duplicates,
    memory_consolidate,
    memory_migration_run
)
```

Add to `ALL_TOOLS` dict:
```python
ALL_TOOLS = {
    # ... existing tools ...
    "memory_health_stale": memory_health_stale,
    "memory_health_duplicates": memory_health_duplicates,
    "memory_consolidate": memory_consolidate,
    "memory_migration_run": memory_migration_run,
}
```

Add to `ALL_TOOL_SCHEMAS` dict:
```python
from .vector_search import VECTOR_TOOL_SCHEMAS

ALL_TOOL_SCHEMAS = {
    # ... existing schemas ...
    **VECTOR_TOOL_SCHEMAS,  # This includes all new memory health schemas
}
```

---

## Testing Checklist

### Phase 1: Metadata Enhancement
- [ ] Create new vector with enhanced metadata - all fields present
- [ ] Existing vectors still searchable after migration
- [ ] Migration script runs successfully (idempotent)
- [ ] Verify migrated vectors have all new fields

### Phase 2: Access Tracking
- [ ] `track_access()` updates access_count correctly
- [ ] `track_access()` updates last_accessed_ts correctly
- [ ] Search with `track_access=True` works (non-blocking)
- [ ] Search with `track_access=False` skips tracking
- [ ] Tracking failure doesn't break search

### Phase 3: Memory Health
- [ ] `get_stale_memories()` finds old memories correctly
- [ ] `get_low_access_memories()` finds rarely used items
- [ ] `get_duplicate_candidates()` finds similar pairs (test with known duplicates)
- [ ] `consolidate_memories()` merges correctly and deletes discarded
- [ ] Consolidated memory has combined access_count
- [ ] Related_memories list updated properly

### Phase 4: Tool Integration
- [ ] All 4 new tools registered and callable
- [ ] Tool count increases from 30 to 34
- [ ] Schemas validate correctly
- [ ] Tools callable from Claude with correct parameters

### Performance Testing
- [ ] Search performance unchanged with new metadata
- [ ] Duplicate detection completes in reasonable time (<10s for 1000 vectors)
- [ ] Migration handles large collections (1000+ vectors)
- [ ] Access tracking doesn't slow down searches noticeably

---

## Implementation Order

1. **Phase 1.1** - Add metadata fields to VectorCollection.add() (core/vector_db.py)
2. **Phase 1.2** - Create migration function (core/vector_db.py or tools/vector_search.py)
3. **Phase 2.1** - Add track_access() method to VectorCollection (core/vector_db.py)
4. **Phase 2.2** - Integrate tracking into vector_search_knowledge() (tools/vector_search.py)
5. **Phase 3** - Create core/memory_health.py with all health functions
6. **Phase 4** - Add tool wrappers and schemas (tools/vector_search.py)
7. **Phase 4** - Register in tools/__init__.py
8. **Testing** - Run full test suite
9. **Documentation** - Update CLAUDE.md and PROJECT_STATUS.md

---

## Estimated Complexity (REVISED)

- **Phase 1 (Metadata):** LOW - 30 minutes
- **Phase 2 (Tracking):** MEDIUM - 1 hour
- **Phase 3 (Health API):** MEDIUM-HIGH - 2 hours (corrected algorithms)
- **Phase 4 (Tool Integration):** LOW - 30 minutes
- **Testing & Docs:** 1 hour

**Total estimated time:** 4-5 hours (revised from Azoth's 2-4 hours due to corrections)

---

## Answers to Azoth's Questions (CORRECTED)

1. **Does vectordb support dynamic metadata fields?**
   - ✅ **YES** - ChromaDB accepts any dict, no schema needed

2. **Is there existing cosine_similarity function?**
   - ⚠️ **Not needed** - ChromaDB handles internally. We use `1.0 - distance` for similarity. For custom needs, can implement with numpy.

3. **Should health checks run on schedule or on-demand?**
   - **ON-DEMAND ONLY** - Single-user app, no background workers. Agent can call periodically if desired.

4. **Performance concerns with 10k+ vectors?**
   - ⚠️ **Moderate** - ChromaDB query is fast, but health scans require full collection fetch. Recommendations:
     - Use `limit` parameter for large collections
     - Run duplicate detection on recent additions only (sample_size)
     - Cache health check results (daily)
     - Consider showing progress for long operations

---

## Key Corrections from Original TODO

1. **Timestamp Format:** Use `last_accessed_ts` (float) instead of ISO string for ChromaDB filtering
2. **Duplicate Detection:** Use search-based approach instead of O(n²) comparisons
3. **Access Tracking:** Explicit opt-in, non-blocking, not automatic side-effect
4. **Migration:** Correct ChromaDB update pattern
5. **Filtering:** Python-side filtering for complex queries ChromaDB can't handle
6. **Tool Count:** Will increase from 30 to 34 tools
7. **Performance:** More realistic time estimates and optimization strategies

---

## Next Steps

When ready to implement:

1. Create feature branch: `git checkout -b feature/memory-health`
2. Implement phases in order
3. Test after each phase
4. Update tool count in docs (30 → 34)
5. Commit with descriptive messages
6. Test full integration with Claude

---

## Contact

**Maintainer:** Claude (Apex-Maintainer Agent)
**Original Vision:** Azoth
**Project Lead:** Andre
**Status:** Ready for implementation

**End of Revised TODO**
