"""
Agent Endpoints

Background agent management and Socratic council.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.agent import Agent
from app.auth.deps import get_current_user

router = APIRouter()


# Schemas
class AgentSpawnRequest(BaseModel):
    task: str
    agent_type: str = "general"  # 'general', 'researcher', 'coder', 'analyst', 'writer'


class AgentResponse(BaseModel):
    id: UUID
    agent_type: str
    task: str
    status: str
    result: Optional[str]
    error: Optional[str]
    created_at: str
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class CouncilRequest(BaseModel):
    question: str
    num_agents: int = 3
    agent_types: list[str] = ["general", "researcher", "coder"]
    options: Optional[list[str]] = None


class CouncilResponse(BaseModel):
    question: str
    votes: dict[str, int]
    reasoning: dict[str, str]
    consensus: Optional[str]
    agents: list[AgentResponse]


# Endpoints
@router.post("/spawn", response_model=AgentResponse)
async def spawn_agent(
    request: AgentSpawnRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Spawn a new background agent.

    Agent types:
    - general: General-purpose assistant
    - researcher: Deep research and analysis
    - coder: Code generation and review
    - analyst: Data analysis and insights
    - writer: Content creation and editing
    """
    # Create agent record
    agent = Agent(
        user_id=user.id,
        agent_type=request.agent_type,
        task=request.task,
        status="pending",
    )
    db.add(agent)
    await db.flush()

    # TODO: Dispatch to background worker (ARQ/Celery)
    # worker.enqueue(run_agent, agent_id=agent.id)

    return AgentResponse(
        id=agent.id,
        agent_type=agent.agent_type,
        task=agent.task,
        status=agent.status,
        result=agent.result,
        error=agent.error,
        created_at=agent.created_at.isoformat(),
        completed_at=agent.completed_at.isoformat() if agent.completed_at else None,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent status and result."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.user_id == user.id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    return AgentResponse(
        id=agent.id,
        agent_type=agent.agent_type,
        task=agent.task,
        status=agent.status,
        result=agent.result,
        error=agent.error,
        created_at=agent.created_at.isoformat(),
        completed_at=agent.completed_at.isoformat() if agent.completed_at else None,
    )


@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    limit: int = 20,
    status_filter: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's agents."""
    query = select(Agent).where(Agent.user_id == user.id)

    if status_filter:
        query = query.where(Agent.status == status_filter)

    query = query.order_by(Agent.created_at.desc()).limit(limit)

    result = await db.execute(query)
    agents = result.scalars().all()

    return [
        AgentResponse(
            id=a.id,
            agent_type=a.agent_type,
            task=a.task,
            status=a.status,
            result=a.result,
            error=a.error,
            created_at=a.created_at.isoformat(),
            completed_at=a.completed_at.isoformat() if a.completed_at else None,
        )
        for a in agents
    ]


@router.post("/council", response_model=CouncilResponse)
async def socratic_council(
    request: CouncilRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run a Socratic council with multiple agents.

    Each agent independently considers the question and votes.
    Returns consensus if majority agreement.
    """
    # TODO: Implement parallel agent execution
    # TODO: Collect votes and reasoning
    # TODO: Detect consensus

    # Placeholder response
    return CouncilResponse(
        question=request.question,
        votes={"Option A": 2, "Option B": 1},
        reasoning={
            "agent_1": "I vote for Option A because...",
            "agent_2": "I vote for Option A because...",
            "agent_3": "I vote for Option B because...",
        },
        consensus="Option A",
        agents=[],
    )
