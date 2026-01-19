"""
LLM Service

Provides access to the LLM client from reusable_lib.
Handles client initialization and caching.
Supports both local (Ollama) and Claude API providers.
"""

import logging
from typing import Optional, List, Dict, Any, Generator, Union
from dataclasses import dataclass

# Import from reusable_lib (adjust path as needed)
import sys
from pathlib import Path

# Add reusable_lib to path if running from scaffold
lib_path = Path(__file__).parent.parent.parent.parent
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from reusable_lib.api import (
    OpenAICompatibleClient,
    OllamaClient,
    create_ollama_client,
    create_local_client,
    create_hosted_client,
    PROVIDER_URLS
)

from app_config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Claude Client Wrapper
# ============================================================================

@dataclass
class ChatResponse:
    """Unified response format for all providers."""
    content: str
    model: str
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None
    tool_calls: Optional[List[Dict]] = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class ClaudeClient:
    """
    Claude API client wrapper with the same interface as OpenAICompatibleClient.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

        self.default_model = model
        self.max_tokens = 4096
        self.temperature = 0.7

    def chat(
        self,
        messages: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict]] = None,
    ) -> ChatResponse:
        """
        Send a chat completion request to Claude.
        """
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        # Convert string prompt to messages format
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        # Build request kwargs
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if temperature is not None:
            kwargs["temperature"] = temperature

        if tools:
            # Convert to Anthropic tool format
            kwargs["tools"] = self._convert_tools(tools)

        response = self.client.messages.create(**kwargs)

        # Extract content
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "function": {
                        "name": block.name,
                        "arguments": block.input
                    }
                })

        return ChatResponse(
            content=content,
            model=response.model,
            finish_reason=response.stop_reason or "stop",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            tool_calls=tool_calls if tool_calls else None
        )

    def chat_stream(
        self,
        messages: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Generator[str, None, None]:
        """
        Stream a chat completion from Claude.
        """
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        # Convert string prompt to messages format
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        # Build request kwargs
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if temperature is not None:
            kwargs["temperature"] = temperature

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI tool format to Anthropic format."""
        anthropic_tools = []
        for tool in tools:
            if "function" in tool:
                # OpenAI format
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                })
            else:
                # Already Anthropic format
                anthropic_tools.append(tool)
        return anthropic_tools


# ============================================================================
# Client Management
# ============================================================================

# Cached client instances
_llm_client: Optional[Union[OpenAICompatibleClient, ClaudeClient]] = None
_ollama_client: Optional[OllamaClient] = None
_claude_client: Optional[ClaudeClient] = None


def get_llm_client(provider: Optional[str] = None) -> Union[OpenAICompatibleClient, ClaudeClient]:
    """
    Get the LLM client instance.

    Creates a new client on first call, returns cached instance after.

    Args:
        provider: Optional provider override ("ollama", "claude", etc.)
                  If not specified, uses settings.LLM_PROVIDER
    """
    global _llm_client

    provider = (provider or settings.LLM_PROVIDER).lower()

    # Check if we need Claude
    if provider == "claude" or provider == "anthropic":
        return get_claude_client()

    if _llm_client is None:
        if provider == "ollama":
            # Extract host from base URL
            host = settings.LLM_BASE_URL.replace("/v1", "")
            _llm_client = create_ollama_client(host=host)

        elif provider in ["together", "groq", "openrouter", "fireworks", "anyscale"]:
            if not settings.LLM_API_KEY:
                raise ValueError(f"{provider} requires LLM_API_KEY")
            _llm_client = create_hosted_client(
                provider=provider,
                api_key=settings.LLM_API_KEY
            )

        else:
            # Generic OpenAI-compatible endpoint
            _llm_client = create_local_client(
                provider=provider,
                host=settings.LLM_BASE_URL
            )

        # Set defaults from config
        _llm_client.config.default_model = settings.DEFAULT_MODEL
        _llm_client.config.max_tokens = settings.MAX_TOKENS
        _llm_client.config.temperature = settings.TEMPERATURE

        logger.info(f"Initialized LLM client: {provider} @ {settings.LLM_BASE_URL}")

    return _llm_client


def get_claude_client() -> ClaudeClient:
    """
    Get the Claude API client.

    Returns cached instance after first initialization.
    Requires ANTHROPIC_API_KEY in settings.
    """
    global _claude_client

    if _claude_client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("Claude requires ANTHROPIC_API_KEY in environment")

        _claude_client = ClaudeClient(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.CLAUDE_MODEL
        )
        _claude_client.max_tokens = settings.MAX_TOKENS
        _claude_client.temperature = settings.TEMPERATURE

        logger.info(f"Initialized Claude client: {settings.CLAUDE_MODEL}")

    return _claude_client


def get_ollama_client() -> Optional[OllamaClient]:
    """
    Get an Ollama-specific client (for native API features).

    Returns None if not using Ollama.
    """
    global _ollama_client

    if settings.LLM_PROVIDER.lower() != "ollama":
        return None

    if _ollama_client is None:
        host = settings.LLM_BASE_URL.replace("/v1", "")
        _ollama_client = create_ollama_client(host=host)
        logger.info(f"Initialized Ollama client: {host}")

    return _ollama_client


def reset_client():
    """Reset all clients (useful for config changes)."""
    global _llm_client, _ollama_client, _claude_client
    _llm_client = None
    _ollama_client = None
    _claude_client = None
    logger.info("All LLM clients reset")


def get_client_info() -> dict:
    """Get information about the current client configuration."""
    provider = settings.LLM_PROVIDER.lower()

    info = {
        "provider": settings.LLM_PROVIDER,
        "default_model": settings.DEFAULT_MODEL,
        "max_tokens": settings.MAX_TOKENS,
        "temperature": settings.TEMPERATURE,
        "is_ollama": provider == "ollama",
        "is_claude": provider in ["claude", "anthropic"],
        "claude_available": bool(settings.ANTHROPIC_API_KEY),
    }

    if provider in ["claude", "anthropic"]:
        info["base_url"] = "https://api.anthropic.com"
        info["claude_model"] = settings.CLAUDE_MODEL
    else:
        info["base_url"] = settings.LLM_BASE_URL

    return info


def get_available_providers() -> List[str]:
    """Get list of available providers based on configuration."""
    providers = ["ollama"]  # Always available locally

    if settings.ANTHROPIC_API_KEY:
        providers.append("claude")

    if settings.LLM_API_KEY:
        # Check for hosted providers
        if settings.LLM_PROVIDER.lower() in ["together", "groq", "openrouter", "fireworks", "anyscale"]:
            providers.append(settings.LLM_PROVIDER.lower())

    return providers
