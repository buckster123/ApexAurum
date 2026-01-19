"""
Memory Service

Handles key-value memory and vector storage.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional

# Import from reusable_lib
import sys
from pathlib import Path

lib_path = Path(__file__).parent.parent.parent.parent
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from reusable_lib.tools.memory import SimpleMemory, set_memory_path

from app_config import settings

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for memory operations.

    Provides both key-value storage and vector search.
    """

    def __init__(self):
        """Initialize memory service."""
        # Set up key-value memory
        set_memory_path(settings.MEMORY_FILE)
        self.kv_memory = SimpleMemory(storage_file=settings.MEMORY_FILE)

        # Vector DB (lazy loaded)
        self._vector_db = None

    @property
    def vector_db(self):
        """Lazy load vector database."""
        if self._vector_db is None:
            try:
                from reusable_lib.vector import VectorDB
                self._vector_db = VectorDB(
                    persist_directory=str(settings.VECTOR_DIR)
                )
                logger.info(f"Initialized vector DB at {settings.VECTOR_DIR}")
            except ImportError:
                logger.warning("Vector DB not available (install chromadb, sentence-transformers)")
                raise ImportError("Vector DB requires: pip install chromadb sentence-transformers")
        return self._vector_db

    # === Key-Value Memory ===

    def store(self, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        """Store a key-value pair."""
        return self.kv_memory.store(key, value, metadata)

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        result = self.kv_memory.retrieve(key)
        return result.get("value") if result else None

    def delete(self, key: str) -> bool:
        """Delete a key."""
        return self.kv_memory.delete(key)

    def list_all(self) -> List[Dict]:
        """List all memories."""
        result = self.kv_memory.list_keys()
        return result.get("keys", [])

    def search(self, pattern: str, limit: int = 10) -> List[Dict]:
        """Search memories by key pattern."""
        result = self.kv_memory.search(pattern, limit)
        return result.get("results", [])

    # === Vector Memory ===

    def list_vector_collections(self) -> List[str]:
        """List all vector collections."""
        try:
            return self.vector_db.list_collections()
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []

    def vector_add(
        self,
        collection: str,
        text: str,
        metadata: Optional[Dict] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """Add a document to a vector collection."""
        coll = self.vector_db.get_or_create_collection(collection)

        doc_id = doc_id or str(uuid.uuid4())[:8]
        metadata = metadata or {}

        coll.add(
            texts=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )

        return doc_id

    def vector_search(
        self,
        collection: str,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """Search a vector collection."""
        coll = self.vector_db.get_or_create_collection(collection)

        results = coll.query(query, n_results=limit)

        # Format results
        formatted = []
        if results.get("ids"):
            for i, doc_id in enumerate(results["ids"]):
                formatted.append({
                    "id": doc_id,
                    "text": results["documents"][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                    "distance": results["distances"][i] if results.get("distances") else 0
                })

        return formatted

    def vector_delete(self, collection: str, doc_id: str) -> bool:
        """Delete a document from a vector collection."""
        coll = self.vector_db.get_or_create_collection(collection)
        coll.delete(ids=[doc_id])
        return True

    def vector_stats(self, collection: str) -> Dict:
        """Get statistics for a collection."""
        coll = self.vector_db.get_or_create_collection(collection)
        return {
            "collection": collection,
            "count": coll.count()
        }
