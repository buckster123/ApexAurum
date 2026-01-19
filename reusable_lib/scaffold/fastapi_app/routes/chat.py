"""
Chat Routes

Handles chat completions with streaming support.
Includes tool-enabled chat for models to use tools.
Integrates cost tracking and context management.
"""

import json
import logging
import re
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from services.llm_service import get_llm_client
from services.tool_service import ToolService
from services.cost_service import get_cost_service
from services.context_service import get_context_manager
from app_config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Global tool service instance
_tool_service: Optional[ToolService] = None


def get_tool_service() -> ToolService:
    """Get or create the tool service singleton."""
    global _tool_service
    if _tool_service is None:
        _tool_service = ToolService()
    return _tool_service


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    """Chat completion request."""
    messages: List[ChatMessage]
    model: Optional[str] = None
    system: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False
    use_tools: bool = False  # Enable tool calling
    provider: Optional[str] = None  # "ollama", "claude", etc.
    conversation_id: Optional[str] = None  # For cost tracking per conversation
    optimize_context: bool = True  # Apply context management


class ChatResponse(BaseModel):
    """Chat completion response."""
    content: str
    model: str
    finish_reason: str
    usage: Optional[dict] = None
    cost: Optional[dict] = None  # Cost tracking info
    context_info: Optional[dict] = None  # Context management info


