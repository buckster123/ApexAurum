"""
Rate Limiter for Claude API

Implements sliding window rate limiting to respect Claude's API limits:
- 50 requests per minute
- 40,000 input tokens per minute
- 8,000 output tokens per minute

Tracks usage and prevents hitting rate limits.
"""

import time
import logging
from typing import Tuple, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RequestRecord:
    """Record of a single API request"""
    timestamp: float
    input_tokens: int
    output_tokens: int


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.

    Tracks requests and tokens over a 60-second window.
    """

    def __init__(
        self,
        max_requests_per_min: int = 2000,
        max_input_tokens_per_min: int = 800000,
        max_output_tokens_per_min: int = 160000,
        safety_margin: float = 0.95  # Use 95% of limits
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests_per_min: Maximum requests per minute
            max_input_tokens_per_min: Maximum input tokens per minute
            max_output_tokens_per_min: Maximum output tokens per minute
            safety_margin: Safety factor (0.9 = use 90% of limit)
        """
        self.max_requests = max_requests_per_min
        self.max_input_tokens = max_input_tokens_per_min
        self.max_output_tokens = max_output_tokens_per_min
        self.safety_margin = safety_margin

        # History of requests in the last 60 seconds
        self.request_history: List[RequestRecord] = []

        logger.info(
            f"Rate limiter initialized: {max_requests_per_min} req/min, "
            f"{max_input_tokens_per_min} input tokens/min, "
            f"{max_output_tokens_per_min} output tokens/min"
        )

    def _clean_old_records(self):
        """Remove records older than 60 seconds"""
        cutoff_time = time.time() - 60.0
        self.request_history = [
            record for record in self.request_history
            if record.timestamp > cutoff_time
        ]

    def _get_current_usage(self) -> Tuple[int, int, int]:
        """
        Get current usage in the last 60 seconds.

        Returns:
            Tuple of (request_count, input_tokens, output_tokens)
        """
        self._clean_old_records()

        request_count = len(self.request_history)
        input_tokens = sum(r.input_tokens for r in self.request_history)
        output_tokens = sum(r.output_tokens for r in self.request_history)

        return request_count, input_tokens, output_tokens

    def can_make_request(self, estimated_input_tokens: int = 0, estimated_output_tokens: int = 0) -> Tuple[bool, float]:
        """
        Check if a request can be made without exceeding rate limits.

        Args:
            estimated_input_tokens: Estimated input tokens for the request
            estimated_output_tokens: Estimated output tokens for the request

        Returns:
            Tuple of (can_proceed, wait_time)
            - can_proceed: True if request can be made now
            - wait_time: Seconds to wait if cannot proceed (0 if can proceed)
        """
        self._clean_old_records()
        req_count, input_tokens, output_tokens = self._get_current_usage()

        # Apply safety margin
        safe_max_requests = int(self.max_requests * self.safety_margin)
        safe_max_input = int(self.max_input_tokens * self.safety_margin)
        safe_max_output = int(self.max_output_tokens * self.safety_margin)

        # Check if adding this request would exceed limits
        would_exceed_requests = (req_count + 1) > safe_max_requests
        would_exceed_input = (input_tokens + estimated_input_tokens) > safe_max_input
        would_exceed_output = (output_tokens + estimated_output_tokens) > safe_max_output

        if would_exceed_requests or would_exceed_input or would_exceed_output:
            # Calculate wait time (time until oldest record expires)
            if self.request_history:
                oldest_timestamp = min(r.timestamp for r in self.request_history)
                wait_time = max(0.0, 60.0 - (time.time() - oldest_timestamp) + 1.0)  # +1s buffer
            else:
                wait_time = 1.0  # Default 1s wait

            reason = []
            if would_exceed_requests:
                reason.append(f"requests ({req_count + 1}/{safe_max_requests})")
            if would_exceed_input:
                reason.append(f"input tokens ({input_tokens + estimated_input_tokens}/{safe_max_input})")
            if would_exceed_output:
                reason.append(f"output tokens ({output_tokens + estimated_output_tokens}/{safe_max_output})")

            logger.warning(
                f"Rate limit approaching: {', '.join(reason)}. "
                f"Waiting {wait_time:.1f}s"
            )

            return False, wait_time

        return True, 0.0

    def record_request(self, input_tokens: int, output_tokens: int):
        """
        Record a completed request.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
        """
        record = RequestRecord(
            timestamp=time.time(),
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        self.request_history.append(record)

        logger.debug(
            f"Recorded request: {input_tokens} input, {output_tokens} output tokens"
        )

    def get_usage_stats(self) -> Dict[str, any]:
        """
        Get current usage statistics.

        Returns:
            Dictionary with usage stats for the last 60 seconds
        """
        self._clean_old_records()
        req_count, input_tokens, output_tokens = self._get_current_usage()

        return {
            "requests": req_count,
            "requests_limit": self.max_requests,
            "requests_percent": (req_count / self.max_requests) * 100,
            "input_tokens": input_tokens,
            "input_tokens_limit": self.max_input_tokens,
            "input_tokens_percent": (input_tokens / self.max_input_tokens) * 100,
            "output_tokens": output_tokens,
            "output_tokens_limit": self.max_output_tokens,
            "output_tokens_percent": (output_tokens / self.max_output_tokens) * 100,
            "window_seconds": 60,
        }

    def get_status_message(self) -> str:
        """
        Get a human-readable status message.

        Returns:
            Status message describing current usage
        """
        stats = self.get_usage_stats()

        max_percent = max(
            stats["requests_percent"],
            stats["input_tokens_percent"],
            stats["output_tokens_percent"]
        )

        if max_percent < 50:
            return "✅ All systems normal"
        elif max_percent < 80:
            return "⚠️ Moderate usage"
        elif max_percent < 95:
            return "🔶 High usage - approaching limits"
        else:
            return "🔴 Very high usage - throttling active"

    def reset(self):
        """Reset all tracking (useful for testing)"""
        self.request_history = []
        logger.info("Rate limiter reset")
