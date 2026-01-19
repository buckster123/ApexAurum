"""
Cost Tracker for AI APIs

Tracks token usage and calculates costs based on model-specific pricing.
Supports cache pricing for APIs with prompt caching (like Claude).

Pricing is configurable - defaults to Claude pricing as of January 2026:
- Claude Opus 4.5: $15/$75 per 1M input/output tokens
- Claude Sonnet 4.5: $3/$15 per 1M input/output tokens
- Claude Haiku 4.5: $0.80/$4.00 per 1M input/output tokens

Cache pricing:
- Cache write: base_price * 1.25 (+25%)
- Cache read: base_price * 0.10 (-90% savings!)

Usage:
    from reusable_lib.costs import CostTracker

    tracker = CostTracker()

    # Record API usage
    tracker.record_usage(
        model="claude-sonnet-4-5",
        input_tokens=1000,
        output_tokens=500,
        cache_creation_tokens=100,  # Optional: tokens written to cache
        cache_read_tokens=800       # Optional: tokens read from cache
    )

    # Get statistics
    stats = tracker.get_session_stats()
    print(f"Session cost: ${stats['cost']:.4f}")
    print(f"Total tokens: {stats['total_tokens']}")

    # Cost breakdown by model
    breakdown = tracker.get_cost_breakdown_by_model()
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# Pricing per 1M tokens (input_price, output_price)
MODEL_PRICING = {
    # Claude 4.5 models
    "claude-opus-4-5": (15.00, 75.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (0.80, 4.00),
    # Claude 3.x models (legacy)
    "claude-sonnet-3-7": (3.00, 15.00),
    "claude-haiku-3-5": (0.25, 1.25),
    # OpenAI models (for reference/future use)
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4o": (5.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
}

# Cache pricing multipliers (write_multiplier, read_multiplier)
# Cache write = base_price * 1.25 (+25%)
# Cache read = base_price * 0.10 (-90% savings)
CACHE_PRICING = {
    "claude-opus-4-5": (1.25, 0.10),
    "claude-sonnet-4-5": (1.25, 0.10),
    "claude-haiku-4-5": (1.25, 0.10),
    "claude-sonnet-3-7": (1.25, 0.10),
    "claude-haiku-3-5": (1.25, 0.10),
}

# Fallback pricing for unknown models
DEFAULT_PRICING = (3.00, 15.00)  # Sonnet-level pricing
DEFAULT_CACHE_PRICING = (1.25, 0.10)


@dataclass
class UsageRecord:
    """Record of token usage for a single API request"""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    # Cache tokens (optional)
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_cost: float = 0.0
    cache_read_cost: float = 0.0


class CostTracker:
    """
    Tracks token usage and calculates costs.

    Maintains both session statistics (reset on restart) and
    total statistics (can be persisted).
    """

    def __init__(self, custom_pricing: Optional[Dict] = None):
        """
        Initialize cost tracker.

        Args:
            custom_pricing: Optional custom pricing dict to override defaults.
                           Format: {"model-name": (input_per_1m, output_per_1m)}
        """
        self.custom_pricing = custom_pricing or {}

        # Session stats (reset when app restarts)
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        self.session_cost = 0.0

        # Cache stats
        self.session_cache_creation_tokens = 0
        self.session_cache_read_tokens = 0
        self.session_cache_write_cost = 0.0
        self.session_cache_read_cost = 0.0

        # Total stats (cumulative, can be persisted)
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

        # Total cache stats
        self.total_cache_creation_tokens = 0
        self.total_cache_read_tokens = 0
        self.total_cache_write_cost = 0.0
        self.total_cache_read_cost = 0.0

        # Request history
        self.history: List[UsageRecord] = []

        logger.info("Cost tracker initialized")

    def get_model_pricing(self, model: str) -> tuple:
        """
        Get pricing for a model.

        Args:
            model: Model ID (e.g., 'claude-sonnet-4-5')

        Returns:
            Tuple of (input_price_per_1m, output_price_per_1m)
        """
        model_key = model.lower()

        # Check custom pricing first
        if model_key in self.custom_pricing:
            return self.custom_pricing[model_key]

        # Check default pricing (exact match)
        if model_key in MODEL_PRICING:
            return MODEL_PRICING[model_key]

        # Try partial match
        for key in MODEL_PRICING:
            if key in model_key:
                return MODEL_PRICING[key]

        logger.warning(f"Unknown model '{model}', using default pricing")
        return DEFAULT_PRICING

    def get_cache_pricing(self, model: str) -> tuple:
        """
        Get cache pricing multipliers for a model.

        Args:
            model: Model ID

        Returns:
            Tuple of (write_multiplier, read_multiplier)
        """
        model_key = model.lower()

        if model_key in CACHE_PRICING:
            return CACHE_PRICING[model_key]

        for key in CACHE_PRICING:
            if key in model_key:
                return CACHE_PRICING[key]

        return DEFAULT_CACHE_PRICING

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, float]:
        """
        Calculate cost for a request (excluding cache).

        Args:
            model: Model ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Dictionary with cost breakdown
        """
        input_price, output_price = self.get_model_pricing(model)

        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        total_cost = input_cost + output_cost

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }

    def calculate_cache_cost(
        self,
        model: str,
        cache_creation_tokens: int,
        cache_read_tokens: int
    ) -> Dict[str, float]:
        """
        Calculate cache-specific costs.

        Args:
            model: Model ID
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache

        Returns:
            Dictionary with cache cost breakdown
        """
        if cache_creation_tokens == 0 and cache_read_tokens == 0:
            return {
                "cache_write_cost": 0.0,
                "cache_read_cost": 0.0,
                "total_cache_cost": 0.0,
                "cache_savings": 0.0
            }

        base_input_price, _ = self.get_model_pricing(model)
        write_mult, read_mult = self.get_cache_pricing(model)

        # Cache write: base_price * 1.25 (+25%)
        cache_write_cost = (cache_creation_tokens / 1_000_000) * (base_input_price * write_mult)

        # Cache read: base_price * 0.10 (-90%)
        cache_read_cost = (cache_read_tokens / 1_000_000) * (base_input_price * read_mult)

        # Calculate savings (what it would have cost without cache)
        would_have_cost = (cache_read_tokens / 1_000_000) * base_input_price
        savings = would_have_cost - cache_read_cost

        return {
            "cache_write_cost": cache_write_cost,
            "cache_read_cost": cache_read_cost,
            "total_cache_cost": cache_write_cost + cache_read_cost,
            "cache_savings": savings
        }

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0
    ):
        """
        Record token usage and calculate cost.

        Args:
            model: Model ID
            input_tokens: Number of input tokens (includes cache tokens)
            output_tokens: Number of output tokens generated
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache
        """
        # Calculate base costs (excluding cache tokens from input)
        regular_input_tokens = input_tokens - cache_creation_tokens - cache_read_tokens
        regular_input_tokens = max(0, regular_input_tokens)  # Safety check

        costs = self.calculate_cost(model, regular_input_tokens, output_tokens)
        cache_costs = self.calculate_cache_cost(model, cache_creation_tokens, cache_read_tokens)

        total_cost = costs["total_cost"] + cache_costs["total_cache_cost"]

        # Update session stats
        self.session_input_tokens += input_tokens
        self.session_output_tokens += output_tokens
        self.session_cost += total_cost

        self.session_cache_creation_tokens += cache_creation_tokens
        self.session_cache_read_tokens += cache_read_tokens
        self.session_cache_write_cost += cache_costs["cache_write_cost"]
        self.session_cache_read_cost += cache_costs["cache_read_cost"]

        # Update total stats
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += total_cost

        self.total_cache_creation_tokens += cache_creation_tokens
        self.total_cache_read_tokens += cache_read_tokens
        self.total_cache_write_cost += cache_costs["cache_write_cost"]
        self.total_cache_read_cost += cache_costs["cache_read_cost"]

        # Create record
        record = UsageRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=costs["input_cost"],
            output_cost=costs["output_cost"],
            total_cost=total_cost,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_cost=cache_costs["cache_write_cost"],
            cache_read_cost=cache_costs["cache_read_cost"]
        )
        self.history.append(record)

        logger.debug(
            f"Recorded usage: {input_tokens} in + {output_tokens} out = ${total_cost:.6f}"
        )

    def get_session_stats(self) -> Dict[str, any]:
        """Get statistics for the current session."""
        return {
            "input_tokens": self.session_input_tokens,
            "output_tokens": self.session_output_tokens,
            "total_tokens": self.session_input_tokens + self.session_output_tokens,
            "cost": self.session_cost,
            "request_count": len(self.history),
            "cache_creation_tokens": self.session_cache_creation_tokens,
            "cache_read_tokens": self.session_cache_read_tokens,
            "cache_write_cost": self.session_cache_write_cost,
            "cache_read_cost": self.session_cache_read_cost,
        }

    def get_total_stats(self) -> Dict[str, any]:
        """Get cumulative statistics."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "cost": self.total_cost,
            "request_count": len(self.history),
            "cache_creation_tokens": self.total_cache_creation_tokens,
            "cache_read_tokens": self.total_cache_read_tokens,
        }

    def get_cost_breakdown_by_model(self) -> Dict[str, Dict[str, any]]:
        """Get cost breakdown by model."""
        breakdown = {}

        for record in self.history:
            model = record.model
            if model not in breakdown:
                breakdown[model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "request_count": 0
                }

            breakdown[model]["input_tokens"] += record.input_tokens
            breakdown[model]["output_tokens"] += record.output_tokens
            breakdown[model]["cost"] += record.total_cost
            breakdown[model]["request_count"] += 1

        return breakdown

    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache-specific statistics."""
        total_cache_tokens = self.session_cache_creation_tokens + self.session_cache_read_tokens
        total_tokens = self.session_input_tokens

        return {
            "cache_creation_tokens": self.session_cache_creation_tokens,
            "cache_read_tokens": self.session_cache_read_tokens,
            "cache_write_cost": self.session_cache_write_cost,
            "cache_read_cost": self.session_cache_read_cost,
            "total_cache_cost": self.session_cache_write_cost + self.session_cache_read_cost,
            "cache_hit_rate": (
                self.session_cache_read_tokens / total_tokens * 100
                if total_tokens > 0 else 0
            ),
        }

    def reset_session(self):
        """Reset session statistics (keeps total)."""
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        self.session_cost = 0.0
        self.session_cache_creation_tokens = 0
        self.session_cache_read_tokens = 0
        self.session_cache_write_cost = 0.0
        self.session_cache_read_cost = 0.0
        self.history = []
        logger.info("Session stats reset")

    def reset_all(self):
        """Reset all statistics."""
        self.reset_session()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.total_cache_creation_tokens = 0
        self.total_cache_read_tokens = 0
        self.total_cache_write_cost = 0.0
        self.total_cache_read_cost = 0.0
        logger.info("All stats reset")

    def to_dict(self) -> Dict[str, any]:
        """Serialize to dictionary for persistence."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "total_cache_creation_tokens": self.total_cache_creation_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
        }

    def from_dict(self, data: Dict[str, any]):
        """Restore from dictionary."""
        self.total_input_tokens = data.get("total_input_tokens", 0)
        self.total_output_tokens = data.get("total_output_tokens", 0)
        self.total_cost = data.get("total_cost", 0.0)
        self.total_cache_creation_tokens = data.get("total_cache_creation_tokens", 0)
        self.total_cache_read_tokens = data.get("total_cache_read_tokens", 0)
