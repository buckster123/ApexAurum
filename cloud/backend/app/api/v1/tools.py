"""
Tools Endpoints

Direct tool execution and listing.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.user import User
from app.auth.deps import get_current_user

router = APIRouter()


# Schemas
class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict
    category: str


class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: dict[str, Any]


class ToolExecuteResponse(BaseModel):
    success: bool
    result: Any
    error: Optional[str] = None


# Tool registry (will be populated from tools/ module)
TOOL_REGISTRY: dict[str, dict] = {
    # Placeholder - will be populated with actual tools
    "time_now": {
        "name": "time_now",
        "description": "Get the current time",
        "parameters": {},
        "category": "utilities",
        "handler": lambda: {"time": "2026-01-24T12:00:00Z"},
    },
    "calculator": {
        "name": "calculator",
        "description": "Perform mathematical calculations",
        "parameters": {
            "expression": {"type": "string", "description": "Math expression to evaluate"}
        },
        "category": "utilities",
        "handler": lambda expression: {"result": eval(expression)},
    },
}


# Endpoints
@router.get("/", response_model=list[ToolSchema])
async def list_tools(
    category: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """
    List all available tools.

    Categories: utilities, filesystem, web, code, memory, vector, agents, music
    """
    tools = []
    for name, tool in TOOL_REGISTRY.items():
        if category and tool.get("category") != category:
            continue
        tools.append(ToolSchema(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
            category=tool.get("category", "other"),
        ))

    return tools


@router.get("/{tool_name}/schema", response_model=ToolSchema)
async def get_tool_schema(
    tool_name: str,
    user: User = Depends(get_current_user),
):
    """Get schema for a specific tool."""
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found"
        )

    return ToolSchema(
        name=tool["name"],
        description=tool["description"],
        parameters=tool["parameters"],
        category=tool.get("category", "other"),
    )


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    request: ToolExecuteRequest,
    user: User = Depends(get_current_user),
):
    """
    Execute a tool directly.

    Note: Some tools may require additional permissions.
    """
    tool = TOOL_REGISTRY.get(request.tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{request.tool_name}' not found"
        )

    try:
        handler = tool.get("handler")
        if not handler:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Tool handler not implemented"
            )

        result = handler(**request.parameters)
        return ToolExecuteResponse(success=True, result=result)

    except Exception as e:
        return ToolExecuteResponse(
            success=False,
            result=None,
            error=str(e),
        )
