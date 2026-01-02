"""
Import Engine for Conversations

Handles importing conversations from various formats:
- JSON (lossless import)
- Markdown (basic import)
- Auto-detection of format
"""

import json
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ImportEngine:
    """Main import engine for conversations"""

    def __init__(self):
        """Initialize import engine"""
        self.importers = {
            "json": JSONImporter(),
            "markdown": MarkdownImporter(),
            "text": TextImporter(),
        }

    def detect_format(self, content: bytes) -> str:
        """
        Auto-detect file format from content.

        Args:
            content: File content as bytes

        Returns:
            Format string (json, markdown, text)
        """
        # Try to decode
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return "unknown"

        # Try JSON first
        try:
            json.loads(text)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass

        # Check for markdown headers
        if re.search(r'^#\s+', text, re.MULTILINE):
            return "markdown"

        # Check for common patterns
        if "**User:**" in text or "**Assistant:**" in text:
            return "markdown"

        # Default to text
        return "text"

    def import_conversation(
        self,
        content: bytes,
        format: Optional[str] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Import a single conversation.

        Args:
            content: File content as bytes
            format: Format hint (auto-detected if None)
            validate: Whether to validate after import

        Returns:
            Conversation dict (or dict with multiple conversations if file contains multiple)

        Raises:
            ValueError: If format unsupported or validation fails
        """
        # Auto-detect format if not provided
        if format is None:
            format = self.detect_format(content)

        if format not in self.importers:
            raise ValueError(f"Unsupported format: {format}")

        # Import using appropriate importer
        importer = self.importers[format]
        conversation = importer.import_conversation(content)

        # Check if this is a multi-conversation file
        if isinstance(conversation, dict) and "conversations" in conversation:
            # This is a multi-conversation export - return metadata about it
            return {
                "_multiple": True,
                "conversations": conversation["conversations"],
                "count": len(conversation["conversations"])
            }

        # Normalize first (add missing fields, fix structure)
        conversation = self._normalize_conversation(conversation)

        # Then validate the normalized structure
        if validate:
            is_valid, errors = self.validate_conversation(conversation)
            if not is_valid:
                raise ValueError(f"Validation failed: {', '.join(errors)}")

        return conversation

    def import_multiple(
        self,
        files: List[Tuple[str, bytes]],
        validate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Import multiple conversations.

        Args:
            files: List of (filename, content) tuples
            validate: Whether to validate each import

        Returns:
            List of conversation dicts
        """
        conversations = []

        for filename, content in files:
            try:
                conv = self.import_conversation(content, validate=validate)
                conv["metadata"] = conv.get("metadata", {})
                conv["metadata"]["imported_from"] = filename
                conversations.append(conv)
            except Exception as e:
                logger.error(f"Failed to import {filename}: {e}")
                # Continue with other files

        return conversations

    def validate_conversation(self, conversation: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate conversation structure.

        Args:
            conversation: Conversation dict to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required fields
        if "title" not in conversation:
            errors.append("Missing 'title' field")

        if "messages" not in conversation:
            errors.append("Missing 'messages' field")
        elif not isinstance(conversation["messages"], list):
            errors.append("'messages' must be a list")
        elif len(conversation["messages"]) == 0:
            errors.append("'messages' list is empty")

        # Validate messages
        messages = conversation.get("messages", [])
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                errors.append(f"Message {i} is not a dict")
                continue

            if "role" not in msg:
                errors.append(f"Message {i} missing 'role'")

            if "content" not in msg:
                errors.append(f"Message {i} missing 'content'")

            # Validate role
            role = msg.get("role")
            if role not in ["user", "assistant", "system"]:
                errors.append(f"Message {i} has invalid role: {role}")

        # Validate timestamps if present
        for field in ["created_at", "updated_at"]:
            if field in conversation:
                try:
                    # Try to parse ISO format
                    datetime.fromisoformat(conversation[field].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    errors.append(f"Invalid {field} format")

        return (len(errors) == 0, errors)

    def _normalize_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize conversation structure.

        Args:
            conversation: Raw conversation dict

        Returns:
            Normalized conversation dict
        """
        # Generate new ID to avoid conflicts
        conversation["id"] = f"conv_{uuid.uuid4().hex[:16]}"

        # Ensure title (auto-generate from first message if missing)
        if "title" not in conversation or not conversation["title"]:
            messages = conversation.get("messages", [])
            if messages and len(messages) > 0:
                # Use first user message content (truncated)
                first_user_msg = next(
                    (msg for msg in messages if msg.get("role") == "user"),
                    messages[0]  # Fallback to first message
                )
                content = first_user_msg.get("content", "")
                if isinstance(content, list):
                    # Handle new Claude format with content blocks
                    text = next((block.get("text", "") for block in content if block.get("type") == "text"), "")
                else:
                    text = content
                # Truncate to reasonable title length
                conversation["title"] = text[:60] + "..." if len(text) > 60 else text or "Imported Conversation"
            else:
                conversation["title"] = "Imported Conversation"

        # Ensure timestamps
        now = datetime.now().isoformat()
        if "created_at" not in conversation or conversation["created_at"] is None:
            conversation["created_at"] = now
        if "updated_at" not in conversation or conversation["updated_at"] is None:
            conversation["updated_at"] = now

        # Ensure metadata structure
        if "metadata" not in conversation:
            conversation["metadata"] = {}

        conversation["metadata"]["imported_at"] = now

        # Ensure messages have timestamps
        for msg in conversation.get("messages", []):
            if "timestamp" not in msg:
                msg["timestamp"] = now

        return conversation


class BaseImporter:
    """Base class for importers"""

    def import_conversation(self, content: bytes) -> Dict[str, Any]:
        """Import conversation from bytes"""
        raise NotImplementedError


class JSONImporter(BaseImporter):
    """Import from JSON format"""

    def import_conversation(self, content: bytes) -> Dict[str, Any]:
        """Import from JSON"""
        try:
            text = content.decode("utf-8")
            data = json.loads(text)

            # Handle both single conversation and wrapped format
            if "conversations" in data:
                # Multiple conversations exported together - return the full structure
                if len(data["conversations"]) == 0:
                    raise ValueError("No conversations in file")
                # Return the data as-is, let import_conversation() handle the multiple case
                return data

            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid encoding: {e}")


class MarkdownImporter(BaseImporter):
    """Import from Markdown format (basic support)"""

    def import_conversation(self, content: bytes) -> Dict[str, Any]:
        """
        Import from Markdown.

        Note: This is best-effort parsing. Some information may be lost.
        """
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid encoding: {e}")

        # Extract title (first # heading)
        title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        title = title_match.group(1) if title_match else "Imported Conversation"

        # Extract metadata if present
        created_at = None
        created_match = re.search(r'\*\*Created:\*\*\s+(.+)$', text, re.MULTILINE)
        if created_match:
            created_at = created_match.group(1).strip()

        # Parse messages
        messages = self._parse_messages(text)

        if not messages:
            raise ValueError("No messages found in Markdown")

        return {
            "title": title,
            "created_at": created_at,
            "messages": messages,
            "metadata": {
                "imported_from_format": "markdown"
            }
        }

    def _parse_messages(self, text: str) -> List[Dict[str, Any]]:
        """Parse messages from Markdown text"""
        messages = []

        # Split on message headers
        # Look for patterns like "**User:**" or "**Assistant:**"
        pattern = r'\*\*(User|Assistant):\*\*\s*\n(.*?)(?=\*\*(User|Assistant):\*\*|$)'

        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            role = match[0].lower()
            content = match[1].strip()

            if content:  # Skip empty messages
                messages.append({
                    "role": role,
                    "content": content
                })

        return messages


class TextImporter(BaseImporter):
    """Import from plain text format"""

    def import_conversation(self, content: bytes) -> Dict[str, Any]:
        """
        Import from plain text.

        Very basic parsing - looks for role indicators.
        """
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid encoding: {e}")

        lines = text.split("\n")

        # Extract title (first line)
        title = lines[0].strip() if lines else "Imported Conversation"

        # Parse messages
        messages = self._parse_messages(text)

        if not messages:
            # If no structured messages found, treat whole text as single user message
            messages = [{
                "role": "user",
                "content": text.strip()
            }]

        return {
            "title": title,
            "messages": messages,
            "metadata": {
                "imported_from_format": "text"
            }
        }

    def _parse_messages(self, text: str) -> List[Dict[str, Any]]:
        """Parse messages from plain text"""
        messages = []

        # Look for patterns like "USER:" or "ASSISTANT:"
        pattern = r'(USER|ASSISTANT):\s*\n(.*?)(?=(USER|ASSISTANT):|$)'

        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            role = match[0].lower()
            content = match[1].strip()

            if content:
                messages.append({
                    "role": role,
                    "content": content
                })

        return messages


def merge_conversations(
    base: Dict[str, Any],
    incoming: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge incoming conversation into base conversation.

    Args:
        base: Base conversation
        incoming: Conversation to merge in

    Returns:
        Merged conversation
    """
    merged = base.copy()

    # Append messages
    merged["messages"].extend(incoming["messages"])

    # Update timestamp
    merged["updated_at"] = datetime.now().isoformat()

    # Merge metadata
    base_meta = merged.get("metadata", {})
    incoming_meta = incoming.get("metadata", {})

    # Merge tags
    base_tags = set(base_meta.get("tags", []))
    incoming_tags = set(incoming_meta.get("tags", []))
    merged_tags = list(base_tags | incoming_tags)

    if merged_tags:
        base_meta["tags"] = merged_tags

    merged["metadata"] = base_meta

    return merged
