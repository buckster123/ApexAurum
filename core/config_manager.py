"""
Configuration Manager

Handles export/import of app configurations including:
- Model settings
- UI preferences
- System prompts
- Tool configurations
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manager for app configuration export/import"""

    VERSION = "1.0"

    def __init__(self):
        """Initialize configuration manager"""
        self.default_config = self._get_default_config()

    def export_config(self, session_state: Any) -> Dict[str, Any]:
        """
        Export current configuration from session state.

        Args:
            session_state: Streamlit session state object

        Returns:
            Configuration dict
        """
        config = {
            "version": self.VERSION,
            "exported_at": datetime.now().isoformat(),
            "settings": self._export_settings(session_state),
            "system_prompts": self._export_system_prompts(session_state),
            "ui_preferences": self._export_ui_preferences(session_state),
        }

        return config

    def import_config(
        self,
        config: Dict[str, Any],
        session_state: Any,
        merge: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Import configuration into session state.

        Args:
            config: Configuration dict to import
            session_state: Streamlit session state object
            merge: If True, merge with existing. If False, replace.

        Returns:
            Tuple of (success, messages)
        """
        messages = []

        # Validate first
        is_valid, errors = self.validate_config(config)
        if not is_valid:
            return False, errors

        try:
            # Import settings
            settings = config.get("settings", {})
            self._import_settings(settings, session_state, merge)
            messages.append("Settings imported")

            # Import system prompts
            prompts = config.get("system_prompts", [])
            self._import_system_prompts(prompts, session_state, merge)
            messages.append("System prompts imported")

            # Import UI preferences
            ui_prefs = config.get("ui_preferences", {})
            self._import_ui_preferences(ui_prefs, session_state, merge)
            messages.append("UI preferences imported")

            return True, messages

        except Exception as e:
            logger.error(f"Error importing config: {e}", exc_info=True)
            return False, [f"Import failed: {str(e)}"]

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration structure.

        Args:
            config: Configuration dict to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check version
        if "version" not in config:
            errors.append("Missing 'version' field")

        # Check main sections
        if "settings" not in config:
            errors.append("Missing 'settings' section")

        # Validate settings if present
        settings = config.get("settings", {})
        if settings:
            # Validate temperature range
            temp = settings.get("temperature")
            if temp is not None and not (0.0 <= temp <= 1.0):
                errors.append("temperature must be between 0.0 and 1.0")

            # Validate max_tokens
            max_tokens = settings.get("max_tokens")
            if max_tokens is not None and not (256 <= max_tokens <= 128000):
                errors.append("max_tokens must be between 256 and 128000")

            # Validate model
            model = settings.get("model")
            valid_models = [
                "claude-opus-4-5-20251101",
                "claude-sonnet-4-5-20250929",
                "claude-haiku-4-5-20251001",
                "claude-sonnet-3-7-20250219",
                "claude-3-5-haiku-20241022"
            ]
            if model is not None and model not in valid_models:
                errors.append(f"Invalid model: {model}")

        return (len(errors) == 0, errors)

    def reset_to_defaults(self, session_state: Any) -> None:
        """
        Reset all settings to defaults.

        Args:
            session_state: Streamlit session state object
        """
        defaults = self._get_default_config()

        # Apply default settings
        self._import_settings(defaults["settings"], session_state, merge=False)
        self._import_ui_preferences(defaults["ui_preferences"], session_state, merge=False)

        logger.info("Configuration reset to defaults")

    def _export_settings(self, session_state: Any) -> Dict[str, Any]:
        """Export model and API settings"""
        return {
            "model": getattr(session_state, "model", None),
            "temperature": getattr(session_state, "temperature", 0.7),
            "max_tokens": getattr(session_state, "max_tokens", 64000),
            "tools_enabled": getattr(session_state, "tools_enabled", True),
        }

    def _export_system_prompts(self, session_state: Any) -> List[Dict[str, str]]:
        """Export system prompts"""
        # For now, just export the current system prompt
        # Future: Support multiple named prompts
        current_prompt = getattr(session_state, "system_prompt", "")

        if current_prompt:
            return [{
                "name": "Default",
                "content": current_prompt
            }]
        return []

    def _export_ui_preferences(self, session_state: Any) -> Dict[str, Any]:
        """Export UI preferences"""
        return {
            "streaming_enabled": getattr(session_state, "streaming_enabled", True),
            "show_tool_execution": getattr(session_state, "show_tool_execution", True),
            "show_partial_results": getattr(session_state, "show_partial_results", True),
            "context_strategy": getattr(session_state, "context_strategy", "balanced"),
            "preserve_recent_count": getattr(session_state, "preserve_recent_count", 10),
            "auto_summarize": getattr(session_state, "auto_summarize", True),
        }

    def _import_settings(
        self,
        settings: Dict[str, Any],
        session_state: Any,
        merge: bool
    ) -> None:
        """Import model and API settings"""
        if not merge:
            # Replace mode - use defaults for missing values
            defaults = self._get_default_config()["settings"]
            settings = {**defaults, **settings}

        # Apply settings
        for key, value in settings.items():
            if value is not None:  # Only set non-None values
                setattr(session_state, key, value)

    def _import_system_prompts(
        self,
        prompts: List[Dict[str, str]],
        session_state: Any,
        merge: bool
    ) -> None:
        """Import system prompts"""
        if prompts:
            # For now, just use the first prompt as the system prompt
            # Future: Support multiple named prompts
            first_prompt = prompts[0]
            content = first_prompt.get("content", "")
            if content:
                session_state.system_prompt = content

    def _import_ui_preferences(
        self,
        ui_prefs: Dict[str, Any],
        session_state: Any,
        merge: bool
    ) -> None:
        """Import UI preferences"""
        if not merge:
            # Replace mode - use defaults for missing values
            defaults = self._get_default_config()["ui_preferences"]
            ui_prefs = {**defaults, **ui_prefs}

        # Apply preferences
        for key, value in ui_prefs.items():
            if value is not None:
                setattr(session_state, key, value)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "version": self.VERSION,
            "settings": {
                "model": "claude-sonnet-4-5-20250929",
                "temperature": 0.7,
                "max_tokens": 64000,
                "tools_enabled": True,
            },
            "system_prompts": [],
            "ui_preferences": {
                "streaming_enabled": True,
                "show_tool_execution": True,
                "show_partial_results": True,
                "context_strategy": "balanced",
                "preserve_recent_count": 10,
                "auto_summarize": True,
            }
        }

    def export_to_json(self, session_state: Any, indent: int = 2) -> str:
        """
        Export configuration as JSON string.

        Args:
            session_state: Streamlit session state
            indent: JSON indentation

        Returns:
            JSON string
        """
        config = self.export_config(session_state)
        return json.dumps(config, indent=indent, ensure_ascii=False)

    def import_from_json(
        self,
        json_str: str,
        session_state: Any,
        merge: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Import configuration from JSON string.

        Args:
            json_str: JSON configuration string
            session_state: Streamlit session state
            merge: Whether to merge or replace

        Returns:
            Tuple of (success, messages)
        """
        try:
            config = json.loads(json_str)
            return self.import_config(config, session_state, merge)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {str(e)}"]
