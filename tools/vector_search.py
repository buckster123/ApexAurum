"""
Vector Search Tools for Claude

Provides semantic search capabilities using vector embeddings.
Claude can use these tools to:
- Store documents in vector database
- Search for similar documents semantically
- Manage vector collections
- Build and query knowledge bases

Dependencies: Phase 13.1 (core/vector_db.py)
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Global vector database instance (lazy-loaded)
_vector_db = None


def _get_vector_db():
    """Get or create global vector database instance"""
    global _vector_db

    if _vector_db is None:
        from core.vector_db import create_vector_db

        try:
            _vector_db = create_vector_db(
                persist_directory="./sandbox/vector_db",
                model_name="all-MiniLM-L6-v2"
            )
            logger.info("Vector database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            return None

    return _vector_db


def vector_add(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    collection: str = "documents",
    id: Optional[str] = None
) -> Dict:
    """
    Add a document to the vector database for semantic search.

    This stores text with its embedding, making it searchable by meaning.
    Use this to build a searchable knowledge base of facts, documents, or information.

    Args:
        text: The text content to store (will be embedded)
        metadata: Optional dict of metadata (tags, category, source, etc.)
        collection: Collection name (default: "documents")
        id: Optional custom ID (auto-generated if not provided)

    Returns:
        Dict with success status, id, and collection

    Example:
        >>> vector_add(
        ...     "Python is a high-level programming language",
        ...     metadata={"category": "programming", "language": "python"},
        ...     collection="knowledge"
        ... )
        {"success": True, "id": "doc_123", "collection": "knowledge"}
    """
    try:
        db = _get_vector_db()
        if db is None:
            return {
                "success": False,
                "error": "Vector database not available"
            }

        # Get or create collection
        coll = db.get_or_create_collection(collection)

        # Generate ID if not provided
        if id is None:
            id = f"{collection}_{datetime.now().timestamp()}"

        # Add metadata fields
        if metadata is None:
            metadata = {}

        metadata["added_at"] = datetime.now().isoformat()

        # Add document
        coll.add(
            texts=[text],
            metadatas=[metadata],
            ids=[id]
        )

        logger.info(f"Added document to {collection}: {id}")

        return {
            "success": True,
            "id": id,
            "collection": collection,
            "text_length": len(text)
        }

    except Exception as e:
        logger.error(f"Error in vector_add: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def vector_search(
    query: str,
    collection: str = "documents",
    top_k: int = 5,
    filter: Optional[Dict[str, Any]] = None,
    include_distances: bool = True
) -> Union[List[Dict], Dict]:
    """
    Search for documents semantically similar to the query.

    This performs semantic search - it finds documents by *meaning*, not just keywords.
    Results are ranked by similarity.

    Args:
        query: Search query (natural language)
        collection: Collection to search in (default: "documents")
        top_k: Number of results to return (default: 5)
        filter: Optional metadata filter (e.g., {"category": "programming"})
        include_distances: Include similarity scores (default: True)

    Returns:
        List of matching documents with ids, text, metadata, and similarity scores

    Example:
        >>> vector_search(
        ...     "How do I write functions in Python?",
        ...     collection="knowledge",
        ...     top_k=3
        ... )
        [
            {
                "id": "doc_123",
                "text": "Python functions are defined with def...",
                "metadata": {"category": "programming"},
                "distance": 0.234  # Lower = more similar
            },
            ...
        ]
    """
    try:
        db = _get_vector_db()
        if db is None:
            return {
                "success": False,
                "error": "Vector database not available"
            }

        # Get collection
        coll = db.get_or_create_collection(collection)

        # Check if collection is empty
        if coll.count() == 0:
            return {
                "success": False,
                "error": f"Collection '{collection}' is empty. Add documents first.",
                "count": 0
            }

        # Search
        results = coll.query(
            query_text=query,
            n_results=min(top_k, coll.count()),
            filter=filter,
            include_distances=include_distances
        )

        # Format results
        formatted_results = []
        for i in range(len(results["ids"])):
            result = {
                "id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i]
            }

            if include_distances and "distances" in results:
                result["distance"] = results["distances"][i]
                result["similarity"] = 1.0 - results["distances"][i]  # Convert to similarity

            formatted_results.append(result)

        logger.info(f"Vector search in {collection}: {len(formatted_results)} results")

        return formatted_results

    except Exception as e:
        logger.error(f"Error in vector_search: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def vector_delete(
    id: str,
    collection: str = "documents"
) -> Dict:
    """
    Delete a document from the vector database.

    Args:
        id: Document ID to delete
        collection: Collection name (default: "documents")

    Returns:
        Dict with success status

    Example:
        >>> vector_delete("doc_123", collection="knowledge")
        {"success": True, "id": "doc_123", "collection": "knowledge"}
    """
    try:
        db = _get_vector_db()
        if db is None:
            return {
                "success": False,
                "error": "Vector database not available"
            }

        # Get collection
        coll = db.get_or_create_collection(collection)

        # Delete document
        coll.delete([id])

        logger.info(f"Deleted document from {collection}: {id}")

        return {
            "success": True,
            "id": id,
            "collection": collection
        }

    except Exception as e:
        logger.error(f"Error in vector_delete: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def vector_list_collections() -> Union[List[str], Dict]:
    """
    List all available vector collections.

    Returns:
        List of collection names

    Example:
        >>> vector_list_collections()
        ["documents", "knowledge", "conversations"]
    """
    try:
        db = _get_vector_db()
        if db is None:
            return {
                "success": False,
                "error": "Vector database not available"
            }

        collections = db.list_collections()

        logger.info(f"Listed {len(collections)} collections")

        return collections

    except Exception as e:
        logger.error(f"Error in vector_list_collections: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def vector_get_stats(collection: str = "documents") -> Dict:
    """
    Get statistics about a vector collection.

    Args:
        collection: Collection name (default: "documents")

    Returns:
        Dict with collection stats (count, model, dimension)

    Example:
        >>> vector_get_stats("knowledge")
        {
            "collection": "knowledge",
            "count": 42,
            "model": "all-MiniLM-L6-v2",
            "dimension": 384
        }
    """
    try:
        db = _get_vector_db()
        if db is None:
            return {
                "success": False,
                "error": "Vector database not available"
            }

        stats = db.get_collection_stats(collection)

        logger.info(f"Got stats for {collection}")

        return stats

    except Exception as e:
        logger.error(f"Error in vector_get_stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Knowledge Base Convenience Functions
# ============================================================================

def vector_add_knowledge(
    fact: str,
    category: str = "general",
    confidence: float = 1.0,
    source: str = "conversation"
) -> Dict:
    """
    Add a fact to the knowledge base (convenience function).

    This is a shorthand for adding to the "knowledge" collection with
    structured metadata. Use this to remember important facts, preferences,
    or information across conversations.

    Args:
        fact: The fact or information to remember
        category: Category (general, preferences, technical, project)
        confidence: Confidence score 0.0-1.0 (default: 1.0)
        source: Where this fact came from (default: "conversation")

    Returns:
        Dict with success status and fact ID

    Example:
        >>> vector_add_knowledge(
        ...     "User prefers functional programming",
        ...     category="preferences",
        ...     confidence=0.9,
        ...     source="conversation_2025-01-15"
        ... )
        {"success": True, "id": "knowledge_123", "category": "preferences"}
    """
    metadata = {
        "category": category,
        "confidence": confidence,
        "source": source,
        "type": "fact"
    }

    result = vector_add(
        text=fact,
        metadata=metadata,
        collection="knowledge"
    )

    if result.get("success"):
        result["category"] = category

    return result


def vector_search_knowledge(
    query: str,
    category: Optional[str] = None,
    min_confidence: float = 0.0,
    top_k: int = 5
) -> Union[List[Dict], Dict]:
    """
    Search the knowledge base (convenience function).

    Search for relevant facts in the knowledge base, optionally filtered
    by category and confidence.

    Args:
        query: What to search for
        category: Filter by category (optional)
        min_confidence: Minimum confidence score (default: 0.0)
        top_k: Number of results (default: 5)

    Returns:
        List of matching facts with metadata

    Example:
        >>> vector_search_knowledge(
        ...     "What are the user's coding preferences?",
        ...     category="preferences",
        ...     top_k=3
        ... )
        [
            {
                "id": "knowledge_123",
                "text": "User prefers functional programming",
                "metadata": {"category": "preferences", "confidence": 0.9},
                "similarity": 0.87
            },
            ...
        ]
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

    return results


