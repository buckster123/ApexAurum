"""
Vector Database Engine for Semantic Search

Provides ChromaDB wrapper and embedding generation using sentence-transformers.
Backend-agnostic infrastructure for semantic search capabilities.

Key Features:
- Lazy loading (only initializes when needed)
- Multiple collection support
- Batch embedding for performance
- Disk persistence
- Access tracking for memory health
- Error handling and fallbacks

Requirements:
    pip install chromadb sentence-transformers numpy

Usage:
    from reusable_lib.vector import VectorDB, create_vector_db

    # Initialize
    db = VectorDB(persist_directory="./data/vector_db")

    # Get collection
    collection = db.get_or_create_collection("documents")

    # Add documents
    collection.add(
        texts=["Hello world", "AI is amazing"],
        metadatas=[{"source": "test"}, {"source": "test"}],
        ids=["doc1", "doc2"]
    )

    # Search
    results = collection.query("greeting", n_results=5)

    # Track access (for memory health analytics)
    collection.track_access(["doc1", "doc2"])
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

# Optional numpy import with fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


class VectorDBError(Exception):
    """Base exception for vector DB operations."""
    pass


class EmbeddingGenerator:
    """
    Handle text embeddings using sentence-transformers.

    Supports multiple models with different quality/speed tradeoffs:
    - all-MiniLM-L6-v2: Fast, 384 dims, 90MB (recommended)
    - all-MiniLM-L12-v2: Better, 384 dims, 134MB
    - all-mpnet-base-v2: Best, 768 dims, 438MB
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding generator.

        Args:
            model_name: Sentence-transformers model name
        """
        self.model_name = model_name
        self._model = None
        self._model_loaded = False

    def _load_model(self):
        """Lazy load the embedding model."""
        if self._model_loaded:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            self._model_loaded = True
            logger.info(f"Model loaded successfully: {self.model_name}")

        except ImportError:
            raise VectorDBError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {e}")
            raise VectorDBError(f"Failed to load model: {e}")

    def encode(self, texts: Union[str, List[str]], show_progress: bool = False) -> Any:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text or list of texts
            show_progress: Show progress bar for batch encoding

        Returns:
            Numpy array of embeddings (or list if numpy unavailable)
        """
        self._load_model()

        try:
            # Convert single text to list
            if isinstance(texts, str):
                texts = [texts]

            # Generate embeddings
            embeddings = self._model.encode(
                texts,
                show_progress_bar=show_progress,
                convert_to_numpy=HAS_NUMPY
            )

            return embeddings

        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            raise VectorDBError(f"Encoding failed: {e}")

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """
        Generate embeddings in batches for better performance.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch
            progress_callback: Optional callback(current, total)

        Returns:
            List of embedding arrays
        """
        self._load_model()

        embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.encode(batch, show_progress=False)
            embeddings.extend(batch_embeddings)

            if progress_callback:
                progress_callback(min(i + batch_size, total), total)

        return embeddings

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()


