"""
Cost Tracking Service

Tracks token usage and calculates costs per conversation and session.
Supports both Claude API (actual usage) and local models (estimated).
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

from app_config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Pricing Data (per 1M tokens)
# =============================================================================

# Claude API pricing (as of Jan 2026)
CLAUDE_PRICING = {
    "claude-opus-4-5-20250929": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
    # Fallback for unknown models
    "default": {"input": 3.00, "output": 15.00}
}

# Local models are free but we track tokens for context management
LOCAL_PRICING = {
    "default": {"input": 0.0, "output": 0.0}
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class UsageRecord:
    """A single usage record."""
    timestamp: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    conversation_id: Optional[str] = None
    tool_name: Optional[str] = None  # If this was a tool call


@dataclass
class ConversationUsage:
    """Aggregated usage for a conversation."""
    conversation_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0
    tool_calls: int = 0
    started_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class SessionStats:
    """Session-level statistics."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0
    tool_calls: int = 0
    conversations: int = 0
    started_at: Optional[str] = None


# =============================================================================
# Cost Tracking Service
# =============================================================================

class CostService:
    """
    Service for tracking token usage and costs.

    Tracks per-request, per-conversation, and session-level statistics.
    Persists data to JSON for historical analysis.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize cost tracking service.

        Args:
            storage_path: Path to JSON storage file
        """
        self.storage_path = storage_path or settings.DATA_DIR / "cost_tracking.json"
        self.records: List[UsageRecord] = []
        self.conversations: Dict[str, ConversationUsage] = {}
        self.session_stats = SessionStats(started_at=datetime.now().isoformat())

        self._ensure_storage()
        self._load_data()

    def _ensure_storage(self):
        """Ensure storage directory exists."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_data(self):
        """Load historical data from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    # We don't load old records into memory, just keep the file
                    logger.info(f"Cost tracking storage initialized: {self.storage_path}")
        except Exception as e:
            logger.error(f"Error loading cost data: {e}")

    def _save_data(self):
        """Save current session data to storage."""
        try:
            # Load existing data
            existing = []
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    existing = data.get("records", [])

            # Append new records
            new_records = [asdict(r) for r in self.records]
            all_records = existing + new_records

            # Keep only last 1000 records to avoid unbounded growth
            if len(all_records) > 1000:
                all_records = all_records[-1000:]

            with open(self.storage_path, 'w') as f:
                json.dump({
                    "records": all_records,
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving cost data: {e}")

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple heuristic: ~4 characters per token.
        This is a rough estimate; actual counts vary by model.

        Args:
            text: The text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        # Rough estimate: 4 chars per token (conservative)
        return max(1, len(text) // 4)

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: str = "ollama"
    ) -> float:
        """
        Calculate cost for a request.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Provider name (ollama, claude, etc.)

        Returns:
            Cost in USD
        """
        if provider.lower() in ["ollama", "local"]:
            return 0.0

        if provider.lower() in ["claude", "anthropic"]:
            pricing = CLAUDE_PRICING.get(model, CLAUDE_PRICING["default"])
        else:
            # Unknown provider, assume free for now
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return round(input_cost + output_cost, 6)

    def track_request(
        self,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        conversation_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        usage_dict: Optional[Dict] = None
    ) -> UsageRecord:
        """
        Track a single request's usage.

        Args:
            model: Model name
            provider: Provider name
            input_tokens: Input token count (or estimate)
            output_tokens: Output token count (or estimate)
            conversation_id: Optional conversation ID
            tool_name: Optional tool name if this was a tool call
            usage_dict: Optional usage dict from API response

        Returns:
            The created usage record
        """
        # Use actual usage from API if available
        if usage_dict:
            input_tokens = usage_dict.get("input_tokens", input_tokens)
            output_tokens = usage_dict.get("output_tokens", output_tokens)

        cost = self.calculate_cost(model, input_tokens, output_tokens, provider)

        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            conversation_id=conversation_id,
            tool_name=tool_name
        )

        self.records.append(record)

        # Update session stats
        self.session_stats.total_input_tokens += input_tokens
        self.session_stats.total_output_tokens += output_tokens
        self.session_stats.total_cost += cost
        self.session_stats.request_count += 1
        if tool_name:
            self.session_stats.tool_calls += 1

        # Update conversation stats if applicable
        if conversation_id:
            self._update_conversation_usage(conversation_id, record)

        # Persist periodically (every 10 requests)
        if len(self.records) % 10 == 0:
            self._save_data()

        logger.debug(f"Tracked: {input_tokens}in/{output_tokens}out = ${cost:.6f} ({model})")

        return record

    def _update_conversation_usage(self, conv_id: str, record: UsageRecord):
        """Update conversation-level statistics."""
        if conv_id not in self.conversations:
            self.conversations[conv_id] = ConversationUsage(
                conversation_id=conv_id,
                started_at=record.timestamp
            )
            self.session_stats.conversations += 1

        conv = self.conversations[conv_id]
        conv.total_input_tokens += record.input_tokens
        conv.total_output_tokens += record.output_tokens
        conv.total_cost += record.cost
        conv.request_count += 1
        if record.tool_name:
            conv.tool_calls += 1
        conv.updated_at = record.timestamp

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get current session statistics.

        Returns:
            Dict with session stats
        """
        return {
            "input_tokens": self.session_stats.total_input_tokens,
            "output_tokens": self.session_stats.total_output_tokens,
            "total_tokens": self.session_stats.total_input_tokens + self.session_stats.total_output_tokens,
            "cost": round(self.session_stats.total_cost, 4),
            "cost_formatted": f"${self.session_stats.total_cost:.4f}",
            "requests": self.session_stats.request_count,
            "tool_calls": self.session_stats.tool_calls,
            "conversations": self.session_stats.conversations,
            "started_at": self.session_stats.started_at
        }

    def get_conversation_stats(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific conversation.

        Args:
            conv_id: Conversation ID

        Returns:
            Dict with conversation stats or None if not found
        """
        conv = self.conversations.get(conv_id)
        if not conv:
            return None

        return {
            "conversation_id": conv.conversation_id,
            "input_tokens": conv.total_input_tokens,
            "output_tokens": conv.total_output_tokens,
            "total_tokens": conv.total_input_tokens + conv.total_output_tokens,
            "cost": round(conv.total_cost, 4),
            "cost_formatted": f"${conv.total_cost:.4f}",
            "requests": conv.request_count,
            "tool_calls": conv.tool_calls,
            "started_at": conv.started_at,
            "updated_at": conv.updated_at
        }

    def get_recent_records(self, limit: int = 50) -> List[Dict]:
        """
        Get recent usage records.

        Args:
            limit: Maximum records to return

        Returns:
            List of recent records
        """
        records = self.records[-limit:] if len(self.records) > limit else self.records
        return [asdict(r) for r in reversed(records)]

    def get_model_breakdown(self) -> Dict[str, Dict]:
        """
        Get usage breakdown by model.

        Returns:
            Dict mapping model name to usage stats
        """
        breakdown = {}

        for record in self.records:
            if record.model not in breakdown:
                breakdown[record.model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "requests": 0
                }

            breakdown[record.model]["input_tokens"] += record.input_tokens
            breakdown[record.model]["output_tokens"] += record.output_tokens
            breakdown[record.model]["cost"] += record.cost
            breakdown[record.model]["requests"] += 1

        # Round costs
        for model in breakdown:
            breakdown[model]["cost"] = round(breakdown[model]["cost"], 4)

        return breakdown

    def reset_session(self):
        """Reset session statistics (keeps historical data)."""
        self._save_data()  # Save current data first
        self.records = []
        self.conversations = {}
        self.session_stats = SessionStats(started_at=datetime.now().isoformat())
        logger.info("Session stats reset")

    def flush(self):
        """Force save all pending data."""
        self._save_data()


# =============================================================================
# Singleton Access
# =============================================================================

_cost_service: Optional[CostService] = None


def get_cost_service() -> CostService:
    """Get or create the cost service singleton."""
    global _cost_service
    if _cost_service is None:
        _cost_service = CostService()
    return _cost_service