def vector_update_knowledge_confidence(
    fact_id: str,
    new_confidence: float
) -> Dict:
    """
    Update confidence score for a knowledge base fact.

    Args:
        fact_id: ID of the fact
        new_confidence: New confidence score (0.0-1.0)

    Returns:
        Dict with success status
    """
    try:
        db = _get_vector_db()
        if db is None:
            return {
                "success": False,
                "error": "Vector database not available"
            }

        coll = db.get_or_create_collection("knowledge")

        # Get current metadata
        doc = coll.get(ids=[fact_id])
        if not doc["ids"]:
            return {
                "success": False,
                "error": f"Fact not found: {fact_id}"
            }

        # Update confidence
        metadata = doc["metadatas"][0]
        metadata["confidence"] = new_confidence
        metadata["updated_at"] = datetime.now().isoformat()

        coll.update(
            ids=[fact_id],
            metadatas=[metadata]
        )

        return {
            "success": True,
            "id": fact_id,
            "new_confidence": new_confidence
        }

    except Exception as e:
        logger.error(f"Error updating confidence: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Tool Schemas for Claude API
# ============================================================================

VECTOR_TOOL_SCHEMAS = {
    "vector_add": {
        "name": "vector_add",
        "description": (
            "Add a document to the vector database for semantic search. "
            "This stores text with its embedding, making it searchable by meaning, not just keywords. "
            "Use this to build a searchable knowledge base of facts, documents, conversations, or any information "
            "you want to be able to find semantically later. "
            "The text will be embedded into a 384-dimensional vector for similarity search."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text content to store and make searchable. Can be a fact, document, conversation summary, or any text."
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata dict with tags, category, source, or any custom fields for filtering",
                    "default": {}
                },
                "collection": {
                    "type": "string",
                    "description": "Collection name to store in. Common collections: 'documents', 'knowledge', 'conversations'",
                    "default": "documents"
                },
                "id": {
                    "type": "string",
                    "description": "Optional custom ID. Auto-generated if not provided.",
                    "default": None
                }
            },
            "required": ["text"]
        }
    },

    "vector_search": {
        "name": "vector_search",
        "description": (
            "Search for documents semantically similar to a query. "
            "This performs SEMANTIC search - it finds documents by *meaning*, not just keyword matching. "
            "For example, searching 'machine learning' will find documents about 'neural networks', 'AI models', etc. "
            "Results are ranked by semantic similarity. Use this to find relevant information, recall facts, "
            "or discover related content in the knowledge base."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query. Can be a question, phrase, or description of what you're looking for."
                },
                "collection": {
                    "type": "string",
                    "description": "Collection to search in. Common: 'documents', 'knowledge', 'conversations'",
                    "default": "documents"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max recommended: 20)",
                    "default": 5
                },
                "filter": {
                    "type": "object",
                    "description": "Optional metadata filter. E.g., {'category': 'programming'} or {'confidence': {'$gte': 0.8}}",
                    "default": None
                },
                "include_distances": {
                    "type": "boolean",
                    "description": "Include similarity scores in results (default: true)",
                    "default": True
                }
            },
            "required": ["query"]
        }
    },

    "vector_delete": {
        "name": "vector_delete",
        "description": (
            "Delete a document from the vector database. "
            "Use this to remove outdated or incorrect information. "
            "You need the document ID from a previous search or add operation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Document ID to delete"
                },
                "collection": {
                    "type": "string",
                    "description": "Collection containing the document",
                    "default": "documents"
                }
            },
            "required": ["id"]
        }
    },

    "vector_list_collections": {
        "name": "vector_list_collections",
        "description": (
            "List all available vector collections in the database. "
            "Use this to see what collections exist before searching or adding documents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    "vector_add_knowledge": {
        "name": "vector_add_knowledge",
        "description": (
            "Add a fact to the knowledge base (convenience function). "
            "Use this to remember important facts, user preferences, technical information, or project context "
            "across conversations. Facts are stored in the 'knowledge' collection with structured metadata. "
            "This is better than regular memory_store for semantic facts that need to be recalled by meaning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "The fact or information to remember. Be specific and clear."
                },
                "category": {
                    "type": "string",
                    "description": "Category: 'preferences', 'technical', 'project', or 'general'",
                    "default": "general"
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score 0.0-1.0. Use 1.0 for facts, 0.5-0.9 for inferences",
                    "default": 1.0
                },
                "source": {
                    "type": "string",
                    "description": "Where this fact came from (e.g., 'conversation_2025-01-15', 'user_stated', 'inferred')",
                    "default": "conversation"
                }
            },
            "required": ["fact"]
        }
    },

    "vector_search_knowledge": {
        "name": "vector_search_knowledge",
        "description": (
            "Search the knowledge base for relevant facts (convenience function). "
            "Use this to recall information, check user preferences, look up technical details, "
            "or find project context. Searches semantically in the 'knowledge' collection. "
            "Results can be filtered by category and confidence level."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for. Natural language question or keywords."
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category: 'preferences', 'technical', 'project', or 'general'",
                    "default": None
                },
                "min_confidence": {
                    "type": "number",
                    "description": "Minimum confidence score (0.0-1.0). Use 0.8+ for high-confidence facts only",
                    "default": 0.0
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}


# ============================================================================
# Memory System Utilities (Phase 1)
# ============================================================================

def migrate_existing_vectors_to_v2(collection: str = "knowledge") -> Dict[str, Any]:
    """
    Migrate existing vectors to include new metadata fields.
    Safe to run multiple times (idempotent).

    This adds the following fields to existing vectors:
    - access_count: Initialized to 0
    - last_accessed_ts: Set to creation time or current time
    - related_memories: Initialized to empty list
    - session_id: Marked as "migrated_v1"
    - embedding_version: Set to current model

    Args:
        collection: Collection name to migrate (default: "knowledge")

    Returns:
        Dict with migration stats including success status, total vectors, and migrated count
    """
    try:
        db = _get_vector_db()
        if db is None:
            return {"success": False, "error": "Vector database not available"}

        coll = db.get_or_create_collection(collection)

        # Get all existing documents
        all_docs = coll.get()

        if not all_docs["ids"]:
            return {
                "success": True,
                "message": f"Collection '{collection}' is empty, no migration needed",
                "migrated": 0,
                "total_vectors": 0
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
                # ChromaDB only accepts str/int/float/bool, so store as JSON string
                metadata["related_memories"] = "[]"
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


# For backward compatibility and easy imports
__all__ = [
    'vector_add',
    'vector_search',
    'vector_delete',
    'vector_list_collections',
    'vector_get_stats',
    'vector_add_knowledge',
    'vector_search_knowledge',
    'vector_update_knowledge_confidence',
    'migrate_existing_vectors_to_v2',
    'VECTOR_TOOL_SCHEMAS'
]
