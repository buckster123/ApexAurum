"""
Context Management Service

Manages conversation context to stay within token limits.
Supports multiple strategies: rolling window, summarization, hybrid.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from enum import Enum

from services.llm_service import get_llm_client
from services.cost_service import get_cost_service
from app_config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Model context limits (in tokens)
MODEL_CONTEXT_LIMITS = {
    # Claude models
    "claude-opus-4-5-20250929": 200000,
    "claude-sonnet-4-5-20250929": 200000,
    "claude-sonnet-4-20250514": 200000,
    "claude-haiku-4-20250514": 200000,
    # Ollama models (typical limits)
    "qwen2.5:3b": 32768,
    "qwen2.5:7b": 32768,
    "qwen2:1.5b": 8192,
    "qwen2:0.5b": 8192,
    "llama3.2:3b": 8192,
    "gemma2:2b": 8192,
    # Default for unknown models
    "default": 8192
}

# Reserve tokens for response
RESPONSE_RESERVE = 2048


class ContextStrategy(str, Enum):
    """Available context management strategies."""
    DISABLED = "disabled"       # No management, may fail on long contexts
    ROLLING = "rolling"         # Keep only recent N messages
    SUMMARIZE = "summarize"     # Summarize old messages when limit approached
    HYBRID = "hybrid"           # Rolling + summarization for very long contexts
    ADAPTIVE = "adaptive"       # Auto-select strategy based on context size


# =============================================================================
# Context Manager
# =============================================================================

class ContextManager:
    """
    Manages conversation context to prevent token limit overflow.

    Strategies:
    - rolling: Keep only the most recent N messages
    - summarize: When approaching limit, summarize older messages
    - hybrid: Combine rolling window with periodic summaries
    - adaptive: Automatically choose best strategy
    """

    def __init__(
        self,
        strategy: ContextStrategy = ContextStrategy.ADAPTIVE,
        max_messages: int = 20,
        summarize_threshold: float = 0.75,
        summary_model: Optional[str] = None
    ):
        """
        Initialize context manager.

        Args:
            strategy: Context management strategy
            max_messages: Max messages for rolling window
            summarize_threshold: Fraction of limit before summarizing (0.0-1.0)
            summary_model: Model to use for summarization (defaults to current)
        """
        self.strategy = strategy
        self.max_messages = max_messages
        self.summarize_threshold = summarize_threshold
        self.summary_model = summary_model

        # Conversation summaries cache
        self.summaries: Dict[str, str] = {}

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def estimate_messages_tokens(self, messages: List[Dict]) -> int:
        """Estimate total tokens in a message list."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.estimate_tokens(content)
            elif isinstance(content, list):
                # Handle content blocks
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        total += self.estimate_tokens(block["text"])
            # Add overhead for role, formatting
            total += 10
        return total

    def get_context_limit(self, model: str) -> int:
        """Get context limit for a model."""
        return MODEL_CONTEXT_LIMITS.get(model, MODEL_CONTEXT_LIMITS["default"])

    def get_available_tokens(self, model: str, messages: List[Dict]) -> int:
        """Get remaining available tokens for response."""
        limit = self.get_context_limit(model)
        used = self.estimate_messages_tokens(messages)
        available = limit - used - RESPONSE_RESERVE
        return max(0, available)

    def needs_optimization(self, model: str, messages: List[Dict]) -> bool:
        """Check if context needs optimization."""
        if self.strategy == ContextStrategy.DISABLED:
            return False

        limit = self.get_context_limit(model)
        used = self.estimate_messages_tokens(messages)
        threshold = limit * self.summarize_threshold

        return used > threshold

    def optimize_context(
        self,
        messages: List[Dict],
        model: str,
        conversation_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Optimize messages to fit within context limits.

        Args:
            messages: Current message list
            model: Model being used
            conversation_id: Optional conversation ID for caching

        Returns:
            Optimized message list
        """
        if self.strategy == ContextStrategy.DISABLED:
            return messages

        if not self.needs_optimization(model, messages):
            return messages

        logger.info(f"Optimizing context: {len(messages)} messages, strategy={self.strategy}")

        if self.strategy == ContextStrategy.ROLLING:
            return self._apply_rolling_window(messages)

        elif self.strategy == ContextStrategy.SUMMARIZE:
            return self._apply_summarization(messages, model, conversation_id)

        elif self.strategy == ContextStrategy.HYBRID:
            return self._apply_hybrid(messages, model, conversation_id)

        elif self.strategy == ContextStrategy.ADAPTIVE:
            return self._apply_adaptive(messages, model, conversation_id)

        return messages

    def _apply_rolling_window(self, messages: List[Dict]) -> List[Dict]:
        """Keep only the most recent messages."""
        if len(messages) <= self.max_messages:
            return messages

        # Always keep system message if present
        result = []
        start_idx = 0

        if messages and messages[0].get("role") == "system":
            result.append(messages[0])
            start_idx = 1

        # Take the most recent messages
        recent = messages[start_idx:][-self.max_messages:]
        result.extend(recent)

        logger.info(f"Rolling window: {len(messages)} -> {len(result)} messages")
        return result

    def _apply_summarization(
        self,
        messages: List[Dict],
        model: str,
        conversation_id: Optional[str] = None
    ) -> List[Dict]:
        """Summarize older messages."""
        if len(messages) < 6:
            return messages

        # Find messages to summarize (keep last 4 messages intact)
        keep_recent = 4
        to_summarize = messages[:-keep_recent]
        recent = messages[-keep_recent:]

        if len(to_summarize) < 3:
            return messages

        # Check cache
        cache_key = conversation_id or str(hash(str(to_summarize)))
        if cache_key in self.summaries:
            summary = self.summaries[cache_key]
        else:
            summary = self._generate_summary(to_summarize, model)
            self.summaries[cache_key] = summary

        # Build optimized messages
        result = []

        # Keep system message if present
        if messages[0].get("role") == "system":
            result.append(messages[0])

        # Add summary as a system message
        result.append({
            "role": "user",
            "content": f"[Previous conversation summary: {summary}]"
        })

        # Add recent messages
        result.extend(recent)

        logger.info(f"Summarization: {len(messages)} -> {len(result)} messages")
        return result

    def _generate_summary(self, messages: List[Dict], model: str) -> str:
        """Generate a summary of messages using the LLM."""
        try:
            client = get_llm_client()
            cost_service = get_cost_service()

            # Build summary prompt
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in messages
                if msg.get("role") != "system"
            ])

            summary_prompt = f"""Summarize this conversation in 2-3 sentences, capturing the key points and context needed to continue the discussion:

{conversation_text}

Summary:"""

            summary_model = self.summary_model or model
            response = client.chat(
                summary_prompt,
                model=summary_model,
                max_tokens=200,
                temperature=0.3
            )

            # Track cost
            cost_service.track_request(
                model=summary_model,
                provider="ollama",  # Will be corrected by actual usage
                input_tokens=self.estimate_tokens(summary_prompt),
                output_tokens=self.estimate_tokens(response.content),
                usage_dict=response.usage
            )

            return response.content.strip()

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            # Fallback to simple truncation
            return "Earlier conversation discussed various topics."

    def _apply_hybrid(
        self,
        messages: List[Dict],
        model: str,
        conversation_id: Optional[str] = None
    ) -> List[Dict]:
        """Apply rolling window first, then summarize if still too large."""
        # First apply rolling window
        messages = self._apply_rolling_window(messages)

        # If still too large, apply summarization
        if self.needs_optimization(model, messages):
            messages = self._apply_summarization(messages, model, conversation_id)

        return messages

    def _apply_adaptive(
        self,
        messages: List[Dict],
        model: str,
        conversation_id: Optional[str] = None
    ) -> List[Dict]:
        """Automatically choose the best strategy."""
        limit = self.get_context_limit(model)
        used = self.estimate_messages_tokens(messages)
        usage_ratio = used / limit

        if usage_ratio < 0.5:
            # Plenty of room, no optimization needed
            return messages

        elif usage_ratio < 0.75:
            # Getting full, use rolling window
            return self._apply_rolling_window(messages)

        elif usage_ratio < 0.9:
            # Nearly full, use summarization
            return self._apply_summarization(messages, model, conversation_id)

        else:
            # Critical, use hybrid
            return self._apply_hybrid(messages, model, conversation_id)

    def get_context_info(self, messages: List[Dict], model: str) -> Dict[str, Any]:
        """Get information about current context usage."""
        limit = self.get_context_limit(model)
        used = self.estimate_messages_tokens(messages)
        available = max(0, limit - used - RESPONSE_RESERVE)
        usage_pct = (used / limit) * 100 if limit > 0 else 0

        return {
            "model": model,
            "context_limit": limit,
            "tokens_used": used,
            "tokens_available": available,
            "response_reserve": RESPONSE_RESERVE,
            "usage_percent": round(usage_pct, 1),
            "message_count": len(messages),
            "strategy": self.strategy.value,
            "needs_optimization": self.needs_optimization(model, messages)
        }

    def clear_cache(self, conversation_id: Optional[str] = None):
        """Clear cached summaries."""
        if conversation_id:
            self.summaries.pop(conversation_id, None)
        else:
            self.summaries.clear()


# =============================================================================
# Singleton Access
# =============================================================================

_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create the context manager singleton."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager(
            strategy=ContextStrategy.ADAPTIVE,
            max_messages=20,
            summarize_threshold=0.75
        )
    return _context_manager


def set_context_strategy(strategy: str):
    """Update the context management strategy."""
    global _context_manager
    if _context_manager is None:
        _context_manager = get_context_manager()

    try:
        _context_manager.strategy = ContextStrategy(strategy)
        logger.info(f"Context strategy set to: {strategy}")
    except ValueError:
        logger.error(f"Unknown context strategy: {strategy}")
