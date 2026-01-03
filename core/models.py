"""
Claude Model Configuration

Defines available Claude models and provides model selection utilities.
"""

from enum import Enum
from typing import Optional


class ClaudeModels(Enum):
    """Available Claude models with their identifiers"""

    # Claude Opus 4.5 - Most capable, best for complex reasoning
    OPUS_4_5 = "claude-opus-4-5-20251101"

    # Claude Sonnet 4.5 - Balanced performance (RECOMMENDED DEFAULT)
    SONNET_4_5 = "claude-sonnet-4-5-20250929"

    # Claude Haiku 4.5 - Fastest, most cost-effective
    HAIKU_4_5 = "claude-haiku-4-5-20251001"

    # Legacy models (kept for backwards compatibility)
    SONNET_3_7 = "claude-3-7-sonnet-20250219"
    HAIKU_3_5 = "claude-3-5-haiku-20241022"


class ModelCapabilities:
    """Model capabilities and use case recommendations"""

    CAPABILITIES = {
        ClaudeModels.OPUS_4_5: {
            "name": "Claude Opus 4.5",
            "max_tokens": 64000,  # Claude 4 supports up to 128k with extended output
            "context_window": 200000,
            "best_for": ["complex reasoning", "coding", "analysis", "multi-step tasks"],
            "speed": "slow",
            "cost": "high",
            "extended_thinking": True,
        },
        ClaudeModels.SONNET_4_5: {
            "name": "Claude Sonnet 4.5",
            "max_tokens": 64000,  # Claude 4 supports up to 128k with extended output
            "context_window": 200000,
            "best_for": ["general purpose", "coding", "conversation", "balanced tasks"],
            "speed": "medium",
            "cost": "medium",
            "extended_thinking": False,
        },
        ClaudeModels.SONNET_3_7: {
            "name": "Claude Sonnet 3.7",
            "max_tokens": 8192,  # Legacy model limit
            "context_window": 200000,
            "best_for": ["fast responses", "simple tasks", "high throughput"],
            "speed": "fast",
            "cost": "low",
            "extended_thinking": False,
        },
        ClaudeModels.HAIKU_4_5: {
            "name": "Claude Haiku 4.5",
            "max_tokens": 64000,  # Claude 4 supports up to 128k with extended output
            "context_window": 200000,
            "best_for": ["simple queries", "high volume", "testing"],
            "speed": "fastest",
            "cost": "lowest",
            "extended_thinking": False,
        },
        ClaudeModels.HAIKU_3_5: {
            "name": "Claude Haiku 3.5 (Legacy)",
            "max_tokens": 8192,  # Legacy model limit
            "context_window": 200000,
            "best_for": ["legacy support"],
            "speed": "fastest",
            "cost": "lowest",
            "extended_thinking": False,
        },
    }

    @classmethod
    def get_info(cls, model: ClaudeModels) -> dict:
        """Get capabilities info for a model"""
        return cls.CAPABILITIES.get(model, {})

    @classmethod
    def get_max_tokens(cls, model: ClaudeModels) -> int:
        """Get max output tokens for a model"""
        return cls.CAPABILITIES.get(model, {}).get("max_tokens", 64000)


class ModelSelector:
    """Intelligent model selection based on task requirements"""

    @staticmethod
    def select_for_task(task_type: str) -> ClaudeModels:
        """
        Select appropriate model based on task type

        Args:
            task_type: One of: "simple", "standard", "complex", "coding",
                      "analysis", "fast", "testing"

        Returns:
            Recommended ClaudeModels enum value
        """
        task_map = {
            "simple": ClaudeModels.HAIKU_4_5,
            "fast": ClaudeModels.HAIKU_4_5,
            "testing": ClaudeModels.HAIKU_4_5,
            "standard": ClaudeModels.SONNET_4_5,
            "general": ClaudeModels.SONNET_4_5,
            "coding": ClaudeModels.SONNET_4_5,
            "conversation": ClaudeModels.SONNET_4_5,
            "complex": ClaudeModels.OPUS_4_5,
            "reasoning": ClaudeModels.OPUS_4_5,
            "analysis": ClaudeModels.OPUS_4_5,
        }

        return task_map.get(task_type.lower(), ClaudeModels.SONNET_4_5)

    @staticmethod
    def get_default() -> ClaudeModels:
        """Get the default recommended model"""
        return ClaudeModels.SONNET_4_5

    @staticmethod
    def get_cheapest() -> ClaudeModels:
        """Get the cheapest model for testing/high volume"""
        return ClaudeModels.HAIKU_4_5

    @staticmethod
    def get_best() -> ClaudeModels:
        """Get the most capable model"""
        return ClaudeModels.OPUS_4_5


def resolve_model(model_str: Optional[str] = None) -> str:
    """
    Resolve model string to valid Claude model ID

    Args:
        model_str: Model name/identifier (can be enum name, full ID, or None)

    Returns:
        Valid Claude model ID string
    """
    if not model_str:
        return ModelSelector.get_default().value

    # If already a valid model ID, return it
    if model_str.startswith("claude-"):
        return model_str

    # Try to match enum name
    model_upper = model_str.upper().replace("-", "_").replace(".", "_")
    for model in ClaudeModels:
        if model.name == model_upper:
            return model.value

    # Try partial matching
    model_lower = model_str.lower()
    if "opus" in model_lower:
        return ClaudeModels.OPUS_4_5.value
    elif "sonnet" in model_lower and ("4" in model_lower or "45" in model_lower):
        return ClaudeModels.SONNET_4_5.value
    elif "sonnet" in model_lower:
        return ClaudeModels.SONNET_3_7.value
    elif "haiku" in model_lower and ("4" in model_lower or "45" in model_lower):
        return ClaudeModels.HAIKU_4_5.value
    elif "haiku" in model_lower:
        return ClaudeModels.HAIKU_4_5.value  # Default to 4.5

    # Default fallback
    return ModelSelector.get_default().value


# Export convenience functions
def get_model_list() -> list[tuple[str, str]]:
    """Get list of (model_id, display_name) tuples for UI"""
    return [
        (model.value, ModelCapabilities.get_info(model)["name"])
        for model in ClaudeModels
    ]


def get_model_display_name(model: ClaudeModels) -> str:
    """Get human-readable display name for model"""
    return ModelCapabilities.get_info(model)["name"]


# Default model configuration
DEFAULT_MODEL = ClaudeModels.SONNET_4_5
DEFAULT_MAX_TOKENS = 64000  # Claude 4 models support up to 128k with extended output
DEFAULT_TEMPERATURE = 1.0  # Claude's default
