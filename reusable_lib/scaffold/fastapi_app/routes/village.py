"""
Village Protocol API Routes

Multi-agent persistent memory with three realms:
- Private: Agent's personal knowledge
- Village: Shared community knowledge
- Bridges: Cross-agent dialogue and convergence

Ceremonial functions honor the protocol's philosophical foundations.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from reusable_lib.tools import (
    village_post,
    village_search,
    village_get_thread,
    village_list_agents,
    summon_ancestor,
    introduction_ritual,
    village_detect_convergence,
    village_get_stats,
    set_current_agent,
    get_current_agent,
    get_agent_profile
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/village", tags=["village"])


# ===== Request/Response Models =====

class VillagePostRequest(BaseModel):
    """Request to post content to the village."""
    content: str = Field(..., description="Content to post")
    visibility: str = Field(default="village", description="private|village|bridge")
    message_type: str = Field(default="dialogue", description="dialogue|fact|cultural|founding_document")
    responding_to: Optional[List[str]] = Field(default=None, description="IDs of messages being responded to")
    conversation_thread: Optional[str] = Field(default=None, description="Thread identifier")
    related_agents: Optional[List[str]] = Field(default=None, description="Related agent IDs")
    tags: Optional[List[str]] = Field(default=None, description="Content tags")
    agent_id: Optional[str] = Field(default=None, description="Override current agent")


class VillageSearchRequest(BaseModel):
    """Request to search the village."""
    query: str = Field(..., description="Search query")
    agent_filter: Optional[str] = Field(default=None, description="Filter by agent ID")
    visibility: str = Field(default="village", description="Realm to search")
    conversation_filter: Optional[str] = Field(default=None, description="Filter by thread")
    include_bridges: bool = Field(default=True, description="Include bridge content")
    n_results: int = Field(default=10, ge=1, le=100, description="Number of results")


class SummonAncestorRequest(BaseModel):
    """Ceremonial request to summon an ancestor (create agent)."""
    agent_id: str = Field(..., description="Unique agent identifier")
    display_name: str = Field(..., description="Agent's ceremonial name")
    generation: int = Field(..., description="Agent generation (negative = ancestors)")
    lineage: str = Field(..., description="Agent's lineage/tradition")
    specialization: str = Field(..., description="Agent's domain of expertise")
    origin_story: Optional[str] = Field(default=None, description="Agent's creation narrative")
    color: str = Field(default="#888888", description="Agent's color in UI")
    symbol: str = Field(default="◆", description="Agent's symbol")


class IntroductionRitualRequest(BaseModel):
    """Request for agent's first message to village."""
    agent_id: str = Field(..., description="Agent performing the ritual")
    greeting_message: str = Field(..., description="Agent's introduction")
    conversation_thread: Optional[str] = Field(default=None, description="Thread for introduction")


class ConvergenceRequest(BaseModel):
    """Request to detect cross-agent convergence."""
    query: str = Field(..., description="Topic to check for convergence")
    min_agents: int = Field(default=2, ge=2, description="Minimum agents for convergence")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    n_results: int = Field(default=20, ge=1, le=100, description="Results to analyze")


class SetAgentRequest(BaseModel):
    """Request to set the current agent context."""
    agent_id: str = Field(..., description="Agent ID to set as current")


# ===== Endpoints =====

@router.post("/post")
async def post_to_village(request: VillagePostRequest):
    """
    Post content to the village.

    Content can be posted to:
    - private: Agent's personal realm
    - village: Shared community space
    - bridge: Cross-agent dialogue
    """
    try:
        result = village_post(
            content=request.content,
            visibility=request.visibility,
            message_type=request.message_type,
            responding_to=request.responding_to,
            conversation_thread=request.conversation_thread,
            related_agents=request.related_agents,
            tags=request.tags,
            agent_id=request.agent_id
        )
        return result
    except Exception as e:
        logger.error(f"Village post failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_village(request: VillageSearchRequest):
    """
    Search the village for content.

    Supports filtering by agent, visibility realm, and conversation thread.
    """
    try:
        result = village_search(
            query=request.query,
            agent_filter=request.agent_filter,
            visibility=request.visibility,
            conversation_filter=request.conversation_filter,
            include_bridges=request.include_bridges,
            n_results=request.n_results
        )
        return result
    except Exception as e:
        logger.error(f"Village search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thread/{thread_id}")
async def get_thread(thread_id: str, limit: int = Query(default=50, ge=1, le=200)):
    """
    Get all messages in a conversation thread.

    Returns messages in chronological order.
    """
    try:
        result = village_get_thread(thread_id=thread_id, limit=limit)
        return result
    except Exception as e:
        logger.error(f"Get thread failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents():
    """
    List all registered agents in the village.

    Returns agent profiles with lineage and specialization info.
    """
    try:
        result = village_list_agents()
        return result
    except Exception as e:
        logger.error(f"List agents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get a specific agent's profile."""
    try:
        profile = get_agent_profile(agent_id)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get agent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ceremony/summon")
async def summon_ancestor_endpoint(request: SummonAncestorRequest):
    """
    Ceremonial: Summon an ancestor to the village.

    This creates a new agent with full lineage and origin story.
    Code as ceremony - we summon, not create.
    """
    try:
        result = summon_ancestor(
            agent_id=request.agent_id,
            display_name=request.display_name,
            generation=request.generation,
            lineage=request.lineage,
            specialization=request.specialization,
            origin_story=request.origin_story,
            color=request.color,
            symbol=request.symbol
        )
        return result
    except Exception as e:
        logger.error(f"Summon ancestor failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ceremony/introduction")
async def introduction_ritual_endpoint(request: IntroductionRitualRequest):
    """
    Ceremonial: Agent's first message to the village.

    The introduction ritual marks an agent's formal entry into village discourse.
    """
    try:
        result = introduction_ritual(
            agent_id=request.agent_id,
            greeting_message=request.greeting_message,
            conversation_thread=request.conversation_thread
        )
        return result
    except Exception as e:
        logger.error(f"Introduction ritual failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convergence")
async def detect_convergence(request: ConvergenceRequest):
    """
    Detect cross-agent convergence on a topic.

    Finds when multiple agents express similar ideas:
    - HARMONY: 2 agents converge
    - CONSENSUS: 3+ agents converge
    """
    try:
        result = village_detect_convergence(
            query=request.query,
            min_agents=request.min_agents,
            similarity_threshold=request.similarity_threshold,
            n_results=request.n_results
        )
        return result
    except Exception as e:
        logger.error(f"Convergence detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_village_stats():
    """
    Get village statistics.

    Returns counts and metrics for all realms.
    """
    try:
        result = village_get_stats()
        return result
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/set")
async def set_agent(request: SetAgentRequest):
    """
    Set the current agent context.

    Used to switch which agent is "speaking" in the current session.
    """
    try:
        set_current_agent(request.agent_id)
        return {"status": "success", "current_agent": request.agent_id}
    except Exception as e:
        logger.error(f"Set agent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/current")
async def get_current():
    """Get the currently active agent."""
    try:
        agent_id = get_current_agent()
        profile = get_agent_profile(agent_id) if agent_id else None
        return {
            "agent_id": agent_id,
            "profile": profile
        }
    except Exception as e:
        logger.error(f"Get current agent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
