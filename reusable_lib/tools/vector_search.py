"""
Vector Search Tools

Provides AI-callable tools for semantic search using ChromaDB.
Wraps reusable_lib.vector for tool-based access.

Tools:
    - vector_add: Add document to a collection
    - vector_search: Semantic search in a collection
    - vector_delete: Delete documents from collection
    - vector_list_collections: List all collections
    - vector_get_stats: Get collection statistics
    - vector_add_knowledge: Add to knowledge base (with categories)
    - vector_search_knowledge: Search knowledge base

Requirements:
    pip install chromadb sentence-transformers
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Global VectorDB instance - initialized lazily
_vector_db = None
_vector_db_path = "./data/vectors"

# Knowledge base collection name
KNOWLEDGE_COLLECTION = "knowledge_base"

# Valid knowledge categories
KNOWLEDGE_CATEGORIES = ["general", "technical", "preferences", "project", "facts"]


def _get_db():
    """Get or create the global VectorDB instance."""
    global _vector_db

    if _vector_db is None:
        try:
            from reusable_lib.vector import VectorDB
            _vector_db = VectorDB(persist_directory=_vector_db_path)
            logger.info(f"Initialized VectorDB at {_vector_db_path}")
        except ImportError as e:
            logger.error(f"Failed to import VectorDB: {e}")
            raise RuntimeError(
                "Vector database not available. Install with: "
                "pip install chromadb sentence-transformers"
            )

    return _vector_db


def set_vector_db_path(path: str):
    """
    Set the path for vector database storage.
    Must be called before any vector operations.

    Args:
        path: Directory path for vector storage
    """
    global _vector_db_path, _vector_db
    _vector_db_path = path
    _vector_db = None  # Reset to reinitialize with new path

    # Ensure directory exists
    Path(path).mkdir(parents=True, exist_ok=True)
    logger.info(f"Vector DB path set to: {path}")


# =============================================================================
# Core Vector Tools
# =============================================================================

def vector_add(
    collection: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a document to a vector collection for semantic search.

    Args:
        collection: Name of the collection to add to
        text: The text content to store and make searchable
        metadata: Optional metadata dict (e.g., {"source": "user", "type": "note"})
        id: Optional document ID (auto-generated if not provided)

    Returns:
        Dict with success status and document ID
    """
    try:
        db = _get_db()
        coll = db.get_or_create_collection(collection)

        # Generate ID if not provided
        if id is None:
            id = f"{collection}_{datetime.now().timestamp()}"

        # Prepare metadata
        meta = metadata or {}
        meta["added_at"] = datetime.now().isoformat()

        # Add document
        coll.add(
            texts=[text],
            metadatas=[meta],
            ids=[id]
        )

        return {
            "success": True,
            "id": id,
            "collection": collection,
            "message": f"Added document to '{collection}'"
        }

    except Exception as e:
        logger.error(f"vector_add failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def vector_search(
    collection: str,
    query: str,
    n_results: int = 5,
    filter: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Search a vector collection for semantically similar documents.

    Args:
        collection: Name of the collection to search
        query: Search query text
        n_results: Maximum number of results to return (default: 5)
        filter: Optional metadata filter (e.g., {"type": "note"})

    Returns:
        Dict with results list containing id, text, metadata, and similarity score
    """
    try:
        db = _get_db()
        coll = db.get_or_create_collection(collection)

        # Perform search
        results = coll.query(
            query_text=query,
            n_results=n_results,
            filter=filter
        )

        # Format results
        formatted = []
        for i, doc_id in enumerate(results.get("ids", [])):
            result = {
                "id": doc_id,
                "text": results["documents"][i] if results.get("documents") else None,
                "metadata": results["metadatas"][i] if results.get("metadatas") else {},
            }
            if "distances" in results:
                # Convert distance to similarity (lower distance = higher similarity)
                result["similarity"] = round(1 - results["distances"][i], 4)
            formatted.append(result)

        # Track access for memory health
        if results.get("ids"):
            try:
                coll.track_access(results["ids"])
            except Exception:
                pass  # Non-blocking

        return {
            "success": True,
            "collection": collection,
            "query": query,
            "count": len(formatted),
            "results": formatted
        }

    except Exception as e:
        logger.error(f"vector_search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


def vector_delete(
    collection: str,
    ids: List[str]
) -> Dict[str, Any]:
    """
    Delete documents from a vector collection.

    Args:
        collection: Name of the collection
        ids: List of document IDs to delete

    Returns:
        Dict with success status and count of deleted documents
    """
    try:
        db = _get_db()
        coll = db.get_or_create_collection(collection)

        coll.delete(ids=ids)

        return {
            "success": True,
            "collection": collection,
            "deleted_count": len(ids),
            "deleted_ids": ids
        }

    except Exception as e:
        logger.error(f"vector_delete failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def vector_list_collections() -> Dict[str, Any]:
    """
    List all vector collections in the database.

    Returns:
        Dict with list of collection names and their document counts
    """
    try:
        db = _get_db()
        names = db.list_collections()

        collections = []
        for name in names:
            stats = db.get_collection_stats(name)
            collections.append({
                "name": name,
                "count": stats.get("count", 0)
            })

        return {
            "success": True,
            "count": len(collections),
            "collections": collections
        }

    except Exception as e:
        logger.error(f"vector_list_collections failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "collections": []
        }


def vector_get_stats(collection: str) -> Dict[str, Any]:
    """
    Get statistics for a vector collection.

    Args:
        collection: Name of the collection

    Returns:
        Dict with collection stats (count, model, dimension)
    """
    try:
        db = _get_db()
        stats = db.get_collection_stats(collection)

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"vector_get_stats failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# Knowledge Base Tools (Higher-level abstraction)
# =============================================================================

def vector_add_knowledge(
    content: str,
    category: str = "general",
    tags: Optional[List[str]] = None,
    source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add knowledge to the knowledge base for later retrieval.

    This is a higher-level tool for storing facts, preferences, and
    information that should be remembered across conversations.

    Args:
        content: The knowledge content to store
        category: Category - one of: general, technical, preferences, project, facts
        tags: Optional list of tags for filtering
        source: Optional source attribution

    Returns:
        Dict with success status and knowledge ID
    """
    try:
        # Validate category
        if category not in KNOWLEDGE_CATEGORIES:
            return {
                "success": False,
                "error": f"Invalid category. Must be one of: {KNOWLEDGE_CATEGORIES}"
            }

        # Build metadata
        metadata = {
            "category": category,
            "tags": json.dumps(tags or []),  # ChromaDB needs string
            "source": source or "user",
            "added_at": datetime.now().isoformat()
        }

        # Generate meaningful ID
        knowledge_id = f"kb_{category}_{datetime.now().timestamp()}"

        # Add to knowledge collection
        result = vector_add(
            collection=KNOWLEDGE_COLLECTION,
            text=content,
            metadata=metadata,
            id=knowledge_id
        )

        if result["success"]:
            return {
                "success": True,
                "id": knowledge_id,
                "category": category,
                "message": f"Knowledge added to '{category}' category"
            }
        else:
            return result

    except Exception as e:
        logger.error(f"vector_add_knowledge failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def vector_search_knowledge(
    query: str,
    category: Optional[str] = None,
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Search the knowledge base for relevant information.

    Args:
        query: Search query
        category: Optional category filter (general, technical, preferences, project, facts)
        n_results: Maximum results to return (default: 5)

    Returns:
        Dict with matching knowledge entries
    """
    try:
        # Build filter if category specified
        filter_dict = None
        if category:
            if category not in KNOWLEDGE_CATEGORIES:
                return {
                    "success": False,
                    "error": f"Invalid category. Must be one of: {KNOWLEDGE_CATEGORIES}"
                }
            filter_dict = {"category": category}

        # Search knowledge base
        result = vector_search(
            collection=KNOWLEDGE_COLLECTION,
            query=query,
            n_results=n_results,
            filter=filter_dict
        )

        # Format for knowledge-specific response
        if result["success"]:
            knowledge = []
            for item in result["results"]:
                meta = item.get("metadata", {})
                # Parse tags back from JSON string
                tags = []
                if meta.get("tags"):
                    try:
                        tags = json.loads(meta["tags"])
                    except:
                        pass

                knowledge.append({
                    "id": item["id"],
                    "content": item["text"],
                    "category": meta.get("category", "general"),
                    "tags": tags,
                    "source": meta.get("source"),
                    "similarity": item.get("similarity")
                })

            return {
                "success": True,
                "query": query,
                "category_filter": category,
                "count": len(knowledge),
                "knowledge": knowledge
            }
        else:
            return result

    except Exception as e:
        logger.error(f"vector_search_knowledge failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "knowledge": []
        }


# =============================================================================
# Tool Schemas for LLM Integration
# =============================================================================

VECTOR_TOOL_SCHEMAS = {
    "vector_add": {
        "name": "vector_add",
        "description": "Add a document to a vector collection for semantic search. Use this to store text that should be searchable by meaning.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Name of the collection to add to"
                },
                "text": {
                    "type": "string",
                    "description": "The text content to store"
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata (e.g., {\"source\": \"user\", \"type\": \"note\"})"
                },
                "id": {
                    "type": "string",
                    "description": "Optional document ID (auto-generated if not provided)"
                }
            },
            "required": ["collection", "text"]
        }
    },
    "vector_search": {
        "name": "vector_search",
        "description": "Search a vector collection for semantically similar documents. Returns documents ranked by similarity to the query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Name of the collection to search"
                },
                "query": {
                    "type": "string",
                    "description": "Search query text"
                },
                "n_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)"
                },
                "filter": {
                    "type": "object",
                    "description": "Optional metadata filter"
                }
            },
            "required": ["collection", "query"]
        }
    },
    "vector_delete": {
        "name": "vector_delete",
        "description": "Delete documents from a vector collection by their IDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Name of the collection"
                },
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of document IDs to delete"
                }
            },
            "required": ["collection", "ids"]
        }
    },
    "vector_list_collections": {
        "name": "vector_list_collections",
        "description": "List all vector collections in the database with their document counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "vector_get_stats": {
        "name": "vector_get_stats",
        "description": "Get statistics for a vector collection (document count, embedding model, dimension).",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Name of the collection"
                }
            },
            "required": ["collection"]
        }
    },
    "vector_add_knowledge": {
        "name": "vector_add_knowledge",
        "description": "Add knowledge to the knowledge base. Use this to store facts, preferences, or information to remember. Categories: general, technical, preferences, project, facts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The knowledge content to store"
                },
                "category": {
                    "type": "string",
                    "description": "Category: general, technical, preferences, project, or facts",
                    "enum": ["general", "technical", "preferences", "project", "facts"]
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for filtering"
                },
                "source": {
                    "type": "string",
                    "description": "Optional source attribution"
                }
            },
            "required": ["content"]
        }
    },
    "vector_search_knowledge": {
        "name": "vector_search_knowledge",
        "description": "Search the knowledge base for relevant information. Use this to recall stored facts, preferences, or project details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter",
                    "enum": ["general", "technical", "preferences", "project", "facts"]
                },
                "n_results": {
                    "type": "integer",
                    "description": "Maximum results (default: 5)"
                }
            },
            "required": ["query"]
        }
    }
}
