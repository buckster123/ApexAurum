"""
Models Routes

Manage and query available LLM models.
Supports both Ollama and Claude providers.
"""

import logging
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from services.llm_service import (
    get_llm_client,
    get_ollama_client,
    get_claude_client,
    get_client_info,
    get_available_providers,
    reset_client
)
from app_config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Claude models available
CLAUDE_MODELS = [
    {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5 (Latest)"},
    {"id": "claude-opus-4-5-20251101", "name": "Claude Opus 4.5"},
    {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
    {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku (Fast)"},
]


class ModelPullRequest(BaseModel):
    """Request to pull/download a model."""
    model: str


@router.get("")
async def list_models():
    """
    List available models from the LLM endpoint.
    """
    try:
        client = get_llm_client()
        models = client.list_models()
        return {
            "models": models,
            "count": len(models),
            "default": settings.DEFAULT_MODEL
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local")
async def list_local_models():
    """
    List locally installed models (Ollama only).
    """
    try:
        client = get_ollama_client()
        if not client:
            raise HTTPException(
                status_code=400,
                detail="Local model listing only available with Ollama"
            )

        models = client.list_local_models()
        return {
            "models": models,
            "count": len(models)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing local models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Provider Management (before catch-all route)
# ============================================================================

@router.get("/providers")
async def list_providers():
    """
    List available LLM providers.
    """
    providers = get_available_providers()
    return {
        "providers": providers,
        "current": settings.LLM_PROVIDER,
        "client_info": get_client_info()
    }


@router.get("/providers/claude/models")
async def list_claude_models():
    """
    List available Claude models.
    """
    return {
        "models": CLAUDE_MODELS,
        "default": settings.CLAUDE_MODEL,
        "available": bool(settings.ANTHROPIC_API_KEY)
    }


@router.get("/all")
async def list_all_models():
    """
    List all available models from all providers.
    """
    result = {
        "providers": {},
        "current_provider": settings.LLM_PROVIDER
    }

    # Get Ollama models
    try:
        ollama = get_ollama_client()
        if ollama:
            local_models = ollama.list_local_models()
            result["providers"]["ollama"] = {
                "models": local_models,
                "count": len(local_models)
            }
    except Exception as e:
        result["providers"]["ollama"] = {"error": str(e), "models": []}

    # Add Claude models if available
    if settings.ANTHROPIC_API_KEY:
        result["providers"]["claude"] = {
            "models": CLAUDE_MODELS,
            "count": len(CLAUDE_MODELS)
        }

    return result


@router.get("/health/check")
async def check_llm_health():
    """
    Check if the LLM endpoint is healthy.
    """
    try:
        client = get_llm_client()
        healthy = client.health_check()
        return {
            "healthy": healthy,
            "provider": settings.LLM_PROVIDER,
            "endpoint": settings.LLM_BASE_URL
        }
    except Exception as e:
        return {
            "healthy": False,
            "provider": settings.LLM_PROVIDER,
            "endpoint": settings.LLM_BASE_URL,
            "error": str(e)
        }


# ============================================================================
# Model-specific operations (catch-all must be last)
# ============================================================================

@router.get("/{model_name}")
async def get_model_info(model_name: str):
    """
    Get detailed information about a model (Ollama only).
    """
    try:
        client = get_ollama_client()
        if not client:
            return {"model": model_name, "info": "Detailed info only available with Ollama"}

        info = client.show_model(model_name)
        return {"model": model_name, "info": info}

    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pull")
async def pull_model(request: ModelPullRequest):
    """
    Pull/download a model (Ollama only).

    Returns progress updates via streaming.
    """
    from fastapi.responses import StreamingResponse
    import json

    client = get_ollama_client()
    if not client:
        raise HTTPException(
            status_code=400,
            detail="Model pulling only available with Ollama"
        )

    async def generate():
        try:
            for progress in client.pull_model(request.model, stream=True):
                yield f"data: {json.dumps(progress)}\n\n"
            yield f"data: {json.dumps({'status': 'complete'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.delete("/{model_name}")
async def delete_model(model_name: str):
    """
    Delete a local model (Ollama only).
    """
    client = get_ollama_client()
    if not client:
        raise HTTPException(
            status_code=400,
            detail="Model deletion only available with Ollama"
        )

    try:
        success = client.delete_model(model_name)
        if success:
            return {"message": f"Model {model_name} deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete model")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
