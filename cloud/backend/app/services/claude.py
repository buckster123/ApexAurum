"""
Claude API Service

Wrapper for Anthropic Claude API with streaming support.
"""

from typing import AsyncGenerator, Optional
import anthropic

from app.config import get_settings

settings = get_settings()


class ClaudeService:
    """Service for interacting with Claude API."""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key
        )

    async def chat(
        self,
        messages: list[dict],
        model: str = "claude-3-haiku-20240307",
        system: Optional[str] = None,
        max_tokens: int = 4096,
        tools: Optional[list[dict]] = None,
    ) -> dict:
        """
        Send a chat message and get a response.

        Non-streaming version for simple requests.
        """
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        return {
            "id": response.id,
            "role": response.role,
            "content": [
                {"type": block.type, "text": getattr(block, "text", None)}
                for block in response.content
            ],
            "model": response.model,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    async def chat_stream(
        self,
        messages: list[dict],
        model: str = "claude-3-haiku-20240307",
        system: Optional[str] = None,
        max_tokens: int = 4096,
        tools: Optional[list[dict]] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Send a chat message and stream the response.

        Yields events as they arrive.
        """
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield {
                            "type": "token",
                            "content": event.delta.text,
                        }
                elif event.type == "message_start":
                    yield {
                        "type": "start",
                        "model": event.message.model,
                    }
                elif event.type == "message_stop":
                    yield {
                        "type": "end",
                    }
                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        yield {
                            "type": "tool_start",
                            "tool_name": event.content_block.name,
                            "tool_id": event.content_block.id,
                        }

    async def count_tokens(self, text: str, model: str = "claude-3-haiku-20240307") -> int:
        """Count tokens in text."""
        response = await self.client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": text}],
        )
        return response.input_tokens
