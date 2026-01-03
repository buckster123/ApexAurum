"""
Claude API Client

Main wrapper for Anthropic Claude API with streaming support.
Handles message formatting, error handling, and response processing.
"""

import os
import time
import logging
from typing import Generator, List, Dict, Any, Optional
from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message, ContentBlock, TextBlock, ToolUseBlock
import anthropic

from .models import ClaudeModels, resolve_model, DEFAULT_MAX_TOKENS
from .message_converter import (
    prepare_messages_for_claude,
    validate_claude_messages,
    merge_consecutive_tool_results,
)
from .retry_handler import retry_on_error
from .rate_limiter import RateLimiter
from .token_counter import count_tokens
from .cost_tracker import CostTracker
from .cache_manager import CacheManager, CacheStrategy
from .cache_tracker import CacheTracker

logger = logging.getLogger(__name__)


class ClaudeAPIClient:
    """
    Main Claude API client wrapper

    Provides methods for:
    - Basic message creation (streaming and non-streaming)
    - Message format conversion
    - Error handling and retries
    - Token management
    """

    def __init__(self, api_key: Optional[str] = None, timeout: float = 1200.0):
        """
        Initialize Claude API client

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Please set it in .env or pass to constructor."
            )

        self.client = Anthropic(api_key=self.api_key, timeout=timeout)
        self.async_client = AsyncAnthropic(api_key=self.api_key, timeout=timeout)

        # Initialize rate limiter and cost tracker
        self.rate_limiter = RateLimiter()
        self.cost_tracker = CostTracker()

        # Phase 14: Initialize cache components (default: disabled)
        self.cache_strategy = CacheStrategy.DISABLED
        self.cache_manager = CacheManager(self.cache_strategy)
        self.cache_tracker = CacheTracker()

        logger.info(f"Claude API client initialized (cache: {self.cache_strategy.value})")

    def set_cache_strategy(self, strategy: CacheStrategy):
        """
        Change caching strategy (Phase 14).

        Args:
            strategy: CacheStrategy enum value
        """
        self.cache_strategy = strategy
        self.cache_manager = CacheManager(strategy)
        logger.info(f"Cache strategy changed to: {strategy.value}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics (Phase 14).

        Returns:
            Dictionary with cache statistics
        """
        return self.cache_tracker.get_cache_stats()

    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status (Phase 14).

        Returns:
            Dictionary with cache state information
        """
        return self.cache_manager.get_cache_status()

    @retry_on_error(max_retries=3, base_delay=1.0, max_delay=32.0)
    def create_message(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 1.0,
        top_p: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> Any:
        """
        Create a message with Claude API

        Args:
            messages: List of message dicts (OpenAI format - will be converted)
            model: Model ID (defaults to Sonnet 4.5)
            system: System prompt (optional - will extract from messages if not provided)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            top_p: Nucleus sampling parameter (0-1, optional - Claude default if None)
            tools: List of tool definitions (Claude format)
            stream: Whether to stream the response

        Returns:
            Message object (if not streaming) or generator (if streaming)
        """
        # Resolve model
        model_id = resolve_model(model)

        # Prepare messages for Claude
        if system is None:
            system, messages = prepare_messages_for_claude(messages)
        else:
            # System provided separately, just convert messages
            _, messages = prepare_messages_for_claude(messages)

        # Merge consecutive tool results
        messages = merge_consecutive_tool_results(messages)

        # Validate messages
        if not validate_claude_messages(messages):
            logger.warning("Message validation failed - Claude may reject this request")

        # Phase 14: Apply cache controls based on strategy
        if self.cache_strategy != CacheStrategy.DISABLED:
            system, tools, messages = self.cache_manager.apply_cache_controls(
                system, tools, messages
            )
            logger.debug(f"Cache controls applied (strategy: {self.cache_strategy.value})")

        # Build request parameters
        request_params = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add top_p if provided (optional parameter)
        if top_p is not None:
            request_params["top_p"] = top_p

        # Add system prompt if provided
        if system:
            request_params["system"] = system

        # Add tools if provided
        if tools:
            request_params["tools"] = tools

        # Add streaming flag
        if stream:
            request_params["stream"] = True

        # Estimate token usage for rate limiting
        token_estimate = count_tokens(messages, system, tools, model_id)
        estimated_input = token_estimate["input_tokens"]
        estimated_output = token_estimate["output_tokens"]

        # Check rate limits
        can_proceed, wait_time = self.rate_limiter.can_make_request(
            estimated_input_tokens=estimated_input,
            estimated_output_tokens=estimated_output
        )

        # Wait if needed
        if not can_proceed and wait_time > 0:
            logger.info(f"Rate limit approaching, waiting {wait_time:.1f}s")
            time.sleep(wait_time)

        logger.info(
            f"Creating message: model={model_id}, messages={len(messages)}, "
            f"system={'yes' if system else 'no'}, tools={len(tools) if tools else 0}, "
            f"stream={stream}, estimated_tokens={estimated_input}"
        )

        try:
            response = self.client.messages.create(**request_params)

            # Record usage for rate limiting and cost tracking
            if hasattr(response, 'usage'):
                actual_input = response.usage.input_tokens
                actual_output = response.usage.output_tokens

                # Phase 14: Extract cache token counts from response
                cache_creation_tokens = getattr(response.usage, 'cache_creation_input_tokens', 0)
                cache_read_tokens = getattr(response.usage, 'cache_read_input_tokens', 0)
                regular_input_tokens = actual_input - cache_creation_tokens - cache_read_tokens

                # Record for rate limiting
                self.rate_limiter.record_request(actual_input, actual_output)

                # Record for cost tracking (with cache tokens)
                self.cost_tracker.record_usage(
                    model=model_id,
                    input_tokens=actual_input,
                    output_tokens=actual_output,
                    cache_creation_tokens=cache_creation_tokens,
                    cache_read_tokens=cache_read_tokens
                )

                # Phase 14: Record cache usage statistics
                self.cache_tracker.record_cache_usage(
                    model=model_id,
                    cache_creation_tokens=cache_creation_tokens,
                    cache_read_tokens=cache_read_tokens,
                    regular_input_tokens=regular_input_tokens
                )

                # Enhanced logging with cache info
                if cache_creation_tokens > 0 or cache_read_tokens > 0:
                    logger.info(
                        f"Request completed: {regular_input_tokens} regular + "
                        f"{cache_creation_tokens} cache_write + {cache_read_tokens} cache_read + "
                        f"{actual_output} output = {actual_input + actual_output} total tokens"
                    )
                else:
                    logger.info(
                        f"Request completed: {actual_input} input + {actual_output} output "
                        f"= {actual_input + actual_output} total tokens"
                    )

            return response

        except anthropic.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise
        except anthropic.RateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            raise
        except anthropic.APIStatusError as e:
            logger.error(f"API status error: {e.status_code} - {e.message}")
            raise
        except anthropic.APIError as e:
            logger.error(f"API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    def create_message_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 1.0,
        top_p: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[str, None, None]:
        """
        Create a streaming message with Claude API

        Yields text chunks as they arrive. Also handles tool use blocks.

        Args:
            messages: List of message dicts
            model: Model ID
            system: System prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter (optional)
            tools: Tool definitions

        Yields:
            Text chunks from the response
        """
        try:
            response = self.create_message(
                messages=messages,
                model=model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                tools=tools,
                stream=True,
            )

            # Process streaming events
            for event in response:
                if event.type == "content_block_start":
                    # New content block started
                    if hasattr(event, "content_block"):
                        if event.content_block.type == "text":
                            # Text block starting
                            pass
                        elif event.content_block.type == "tool_use":
                            # Tool use block starting
                            yield f"\n> **Calling tool:** `{event.content_block.name}`\n"

                elif event.type == "content_block_delta":
                    # Content chunk arrived
                    delta = event.delta

                    if delta.type == "text_delta":
                        # Text content
                        yield delta.text

                    elif delta.type == "input_json_delta":
                        # Tool input being streamed (we'll handle this after completion)
                        pass

                elif event.type == "content_block_stop":
                    # Content block finished
                    pass

                elif event.type == "message_delta":
                    # Message-level delta (e.g., stop_reason)
                    pass

                elif event.type == "message_stop":
                    # Message complete
                    break

        except anthropic.RateLimitError as e:
            yield f"\n\n**Rate Limit Error:** {e.message}\nPlease wait a moment and try again."
        except anthropic.APIError as e:
            yield f"\n\n**API Error:** {str(e)}"
        except Exception as e:
            yield f"\n\n**Error:** {str(e)}"
            logger.error(f"Streaming error: {e}", exc_info=True)

    def simple_message(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        """
        Send a simple text prompt and get text response (non-streaming)

        Convenience method for simple use cases.

        Args:
            prompt: User prompt text
            model: Model to use
            system: System prompt
            max_tokens: Max output tokens

        Returns:
            Assistant's text response
        """
        messages = [{"role": "user", "content": prompt}]

        response = self.create_message(
            messages=messages,
            model=model,
            system=system,
            max_tokens=max_tokens,
            stream=False,
        )

        # Extract text from response
        if response.content:
            for block in response.content:
                if isinstance(block, TextBlock):
                    return block.text

        return ""


class ClaudeAPIClientWithRetry(ClaudeAPIClient):
    """
    Claude API client with automatic retry logic

    Extends base client with:
    - Exponential backoff on rate limits
    - Automatic retries on transient errors
    - Configurable retry attempts
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 600.0,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ):
        """
        Initialize client with retry configuration

        Args:
            api_key: Anthropic API key
            timeout: Request timeout
            max_retries: Maximum retry attempts
            initial_backoff: Initial backoff duration (seconds)
        """
        super().__init__(api_key, timeout)
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> Any:
        """
        Create message with retry logic

        Retries on:
        - Rate limit errors (with backoff)
        - Overloaded errors (529)
        - Transient network errors

        Args:
            Same as base class

        Returns:
            Same as base class
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return super().create_message(
                    messages=messages,
                    model=model,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tools=tools,
                    stream=stream,
                )

            except anthropic.RateLimitError as e:
                last_exception = e
                backoff = self.initial_backoff * (2**attempt)
                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}). "
                    f"Backing off for {backoff}s..."
                )
                if attempt < self.max_retries - 1:
                    time.sleep(backoff)
                    continue
                else:
                    raise

            except anthropic.APIStatusError as e:
                last_exception = e
                # Retry on 529 (overloaded) or 5xx errors
                if e.status_code == 529 or (500 <= e.status_code < 600):
                    backoff = self.initial_backoff * (2**attempt)
                    logger.warning(
                        f"API overloaded/error {e.status_code} "
                        f"(attempt {attempt + 1}/{self.max_retries}). "
                        f"Backing off for {backoff}s..."
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(backoff)
                        continue
                raise

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.initial_backoff * (2**attempt))
                    continue
                raise

        # If we get here, all retries failed
        if last_exception:
            raise last_exception


def test_connection(api_key: Optional[str] = None) -> bool:
    """
    Test Claude API connection

    Args:
        api_key: API key to test (optional)

    Returns:
        True if connection successful, False otherwise
    """
    try:
        client = ClaudeAPIClient(api_key=api_key)
        response = client.simple_message(
            prompt="Say 'hello' in one word.",
            system="You are a helpful assistant.",
            max_tokens=10,
        )

        logger.info(f"Connection test successful. Response: {response}")
        return True

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


# Convenience function for quick testing
def quick_test():
    """Quick test of Claude API"""
    print("Testing Claude API connection...")

    try:
        client = ClaudeAPIClient()
        print("✓ Client initialized")

        response = client.simple_message(
            prompt="Say hello in exactly 5 words.",
            model="claude-3-5-haiku-20241022",  # Use cheapest model for testing
            max_tokens=50,
        )

        print(f"✓ Response received: {response}")
        print("\n✅ Claude API is working!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Run quick test when module is run directly
    quick_test()
