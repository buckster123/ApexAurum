"""
Tools Routes

Execute AI tools and manage tool schemas.
"""

import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from services.tool_service import ToolService
from services.event_service import get_event_broadcaster

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize tool service
tool_service = ToolService()
broadcaster = get_event_broadcaster()


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
    Execute a tool directly with Village GUI event broadcasting.

    Example:
        POST /api/tools/execute
        {"tool": "calculator", "arguments": {"operation": "add", "a": 5, "b": 3}}
    """
    # Broadcast tool start event (async - works with WebSocket)
    await broadcaster.broadcast_tool_start(request.tool, request.arguments)

    try:
        # Execute tool (sync - the actual tool functions are sync)
        result = tool_service.execute_without_broadcast(request.tool, request.arguments)

        # Broadcast completion event
        await broadcaster.broadcast_tool_complete(request.tool, result, success=True)

        return ToolCallResponse(
            tool=request.tool,
            result=result,
            success=True
        )
    except ValueError as e:
        await broadcaster.broadcast_tool_error(request.tool, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        await broadcaster.broadcast_tool_complete(request.tool, str(e), success=False)
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


# ============================================================================
# Tool Selection / Settings
# ============================================================================

class ToolGroupUpdate(BaseModel):
    """Update a tool group's enabled state."""
    enabled: bool


class ToolUpdate(BaseModel):
    """Update a single tool's enabled state."""
    enabled: bool


class PresetApply(BaseModel):
    """Apply a tool preset."""
    preset_id: str


@router.get("/settings/groups")
async def get_tool_groups():
    """
    Get all tool groups with their tools and enabled states.

    Returns groups organized by category with individual tool states.
    """
    groups = tool_service.get_tool_groups()
    enabled_count = len(tool_service.get_enabled_tools())
    total_count = len(tool_service.tools)

    return {
        "groups": groups,
        "enabled_count": enabled_count,
        "total_count": total_count,
        "summary": f"{enabled_count}/{total_count} tools enabled"
    }


@router.get("/settings/presets")
async def get_tool_presets():
    """
    Get available tool presets (Minimal, Standard, Creative, etc.).
    """
    from services.tool_service import TOOL_PRESETS
    presets = []
    for preset_id, preset_info in TOOL_PRESETS.items():
        # Calculate how many tools this preset enables
        enabled_groups = set(preset_info.get("groups", []))
        tool_count = sum(
            len(tool_service.get_tool_groups().get(g, {}).get("tools", []))
            for g in enabled_groups
        )
        # Add extra_tools
        tool_count += len(preset_info.get("extra_tools", []))

        presets.append({
            "id": preset_id,
            "name": preset_info["name"],
            "description": preset_info["description"],
            "tool_count": tool_count
        })
    return {"presets": presets}


@router.post("/settings/presets/apply")
async def apply_tool_preset(request: PresetApply):
    """
    Apply a tool preset.

    This enables/disables groups of tools based on the preset configuration.
    """
    result = tool_service.apply_preset(request.preset_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/settings/groups/{group_id}")
async def update_tool_group(group_id: str, request: ToolGroupUpdate):
    """
    Enable or disable an entire tool group.
    """
    from services.tool_service import TOOL_GROUPS
    if group_id not in TOOL_GROUPS:
        raise HTTPException(status_code=404, detail=f"Group not found: {group_id}")

    tool_service.set_group_enabled(group_id, request.enabled)
    group = tool_service.get_tool_groups()[group_id]
    enabled_count = len(tool_service.get_enabled_tools())

    return {
        "group_id": group_id,
        "enabled": request.enabled,
        "affected_tools": len(group["tools"]),
        "total_enabled": enabled_count
    }


@router.put("/settings/tools/{tool_name}")
async def update_tool(tool_name: str, request: ToolUpdate):
    """
    Enable or disable a single tool.
    """
    if tool_name not in tool_service.tools:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    tool_service.set_tool_enabled(tool_name, request.enabled)
    enabled_count = len(tool_service.get_enabled_tools())

    return {
        "tool": tool_name,
        "enabled": request.enabled,
        "total_enabled": enabled_count
    }


@router.get("/enabled")
async def get_enabled_tools():
    """
    Get list of currently enabled tools.

    This is what will be injected into the system prompt when tools are enabled.
    """
    enabled = tool_service.get_enabled_tools()
    return {
        "tools": enabled,
        "count": len(enabled),
        "total": len(tool_service.tools)
    }
