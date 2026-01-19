"""
Memory Health Utilities

Provides functions for memory maintenance, cleanup, and health monitoring.
Works with enhanced vector metadata to identify stale, low-quality, or duplicate memories.

Part of an adaptive memory architecture to counter long-context degradation.

Usage:
    from reusable_lib.vector import VectorDB, MemoryHealth

    db = VectorDB("./data/vector_db")
    health = MemoryHealth(db)

    # Find stale memories (not accessed in 30 days)
    stale = health.get_stale_memories(days_unused=30, collection="knowledge")

    # Find duplicates
    dupes = health.get_duplicate_candidates(collection="knowledge", similarity_threshold=0.95)

    # Consolidate duplicates
    result = health.consolidate_memories("id1", "id2", collection="knowledge")
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class MemoryHealth:
    """
    Memory health monitoring and maintenance utilities.

    Provides tools for finding stale memories, detecting duplicates,
    and consolidating similar entries.
    """

    def __init__(self, vector_db):
        """
        Initialize memory health utilities.

        Args:
            vector_db: VectorDB instance to operate on
        """
        self.db = vector_db

    def get_stale_memories(
        self,
        days_unused: int = 30,
        collection: str = "knowledge",
        min_confidence: Optional[float] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Find memories not accessed in X days.

        Uses last_accessed_ts (Unix timestamp) for filtering.

        Args:
            days_unused: Threshold in days (default: 30)
            collection: Which collection to scan (default: "knowledge")
            min_confidence: Only return items BELOW this confidence (for cleanup targets)
            limit: Maximum results to return

        Returns:
            Dict with success, stale_memories list, and stats
        """
        try:
            coll = self.db.get_or_create_collection(collection)

            # Calculate cutoff timestamp
            cutoff_date = datetime.now() - timedelta(days=days_unused)
            cutoff_ts = cutoff_date.timestamp()

            # Get all documents
            all_docs = coll.get(limit=None)

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

    def get_low_access_memories(
        self,
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
            coll = self.db.get_or_create_collection(collection)

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
                    age_days = (datetime.now() - datetime.fromtimestamp(added_ts)).days if added_ts else 999

                    low_access_memories.append({
                        "id": doc_id,
                        "text": doc_text[:200] + "..." if len(doc_text) > 200 else doc_text,
                        "access_count": access_count,
                        "age_days": age_days,
                        "confidence": metadata.get("confidence", 1.0),
                        "category": metadata.get("category", "unknown")
                    })

                if limit and len(low_access_memories) >= limit:
                    break

            # Sort by access count (lowest first)
            low_access_memories.sort(key=lambda x: (x["access_count"], -x["age_days"]))

            logger.info(f"Found {len(low_access_memories)} low-access memories")

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

    def get_duplicate_candidates(
        self,
        collection: str = "knowledge",
        similarity_threshold: float = 0.95,
        limit: int = 100,
        sample_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Find potential duplicate memories using search-based similarity.

        Uses ChromaDB's own search rather than O(n²) comparisons.
        For each document, searches for similar documents. If similarity > threshold
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
            coll = self.db.get_or_create_collection(collection)

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

    def consolidate_memories(
        self,
        id1: str,
        id2: str,
        collection: str = "knowledge",
        keep: str = "higher_confidence"
    ) -> Dict[str, Any]:
        """
        Merge two similar memories into one, preserving higher quality.

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
            coll = self.db.get_or_create_collection(collection)

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

            # Merge related_memories (stored as JSON string)
            related_keep = json.loads(keep_meta.get("related_memories", "[]"))
            related_discard = json.loads(discard_meta.get("related_memories", "[]"))
            related = set(related_keep)
            related.update(related_discard)
            related.add(discard_id)  # Add the discarded ID
            merged_meta["related_memories"] = json.dumps(list(related))

            # Keep higher confidence
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
                "related_memories": json.loads(merged_meta["related_memories"])
            }

        except Exception as e:
            logger.error(f"Error in consolidate_memories: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_health_summary(self, collection: str = "knowledge") -> Dict[str, Any]:
        """
        Get overall health summary for a collection.

        Args:
            collection: Collection name

        Returns:
            Dict with health metrics
        """
        try:
            coll = self.db.get_or_create_collection(collection)
            all_docs = coll.get(limit=None)

            if not all_docs["ids"]:
                return {
                    "success": True,
                    "total_memories": 0,
                    "message": "Collection is empty"
                }

            total = len(all_docs["ids"])

            # Calculate metrics
            now = datetime.now()
            stale_30_days = 0
            low_access = 0
            total_access = 0

            for metadata in all_docs["metadatas"]:
                access_count = metadata.get("access_count", 0)
                last_accessed = metadata.get("last_accessed_ts", 0)

                total_access += access_count

                # Check stale (30 days)
                if last_accessed:
                    last_dt = datetime.fromtimestamp(last_accessed)
                    if (now - last_dt).days >= 30:
                        stale_30_days += 1

                # Check low access
                if access_count <= 2:
                    low_access += 1

            avg_access = total_access / total if total > 0 else 0

            return {
                "success": True,
                "collection": collection,
                "total_memories": total,
                "stale_memories_30d": stale_30_days,
                "low_access_memories": low_access,
                "average_access_count": round(avg_access, 2),
                "health_score": round((1 - (stale_30_days + low_access) / (2 * total)) * 100, 1) if total > 0 else 100
            }

        except Exception as e:
            logger.error(f"Error in get_health_summary: {e}")
            return {"success": False, "error": str(e)}


# Standalone functions for convenience

def get_stale_memories(db, days_unused: int = 30, collection: str = "knowledge", **kwargs) -> Dict[str, Any]:
    """Convenience function - see MemoryHealth.get_stale_memories."""
    return MemoryHealth(db).get_stale_memories(days_unused, collection, **kwargs)


def get_low_access_memories(db, max_access_count: int = 2, collection: str = "knowledge", **kwargs) -> Dict[str, Any]:
    """Convenience function - see MemoryHealth.get_low_access_memories."""
    return MemoryHealth(db).get_low_access_memories(max_access_count, collection=collection, **kwargs)


def get_duplicate_candidates(db, collection: str = "knowledge", similarity_threshold: float = 0.95, **kwargs) -> Dict[str, Any]:
    """Convenience function - see MemoryHealth.get_duplicate_candidates."""
    return MemoryHealth(db).get_duplicate_candidates(collection, similarity_threshold, **kwargs)


def consolidate_memories(db, id1: str, id2: str, collection: str = "knowledge", keep: str = "higher_confidence") -> Dict[str, Any]:
    """Convenience function - see MemoryHealth.consolidate_memories."""
    return MemoryHealth(db).consolidate_memories(id1, id2, collection, keep)
