"""
Settings Presets Service

Manages saved configurations (presets) for quick switching between setups.
Includes built-in presets and user-defined custom presets.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from app_config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Built-in Presets
# =============================================================================

BUILTIN_PRESETS = {
    "default": {
        "name": "Default",
        "description": "Balanced settings for general use",
        "provider": "ollama",
        "model": "qwen2.5:3b",
        "temperature": 0.7,
        "max_tokens": 2048,
        "use_tools": True,
        "context_strategy": "adaptive",
        "context_max_messages": 20,
        "builtin": True
    },
    "creative": {
        "name": "Creative",
        "description": "Higher temperature for creative tasks",
        "provider": "ollama",
        "model": "qwen2.5:3b",
        "temperature": 0.9,
        "max_tokens": 4096,
        "use_tools": True,
        "context_strategy": "summarize",
        "context_max_messages": 30,
        "builtin": True
    },
    "precise": {
        "name": "Precise",
        "description": "Lower temperature for factual tasks",
        "provider": "ollama",
        "model": "qwen2.5:3b",
        "temperature": 0.3,
        "max_tokens": 2048,
        "use_tools": True,
        "context_strategy": "adaptive",
        "context_max_messages": 20,
        "builtin": True
    },
    "fast": {
        "name": "Fast",
        "description": "Smaller model, shorter responses",
        "provider": "ollama",
        "model": "qwen2:0.5b",
        "temperature": 0.7,
        "max_tokens": 1024,
        "use_tools": False,
        "context_strategy": "rolling",
        "context_max_messages": 10,
        "builtin": True
    },
    "claude_balanced": {
        "name": "Claude Balanced",
        "description": "Claude API with balanced settings",
        "provider": "claude",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.7,
        "max_tokens": 4096,
        "use_tools": True,
        "context_strategy": "adaptive",
        "context_max_messages": 30,
        "builtin": True
    },
    "claude_deep": {
        "name": "Claude Deep Thinking",
        "description": "Claude Opus for complex reasoning",
        "provider": "claude",
        "model": "claude-opus-4-5-20250929",
        "temperature": 0.5,
        "max_tokens": 8192,
        "use_tools": True,
        "context_strategy": "summarize",
        "context_max_messages": 50,
        "builtin": True
    }
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Preset:
    """A settings preset."""
    id: str
    name: str
    description: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    use_tools: bool
    context_strategy: str
    context_max_messages: int
    builtin: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Preset":
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# Presets Service
# =============================================================================

class PresetsService:
    """
    Service for managing settings presets.

    Provides CRUD operations for presets and preset switching.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize presets service.

        Args:
            storage_path: Path to presets JSON file
        """
        self.storage_path = storage_path or settings.DATA_DIR / "presets.json"
        self.presets: Dict[str, Preset] = {}
        self.active_preset_id: Optional[str] = None

        self._load_builtins()
        self._load_custom()

    def _load_builtins(self):
        """Load built-in presets."""
        for preset_id, data in BUILTIN_PRESETS.items():
            self.presets[preset_id] = Preset(
                id=preset_id,
                **data
            )

    def _load_custom(self):
        """Load custom presets from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)

                for preset_id, preset_data in data.get("presets", {}).items():
                    if not preset_data.get("builtin", False):
                        self.presets[preset_id] = Preset.from_dict(preset_data)

                self.active_preset_id = data.get("active_preset_id")
                logger.info(f"Loaded {len([p for p in self.presets.values() if not p.builtin])} custom presets")

        except Exception as e:
            logger.error(f"Error loading presets: {e}")

    def _save_custom(self):
        """Save custom presets to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Only save custom presets
            custom_presets = {
                pid: p.to_dict()
                for pid, p in self.presets.items()
                if not p.builtin
            }

            data = {
                "presets": custom_presets,
                "active_preset_id": self.active_preset_id,
                "updated_at": datetime.now().isoformat()
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving presets: {e}")

    def list_presets(self) -> List[Dict[str, Any]]:
        """
        List all available presets.

        Returns:
            List of preset dictionaries
        """
        result = []
        for preset in self.presets.values():
            d = preset.to_dict()
            d["is_active"] = preset.id == self.active_preset_id
            result.append(d)

        # Sort: active first, then builtins, then custom
        result.sort(key=lambda p: (
            not p.get("is_active", False),
            not p.get("builtin", False),
            p.get("name", "")
        ))

        return result

    def get_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific preset.

        Args:
            preset_id: Preset ID

        Returns:
            Preset dictionary or None
        """
        preset = self.presets.get(preset_id)
        if preset:
            d = preset.to_dict()
            d["is_active"] = preset.id == self.active_preset_id
            return d
        return None

    def get_active_preset(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active preset.

        Returns:
            Active preset dictionary or None
        """
        if self.active_preset_id:
            return self.get_preset(self.active_preset_id)
        return self.get_preset("default")

    def create_preset(
        self,
        name: str,
        description: str = "",
        provider: str = "ollama",
        model: str = "qwen2.5:3b",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_tools: bool = True,
        context_strategy: str = "adaptive",
        context_max_messages: int = 20
    ) -> Dict[str, Any]:
        """
        Create a new custom preset.

        Returns:
            Created preset dictionary
        """
        # Generate unique ID
        import uuid
        preset_id = f"custom_{uuid.uuid4().hex[:8]}"

        now = datetime.now().isoformat()
        preset = Preset(
            id=preset_id,
            name=name,
            description=description,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_tools=use_tools,
            context_strategy=context_strategy,
            context_max_messages=context_max_messages,
            builtin=False,
            created_at=now,
            updated_at=now
        )

        self.presets[preset_id] = preset
        self._save_custom()

        logger.info(f"Created preset: {preset_id} ({name})")
        return preset.to_dict()

    def update_preset(
        self,
        preset_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing preset.

        Args:
            preset_id: Preset ID
            **kwargs: Fields to update

        Returns:
            Updated preset or None if not found
        """
        preset = self.presets.get(preset_id)
        if not preset:
            return None

        if preset.builtin:
            logger.warning(f"Cannot modify builtin preset: {preset_id}")
            return None

        # Update allowed fields
        allowed_fields = [
            "name", "description", "provider", "model", "temperature",
            "max_tokens", "use_tools", "context_strategy", "context_max_messages"
        ]

        for field in allowed_fields:
            if field in kwargs:
                setattr(preset, field, kwargs[field])

        preset.updated_at = datetime.now().isoformat()
        self._save_custom()

        logger.info(f"Updated preset: {preset_id}")
        return preset.to_dict()

    def delete_preset(self, preset_id: str) -> bool:
        """
        Delete a custom preset.

        Args:
            preset_id: Preset ID

        Returns:
            True if deleted, False if not found or builtin
        """
        preset = self.presets.get(preset_id)
        if not preset:
            return False

        if preset.builtin:
            logger.warning(f"Cannot delete builtin preset: {preset_id}")
            return False

        del self.presets[preset_id]

        # Clear active if deleted
        if self.active_preset_id == preset_id:
            self.active_preset_id = "default"

        self._save_custom()
        logger.info(f"Deleted preset: {preset_id}")
        return True

    def activate_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """
        Set a preset as active.

        Args:
            preset_id: Preset ID to activate

        Returns:
            Activated preset or None if not found
        """
        preset = self.presets.get(preset_id)
        if not preset:
            return None

        self.active_preset_id = preset_id
        self._save_custom()

        logger.info(f"Activated preset: {preset_id}")
        return self.get_preset(preset_id)

    def duplicate_preset(self, preset_id: str, new_name: str) -> Optional[Dict[str, Any]]:
        """
        Duplicate an existing preset.

        Args:
            preset_id: Preset ID to duplicate
            new_name: Name for the new preset

        Returns:
            New preset or None if source not found
        """
        source = self.presets.get(preset_id)
        if not source:
            return None

        return self.create_preset(
            name=new_name,
            description=f"Copy of {source.name}",
            provider=source.provider,
            model=source.model,
            temperature=source.temperature,
            max_tokens=source.max_tokens,
            use_tools=source.use_tools,
            context_strategy=source.context_strategy,
            context_max_messages=source.context_max_messages
        )

    def export_presets(self) -> Dict[str, Any]:
        """
        Export all custom presets.

        Returns:
            Dictionary of custom presets for backup
        """
        return {
            pid: p.to_dict()
            for pid, p in self.presets.items()
            if not p.builtin
        }

    def import_presets(self, presets_data: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Import presets from backup.

        Args:
            presets_data: Dictionary of preset data

        Returns:
            Import summary
        """
        imported = 0
        skipped = 0

        for preset_id, data in presets_data.items():
            if data.get("builtin", False):
                skipped += 1
                continue

            if preset_id in self.presets and self.presets[preset_id].builtin:
                skipped += 1
                continue

            try:
                # Generate new ID to avoid conflicts
                data["id"] = f"imported_{preset_id}"
                data["builtin"] = False
                self.presets[data["id"]] = Preset.from_dict(data)
                imported += 1
            except Exception as e:
                logger.error(f"Error importing preset {preset_id}: {e}")
                skipped += 1

        self._save_custom()

        return {
            "imported": imported,
            "skipped": skipped
        }


# =============================================================================
# Singleton Access
# =============================================================================

_presets_service: Optional[PresetsService] = None


def get_presets_service() -> PresetsService:
    """Get or create the presets service singleton."""
    global _presets_service
    if _presets_service is None:
        _presets_service = PresetsService()
    return _presets_service
