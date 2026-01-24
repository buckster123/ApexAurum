"""
Chat Endpoints

Core chat functionality with streaming responses and tool execution.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.auth.deps import get_current_user

router = APIRouter()


# Schemas
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None
    model: str = "claude-sonnet-4-5-20250514"
    stream: bool = True


class ConversationResponse(BaseModel):
    id: UUID
    title: Optional[str]
    created_at: str
    updated_at: str
    message_count: int
    favorite: bool
    archived: bool

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


# Endpoints
@router.post("/message")
async def send_message(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and get a response from Claude.

    If stream=True, returns Server-Sent Events (SSE) stream.
    If stream=False, returns complete response as JSON.
    """
    # TODO: Implement Claude API integration with streaming
    # TODO: Implement tool execution pipeline
    # TODO: Store messages in database

    if request.stream:
        async def stream_response():
            # Placeholder for streaming implementation
            yield "data: {\"type\": \"start\"}\n\n"
            yield "data: {\"type\": \"token\", \"content\": \"Hello from ApexAurum Cloud!\"}\n\n"
            yield "data: {\"type\": \"end\"}\n\n"

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream"
        )
    else:
        return {
            "conversation_id": request.conversation_id,
            "message": "Hello from ApexAurum Cloud!",
            "model": request.model,
        }


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    archived: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .where(Conversation.archived == archived)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = result.scalars().all()

    # Get total count
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.user_id == user.id)
        .where(Conversation.archived == archived)
    )
    total = count_result.scalar()

    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c.id,
                title=c.title,
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat(),
                message_count=len(c.messages),
                favorite=c.favorite,
                archived=c.archived,
            )
            for c in conversations
        ],
        total=total,
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == user.id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "favorite": conversation.favorite,
        "archived": conversation.archived,
        "tags": conversation.tags,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tool_calls": m.tool_calls,
                "tool_results": m.tool_results,
                "created_at": m.created_at.isoformat(),
            }
            for m in conversation.messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == user.id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    await db.delete(conversation)
    return {"message": "Conversation deleted"}


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    title: Optional[str] = None,
    favorite: Optional[bool] = None,
    archived: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update conversation metadata."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == user.id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if title is not None:
        conversation.title = title
    if favorite is not None:
        conversation.favorite = favorite
    if archived is not None:
        conversation.archived = archived

    return {"message": "Conversation updated"}
