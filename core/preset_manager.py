"""
Preset Manager - Phase 2A
Manages settings presets including built-in and custom presets.

Allows users to:
- Switch between built-in presets with one click
- Save custom presets from current settings
- Manage (view, edit, delete) custom presets
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PresetManager:
    """Manages settings presets for quick configuration switching"""

    VERSION = "1.0"

    # Built-in preset definitions
    BUILT_IN_PRESETS = {
        "speed_mode": {
            "id": "speed_mode",
            "name": "🚀 Speed Mode",
            "description": "Fastest responses with minimal cost",
            "is_built_in": True,
            "settings": {
                "model": "claude-3-5-haiku-20241022",
                "cache_strategy": "conservative",
                "context_strategy": "manual",
                "temperature": 0.7,
                "preserve_recent_count": 5,
                "auto_summarize": False,
                "default_subagent_model": "Haiku (fast & cheap)"
            },
            "created_at": "2026-01-02T00:00:00",
            "updated_at": "2026-01-02T00:00:00"
        },
        "cost_saver": {
            "id": "cost_saver",
            "name": "💰 Cost Saver",
            "description": "Maximum savings with aggressive caching",
            "is_built_in": True,
            "settings": {
                "model": "claude-3-5-haiku-20241022",
                "cache_strategy": "aggressive",
                "context_strategy": "aggressive",
                "temperature": 0.8,
                "preserve_recent_count": 5,
                "auto_summarize": True,
                "default_subagent_model": "Haiku (fast & cheap)"
            },
            "created_at": "2026-01-02T00:00:00",
            "updated_at": "2026-01-02T00:00:00"
        },
        "deep_thinking": {
            "id": "deep_thinking",
            "name": "🧠 Deep Thinking",
            "description": "Most capable model for complex reasoning",
            "is_built_in": True,
            "settings": {
                "model": "claude-opus-4-5-20251101",
                "cache_strategy": "balanced",
                "context_strategy": "conservative",
                "temperature": 1.0,
                "preserve_recent_count": 20,
                "auto_summarize": True,
                "default_subagent_model": "Opus (best quality)"
            },
            "created_at": "2026-01-02T00:00:00",
            "updated_at": "2026-01-02T00:00:00"
        },
        "research_mode": {
            "id": "research_mode",
            "name": "🔬 Research Mode",
            "description": "Balanced setup for research tasks",
            "is_built_in": True,
            "settings": {
                "model": "claude-sonnet-4-5-20250929",
                "cache_strategy": "balanced",
                "context_strategy": "balanced",
                "temperature": 0.9,
                "preserve_recent_count": 10,
                "auto_summarize": True,
                "default_subagent_model": "Sonnet (balanced)"
            },
            "created_at": "2026-01-02T00:00:00",
            "updated_at": "2026-01-02T00:00:00"
        },
        "simple_chat": {
            "id": "simple_chat",
            "name": "💬 Simple Chat",
            "description": "Standard conversation mode",
            "is_built_in": True,
            "settings": {
                "model": "claude-sonnet-4-5-20250929",
                "cache_strategy": "conservative",
                "context_strategy": "balanced",
                "temperature": 1.0,
                "preserve_recent_count": 10,
                "auto_summarize": True,
                "default_subagent_model": "Sonnet (balanced)"
            },
            "created_at": "2026-01-02T00:00:00",
            "updated_at": "2026-01-02T00:00:00"
        }
    }

    def __init__(self):
        """Initialize preset manager"""
        self.presets_file = Path("./sandbox/presets.json")
        self._ensure_storage()
        self.presets_data = self._load_presets()

    def _ensure_storage(self):
        """Ensure presets file exists with built-in presets"""
        self.presets_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.presets_file.exists():
            # Create default structure
            default_data = {
                "version": self.VERSION,
                "built_in": self.BUILT_IN_PRESETS.copy(),
                "custom": {},
                "active_preset_id": "simple_chat"  # Default to Simple Chat
            }
            self._save_data(default_data)
            logger.info("Created default presets file with built-in presets")

    def _load_presets(self) -> Dict[str, Any]:
        """Load presets from JSON file"""
        try:
            with open(self.presets_file, 'r') as f:
                data = json.load(f)

            # Validate structure
            if "built_in" not in data:
                data["built_in"] = self.BUILT_IN_PRESETS.copy()
            if "custom" not in data:
                data["custom"] = {}
            if "version" not in data:
                data["version"] = self.VERSION
            if "active_preset_id" not in data:
                data["active_preset_id"] = None

            logger.info(f"Loaded presets: {len(data['built_in'])} built-in, {len(data['custom'])} custom")
            return data

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading presets: {e}")
            # Return default structure
            return {
                "version": self.VERSION,
                "built_in": self.BUILT_IN_PRESETS.copy(),
                "custom": {},
                "active_preset_id": "simple_chat"
            }

    def _save_data(self, data: Dict[str, Any]):
        """Save presets data to file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Saved presets to disk")
        except Exception as e:
            logger.error(f"Error saving presets: {e}")

    def _save_presets(self):
        """Save current presets_data to disk"""
        self._save_data(self.presets_data)

    def get_built_in_presets(self) -> Dict[str, Dict]:
        """Get all built-in presets"""
        return self.presets_data.get("built_in", {})

    def get_custom_presets(self) -> Dict[str, Dict]:
        """Get all custom presets"""
        return self.presets_data.get("custom", {})

    def get_all_presets(self) -> Dict[str, Dict]:
        """Get all presets (built-in + custom)"""
        all_presets = {}
        all_presets.update(self.get_built_in_presets())
        all_presets.update(self.get_custom_presets())
        return all_presets

    def get_preset(self, preset_id: str) -> Optional[Dict]:
        """Get specific preset by ID"""
        # Check built-in first
        if preset_id in self.presets_data.get("built_in", {}):
            return self.presets_data["built_in"][preset_id]
        # Then check custom
        if preset_id in self.presets_data.get("custom", {}):
            return self.presets_data["custom"][preset_id]
        return None

    def get_active_preset_id(self) -> Optional[str]:
        """Get currently active preset ID"""
        return self.presets_data.get("active_preset_id")

    def set_active_preset(self, preset_id: str) -> bool:
        """Mark a preset as active"""
        try:
            self.presets_data["active_preset_id"] = preset_id
            self._save_presets()
            logger.info(f"Set active preset: {preset_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting active preset: {e}")
            return False

    def apply_preset(self, preset_id: str, session_state: Any) -> Tuple[bool, str]:
        """
        Apply preset settings to session state.

        Note: Caller must handle special cases after this returns:
        - cache_strategy: call client.set_cache_strategy(enum)
        - context_strategy: call context_manager.set_strategy(str)

        Args:
            preset_id: Preset identifier
            session_state: Streamlit session state object

        Returns:
            (success: bool, message: str)
        """
        try:
            preset = self.get_preset(preset_id)

            if not preset:
                return False, f"Preset not found: {preset_id}"

            settings = preset["settings"]

            # Apply each setting to session state
            session_state.model = settings["model"]
            session_state.cache_strategy = settings["cache_strategy"]
            session_state.context_strategy = settings["context_strategy"]
            session_state.temperature = settings["temperature"]
            session_state.preserve_recent_count = settings["preserve_recent_count"]
            session_state.auto_summarize = settings["auto_summarize"]
            session_state.default_subagent_model = settings["default_subagent_model"]

            # Set as active preset
            self.set_active_preset(preset_id)

            preset_name = preset["name"]
            logger.info(f"Applied preset: {preset_name} ({preset_id})")

            return True, f"Applied preset: {preset_name}"

        except Exception as e:
            logger.error(f"Error applying preset {preset_id}: {e}", exc_info=True)
            return False, f"Error applying preset: {str(e)}"

    def save_custom_preset(
        self,
        name: str,
        description: str,
        session_state: Any
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Save current settings as custom preset.

        Args:
            name: Preset name
            description: Preset description
            session_state: Streamlit session state object

        Returns:
            (success: bool, message: str, preset_id: Optional[str])
        """
        try:
            # Validate name
            if not name or not name.strip():
                return False, "Preset name is required", None

            # Extract current settings
            current_settings = self.extract_current_settings(session_state)

            # Generate UUID for preset ID
            preset_id = f"custom_{uuid.uuid4().hex[:8]}"

            # Create preset dict
            preset_entry = {
                "id": preset_id,
                "name": name.strip(),
                "description": description.strip() if description else "Custom preset",
                "is_built_in": False,
                "settings": current_settings,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # Add to custom presets
            self.presets_data["custom"][preset_id] = preset_entry
            self._save_presets()

            logger.info(f"Saved custom preset: {name} ({preset_id})")

            return True, f"Saved preset: {name}", preset_id

        except Exception as e:
            logger.error(f"Error saving custom preset: {e}", exc_info=True)
            return False, f"Error saving preset: {str(e)}", None

    def update_custom_preset(
        self,
        preset_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Update custom preset (built-in cannot be modified).

        Args:
            preset_id: Preset identifier
            name: New name (optional)
            description: New description (optional)
            settings: New settings dict (optional)

        Returns:
            (success: bool, message: str)
        """
        try:
            # Check if preset exists
            preset = self.get_preset(preset_id)

            if not preset:
                return False, f"Preset not found: {preset_id}"

            # Check if it's a built-in preset
            if preset.get("is_built_in", False):
                return False, "Cannot modify built-in presets"

            # Check if it's in custom presets
            if preset_id not in self.presets_data["custom"]:
                return False, "Preset is not a custom preset"

            # Update fields
            if name is not None:
                if not name.strip():
                    return False, "Preset name cannot be empty"
                self.presets_data["custom"][preset_id]["name"] = name.strip()

            if description is not None:
                self.presets_data["custom"][preset_id]["description"] = description.strip()

            if settings is not None:
                # Validate settings
                is_valid, errors = self.validate_settings(settings)
                if not is_valid:
                    return False, f"Invalid settings: {', '.join(errors)}"
                self.presets_data["custom"][preset_id]["settings"] = settings

            # Update timestamp
            self.presets_data["custom"][preset_id]["updated_at"] = datetime.now().isoformat()

            # Save to disk
            self._save_presets()

            logger.info(f"Updated custom preset: {preset_id}")

            return True, "Preset updated successfully"

        except Exception as e:
            logger.error(f"Error updating preset {preset_id}: {e}", exc_info=True)
            return False, f"Error updating preset: {str(e)}"

    def delete_custom_preset(self, preset_id: str) -> Tuple[bool, str]:
        """
        Delete custom preset (built-in cannot be deleted).

        Args:
            preset_id: Preset identifier

        Returns:
            (success: bool, message: str)
        """
        try:
            # Check if preset exists
            preset = self.get_preset(preset_id)

            if not preset:
                return False, f"Preset not found: {preset_id}"

            # Check if it's a built-in preset
            if preset.get("is_built_in", False):
                return False, "Cannot delete built-in presets"

            # Check if it's in custom presets
            if preset_id not in self.presets_data["custom"]:
                return False, "Preset is not a custom preset"

            # If it's the active preset, clear active_preset_id
            if preset_id == self.get_active_preset_id():
                self.presets_data["active_preset_id"] = None
                logger.info(f"Cleared active preset (was deleted): {preset_id}")

            # Remove from custom dict
            preset_name = preset["name"]
            del self.presets_data["custom"][preset_id]

            # Save to disk
            self._save_presets()

            logger.info(f"Deleted custom preset: {preset_name} ({preset_id})")

            return True, f"Deleted preset: {preset_name}"

        except Exception as e:
            logger.error(f"Error deleting preset {preset_id}: {e}", exc_info=True)
            return False, f"Error deleting preset: {str(e)}"

    def extract_current_settings(self, session_state: Any) -> Dict[str, Any]:
        """
        Extract the 7 core settings from session state.

        Args:
            session_state: Streamlit session state object

        Returns:
            Dictionary of current settings
        """
        return {
            "model": session_state.model,
            "cache_strategy": session_state.cache_strategy,
            "context_strategy": session_state.context_strategy,
            "temperature": session_state.temperature,
            "preserve_recent_count": session_state.preserve_recent_count,
            "auto_summarize": session_state.auto_summarize,
            "default_subagent_model": session_state.default_subagent_model
        }

    def validate_settings(self, settings: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate settings dictionary.

        Args:
            settings: Settings dict to validate

        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []

        # Required keys
        required_keys = [
            "model", "cache_strategy", "context_strategy", "temperature",
            "preserve_recent_count", "auto_summarize", "default_subagent_model"
        ]

        for key in required_keys:
            if key not in settings:
                errors.append(f"Missing required key: {key}")

        if errors:
            return False, errors

        # Validate types and ranges
        if not isinstance(settings["model"], str):
            errors.append("model must be a string")

        if settings["cache_strategy"] not in ["disabled", "conservative", "balanced", "aggressive"]:
            errors.append("cache_strategy must be one of: disabled, conservative, balanced, aggressive")

        if settings["context_strategy"] not in ["aggressive", "balanced", "conservative", "manual"]:
            errors.append("context_strategy must be one of: aggressive, balanced, conservative, manual")

        if not isinstance(settings["temperature"], (int, float)) or not (0.0 <= settings["temperature"] <= 1.0):
            errors.append("temperature must be a number between 0.0 and 1.0")

        if not isinstance(settings["preserve_recent_count"], int) or settings["preserve_recent_count"] < 0:
            errors.append("preserve_recent_count must be a non-negative integer")

        if not isinstance(settings["auto_summarize"], bool):
            errors.append("auto_summarize must be a boolean")

        if not isinstance(settings["default_subagent_model"], str):
            errors.append("default_subagent_model must be a string")

        return len(errors) == 0, errors

    def settings_match_preset(self, session_state: Any, preset_id: str) -> bool:
        """
        Check if current settings match a preset.

        Args:
            session_state: Streamlit session state object
            preset_id: Preset to compare against

        Returns:
            True if settings match preset, False otherwise
        """
        try:
            preset = self.get_preset(preset_id)
            if not preset:
                return False

            current_settings = self.extract_current_settings(session_state)
            preset_settings = preset["settings"]

            return current_settings == preset_settings

        except Exception as e:
            logger.error(f"Error checking settings match: {e}")
            return False
