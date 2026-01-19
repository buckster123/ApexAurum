"""
Statistics Routes

API endpoints for cost tracking, context info, and session statistics.
"""

import logging
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from services.cost_service import get_cost_service
from services.context_service import get_context_manager, set_context_strategy, ContextStrategy

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ContextStrategyRequest(BaseModel):
    """Request to change context strategy."""
    strategy: str  # disabled, rolling, summarize, hybrid, adaptive


# =============================================================================
# Cost Tracking Routes
# =============================================================================

@router.get("/costs")
async def get_session_costs():
    """
    Get current session cost statistics.

    Returns token counts, costs, and request counts.
    """
    cost_service = get_cost_service()
    return cost_service.get_session_stats()


@router.get("/costs/conversation/{conv_id}")
async def get_conversation_costs(conv_id: str):
    """
    Get costs for a specific conversation.

    Args:
        conv_id: Conversation ID
    """
    cost_service = get_cost_service()
    stats = cost_service.get_conversation_stats(conv_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Conversation not found in cost tracking")
    return stats


@router.get("/costs/recent")
async def get_recent_costs(limit: int = 50):
    """
    Get recent cost records.

    Args:
        limit: Max records to return (default 50)
    """
    cost_service = get_cost_service()
    return {
        "records": cost_service.get_recent_records(limit),
        "session": cost_service.get_session_stats()
    }


@router.get("/costs/breakdown")
async def get_cost_breakdown():
    """
    Get cost breakdown by model.

    Shows which models used most tokens/cost.
    """
    cost_service = get_cost_service()
    return {
        "by_model": cost_service.get_model_breakdown(),
        "session": cost_service.get_session_stats()
    }


@router.post("/costs/reset")
async def reset_session_costs():
    """
    Reset session cost tracking.

    Saves current data and starts fresh counters.
    """
    cost_service = get_cost_service()
    cost_service.reset_session()
    return {"success": True, "message": "Session costs reset"}


# =============================================================================
# Context Management Routes
# =============================================================================

@router.get("/context/info")
async def get_context_info(model: Optional[str] = None):
    """
    Get context management info.

    Args:
        model: Optional model name (uses default if not specified)
    """
    from app_config import settings
    context_manager = get_context_manager()
    model = model or settings.DEFAULT_MODEL

    # Return general info (no messages)
    return {
        "strategy": context_manager.strategy.value,
        "max_messages": context_manager.max_messages,
        "summarize_threshold": context_manager.summarize_threshold,
        "model_context_limit": context_manager.get_context_limit(model),
        "available_strategies": [s.value for s in ContextStrategy]
    }


@router.post("/context/strategy")
async def set_context_management_strategy(request: ContextStrategyRequest):
    """
    Set the context management strategy.

    Available strategies:
    - disabled: No optimization
    - rolling: Keep only recent N messages
    - summarize: Summarize old messages when limit approached
    - hybrid: Rolling + summarization
    - adaptive: Auto-select based on context size
    """
    try:
        set_context_strategy(request.strategy)
        context_manager = get_context_manager()
        return {
            "success": True,
            "strategy": context_manager.strategy.value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/context/clear-cache")
async def clear_context_cache(conversation_id: Optional[str] = None):
    """
    Clear cached summaries.

    Args:
        conversation_id: Optional specific conversation to clear
    """
    context_manager = get_context_manager()
    context_manager.clear_cache(conversation_id)
    return {"success": True, "message": "Cache cleared"}


# =============================================================================
# Combined Stats
# =============================================================================

@router.get("")
async def get_all_stats():
    """
    Get all statistics in one call.

    Returns session costs, context info, and system status.
    """
    from services.tool_service import ToolService
    from services.llm_service import get_client_info
    from app_config import settings

    cost_service = get_cost_service()
    context_manager = get_context_manager()

    tool_service = ToolService()

    return {
        "costs": cost_service.get_session_stats(),
        "context": {
            "strategy": context_manager.strategy.value,
            "max_messages": context_manager.max_messages,
            "model_context_limit": context_manager.get_context_limit(settings.DEFAULT_MODEL)
        },
        "tools": {
            "count": len(tool_service.tools),
            "available": list(tool_service.tools.keys())[:10]  # First 10 for brevity
        },
        "llm": get_client_info()
    }
