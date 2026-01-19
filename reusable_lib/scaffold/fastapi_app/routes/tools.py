"""
Tools Routes

Execute AI tools and manage tool schemas.
"""

import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from services.tool_service import ToolService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize tool service
tool_service = ToolService()


class ToolCallRequest(BaseModel):
    """Request to execute a tool."""
    tool: str
    arguments: Dict[str, Any] = {}


class ToolCallResponse(BaseModel):
    """Response from tool execution."""
    tool: str
    result: Any
    success: bool
    error: Optional[str] = None


class ChatWithToolsRequest(BaseModel):
    """Chat request that may trigger tool calls."""
    prompt: str
    model: Optional[str] = None
    system: Optional[str] = None
    tools: Optional[List[str]] = None  # None = all tools, [] = no tools


@router.get("")
async def list_tools():
    """
    List all available tools with their schemas.
    """
    return {
        "tools": tool_service.get_tool_list(),
        "count": len(tool_service.get_tool_list())
    }


@router.get("/{tool_name}")
async def get_tool(tool_name: str):
    """
    Get details about a specific tool.
    """
    tool = tool_service.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    return tool


@router.post("/execute", response_model=ToolCallResponse)
async def execute_tool(request: ToolCallRequest):
    """
    Execute a tool directly.

    Example:
        POST /api/tools/execute
        {"tool": "calculator", "arguments": {"operation": "add", "a": 5, "b": 3}}
    """
    try:
        result = tool_service.execute(request.tool, request.arguments)
        return ToolCallResponse(
            tool=request.tool,
            result=result,
            success=True
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return ToolCallResponse(
            tool=request.tool,
            result=None,
            success=False,
            error=str(e)
        )


@router.post("/chat")
async def chat_with_tools(request: ChatWithToolsRequest):
    """
    Chat with automatic tool execution.

    The LLM will decide which tools to call based on the prompt.
    Tools are executed automatically and results returned.
    """
    try:
        result = await tool_service.chat_with_tools(
            prompt=request.prompt,
            model=request.model,
            system=request.system,
            tool_filter=request.tools
        )
        return result
    except Exception as e:
        logger.error(f"Chat with tools error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schemas/openai")
async def get_openai_schemas():
    """
    Get tool schemas in OpenAI function-calling format.

    Useful for direct LLM integration.
    """
    return {"tools": tool_service.get_openai_schemas()}


@router.get("/schemas/anthropic")
async def get_anthropic_schemas():
    """
    Get tool schemas in Anthropic/Claude format.
    """
    return {"tools": tool_service.get_anthropic_schemas()}
