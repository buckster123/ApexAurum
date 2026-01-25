"""
User Endpoints

User profile and settings.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.auth.deps import get_current_user

router = APIRouter()


# Schemas
class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    created_at: str
    settings: dict

    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    settings: Optional[dict] = None


class UsageResponse(BaseModel):
    total_messages: int
    total_tokens: int
    total_cost_usd: float
    conversations_count: int
    agents_spawned: int
    music_generated: int


# Endpoints
@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    user: User = Depends(get_current_user),
):
    """Get current user's profile."""
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at.isoformat(),
        settings=user.settings,
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    request: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    if request.display_name is not None:
        user.display_name = request.display_name

    if request.settings is not None:
        # Merge settings (don't replace entirely)
        current_settings = user.settings or {}
        current_settings.update(request.settings)
        user.settings = current_settings

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at.isoformat(),
        settings=user.settings,
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's usage statistics."""
    from sqlalchemy import func, select
    from app.models.conversation import Conversation, Message
    from app.models.agent import Agent
    from app.models.music import MusicTask

    # Count conversations
    conv_result = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.user_id == user.id)
    )
    conversations_count = conv_result.scalar() or 0

    # Count messages and sum tokens/cost
    msg_result = await db.execute(
        select(
            func.count(Message.id),
            func.coalesce(func.sum(Message.tokens_used), 0),
            func.coalesce(func.sum(Message.cost_usd), 0)
        )
        .join(Conversation)
        .where(Conversation.user_id == user.id)
    )
    msg_stats = msg_result.one()
    total_messages = msg_stats[0] or 0
    total_tokens = msg_stats[1] or 0
    total_cost = float(msg_stats[2] or 0)

    # Count agents
    agent_result = await db.execute(
        select(func.count(Agent.id))
        .where(Agent.user_id == user.id)
    )
    agents_spawned = agent_result.scalar() or 0

    # Count music tasks
    music_result = await db.execute(
        select(func.count(MusicTask.id))
        .where(MusicTask.user_id == user.id)
    )
    music_generated = music_result.scalar() or 0

    return UsageResponse(
        total_messages=total_messages,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        conversations_count=conversations_count,
        agents_spawned=agents_spawned,
        music_generated=music_generated,
    )


@router.get("/preferences")
async def get_preferences(
    user: User = Depends(get_current_user),
):
    """Get user preferences (subset of settings)."""
    settings = user.settings or {}
    return {
        "default_model": settings.get("default_model", "claude-3-haiku-20240307"),
        "cache_strategy": settings.get("cache_strategy", "balanced"),
        "context_strategy": settings.get("context_strategy", "adaptive"),
        "theme": settings.get("theme", "dark"),
        "default_agent": settings.get("default_agent", "AZOTH"),
    }


@router.put("/preferences")
async def update_preferences(
    preferences: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user preferences."""
    current_settings = user.settings or {}
    current_settings.update(preferences)
    user.settings = current_settings

    return {"message": "Preferences updated"}