class VectorCollection:
    """
    Wrapper for ChromaDB collection operations.

    Provides a clean interface for adding, querying, and managing documents
    in a ChromaDB collection with automatic access tracking.
    """

    def __init__(self, collection: Any, embedding_generator: EmbeddingGenerator):
        """
        Initialize collection wrapper.

        Args:
            collection: ChromaDB collection object
            embedding_generator: EmbeddingGenerator instance
        """
        self.collection = collection
        self.embedding_generator = embedding_generator
        self.name = collection.name

    def add(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        Add documents to collection with enhanced metadata.

        Enhanced metadata includes:
        - access_count: Track how often this memory is accessed
        - last_accessed_ts: Unix timestamp of last access
        - related_memories: JSON string of related memory IDs
        - embedding_version: Track which embedding model was used

        Args:
            texts: List of text documents
            metadatas: Optional list of metadata dicts
            ids: Optional list of document IDs (auto-generated if not provided)

        Returns:
            True if successful
        """
        try:
            # Generate IDs if not provided
            if ids is None:
                ids = [f"{self.name}_{i}_{datetime.now().timestamp()}"
                       for i in range(len(texts))]

            # Validate inputs
            if len(texts) != len(ids):
                raise ValueError("texts and ids must have same length")

            if metadatas and len(metadatas) != len(texts):
                raise ValueError("metadatas must match texts length")

            # Enhance metadata with tracking fields
            if metadatas is None:
                metadatas = [{} for _ in range(len(texts))]

            current_time = datetime.now()
            current_ts = current_time.timestamp()

            for metadata in metadatas:
                # Add new fields with defaults (only if not already present)
                if "access_count" not in metadata:
                    metadata["access_count"] = 0
                if "last_accessed_ts" not in metadata:
                    metadata["last_accessed_ts"] = current_ts
                if "related_memories" not in metadata:
                    # ChromaDB only accepts str/int/float/bool, so store as JSON string
                    metadata["related_memories"] = "[]"
                if "embedding_version" not in metadata:
                    metadata["embedding_version"] = self.embedding_generator.model_name

            # Generate embeddings
            embeddings = self.embedding_generator.encode(texts)

            # Ensure embeddings are 2D (batch, dimension)
            if HAS_NUMPY and hasattr(embeddings, 'ndim'):
                if embeddings.ndim == 1:
                    embeddings = embeddings.reshape(1, -1)
                embeddings = embeddings.tolist()

            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(texts)} documents to {self.name}")
            return True

        except Exception as e:
            logger.error(f"Error adding documents to {self.name}: {e}")
            raise VectorDBError(f"Failed to add documents: {e}")

    def query(
        self,
        query_text: str,
        n_results: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        include_distances: bool = True
    ) -> Dict[str, Any]:
        """
        Query collection for similar documents.

        Args:
            query_text: Query text
            n_results: Number of results to return
            filter: Optional metadata filter
            include_distances: Include similarity distances

        Returns:
            Query results dict with ids, documents, metadatas, distances
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_generator.encode(query_text)

            # Ensure embedding is 1D array, then convert to list
            if HAS_NUMPY and hasattr(query_embedding, 'ndim'):
                if query_embedding.ndim > 1:
                    query_embedding = query_embedding.flatten()
                query_embedding = query_embedding.tolist()

            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter,
                include=["documents", "metadatas", "distances"]
            )

            # Flatten results (ChromaDB returns nested lists)
            flattened = {
                "ids": results["ids"][0] if results["ids"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            }

            if include_distances and "distances" in results:
                flattened["distances"] = results["distances"][0]

            logger.info(f"Query returned {len(flattened['ids'])} results from {self.name}")
            return flattened

        except Exception as e:
            logger.error(f"Error querying {self.name}: {e}")
            raise VectorDBError(f"Query failed: {e}")

    def delete(self, ids: List[str]) -> bool:
        """
        Delete documents from collection.

        Args:
            ids: List of document IDs to delete

        Returns:
            True if successful
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from {self.name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting from {self.name}: {e}")
            raise VectorDBError(f"Delete failed: {e}")

    def update(self, ids: List[str], metadatas: List[Dict[str, Any]]) -> bool:
        """
        Update document metadata.

        Args:
            ids: List of document IDs
            metadatas: List of new metadata dicts

        Returns:
            True if successful
        """
        try:
            if len(ids) != len(metadatas):
                raise ValueError("ids and metadatas must have same length")

            self.collection.update(
                ids=ids,
                metadatas=metadatas
            )

            logger.info(f"Updated {len(ids)} documents in {self.name}")
            return True

        except Exception as e:
            logger.error(f"Error updating {self.name}: {e}")
            raise VectorDBError(f"Update failed: {e}")

    def track_access(self, vector_ids: List[str]) -> bool:
        """
        Track access to vectors by incrementing access_count and updating last_accessed_ts.

        This is a non-blocking operation used for memory health analytics.
        Failure to track access will be logged but won't raise exceptions.

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
            current_ts = datetime.now().timestamp()
            updated_metadatas = []

            for metadata in docs["metadatas"]:
                metadata["access_count"] = metadata.get("access_count", 0) + 1
                metadata["last_accessed_ts"] = current_ts
                updated_metadatas.append(metadata)

            # Batch update
            self.collection.update(
                ids=docs["ids"],
                metadatas=updated_metadatas
            )

            logger.debug(f"Tracked access for {len(docs['ids'])} vectors in {self.name}")
            return True

        except Exception as e:
            # Non-blocking: log error but don't fail the operation
            logger.warning(f"Failed to track vector access in {self.name}: {e}")
            return False

    def count(self) -> int:
        """
        Get number of documents in collection.

        Returns:
            Document count
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error counting documents in {self.name}: {e}")
            return 0

    def get(self, ids: Optional[List[str]] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get documents from collection.

        Args:
            ids: Optional list of IDs to retrieve
            limit: Optional limit on results

        Returns:
            Dict with ids, documents, metadatas
        """
        try:
            results = self.collection.get(
                ids=ids,
                limit=limit,
                include=["documents", "metadatas"]
            )
            return results

        except Exception as e:
            logger.error(f"Error getting documents from {self.name}: {e}")
            raise VectorDBError(f"Get failed: {e}")


class VectorDB:
    """
    Main vector database interface using ChromaDB.

    Manages collections, embeddings, and provides high-level operations
    for semantic search functionality.
    """

    def __init__(
        self,
        persist_directory: str = "./data/vector_db",
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize vector database.

        Args:
            persist_directory: Directory for persistent storage
            model_name: Sentence-transformers model name
        """
        self.persist_directory = Path(persist_directory)
        self.model_name = model_name

        self._client = None
        self._initialized = False
        self.embedding_generator = EmbeddingGenerator(model_name)

        # Ensure persist directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)

    def _initialize(self):
        """Lazy initialization of ChromaDB client."""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            logger.info(f"Initializing ChromaDB at {self.persist_directory}")

            # Create ChromaDB client with persistence
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            self._initialized = True
            logger.info("ChromaDB initialized successfully")

        except ImportError:
            raise VectorDBError(
                "chromadb not installed. Install with: pip install chromadb"
            )
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise VectorDBError(f"Initialization failed: {e}")

    def get_or_create_collection(self, name: str) -> VectorCollection:
        """
        Get existing collection or create new one.

        Args:
            name: Collection name

        Returns:
            VectorCollection instance
        """
        self._initialize()

        try:
            # Get or create collection
            collection = self._client.get_or_create_collection(
                name=name,
                metadata={"created_at": datetime.now().isoformat()}
            )

            logger.info(f"Got/created collection: {name}")
            return VectorCollection(collection, self.embedding_generator)

        except Exception as e:
            logger.error(f"Error getting/creating collection {name}: {e}")
            raise VectorDBError(f"Collection operation failed: {e}")

    def list_collections(self) -> List[str]:
        """
        List all collection names.

        Returns:
            List of collection names
        """
        self._initialize()

        try:
            collections = self._client.list_collections()
            names = [c.name for c in collections]
            logger.info(f"Found {len(names)} collections")
            return names

        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []

    def delete_collection(self, name: str) -> bool:
        """
        Delete a collection.

        Args:
            name: Collection name to delete

        Returns:
            True if successful
        """
        self._initialize()

        try:
            self._client.delete_collection(name)
            logger.info(f"Deleted collection: {name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting collection {name}: {e}")
            return False

    def get_collection_stats(self, name: str) -> Dict[str, Any]:
        """
        Get statistics for a collection.

        Args:
            name: Collection name

        Returns:
            Stats dict with count, metadata, etc.
        """
        try:
            collection = self.get_or_create_collection(name)
            count = collection.count()

            return {
                "name": name,
                "count": count,
                "model": self.model_name,
                "dimension": self.embedding_generator.dimension
            }

        except Exception as e:
            logger.error(f"Error getting stats for {name}: {e}")
            return {"name": name, "error": str(e)}

    def reset(self):
        """Reset database (delete all collections) - USE WITH CAUTION."""
        self._initialize()

        try:
            self._client.reset()
            logger.warning("Vector database reset - all collections deleted")
            return True
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized

    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.embedding_generator.dimension


# Convenience function
def create_vector_db(
    persist_directory: str = "./data/vector_db",
    model_name: str = "all-MiniLM-L6-v2"
) -> VectorDB:
    """
    Create a VectorDB instance with standard settings.

    Args:
        persist_directory: Storage directory
        model_name: Embedding model

    Returns:
        VectorDB instance
    """
    return VectorDB(persist_directory, model_name)


def test_vector_db() -> bool:
    """
    Test vector database functionality.

    Returns:
        True if all tests pass
    """
    import tempfile

    try:
        logger.info("Testing vector database...")

        # Create test instance in temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            db = create_vector_db(f"{tmpdir}/test_vector_db")

            # Create collection
            collection = db.get_or_create_collection("test")

            # Add test documents
            collection.add(
                texts=["Hello world", "AI is amazing", "Vector search is powerful"],
                metadatas=[
                    {"type": "greeting"},
                    {"type": "statement"},
                    {"type": "statement"}
                ],
                ids=["test1", "test2", "test3"]
            )

            # Query
            results = collection.query("greeting", n_results=2)

            # Verify results
            assert len(results["ids"]) > 0, "No results returned"
            assert results["ids"][0] == "test1", "Wrong result returned"

            # Count
            count = collection.count()
            assert count == 3, f"Expected 3 documents, got {count}"

            # Track access
            collection.track_access(["test1"])
            doc = collection.get(ids=["test1"])
            assert doc["metadatas"][0]["access_count"] == 1, "Access tracking failed"

            # Delete
            collection.delete(["test1"])
            assert collection.count() == 2, "Delete failed"

            # Clean up
            db.delete_collection("test")

        logger.info("All vector database tests passed!")
        return True

    except Exception as e:
        logger.error(f"Vector database test failed: {e}")
        return False


if __name__ == "__main__":
    # Run tests if executed directly
    logging.basicConfig(level=logging.INFO)
    test_vector_db()
