# Vector - ChromaDB wrapper and semantic search infrastructure
# Extracted from ApexAurum - Claude Edition

from .vector_db import (
    VectorDB,
    VectorCollection,
    VectorDBError,
    EmbeddingGenerator,
    create_vector_db,
    test_vector_db,
)

from .memory_health import (
    MemoryHealth,
    get_stale_memories,
    get_low_access_memories,
    get_duplicate_candidates,
    consolidate_memories,
)

__all__ = [
    # Core classes
    'VectorDB',
    'VectorCollection',
    'VectorDBError',
    'EmbeddingGenerator',
    # Convenience functions
    'create_vector_db',
    'test_vector_db',
    # Memory health
    'MemoryHealth',
    'get_stale_memories',
    'get_low_access_memories',
    'get_duplicate_candidates',
    'consolidate_memories',
]
