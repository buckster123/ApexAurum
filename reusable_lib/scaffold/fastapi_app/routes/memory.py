"""
Memory Routes

Key-value memory storage and vector search endpoints.
"""

import logging
from typing import Optional, List, Any
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from services.memory_service import MemoryService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize memory service
memory_service = MemoryService()


class MemoryStoreRequest(BaseModel):
    """Request to store a memory."""
    key: str
    value: Any
    metadata: Optional[dict] = None


class MemorySearchRequest(BaseModel):
    """Request to search memories."""
    query: str
    limit: int = 5


class VectorAddRequest(BaseModel):
    """Request to add to vector store."""
    collection: str
    text: str
    metadata: Optional[dict] = None
    id: Optional[str] = None


class VectorSearchRequest(BaseModel):
    """Request to search vector store."""
    collection: str
    query: str
    limit: int = 5


# === Key-Value Memory ===

@router.get("/kv")
async def list_memories():
    """List all stored key-value memories."""
    return {
        "memories": memory_service.list_all(),
        "count": len(memory_service.list_all())
    }


@router.get("/kv/{key}")
async def get_memory(key: str):
    """Get a specific memory by key."""
    result = memory_service.get(key)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Memory not found: {key}")
    return {"key": key, "value": result}


@router.post("/kv")
async def store_memory(request: MemoryStoreRequest):
    """Store a key-value memory."""
    memory_service.store(request.key, request.value, request.metadata)
    return {"message": f"Stored memory: {request.key}", "key": request.key}


@router.delete("/kv/{key}")
async def delete_memory(key: str):
    """Delete a memory by key."""
    success = memory_service.delete(key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Memory not found: {key}")
    return {"message": f"Deleted memory: {key}"}


@router.post("/kv/search")
async def search_memories(request: MemorySearchRequest):
    """Search memories by key pattern."""
    results = memory_service.search(request.query, request.limit)
    return {"results": results, "count": len(results)}


# === Vector Memory ===

@router.get("/vector/collections")
async def list_collections():
    """List all vector collections."""
    collections = memory_service.list_vector_collections()
    return {"collections": collections}


@router.post("/vector/add")
async def add_to_vector(request: VectorAddRequest):
    """Add a document to a vector collection."""
    try:
        doc_id = memory_service.vector_add(
            collection=request.collection,
            text=request.text,
            metadata=request.metadata,
            doc_id=request.id
        )
        return {"message": "Document added", "id": doc_id, "collection": request.collection}
    except Exception as e:
        logger.error(f"Vector add error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vector/search")
async def search_vector(request: VectorSearchRequest):
    """Search a vector collection."""
    try:
        results = memory_service.vector_search(
            collection=request.collection,
            query=request.query,
            limit=request.limit
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Vector search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector/{collection}/stats")
async def get_collection_stats(collection: str):
    """Get statistics for a vector collection."""
    try:
        stats = memory_service.vector_stats(collection)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vector/{collection}/{doc_id}")
async def delete_from_vector(collection: str, doc_id: str):
    """Delete a document from a vector collection."""
    try:
        memory_service.vector_delete(collection, doc_id)
        return {"message": f"Deleted {doc_id} from {collection}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