class SimplePromptRequest(BaseModel):
    """Simple single-turn prompt."""
    prompt: str
    model: Optional[str] = None
    system: Optional[str] = None


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat completion request.

    Supports multi-turn conversations via the messages array.
    Includes cost tracking and context management.
    """
    try:
        client = get_llm_client(provider=request.provider)
        cost_service = get_cost_service()
        context_manager = get_context_manager()

        provider = request.provider or settings.LLM_PROVIDER
        model = request.model or settings.DEFAULT_MODEL

        # Convert messages to client format
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # Apply context management if enabled
        context_info = None
        if request.optimize_context:
            context_info = context_manager.get_context_info(messages, model)
            messages = context_manager.optimize_context(
                messages, model, request.conversation_id
            )

        # Estimate input tokens
        input_tokens = cost_service.estimate_tokens(str(messages))

        response = client.chat(
            messages,
            model=model,
            system=request.system,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        # Track costs
        output_tokens = cost_service.estimate_tokens(response.content)
        record = cost_service.track_request(
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            conversation_id=request.conversation_id,
            usage_dict=response.usage
        )

        return ChatResponse(
            content=response.content,
            model=response.model,
            finish_reason=response.finish_reason,
            usage=response.usage,
            cost={
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "cost": record.cost
            },
            context_info=context_info
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simple")
async def simple_chat(request: SimplePromptRequest):
    """
    Simple single-turn chat.

    Just send a prompt, get a response.
    """
    try:
        client = get_llm_client()
        model = request.model or settings.DEFAULT_MODEL

        response = client.chat(
            request.prompt,
            model=model,
            system=request.system
        )

        return {
            "content": response.content,
            "model": response.model
        }

    except Exception as e:
        logger.error(f"Simple chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def extract_tool_call(content: str) -> Optional[dict]:
    """
    Extract a tool call JSON from response content.

    Looks for {"tool": "...", "arguments": {...}} pattern.
    """
    # Try to find JSON in code blocks first
    code_block_match = re.search(r'```(?:json)?\s*(\{[^`]+\})\s*```', content, re.DOTALL)
    if code_block_match:
        try:
            parsed = json.loads(code_block_match.group(1))
            if isinstance(parsed, dict) and "tool" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    # Try to find JSON object with "tool" key (handles nested braces)
    # Look for pattern starting with { and containing "tool"
    start_idx = content.find('{"tool"')
    if start_idx == -1:
        start_idx = content.find('{ "tool"')

    if start_idx != -1:
        # Find matching closing brace
        brace_count = 0
        end_idx = start_idx
        for i, char in enumerate(content[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        if end_idx > start_idx:
            try:
                parsed = json.loads(content[start_idx:end_idx])
                if isinstance(parsed, dict) and "tool" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

    # Try the whole content
    try:
        parsed = json.loads(content.strip())
        if isinstance(parsed, dict) and "tool" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    return None


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream a chat completion response.

    Returns Server-Sent Events (SSE) for real-time streaming.

    If use_tools=True, injects tool descriptions into system prompt
    and automatically executes tool calls found in the response.

    Provider can be "ollama", "claude", etc.
    Includes cost tracking and context management.
    """
    client = get_llm_client(provider=request.provider)
    tool_service = get_tool_service()
    cost_service = get_cost_service()
    context_manager = get_context_manager()

    provider = request.provider or settings.LLM_PROVIDER

    # Set default model based on provider
    if request.provider == "claude":
        model = request.model or settings.CLAUDE_MODEL
    else:
        model = request.model or settings.DEFAULT_MODEL

    # Build system prompt
    system_prompt = request.system
    if request.use_tools:
        system_prompt = tool_service.build_system_prompt(request.system)
        logger.info(f"Tools enabled, system prompt length: {len(system_prompt)}")

    # Convert messages
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    # Apply context management if enabled
    if request.optimize_context:
        context_info = context_manager.get_context_info(messages, model)
        messages = context_manager.optimize_context(
            messages, model, request.conversation_id
        )
        logger.info(f"Context: {context_info['usage_percent']:.1f}% used, {len(messages)} messages")

    # Prepare prompt for streaming
    if len(messages) == 1 and messages[0]["role"] == "user":
        prompt = messages[0]["content"]
    else:
        prompt = messages

    # Track input tokens
    input_tokens = cost_service.estimate_tokens(str(prompt) + str(system_prompt or ""))

    async def generate():
        """Generator for SSE stream with tool execution and cost tracking."""
        nonlocal input_tokens
        total_output_tokens = 0

        try:
            full_content = ""

            # Stream the initial response
            for chunk in client.chat_stream(
                prompt,
                model=model,
                system=system_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ):
                full_content += chunk
                data = json.dumps({"content": chunk, "done": False})
                yield f"data: {data}\n\n"

            # Track output tokens for initial response
            total_output_tokens += cost_service.estimate_tokens(full_content)

            # Check for tool calls if tools are enabled
            if request.use_tools:
                tool_call = extract_tool_call(full_content)

                if tool_call:
                    tool_name = tool_call.get("tool")
                    arguments = tool_call.get("arguments", {})

                    logger.info(f"Tool call detected: {tool_name}({arguments})")

                    # Send tool call notification
                    yield f"data: {json.dumps({'tool_call': {'tool': tool_name, 'arguments': arguments}, 'done': False})}\n\n"

                    # Execute the tool
                    try:
                        result = tool_service.execute(tool_name, arguments)
                        result_str = json.dumps(result) if not isinstance(result, str) else result

                        logger.info(f"Tool result: {result_str[:200]}")

                        # Send tool result
                        yield f"data: {json.dumps({'tool_result': {'tool': tool_name, 'result': result, 'success': True}, 'done': False})}\n\n"

                        # Get follow-up response incorporating the tool result
                        follow_up_prompt = f"The tool {tool_name} returned: {result_str}\n\nNow provide a natural response to the user incorporating this result."

                        # Track follow-up input tokens
                        input_tokens += cost_service.estimate_tokens(follow_up_prompt)

                        yield f"data: {json.dumps({'content': '\\n\\n', 'done': False})}\n\n"

                        follow_up_content = ""
                        for chunk in client.chat_stream(
                            follow_up_prompt,
                            model=model,
                            system="You are a helpful assistant. The user asked a question and a tool was executed. Provide a clear, natural response using the tool result.",
                            max_tokens=request.max_tokens,
                            temperature=request.temperature
                        ):
                            follow_up_content += chunk
                            data = json.dumps({"content": chunk, "done": False})
                            yield f"data: {data}\n\n"

                        # Track follow-up output tokens
                        total_output_tokens += cost_service.estimate_tokens(follow_up_content)

                        # Track tool call cost separately
                        cost_service.track_request(
                            model=model,
                            provider=provider,
                            input_tokens=cost_service.estimate_tokens(follow_up_prompt),
                            output_tokens=cost_service.estimate_tokens(follow_up_content),
                            conversation_id=request.conversation_id,
                            tool_name=tool_name
                        )

                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        yield f"data: {json.dumps({'tool_result': {'tool': tool_name, 'error': str(e), 'success': False}, 'done': False})}\n\n"

            # Track main request cost
            record = cost_service.track_request(
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=total_output_tokens,
                conversation_id=request.conversation_id
            )

            # Send done signal with cost info
            done_data = {
                'content': '',
                'done': True,
                'cost': {
                    'input_tokens': record.input_tokens,
                    'output_tokens': record.output_tokens,
                    'cost': record.cost,
                    'session_total': cost_service.get_session_stats()['cost']
                }
            }
            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            error_data = json.dumps({"error": str(e), "done": True})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/stream/test")
async def stream_test():
    """Test endpoint for streaming."""
    async def generate():
        import asyncio
        words = "Hello! This is a test of the streaming endpoint. ".split()
        for word in words:
            yield f"data: {json.dumps({'content': word + ' ', 'done': False})}\n\n"
            await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
