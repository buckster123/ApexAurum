"""
Conversation Service

Manages conversation persistence, search, and export.
Stores conversations in JSON format.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import uuid

from app_config import settings

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Service for managing chat conversations.

    Handles persistence to JSON, search, and export functionality.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize conversation service.

        Args:
            storage_path: Path to JSON storage file (default: from settings)
        """
        self.storage_path = storage_path or settings.CONVERSATIONS_FILE
        self.conversations: Dict[str, Dict] = {}
        self._ensure_storage()
        self._load_conversations()

    def _ensure_storage(self):
        """Ensure storage directory and file exist."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_conversations()

    def _load_conversations(self):
        """Load conversations from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    self.conversations = json.load(f)
                logger.info(f"Loaded {len(self.conversations)} conversations")
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")
            self.conversations = {}

    def _save_conversations(self):
        """Save conversations to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.conversations, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving conversations: {e}")

    def create(
        self,
        messages: List[Dict] = None,
        title: Optional[str] = None,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation.

        Args:
            messages: Initial messages (optional)
            title: Conversation title (auto-generated if not provided)
            tags: Optional tags for categorization
            metadata: Optional metadata

        Returns:
            Created conversation dict
        """
        conv_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Auto-generate title from first user message if not provided
        if not title and messages:
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    title = content[:50] + ("..." if len(content) > 50 else "")
                    break

        conversation = {
            "id": conv_id,
            "title": title or "New Conversation",
            "messages": messages or [],
            "created_at": now,
            "updated_at": now,
            "tags": tags or [],
            "favorite": False,
            "archived": False,
            "metadata": metadata or {}
        }

        self.conversations[conv_id] = conversation
        self._save_conversations()

        logger.info(f"Created conversation: {conv_id}")
        return conversation

    def get(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation by ID.

        Args:
            conv_id: Conversation ID

        Returns:
            Conversation dict or None if not found
        """
        return self.conversations.get(conv_id)

    def update(
        self,
        conv_id: str,
        messages: List[Dict] = None,
        title: str = None,
        tags: List[str] = None,
        favorite: bool = None,
        archived: bool = None,
        metadata: Dict = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a conversation.

        Args:
            conv_id: Conversation ID
            messages: New messages (replaces existing)
            title: New title
            tags: New tags
            favorite: Favorite status
            archived: Archived status
            metadata: Additional metadata

        Returns:
            Updated conversation or None if not found
        """
        conv = self.conversations.get(conv_id)
        if not conv:
            return None

        if messages is not None:
            conv["messages"] = messages
        if title is not None:
            conv["title"] = title
        if tags is not None:
            conv["tags"] = tags
        if favorite is not None:
            conv["favorite"] = favorite
        if archived is not None:
            conv["archived"] = archived
        if metadata is not None:
            conv["metadata"].update(metadata)

        conv["updated_at"] = datetime.now().isoformat()
        self._save_conversations()

        logger.info(f"Updated conversation: {conv_id}")
        return conv

    def add_message(self, conv_id: str, message: Dict) -> Optional[Dict[str, Any]]:
        """
        Add a message to a conversation.

        Args:
            conv_id: Conversation ID
            message: Message dict with role and content

        Returns:
            Updated conversation or None if not found
        """
        conv = self.conversations.get(conv_id)
        if not conv:
            return None

        conv["messages"].append(message)
        conv["updated_at"] = datetime.now().isoformat()

        # Update title if it's still default and this is first user message
        if conv["title"] == "New Conversation" and message.get("role") == "user":
            content = message.get("content", "")
            conv["title"] = content[:50] + ("..." if len(content) > 50 else "")

        self._save_conversations()
        return conv

    def delete(self, conv_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conv_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            self._save_conversations()
            logger.info(f"Deleted conversation: {conv_id}")
            return True
        return False

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
        favorites_only: bool = False,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List conversations with pagination and filtering.

        Args:
            limit: Maximum number to return
            offset: Number to skip
            include_archived: Include archived conversations
            favorites_only: Only return favorites
            tag: Filter by tag

        Returns:
            Dict with conversations list and total count
        """
        convs = list(self.conversations.values())

        # Apply filters
        if not include_archived:
            convs = [c for c in convs if not c.get("archived", False)]
        if favorites_only:
            convs = [c for c in convs if c.get("favorite", False)]
        if tag:
            convs = [c for c in convs if tag in c.get("tags", [])]

        # Sort by updated_at descending
        convs.sort(key=lambda c: c.get("updated_at", ""), reverse=True)

        total = len(convs)
        convs = convs[offset:offset + limit]

        # Return summary (without full messages)
        summaries = []
        for c in convs:
            summary = {
                "id": c["id"],
                "title": c["title"],
                "created_at": c["created_at"],
                "updated_at": c["updated_at"],
                "message_count": len(c.get("messages", [])),
                "tags": c.get("tags", []),
                "favorite": c.get("favorite", False),
                "archived": c.get("archived", False)
            }
            # Add preview of last message
            if c.get("messages"):
                last_msg = c["messages"][-1]
                content = last_msg.get("content", "")
                summary["preview"] = content[:100] + ("..." if len(content) > 100 else "")
            summaries.append(summary)

        return {
            "conversations": summaries,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    def search(
        self,
        query: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search conversations by content.

        Searches titles and message content.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Dict with matching conversations
        """
        query_lower = query.lower()
        results = []

        for conv in self.conversations.values():
            # Search title
            if query_lower in conv.get("title", "").lower():
                results.append({
                    "id": conv["id"],
                    "title": conv["title"],
                    "match_type": "title",
                    "updated_at": conv["updated_at"]
                })
                continue

            # Search message content
            for i, msg in enumerate(conv.get("messages", [])):
                content = msg.get("content", "")
                if query_lower in content.lower():
                    # Find the matching snippet
                    idx = content.lower().find(query_lower)
                    start = max(0, idx - 30)
                    end = min(len(content), idx + len(query) + 30)
                    snippet = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")

                    results.append({
                        "id": conv["id"],
                        "title": conv["title"],
                        "match_type": "message",
                        "message_index": i,
                        "snippet": snippet,
                        "updated_at": conv["updated_at"]
                    })
                    break  # One match per conversation

        # Sort by relevance (title matches first, then by date)
        results.sort(key=lambda r: (r["match_type"] != "title", r["updated_at"]), reverse=True)

        return {
            "query": query,
            "results": results[:limit],
            "total": len(results)
        }

    def export_json(self, conv_id: str) -> Optional[str]:
        """
        Export conversation to JSON string.

        Args:
            conv_id: Conversation ID

        Returns:
            JSON string or None if not found
        """
        conv = self.conversations.get(conv_id)
        if not conv:
            return None
        return json.dumps(conv, indent=2, default=str)

    def export_markdown(self, conv_id: str) -> Optional[str]:
        """
        Export conversation to Markdown format.

        Args:
            conv_id: Conversation ID

        Returns:
            Markdown string or None if not found
        """
        conv = self.conversations.get(conv_id)
        if not conv:
            return None

        lines = [
            f"# {conv['title']}",
            "",
            f"*Created: {conv['created_at']}*",
            f"*Updated: {conv['updated_at']}*",
            ""
        ]

        if conv.get("tags"):
            lines.append(f"Tags: {', '.join(conv['tags'])}")
            lines.append("")

        lines.append("---")
        lines.append("")

        for msg in conv.get("messages", []):
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")

            if role == "User":
                lines.append(f"## User")
            elif role == "Assistant":
                lines.append(f"## Assistant")
            else:
                lines.append(f"## {role}")

            lines.append("")
            lines.append(content)
            lines.append("")

        return "\n".join(lines)

    def export_all(self) -> str:
        """
        Export all conversations to JSON.

        Returns:
            JSON string of all conversations
        """
        return json.dumps(list(self.conversations.values()), indent=2, default=str)

    def import_conversations(self, data: List[Dict]) -> Dict[str, Any]:
        """
        Import conversations from JSON data.

        Args:
            data: List of conversation dicts

        Returns:
            Import summary
        """
        imported = 0
        skipped = 0
        errors = []

        for conv in data:
            try:
                conv_id = conv.get("id") or str(uuid.uuid4())

                if conv_id in self.conversations:
                    skipped += 1
                    continue

                # Validate required fields
                if "messages" not in conv:
                    errors.append(f"Missing messages in conversation {conv_id}")
                    continue

                # Normalize the conversation
                normalized = {
                    "id": conv_id,
                    "title": conv.get("title", "Imported Conversation"),
                    "messages": conv["messages"],
                    "created_at": conv.get("created_at", datetime.now().isoformat()),
                    "updated_at": conv.get("updated_at", datetime.now().isoformat()),
                    "tags": conv.get("tags", []),
                    "favorite": conv.get("favorite", False),
                    "archived": conv.get("archived", False),
                    "metadata": conv.get("metadata", {})
                }

                self.conversations[conv_id] = normalized
                imported += 1

            except Exception as e:
                errors.append(f"Error importing conversation: {str(e)}")

        if imported > 0:
            self._save_conversations()

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get conversation statistics.

        Returns:
            Dict with stats
        """
        convs = list(self.conversations.values())
        total_messages = sum(len(c.get("messages", [])) for c in convs)

        return {
            "total_conversations": len(convs),
            "total_messages": total_messages,
            "favorites": sum(1 for c in convs if c.get("favorite")),
            "archived": sum(1 for c in convs if c.get("archived")),
            "storage_path": str(self.storage_path)
        }


# Global service instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get or create the conversation service singleton."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
