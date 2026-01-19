"""
Preset Manager - Generic Settings Preset System

Manages settings presets for quick configuration switching.
Framework-agnostic - works with any settings dictionary.

Features:
- Built-in presets (read-only)
- Custom presets (full CRUD)
- JSON export/import
- Settings validation
- Active preset tracking

Usage:
    from reusable_lib.config import PresetManager

    # Define built-in presets
    built_ins = {
        "fast": {
            "id": "fast",
            "name": "Fast Mode",
            "description": "Quick responses",
            "settings": {"model": "haiku", "cache": True}
        },
        "quality": {
            "id": "quality",
            "name": "Quality Mode",
            "description": "Best output",
            "settings": {"model": "opus", "cache": False}
        }
    }

    # Create manager
    manager = PresetManager(
        storage_path="./presets.json",
        built_in_presets=built_ins
    )

    # Get all presets
    all_presets = manager.get_all_presets()

    # Save custom preset
    success, msg, preset_id = manager.save_custom_preset(
        name="My Preset",
        description="Custom config",
        settings={"model": "sonnet", "cache": True}
    )

    # Apply preset
    preset = manager.get_preset("fast")
    my_settings.update(preset["settings"])
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime
from copy import deepcopy

logger = logging.getLogger(__name__)


class PresetManager:
    """
    Manages settings presets for quick configuration switching.

    Framework-agnostic - works with any settings dictionary structure.
    """

    VERSION = "1.0"

    def __init__(
        self,
        storage_path: str = "./presets.json",
        built_in_presets: Optional[Dict[str, Dict]] = None,
        default_preset_id: Optional[str] = None,
        settings_validator: Optional[Callable[[Dict], Tuple[bool, List[str]]]] = None
    ):
        """
        Initialize preset manager.

        Args:
            storage_path: Path to JSON file for persistence
            built_in_presets: Dictionary of built-in presets (read-only)
            default_preset_id: Default active preset ID
            settings_validator: Optional function(settings) -> (is_valid, errors)
        """
        self.storage_path = Path(storage_path)
        self.built_in_presets = self._mark_built_in(built_in_presets or {})
        self.default_preset_id = default_preset_id
        self.settings_validator = settings_validator

        self._ensure_storage()
        self.presets_data = self._load_presets()

    def _mark_built_in(self, presets: Dict[str, Dict]) -> Dict[str, Dict]:
        """Mark all presets as built-in."""
        marked = deepcopy(presets)
        for preset_id, preset in marked.items():
            preset["is_built_in"] = True
            if "id" not in preset:
                preset["id"] = preset_id
        return marked

    def _ensure_storage(self):
        """Ensure storage file exists."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.storage_path.exists():
            default_data = {
                "version": self.VERSION,
                "custom": {},
                "active_preset_id": self.default_preset_id
            }
            self._save_data(default_data)
            logger.info(f"Created presets file: {self.storage_path}")

    def _load_presets(self) -> Dict[str, Any]:
        """Load presets from JSON file."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Validate structure
            if "custom" not in data:
                data["custom"] = {}
            if "version" not in data:
                data["version"] = self.VERSION
            if "active_preset_id" not in data:
                data["active_preset_id"] = self.default_preset_id

            logger.info(
                f"Loaded presets: {len(self.built_in_presets)} built-in, "
                f"{len(data['custom'])} custom"
            )
            return data

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading presets: {e}")
            return {
                "version": self.VERSION,
                "custom": {},
                "active_preset_id": self.default_preset_id
            }

    def _save_data(self, data: Dict[str, Any]):
        """Save presets data to file."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved presets to disk")
        except Exception as e:
            logger.error(f"Error saving presets: {e}")

    def _save_presets(self):
        """Save current presets_data to disk."""
        self._save_data(self.presets_data)

    def get_built_in_presets(self) -> Dict[str, Dict]:
        """Get all built-in presets."""
        return deepcopy(self.built_in_presets)

    def get_custom_presets(self) -> Dict[str, Dict]:
        """Get all custom presets."""
        return deepcopy(self.presets_data.get("custom", {}))

    def get_all_presets(self) -> Dict[str, Dict]:
        """Get all presets (built-in + custom)."""
        all_presets = {}
        all_presets.update(self.get_built_in_presets())
        all_presets.update(self.get_custom_presets())
        return all_presets

    def get_preset(self, preset_id: str) -> Optional[Dict]:
        """Get specific preset by ID."""
        # Check built-in first
        if preset_id in self.built_in_presets:
            return deepcopy(self.built_in_presets[preset_id])
        # Then check custom
        if preset_id in self.presets_data.get("custom", {}):
            return deepcopy(self.presets_data["custom"][preset_id])
        return None

    def get_active_preset_id(self) -> Optional[str]:
        """Get currently active preset ID."""
        return self.presets_data.get("active_preset_id")

    def get_active_preset(self) -> Optional[Dict]:
        """Get currently active preset (if any)."""
        active_id = self.get_active_preset_id()
        if active_id:
            return self.get_preset(active_id)
        return None

    def set_active_preset(self, preset_id: str) -> bool:
        """Mark a preset as active."""
        try:
            # Verify preset exists
            if not self.get_preset(preset_id):
                logger.warning(f"Preset not found: {preset_id}")
                return False

            self.presets_data["active_preset_id"] = preset_id
            self._save_presets()
            logger.info(f"Set active preset: {preset_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting active preset: {e}")
            return False

    def save_custom_preset(
        self,
        name: str,
        settings: Dict[str, Any],
        description: str = ""
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Save settings as custom preset.

        Args:
            name: Preset name
            settings: Settings dictionary
            description: Preset description

        Returns:
            (success: bool, message: str, preset_id: Optional[str])
        """
        try:
            # Validate name
            if not name or not name.strip():
                return False, "Preset name is required", None

            # Validate settings if validator provided
            if self.settings_validator:
                is_valid, errors = self.settings_validator(settings)
                if not is_valid:
                    return False, f"Invalid settings: {', '.join(errors)}", None

            # Generate UUID for preset ID
            preset_id = f"custom_{uuid.uuid4().hex[:8]}"

            # Create preset dict
            preset_entry = {
                "id": preset_id,
                "name": name.strip(),
                "description": description.strip() if description else "Custom preset",
                "is_built_in": False,
                "settings": deepcopy(settings),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # Add to custom presets
            self.presets_data["custom"][preset_id] = preset_entry
            self._save_presets()

            logger.info(f"Saved custom preset: {name} ({preset_id})")

            return True, f"Saved preset: {name}", preset_id

        except Exception as e:
            logger.error(f"Error saving custom preset: {e}")
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
            preset = self.get_preset(preset_id)

            if not preset:
                return False, f"Preset not found: {preset_id}"

            if preset.get("is_built_in", False):
                return False, "Cannot modify built-in presets"

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
                # Validate if validator provided
                if self.settings_validator:
                    is_valid, errors = self.settings_validator(settings)
                    if not is_valid:
                        return False, f"Invalid settings: {', '.join(errors)}"
                self.presets_data["custom"][preset_id]["settings"] = deepcopy(settings)

            # Update timestamp
            self.presets_data["custom"][preset_id]["updated_at"] = datetime.now().isoformat()

            self._save_presets()
            logger.info(f"Updated custom preset: {preset_id}")

            return True, "Preset updated successfully"

        except Exception as e:
            logger.error(f"Error updating preset {preset_id}: {e}")
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
            preset = self.get_preset(preset_id)

            if not preset:
                return False, f"Preset not found: {preset_id}"

            if preset.get("is_built_in", False):
                return False, "Cannot delete built-in presets"

            if preset_id not in self.presets_data["custom"]:
                return False, "Preset is not a custom preset"

            # If it's the active preset, clear active_preset_id
            if preset_id == self.get_active_preset_id():
                self.presets_data["active_preset_id"] = self.default_preset_id
                logger.info(f"Cleared active preset (was deleted): {preset_id}")

            # Remove from custom dict
            preset_name = preset["name"]
            del self.presets_data["custom"][preset_id]

            self._save_presets()
            logger.info(f"Deleted custom preset: {preset_name} ({preset_id})")

            return True, f"Deleted preset: {preset_name}"

        except Exception as e:
            logger.error(f"Error deleting preset {preset_id}: {e}")
            return False, f"Error deleting preset: {str(e)}"

    def settings_match_preset(self, settings: Dict[str, Any], preset_id: str) -> bool:
        """
        Check if settings match a preset.

        Args:
            settings: Current settings dict
            preset_id: Preset to compare against

        Returns:
            True if settings match preset
        """
        try:
            preset = self.get_preset(preset_id)
            if not preset:
                return False

            return settings == preset["settings"]

        except Exception as e:
            logger.error(f"Error checking settings match: {e}")
            return False

    def find_matching_preset(self, settings: Dict[str, Any]) -> Optional[str]:
        """
        Find preset that matches given settings.

        Args:
            settings: Settings to match

        Returns:
            Preset ID if found, None otherwise
        """
        for preset_id, preset in self.get_all_presets().items():
            if settings == preset["settings"]:
                return preset_id
        return None

    def export_custom_presets(self) -> str:
        """
        Export custom presets as JSON string.

        Returns:
            JSON string of custom presets
        """
        custom = self.get_custom_presets()
        return json.dumps(custom, indent=2)

    def import_custom_presets(
        self,
        json_data: str,
        overwrite: bool = False
    ) -> Tuple[bool, str, int]:
        """
        Import custom presets from JSON string.

        Args:
            json_data: JSON string of presets
            overwrite: If True, overwrite existing presets with same ID

        Returns:
            (success: bool, message: str, imported_count: int)
        """
        try:
            presets = json.loads(json_data)

            if not isinstance(presets, dict):
                return False, "Invalid preset format - expected dict", 0

            imported = 0
            skipped = 0

            for preset_id, preset in presets.items():
                # Skip built-in-style IDs
                if not preset_id.startswith("custom_"):
                    preset_id = f"custom_{preset_id}"

                # Check if exists
                if preset_id in self.presets_data["custom"]:
                    if not overwrite:
                        skipped += 1
                        continue

                # Validate structure
                if "settings" not in preset:
                    logger.warning(f"Skipping preset without settings: {preset_id}")
                    skipped += 1
                    continue

                # Mark as custom
                preset["is_built_in"] = False
                preset["id"] = preset_id

                # Add timestamp if missing
                if "created_at" not in preset:
                    preset["created_at"] = datetime.now().isoformat()
                preset["updated_at"] = datetime.now().isoformat()

                self.presets_data["custom"][preset_id] = preset
                imported += 1

            self._save_presets()

            message = f"Imported {imported} presets"
            if skipped > 0:
                message += f", skipped {skipped}"

            return True, message, imported

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}", 0
        except Exception as e:
            logger.error(f"Error importing presets: {e}")
            return False, f"Import error: {str(e)}", 0

    def list_presets(self, include_settings: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of all presets with basic info.

        Args:
            include_settings: Include full settings in output

        Returns:
            List of preset info dicts
        """
        result = []

        for preset_id, preset in self.get_all_presets().items():
            info = {
                "id": preset_id,
                "name": preset.get("name", preset_id),
                "description": preset.get("description", ""),
                "is_built_in": preset.get("is_built_in", False),
                "is_active": preset_id == self.get_active_preset_id()
            }

            if include_settings:
                info["settings"] = preset.get("settings", {})

            result.append(info)

        # Sort: built-in first, then by name
        result.sort(key=lambda x: (not x["is_built_in"], x["name"].lower()))

        return result
