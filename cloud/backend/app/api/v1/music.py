"""
Music Endpoints

AI music generation via Suno.
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
from app.models.music import MusicTask
from app.auth.deps import get_current_user

router = APIRouter()


# Schemas
class MusicGenerateRequest(BaseModel):
    prompt: str
    style: Optional[str] = None
    title: Optional[str] = None
    model: str = "V5"  # V3_5, V4, V4_5, V5
    instrumental: bool = False


class MusicTaskResponse(BaseModel):
    id: UUID
    prompt: str
    style: Optional[str]
    title: Optional[str]
    status: str
    file_path: Optional[str]
    error: Optional[str]
    favorite: bool
    play_count: int
    agent_id: Optional[str]
    created_at: str
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class MusicLibraryResponse(BaseModel):
    tasks: list[MusicTaskResponse]
    total: int


# Endpoints
@router.post("/generate", response_model=MusicTaskResponse)
async def generate_music(
    request: MusicGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate music using Suno AI.

    Models:
    - V3_5: Fast, lower quality
    - V4: Balanced
    - V4_5: Better quality
    - V5: Best quality (recommended)
    """
    # Create task record
    task = MusicTask(
        user_id=user.id,
        prompt=request.prompt,
        style=request.style,
        title=request.title,
        status="pending",
    )
    db.add(task)
    await db.flush()

    # TODO: Dispatch to Suno API via background worker
    # worker.enqueue(generate_suno_music, task_id=task.id, model=request.model)

    return MusicTaskResponse(
        id=task.id,
        prompt=task.prompt,
        style=task.style,
        title=task.title,
        status=task.status,
        file_path=task.file_path,
        error=task.error,
        favorite=task.favorite,
        play_count=task.play_count,
        agent_id=task.agent_id,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@router.get("/{task_id}", response_model=MusicTaskResponse)
async def get_music_task(
    task_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get music task status and details."""
    result = await db.execute(
        select(MusicTask)
        .where(MusicTask.id == task_id)
        .where(MusicTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Music task not found"
        )

    return MusicTaskResponse(
        id=task.id,
        prompt=task.prompt,
        style=task.style,
        title=task.title,
        status=task.status,
        file_path=task.file_path,
        error=task.error,
        favorite=task.favorite,
        play_count=task.play_count,
        agent_id=task.agent_id,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@router.get("/{task_id}/stream")
async def stream_music(
    task_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stream music file."""
    result = await db.execute(
        select(MusicTask)
        .where(MusicTask.id == task_id)
        .where(MusicTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Music task not found"
        )

    if task.status != "complete" or not task.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Music not ready for streaming"
        )

    # TODO: Stream from S3/MinIO
    # For now, return placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Streaming not yet implemented"
    )


@router.get("/library", response_model=MusicLibraryResponse)
async def get_library(
    limit: int = 50,
    offset: int = 0,
    favorites_only: bool = False,
    agent_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get music library."""
    query = select(MusicTask).where(MusicTask.user_id == user.id)

    if favorites_only:
        query = query.where(MusicTask.favorite == True)
    if agent_id:
        query = query.where(MusicTask.agent_id == agent_id)

    query = query.order_by(MusicTask.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Get total
    from sqlalchemy import func
    count_query = select(func.count(MusicTask.id)).where(MusicTask.user_id == user.id)
    if favorites_only:
        count_query = count_query.where(MusicTask.favorite == True)
    if agent_id:
        count_query = count_query.where(MusicTask.agent_id == agent_id)

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return MusicLibraryResponse(
        tasks=[
            MusicTaskResponse(
                id=t.id,
                prompt=t.prompt,
                style=t.style,
                title=t.title,
                status=t.status,
                file_path=t.file_path,
                error=t.error,
                favorite=t.favorite,
                play_count=t.play_count,
                agent_id=t.agent_id,
                created_at=t.created_at.isoformat(),
                completed_at=t.completed_at.isoformat() if t.completed_at else None,
            )
            for t in tasks
        ],
        total=total,
    )


@router.patch("/{task_id}/favorite")
async def toggle_favorite(
    task_id: UUID,
    favorite: bool,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle favorite status."""
    result = await db.execute(
        select(MusicTask)
        .where(MusicTask.id == task_id)
        .where(MusicTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Music task not found"
        )

    task.favorite = favorite
    return {"message": "Favorite status updated", "favorite": favorite}
