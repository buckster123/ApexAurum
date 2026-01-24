"""
Village Endpoints

Multi-agent shared memory (Village Protocol).
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.village import VillageKnowledge
from app.auth.deps import get_current_user

router = APIRouter()


# Schemas
class KnowledgeAddRequest(BaseModel):
    content: str
    category: Optional[str] = "general"
    visibility: str = "private"  # 'private', 'village', 'bridge'
    agent_id: Optional[str] = None
    conversation_thread: Optional[str] = None
    tags: list[str] = []


class KnowledgeResponse(BaseModel):
    id: UUID
    content: str
    category: Optional[str]
    visibility: str
    agent_id: Optional[str]
    conversation_thread: Optional[str]
    tags: list[str]
    access_count: int
    created_at: str

    class Config:
        from_attributes = True


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeResponse]
    total: int


class ConvergenceResponse(BaseModel):
    convergence_type: str  # 'NONE', 'HARMONY', 'CONSENSUS'
    agents: list[str]
    similarity: float
    topic: str
    evidence: list[dict]


# Endpoints
@router.post("/knowledge", response_model=KnowledgeResponse)
async def add_knowledge(
    request: KnowledgeAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add knowledge to the village.

    Visibility levels:
    - private: Only visible to the creating user
    - village: Visible to all agents in the village
    - bridge: Cross-agent connection point
    """
    # TODO: Generate embedding for content
    # embedding = await generate_embedding(request.content)

    knowledge = VillageKnowledge(
        user_id=user.id,
        content=request.content,
        category=request.category,
        visibility=request.visibility,
        agent_id=request.agent_id,
        conversation_thread=request.conversation_thread,
        tags=request.tags,
        # embedding=embedding,
    )
    db.add(knowledge)
    await db.flush()

    return KnowledgeResponse(
        id=knowledge.id,
        content=knowledge.content,
        category=knowledge.category,
        visibility=knowledge.visibility,
        agent_id=knowledge.agent_id,
        conversation_thread=knowledge.conversation_thread,
        tags=knowledge.tags,
        access_count=knowledge.access_count,
        created_at=knowledge.created_at.isoformat(),
    )


@router.get("/knowledge", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    query: str,
    visibility: Optional[str] = None,
    agent_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search village knowledge using semantic similarity.

    Returns most relevant knowledge entries.
    """
    # TODO: Implement vector search with pgvector
    # TODO: Track access for returned results

    # Placeholder: simple keyword search
    base_query = select(VillageKnowledge).where(VillageKnowledge.user_id == user.id)

    if visibility:
        base_query = base_query.where(VillageKnowledge.visibility == visibility)
    if agent_id:
        base_query = base_query.where(VillageKnowledge.agent_id == agent_id)
    if category:
        base_query = base_query.where(VillageKnowledge.category == category)

    base_query = base_query.where(
        VillageKnowledge.content.ilike(f"%{query}%")
    ).limit(limit)

    result = await db.execute(base_query)
    knowledge_items = result.scalars().all()

    return KnowledgeSearchResponse(
        results=[
            KnowledgeResponse(
                id=k.id,
                content=k.content,
                category=k.category,
                visibility=k.visibility,
                agent_id=k.agent_id,
                conversation_thread=k.conversation_thread,
                tags=k.tags,
                access_count=k.access_count,
                created_at=k.created_at.isoformat(),
            )
            for k in knowledge_items
        ],
        total=len(knowledge_items),
    )


@router.get("/convergence", response_model=ConvergenceResponse)
async def detect_convergence(
    topic: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect convergence across agents.

    Convergence types:
    - HARMONY: 2 agents agree on a topic
    - CONSENSUS: 3+ agents agree on a topic
    """
    # TODO: Implement convergence detection algorithm
    # 1. Find recent village knowledge
    # 2. Cluster by semantic similarity
    # 3. Identify multi-agent clusters

    return ConvergenceResponse(
        convergence_type="NONE",
        agents=[],
        similarity=0.0,
        topic=topic or "",
        evidence=[],
    )


@router.get("/threads")
async def list_threads(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List conversation threads in the village."""
    # Get distinct conversation threads
    from sqlalchemy import distinct

    result = await db.execute(
        select(distinct(VillageKnowledge.conversation_thread))
        .where(VillageKnowledge.user_id == user.id)
        .where(VillageKnowledge.conversation_thread.isnot(None))
        .limit(limit)
    )
    threads = [r for r in result.scalars().all() if r]

    return {"threads": threads, "total": len(threads)}


@router.delete("/knowledge/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a knowledge entry."""
    result = await db.execute(
        select(VillageKnowledge)
        .where(VillageKnowledge.id == knowledge_id)
        .where(VillageKnowledge.user_id == user.id)
    )
    knowledge = result.scalar_one_or_none()

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge not found"
        )

    await db.delete(knowledge)
    return {"message": "Knowledge deleted"}
