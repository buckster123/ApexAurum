"""
Conversation Routes

CRUD operations for conversation management.
Includes search and export functionality.
"""

import json
import logging
from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from services.conversation_service import get_conversation_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class MessageModel(BaseModel):
    """A chat message."""
    role: str
    content: str


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    messages: Optional[List[MessageModel]] = None
    title: Optional[str] = None
    tags: Optional[List[str]] = None


class UpdateConversationRequest(BaseModel):
    """Request to update a conversation."""
    messages: Optional[List[MessageModel]] = None
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    favorite: Optional[bool] = None
    archived: Optional[bool] = None


class AddMessageRequest(BaseModel):
    """Request to add a message to a conversation."""
    role: str
    content: str


class ImportRequest(BaseModel):
    """Request to import conversations."""
    conversations: List[dict]


# =============================================================================
# Routes
# =============================================================================

@router.get("")
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_archived: bool = Query(False),
    favorites_only: bool = Query(False),
    tag: Optional[str] = Query(None)
):
    """
    List conversations with pagination and filtering.

    - **limit**: Max conversations to return (1-100)
    - **offset**: Number to skip for pagination
    - **include_archived**: Include archived conversations
    - **favorites_only**: Only return favorites
    - **tag**: Filter by tag
    """
    service = get_conversation_service()
    return service.list(
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        favorites_only=favorites_only,
        tag=tag
    )


@router.get("/search")
async def search_conversations(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search conversations by content.

    Searches titles and message content.

    - **q**: Search query
    - **limit**: Max results to return
    """
    service = get_conversation_service()
    return service.search(query=q, limit=limit)


@router.get("/stats")
async def get_stats():
    """Get conversation statistics."""
    service = get_conversation_service()
    return service.get_stats()


@router.get("/export/all")
async def export_all():
    """
    Export all conversations as JSON.

    Returns all conversations for backup/migration.
    """
    service = get_conversation_service()
    return json.loads(service.export_all())


@router.post("/import")
async def import_conversations(request: ImportRequest):
    """
    Import conversations from JSON.

    Skips conversations that already exist (by ID).
    """
    service = get_conversation_service()
    return service.import_conversations(request.conversations)


@router.post("")
async def create_conversation(request: CreateConversationRequest):
    """
    Create a new conversation.

    - **messages**: Optional initial messages
    - **title**: Optional title (auto-generated from first message if not provided)
    - **tags**: Optional tags
    """
    service = get_conversation_service()

    messages = None
    if request.messages:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

    conv = service.create(
        messages=messages,
        title=request.title,
        tags=request.tags
    )
    return conv


@router.get("/{conv_id}")
async def get_conversation(conv_id: str):
    """Get a specific conversation by ID."""
    service = get_conversation_service()
    conv = service.get(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.put("/{conv_id}")
async def update_conversation(conv_id: str, request: UpdateConversationRequest):
    """
    Update a conversation.

    All fields are optional - only provided fields are updated.
    """
    service = get_conversation_service()

    messages = None
    if request.messages:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

    conv = service.update(
        conv_id=conv_id,
        messages=messages,
        title=request.title,
        tags=request.tags,
        favorite=request.favorite,
        archived=request.archived
    )

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    service = get_conversation_service()
    if not service.delete(conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "deleted": conv_id}


@router.post("/{conv_id}/messages")
async def add_message(conv_id: str, request: AddMessageRequest):
    """Add a message to a conversation."""
    service = get_conversation_service()
    conv = service.add_message(
        conv_id=conv_id,
        message={"role": request.role, "content": request.content}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/{conv_id}/favorite")
async def toggle_favorite(conv_id: str):
    """Toggle favorite status of a conversation."""
    service = get_conversation_service()
    conv = service.get(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_status = not conv.get("favorite", False)
    updated = service.update(conv_id, favorite=new_status)
    return {"favorite": new_status, "conversation_id": conv_id}


@router.post("/{conv_id}/archive")
async def toggle_archive(conv_id: str):
    """Toggle archived status of a conversation."""
    service = get_conversation_service()
    conv = service.get(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_status = not conv.get("archived", False)
    updated = service.update(conv_id, archived=new_status)
    return {"archived": new_status, "conversation_id": conv_id}


@router.get("/{conv_id}/export/json")
async def export_json(conv_id: str):
    """Export conversation as JSON."""
    service = get_conversation_service()
    result = service.export_json(conv_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return json.loads(result)


@router.get("/{conv_id}/export/markdown", response_class=PlainTextResponse)
async def export_markdown(conv_id: str):
    """Export conversation as Markdown."""
    service = get_conversation_service()
    result = service.export_markdown(conv_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result
