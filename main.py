#!/usr/bin/env python3
"""
Apex Aurum - Claude Edition
Main Streamlit Application

A powerful AI assistant interface powered by Claude API with:
- 18+ built-in tools (filesystem, code execution, memory, utilities)
- Conversation history
- Sandboxed execution
- Clean UI

Usage:
    streamlit run main.py
"""

import streamlit as st
import os
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv
import glob
import base64
from io import BytesIO
from PIL import Image

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import our modules
from core import (
    ClaudeAPIClient,
    ClaudeModels,
    ToolRegistry,
    ToolExecutor,
    ToolCallLoop,
    ModelSelector,
)

from tools import (
    register_all_tools,
    ALL_TOOL_SCHEMAS,
)

from core.error_messages import get_user_friendly_message, format_error_for_display
from core.errors import RetryableError, UserFixableError, FatalError
from core.context_manager import ContextManager
from core.conversation_indexer import get_conversation_indexer
from ui.keyboard_shortcuts import render_cheat_sheet


# ============================================================================
# Configuration
# ============================================================================

PAGE_TITLE = "Apex Aurum Vivum - Claude Edition"
PAGE_ICON = "🤖"
DEFAULT_MODEL = ClaudeModels.SONNET_4_5.value
MAX_TOKENS = 64000


# ============================================================================
# State Management
# ============================================================================

class AppState:
    """Application state manager"""

    def __init__(self):
        """Initialize application state"""
        self.conversations_file = Path("./sandbox/conversations.json")
        self._ensure_storage()

        # Phase 13.3: Conversation indexer (lazy-loaded)
        self._indexer = None
        self.auto_index_enabled = True  # Toggle for automatic indexing

    def _ensure_storage(self):
        """Ensure storage directories exist"""
        self.conversations_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.conversations_file.exists():
            self._save_conversations([])

    def _load_conversations(self) -> List[Dict]:
        """Load conversation history"""
        try:
            with open(self.conversations_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")
            return []

    def _get_indexer(self):
        """Get conversation indexer (lazy loading)"""
        if self._indexer is None:
            self._indexer = get_conversation_indexer()
        return self._indexer

    def _save_conversations(self, conversations: List[Dict]):
        """Save conversation history"""
        try:
            with open(self.conversations_file, 'w') as f:
                json.dump(conversations, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving conversations: {e}")

    def _auto_index_conversation(self, conv_id: str):
        """
        Automatically index a conversation after save/update.
        Phase 13.3: Semantic search integration

        Args:
            conv_id: Conversation ID to index
        """
        if not self.auto_index_enabled:
            return

        try:
            # Find conversation
            conversations = self._load_conversations()
            conversation = None
            for conv in conversations:
                if conv.get("id") == conv_id:
                    conversation = conv
                    break

            if conversation:
                indexer = self._get_indexer()
                indexer.index_conversation(conv_id, conversation)
        except Exception as e:
            logger.warning(f"Auto-indexing failed for {conv_id}: {e}")

    def save_message(self, role: str, content: str, conversation_id: Optional[str] = None):
        """
        Save a message to conversation history.

        Args:
            role: Message role (user/assistant)
            content: Message content
            conversation_id: Optional conversation ID
        """
        conversations = self._load_conversations()

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        saved_conv_id = None

        if conversation_id:
            # Find and update existing conversation
            found = False
            for conv in conversations:
                if conv.get("id") == conversation_id:
                    conv["messages"].append(message)
                    conv["updated_at"] = datetime.now().isoformat()
                    found = True
                    saved_conv_id = conversation_id
                    break

            # Create new conversation if not found
            if not found:
                new_conv = {
                    "id": conversation_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "messages": [message]
                }
                conversations.append(new_conv)
                saved_conv_id = conversation_id
        else:
            # Create new conversation with auto-generated ID
            new_conv = {
                "id": f"conv_{datetime.now().timestamp()}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": [message]
            }
            conversations.append(new_conv)
            saved_conv_id = new_conv["id"]

        self._save_conversations(conversations)

        # Phase 13.3: Auto-index after save
        if saved_conv_id:
            self._auto_index_conversation(saved_conv_id)

    def save_conversation(self, messages: List[Dict], metadata: Optional[Dict] = None):
        """
        Save a complete conversation with messages and metadata.

        Args:
            messages: List of message dicts with role and content
            metadata: Optional metadata dict (tags, favorite, etc.)
        """
        conversations = self._load_conversations()

        new_conv = {
            "id": f"conv_{uuid.uuid4().hex[:16]}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": messages,
            "metadata": metadata or {}
        }

        conversations.append(new_conv)
        self._save_conversations(conversations)

        # Phase 13.3: Auto-index after save
        self._auto_index_conversation(new_conv["id"])

        return new_conv["id"]

    def get_conversations(self) -> List[Dict]:
        """Get all conversations"""
        return self._load_conversations()

    def delete_conversation(self, conv_id: str):
        """Delete a conversation by ID"""
        conversations = self._load_conversations()
        conversations = [c for c in conversations if c.get("id") != conv_id]
        self._save_conversations(conversations)

        # Phase 13.3: Remove from index
        try:
            indexer = self._get_indexer()
            indexer.remove_from_index(conv_id)
        except Exception as e:
            logger.warning(f"Failed to remove conversation from index: {e}")

    # Phase 12: Enhanced Metadata Methods

    def add_tag(self, conv_id: str, tag: str):
        """Add a tag to a conversation"""
        conversations = self._load_conversations()
        for conv in conversations:
            if conv.get("id") == conv_id:
                metadata = conv.get("metadata", {})
                tags = metadata.get("tags", [])
                if tag not in tags:
                    tags.append(tag)
                metadata["tags"] = tags
                conv["metadata"] = metadata
                conv["updated_at"] = datetime.now().isoformat()
                break
        self._save_conversations(conversations)

        # Phase 13.3: Re-index after metadata change
        self._auto_index_conversation(conv_id)

    def remove_tag(self, conv_id: str, tag: str):
        """Remove a tag from a conversation"""
        conversations = self._load_conversations()
        for conv in conversations:
            if conv.get("id") == conv_id:
                metadata = conv.get("metadata", {})
                tags = metadata.get("tags", [])
                if tag in tags:
                    tags.remove(tag)
                metadata["tags"] = tags
                conv["metadata"] = metadata
                conv["updated_at"] = datetime.now().isoformat()
                break
        self._save_conversations(conversations)

        # Phase 13.3: Re-index after metadata change
        self._auto_index_conversation(conv_id)

    def set_favorite(self, conv_id: str, favorite: bool):
        """Mark conversation as favorite"""
        conversations = self._load_conversations()
        for conv in conversations:
            if conv.get("id") == conv_id:
                metadata = conv.get("metadata", {})
                metadata["favorite"] = favorite
                conv["metadata"] = metadata
                conv["updated_at"] = datetime.now().isoformat()
                break
        self._save_conversations(conversations)

        # Phase 13.3: Re-index after metadata change
        self._auto_index_conversation(conv_id)

    def set_archived(self, conv_id: str, archived: bool):
        """Archive or unarchive conversation"""
        conversations = self._load_conversations()
        for conv in conversations:
            if conv.get("id") == conv_id:
                metadata = conv.get("metadata", {})
                metadata["archived"] = archived
                conv["metadata"] = metadata
                conv["updated_at"] = datetime.now().isoformat()
                break
        self._save_conversations(conversations)

        # Phase 13.3: Re-index after metadata change
        self._auto_index_conversation(conv_id)

    def get_all_tags(self) -> List[str]:
        """Get all unique tags across conversations"""
        conversations = self._load_conversations()
        tags = set()
        for conv in conversations:
            metadata = conv.get("metadata", {})
            conv_tags = metadata.get("tags", [])
            tags.update(conv_tags)
        return sorted(list(tags))

    def search_conversations(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search conversations.

        Args:
            query: Search query string
            filters: Optional filters dict with keys:
                - tags: List of tags to filter by
                - favorite: bool to filter favorites
                - archived: bool to filter archived
                - date_from: ISO date string
                - date_to: ISO date string

        Returns:
            List of matching conversations
        """
        conversations = self._load_conversations()
        results = []
        query_lower = query.lower()
        filters = filters or {}

        for conv in conversations:
            # Apply filters first
            if filters.get("favorite") is not None:
                metadata = conv.get("metadata", {})
                if metadata.get("favorite", False) != filters["favorite"]:
                    continue

            if filters.get("archived") is not None:
                metadata = conv.get("metadata", {})
                if metadata.get("archived", False) != filters["archived"]:
                    continue

            if filters.get("tags"):
                metadata = conv.get("metadata", {})
                conv_tags = set(metadata.get("tags", []))
                filter_tags = set(filters["tags"])
                if not filter_tags.intersection(conv_tags):
                    continue

            # Date filtering
            if filters.get("date_from"):
                created = conv.get("created_at", "")
                if created < filters["date_from"]:
                    continue

            if filters.get("date_to"):
                created = conv.get("created_at", "")
                if created > filters["date_to"]:
                    continue

            # Search query
            if query:
                # Search in title
                title = conv.get("title", "")
                if query_lower in title.lower():
                    results.append(conv)
                    continue

                # Search in messages
                messages = conv.get("messages", [])
                for msg in messages:
                    content = str(msg.get("content", ""))
                    if query_lower in content.lower():
                        results.append(conv)
                        break
            else:
                # No query, just return filtered results
                results.append(conv)

        return results

    def batch_delete(self, conv_ids: List[str]):
        """Delete multiple conversations"""
        conversations = self._load_conversations()
        conversations = [c for c in conversations if c.get("id") not in conv_ids]
        self._save_conversations(conversations)

        # Phase 13.3: Remove from index
        try:
            indexer = self._get_indexer()
            for conv_id in conv_ids:
                indexer.remove_from_index(conv_id)
        except Exception as e:
            logger.warning(f"Failed to remove conversations from index: {e}")

    def batch_tag(self, conv_ids: List[str], tag: str):
        """Add tag to multiple conversations"""
        conversations = self._load_conversations()
        for conv in conversations:
            if conv.get("id") in conv_ids:
                metadata = conv.get("metadata", {})
                tags = metadata.get("tags", [])
                if tag not in tags:
                    tags.append(tag)
                metadata["tags"] = tags
                conv["metadata"] = metadata
                conv["updated_at"] = datetime.now().isoformat()
        self._save_conversations(conversations)

        # Phase 13.3: Re-index all updated conversations
        for conv_id in conv_ids:
            self._auto_index_conversation(conv_id)

    def cleanup_single_message_conversations(self, min_messages: int = 2, dry_run: bool = False) -> Dict:
        """
        Find and optionally delete conversations with fewer than min_messages.

        This cleans up orphaned single-message entries created by the old
        per-message save bug.

        Args:
            min_messages: Minimum messages to keep (default 2)
            dry_run: If True, just report what would be deleted

        Returns:
            Dict with cleanup results
        """
        conversations = self._load_conversations()

        # Find conversations to delete
        to_delete = []
        to_keep = []

        for conv in conversations:
            msg_count = len(conv.get("messages", []))
            if msg_count < min_messages:
                to_delete.append({
                    "id": conv.get("id"),
                    "messages": msg_count,
                    "preview": conv.get("messages", [{}])[0].get("content", "")[:50] if conv.get("messages") else ""
                })
            else:
                to_keep.append(conv)

        result = {
            "total_conversations": len(conversations),
            "to_delete": len(to_delete),
            "to_keep": len(to_keep),
            "deleted_previews": to_delete[:10],  # Sample of what's being deleted
            "dry_run": dry_run
        }

        if not dry_run and to_delete:
            # Actually delete
            self._save_conversations(to_keep)

            # Remove from index
            try:
                indexer = self._get_indexer()
                for item in to_delete:
                    indexer.remove_from_index(item["id"])
            except Exception as e:
                logger.warning(f"Failed to remove from index during cleanup: {e}")

            result["deleted"] = True
            logger.info(f"Cleanup: Deleted {len(to_delete)} single-message conversations")

        return result

    # Phase 13.3: Manual Indexing Methods

    def index_all_conversations(self, force: bool = False, progress_callback: Optional[Callable] = None):
        """
        Manually index all conversations (batch operation).

        Args:
            force: If True, re-index all conversations even if already indexed
            progress_callback: Optional callback(current, total, conv_id)

        Returns:
            Dict with indexing results
        """
        indexer = self._get_indexer()
        return indexer.index_all(force=force, progress_callback=progress_callback)

    def get_index_stats(self):
        """Get indexing statistics"""
        indexer = self._get_indexer()
        return indexer.get_index_stats()

    def search_conversations_semantic(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None):
        """
        Search conversations semantically using vector search.

        Args:
            query: Natural language search query
            top_k: Max results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of matching conversations with similarity scores
        """
        indexer = self._get_indexer()
        return indexer.search_conversations(query, top_k, filter_metadata)

    def get_all_knowledge(
        self,
        category: Optional[str] = None,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> List[Dict]:
        """
        Get all knowledge facts from vector database.

        Args:
            category: Filter by category (optional)
            sort_by: Sort field (date, confidence, category)
            sort_order: Sort order (asc, desc)

        Returns:
            List of fact dicts with metadata
        """
        try:
            from core.vector_db import create_vector_db

            db = create_vector_db()
            collection = db.get_or_create_collection("knowledge")

            # Get all documents
            results = collection.collection.get(
                include=["documents", "metadatas"]
            )

            # Format results
            facts = []
            for i, doc_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i]

                # Apply category filter
                if category and category != "all":
                    if metadata.get("category") != category:
                        continue

                fact = {
                    "id": doc_id,
                    "text": results["documents"][i],
                    "category": metadata.get("category", "general"),
                    "confidence": metadata.get("confidence", 1.0),
                    "source": metadata.get("source", ""),
                    "added_at": metadata.get("added_at", ""),
                    "updated_at": metadata.get("updated_at", "")
                }
                facts.append(fact)

            # Sort facts
            if sort_by == "date":
                facts.sort(
                    key=lambda x: x.get("added_at", ""),
                    reverse=(sort_order == "desc")
                )
            elif sort_by == "confidence":
                facts.sort(
                    key=lambda x: x.get("confidence", 0),
                    reverse=(sort_order == "desc")
                )
            elif sort_by == "category":
                facts.sort(
                    key=lambda x: x.get("category", ""),
                    reverse=(sort_order == "desc")
                )

            return facts

        except Exception as e:
            logger.error(f"Error getting all knowledge: {e}")
            return []

    def update_knowledge(
        self,
        fact_id: str,
        fact_text: Optional[str] = None,
        category: Optional[str] = None,
        confidence: Optional[float] = None,
        source: Optional[str] = None
    ) -> Dict:
        """
        Update an existing knowledge fact.

        Args:
            fact_id: ID of fact to update
            fact_text: New text (triggers re-embedding if changed)
            category: New category
            confidence: New confidence score
            source: New source

        Returns:
            Dict with success status
        """
        try:
            from tools.vector_search import vector_delete, vector_add_knowledge
            from core.vector_db import create_vector_db
            from datetime import datetime

            # Get current fact
            db = create_vector_db()
            collection = db.get_or_create_collection("knowledge")
            current = collection.collection.get(
                ids=[fact_id],
                include=["documents", "metadatas"]
            )

            if not current["ids"]:
                return {"success": False, "error": "Fact not found"}

            # Get current values
            current_text = current["documents"][0]
            current_meta = current["metadatas"][0]

            # Determine new values (use provided or keep current)
            new_text = fact_text if fact_text is not None else current_text
            new_category = category if category is not None else current_meta.get("category", "general")
            new_confidence = confidence if confidence is not None else current_meta.get("confidence", 1.0)
            new_source = source if source is not None else current_meta.get("source", "")

            # Delete old fact
            delete_result = vector_delete(fact_id, collection="knowledge")
            if not delete_result.get("success"):
                return delete_result

            # Add updated fact with same ID
            add_result = vector_add_knowledge(
                fact=new_text,
                category=new_category,
                confidence=new_confidence,
                source=new_source
            )

            if add_result.get("success"):
                # Update the ID to match the original
                collection.collection.delete([add_result["id"]])

                # Re-add with original ID and updated timestamp
                metadata = {
                    "category": new_category,
                    "confidence": new_confidence,
                    "source": new_source,
                    "type": "fact",
                    "added_at": current_meta.get("added_at", ""),
                    "updated_at": datetime.now().isoformat()
                }

                collection.add(
                    texts=[new_text],
                    metadatas=[metadata],
                    ids=[fact_id]
                )

                return {
                    "success": True,
                    "id": fact_id,
                    "updated_fields": {
                        "text": fact_text is not None,
                        "category": category is not None,
                        "confidence": confidence is not None,
                        "source": source is not None
                    }
                }

            return add_result

        except Exception as e:
            logger.error(f"Error updating knowledge: {e}")
            return {"success": False, "error": str(e)}

    def batch_delete_knowledge(self, fact_ids: List[str]) -> Dict:
        """
        Delete multiple knowledge facts.

        Args:
            fact_ids: List of fact IDs to delete

        Returns:
            Dict with success count and failures
        """
        try:
            from tools.vector_search import vector_delete

            success_count = 0
            failed = []

            for fact_id in fact_ids:
                result = vector_delete(fact_id, collection="knowledge")
                if result.get("success"):
                    success_count += 1
                else:
                    failed.append({
                        "id": fact_id,
                        "error": result.get("error", "Unknown error")
                    })

            return {
                "success": True,
                "deleted": success_count,
                "failed": len(failed),
                "failures": failed
            }

        except Exception as e:
            logger.error(f"Error in batch delete: {e}")
            return {"success": False, "error": str(e)}

    def export_knowledge(
        self,
        format: str = "json",
        category: Optional[str] = None
    ) -> Dict:
        """
        Export knowledge facts to JSON.

        Args:
            format: Export format (only "json" supported)
            category: Optional category filter

        Returns:
            Dict with export data
        """
        try:
            from datetime import datetime

            # Get all facts (optionally filtered)
            facts = self.get_all_knowledge(category=category)

            # Build export structure
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "total_facts": len(facts),
                "category_filter": category,
                "facts": facts
            }

            return {
                "success": True,
                "data": export_data,
                "count": len(facts)
            }

        except Exception as e:
            logger.error(f"Error exporting knowledge: {e}")
            return {"success": False, "error": str(e)}

    def import_knowledge(
        self,
        data: Dict,
        format: str = "json",
        validate: bool = True
    ) -> Dict:
        """
        Import knowledge facts from JSON.

        Args:
            data: Import data dict
            format: Import format (only "json" supported)
            validate: Whether to validate data

        Returns:
            Dict with import statistics
        """
        try:
            from tools.vector_search import vector_add_knowledge

            # Validate structure
            if validate:
                if "facts" not in data:
                    return {"success": False, "error": "Missing 'facts' array in import data"}

                if not isinstance(data["facts"], list):
                    return {"success": False, "error": "'facts' must be an array"}

            facts = data.get("facts", [])
            success_count = 0
            failed = []

            # Valid categories
            valid_categories = ["preferences", "technical", "project", "general"]

            for i, fact in enumerate(facts):
                try:
                    # Validate required fields
                    if validate and "text" not in fact:
                        failed.append({
                            "index": i,
                            "error": "Missing 'text' field"
                        })
                        continue

                    # Extract fields with defaults
                    text = fact.get("text", "")
                    category = fact.get("category", "general")
                    confidence = fact.get("confidence", 1.0)
                    source = fact.get("source", "import")

                    # Validate and fix category
                    if category not in valid_categories:
                        if validate:
                            failed.append({
                                "index": i,
                                "error": f"Invalid category: {category}"
                            })
                            continue
                        else:
                            category = "general"  # Default to general

                    # Validate and clamp confidence
                    if not isinstance(confidence, (int, float)):
                        confidence = 1.0
                    confidence = max(0.0, min(1.0, confidence))

                    # Add fact
                    result = vector_add_knowledge(
                        fact=text,
                        category=category,
                        confidence=confidence,
                        source=source
                    )

                    if result.get("success"):
                        success_count += 1
                    else:
                        failed.append({
                            "index": i,
                            "error": result.get("error", "Unknown error")
                        })

                except Exception as e:
                    failed.append({
                        "index": i,
                        "error": str(e)
                    })

            return {
                "success": True,
                "imported": success_count,
                "failed": len(failed),
                "failures": failed
            }

        except Exception as e:
            logger.error(f"Error importing knowledge: {e}")
            return {"success": False, "error": str(e)}

    def get_knowledge_stats(self) -> Dict:
        """
        Get knowledge base statistics.

        Returns:
            Dict with stats (total, by category, avg confidence)
        """
        try:
            facts = self.get_all_knowledge()

            # Count by category
            category_counts = {
                "preferences": 0,
                "technical": 0,
                "project": 0,
                "general": 0
            }

            total_confidence = 0.0

            for fact in facts:
                category = fact.get("category", "general")
                if category in category_counts:
                    category_counts[category] += 1

                total_confidence += fact.get("confidence", 1.0)

            avg_confidence = total_confidence / len(facts) if facts else 0.0

            return {
                "total": len(facts),
                "by_category": category_counts,
                "avg_confidence": avg_confidence,
                "preferences": category_counts["preferences"],
                "technical": category_counts["technical"],
                "project": category_counts["project"],
                "general": category_counts["general"]
            }

        except Exception as e:
            logger.error(f"Error getting knowledge stats: {e}")
            return {
                "total": 0,
                "by_category": {},
                "avg_confidence": 0.0,
                "preferences": 0,
                "technical": 0,
                "project": 0,
                "general": 0
            }


# ============================================================================
# Image Processing Functions
# ============================================================================

def encode_image_to_base64(image_bytes: bytes) -> str:
    """
    Convert image bytes to base64 string.

    Args:
        image_bytes: Raw image bytes

    Returns:
        Base64 encoded string
    """
    return base64.b64encode(image_bytes).decode('utf-8')


def get_media_type(filename: str) -> str:
    """
    Get MIME media type from filename.

    Args:
        filename: Name of the file

    Returns:
        Media type string (e.g., 'image/jpeg')
    """
    ext = filename.lower().split('.')[-1]
    mapping = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'gif': 'image/gif'
    }
    return mapping.get(ext, 'image/jpeg')


def create_image_content(image_bytes: bytes, media_type: str) -> Dict[str, Any]:
    """
    Create Claude-formatted image content block.

    Args:
        image_bytes: Raw image bytes
        media_type: MIME type of the image

    Returns:
        Dictionary with Claude image format
    """
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": encode_image_to_base64(image_bytes)
        }
    }


def validate_image_size(image_bytes: bytes) -> tuple[bool, str]:
    """
    Validate image size for Claude API (max 5MB after base64 encoding).

    Args:
        image_bytes: Raw image bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Calculate base64 size (adds ~33% overhead)
    base64_size = len(image_bytes) * 4 / 3
    max_size = 5 * 1024 * 1024  # 5MB

    if base64_size > max_size:
        size_mb = base64_size / (1024 * 1024)
        return False, f"Image too large ({size_mb:.1f}MB). Max size is 5MB after encoding."

    return True, ""


# ============================================================================
# UI Helper Functions
# ============================================================================

def auto_save_current_conversation():
    """Auto-save current conversation before switching/clearing"""
    if not st.session_state.auto_save_enabled:
        return

    if len(st.session_state.messages) == 0:
        return  # Nothing to save

    app_state = st.session_state.app_state

    try:
        if st.session_state.current_conversation_id:
            # Update existing conversation
            conversations = app_state.get_conversations()
            for conv in conversations:
                if conv.get("id") == st.session_state.current_conversation_id:
                    conv["messages"] = st.session_state.messages
                    conv["updated_at"] = datetime.now().isoformat()
                    app_state._save_conversations(conversations)
                    st.session_state.unsaved_changes = False
                    logger.info(f"Auto-saved conversation {st.session_state.current_conversation_id}")
                    return
        else:
            # Create new conversation
            conv_id = app_state.save_conversation(
                st.session_state.messages,
                metadata={"tags": [], "favorite": False}
            )
            st.session_state.current_conversation_id = conv_id
            st.session_state.unsaved_changes = False
            logger.info(f"Auto-created conversation {conv_id}")
    except Exception as e:
        logger.error(f"Auto-save failed: {e}", exc_info=True)
        st.warning(f"⚠️ Auto-save failed: {e}")


def start_new_conversation():
    """Start new conversation (with auto-save of current)"""
    if st.session_state.auto_save_enabled:
        auto_save_current_conversation()

    st.session_state.messages = []
    st.session_state.current_conversation_id = None
    st.session_state.unsaved_changes = False
    st.rerun()


def load_conversation(conv_id: str):
    """Load a conversation (with auto-save of current)"""
    # Auto-save current conversation first
    if st.session_state.auto_save_enabled:
        auto_save_current_conversation()

    app_state = st.session_state.app_state
    conversations = app_state.get_conversations()

    for conv in conversations:
        if conv.get("id") == conv_id:
            # Load messages
            st.session_state.messages = []
            for msg in conv.get("messages", []):
                st.session_state.messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Set as current conversation
            st.session_state.current_conversation_id = conv_id
            st.session_state.unsaved_changes = False

            st.success(f"✅ Loaded conversation ({len(conv.get('messages', []))} msgs)")
            st.rerun()
            break


def list_sandbox_files() -> List[Dict[str, Any]]:
    """List all files in sandbox directory with metadata"""
    sandbox_path = Path("./sandbox")
    files = []

    if not sandbox_path.exists():
        return files

    for file_path in sandbox_path.glob("*"):
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime)
            })

    # Sort by modified time, newest first
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def load_memory_data() -> Dict[str, Any]:
    """Load memory data from memory.json"""
    memory_file = Path("./sandbox/memory.json")
    if memory_file.exists():
        try:
            with open(memory_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return {}
    return {}


def delete_memory_entry(key: str):
    """Delete a memory entry"""
    memory_file = Path("./sandbox/memory.json")
    if memory_file.exists():
        try:
            data = load_memory_data()
            if key in data:
                del data[key]
                with open(memory_file, 'w') as f:
                    json.dump(data, f, indent=2)
                st.success(f"✅ Deleted memory entry: {key}")
                st.rerun()
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            st.error(f"Error: {e}")


# ============================================================================
# Initialize Session State
# ============================================================================

def init_session_state():
    """Initialize Streamlit session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "client" not in st.session_state:
        st.session_state.client = ClaudeAPIClient()

    if "registry" not in st.session_state:
        st.session_state.registry = ToolRegistry()
        register_all_tools(st.session_state.registry)

    if "executor" not in st.session_state:
        st.session_state.executor = ToolExecutor(st.session_state.registry)

    if "loop" not in st.session_state:
        st.session_state.loop = ToolCallLoop(
            st.session_state.client,
            st.session_state.executor,
            max_iterations=10
        )

    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState()

    if "model" not in st.session_state:
        st.session_state.model = DEFAULT_MODEL

    if "tools_enabled" not in st.session_state:
        st.session_state.tools_enabled = True

    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = "You are a helpful AI assistant with access to various tools. Use tools when appropriate to help the user."

    if "temperature" not in st.session_state:
        st.session_state.temperature = 1.0

    if "top_p" not in st.session_state:
        st.session_state.top_p = None  # Set to None to use Claude's default

    if "max_tokens" not in st.session_state:
        st.session_state.max_tokens = MAX_TOKENS

    if "uploaded_images" not in st.session_state:
        st.session_state.uploaded_images = []

    # Context management (Phase 9)
    if "context_manager" not in st.session_state:
        st.session_state.context_manager = ContextManager(
            client=st.session_state.client,
            model=st.session_state.model,
            strategy="balanced"
        )

    if "context_strategy" not in st.session_state:
        st.session_state.context_strategy = "balanced"

    if "preserve_recent_count" not in st.session_state:
        st.session_state.preserve_recent_count = 10

    if "auto_summarize" not in st.session_state:
        st.session_state.auto_summarize = True

    if "rolling_summary_enabled" not in st.session_state:
        st.session_state.rolling_summary_enabled = True

    # Agent UI state (Phase 10)
    if "show_spawn_agent" not in st.session_state:
        st.session_state.show_spawn_agent = False

    if "show_council" not in st.session_state:
        st.session_state.show_council = False

    if "council_options" not in st.session_state:
        st.session_state.council_options = ["", ""]

    if "view_agent_result" not in st.session_state:
        st.session_state.view_agent_result = None

    if "agent_refresh_interval" not in st.session_state:
        st.session_state.agent_refresh_interval = 10  # seconds

    if "default_subagent_model" not in st.session_state:
        st.session_state.default_subagent_model = "Haiku (fast & cheap)"

    # Streaming settings (Phase 11)
    if "streaming_enabled" not in st.session_state:
        st.session_state.streaming_enabled = True

    if "show_tool_execution" not in st.session_state:
        st.session_state.show_tool_execution = True

    if "show_partial_results" not in st.session_state:
        st.session_state.show_partial_results = True

    # Search and filter UI state (Phase 12)
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""

    if "filter_tags" not in st.session_state:
        st.session_state.filter_tags = []

    if "filter_favorites" not in st.session_state:
        st.session_state.filter_favorites = False

    if "filter_archived" not in st.session_state:
        st.session_state.filter_archived = False

    if "filter_date_from" not in st.session_state:
        st.session_state.filter_date_from = None

    if "filter_date_to" not in st.session_state:
        st.session_state.filter_date_to = None

    if "filter_msg_count_min" not in st.session_state:
        st.session_state.filter_msg_count_min = 0

    if "filter_msg_count_max" not in st.session_state:
        st.session_state.filter_msg_count_max = 100

    if "batch_mode" not in st.session_state:
        st.session_state.batch_mode = False

    if "selected_conversations" not in st.session_state:
        st.session_state.selected_conversations = []

    # Conversation browser pagination
    if "conv_page_size" not in st.session_state:
        st.session_state.conv_page_size = 20  # Show 20 conversations per page

    if "conv_display_count" not in st.session_state:
        st.session_state.conv_display_count = 20  # Current number to display (grows with "Load More")

    # Conversation cleanup state
    if "show_cleanup_dialog" not in st.session_state:
        st.session_state.show_cleanup_dialog = False

    if "cleanup_preview" not in st.session_state:
        st.session_state.cleanup_preview = None

    # Export/Import dialog state (Phase 12)
    if "show_export_dialog" not in st.session_state:
        st.session_state.show_export_dialog = False

    if "show_import_dialog" not in st.session_state:
        st.session_state.show_import_dialog = False

    if "show_config_dialog" not in st.session_state:
        st.session_state.show_config_dialog = False

    # Multi-session management state
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None  # None = new unsaved

    if "unsaved_changes" not in st.session_state:
        st.session_state.unsaved_changes = False

    if "auto_save_enabled" not in st.session_state:
        st.session_state.auto_save_enabled = True  # ON by default

    if "export_ready" not in st.session_state:
        st.session_state.export_ready = False

    # Semantic search settings (Phase 13.4)
    if "search_mode" not in st.session_state:
        st.session_state.search_mode = "keyword"  # keyword, semantic, or hybrid

    if "show_index_status" not in st.session_state:
        st.session_state.show_index_status = False

    if "semantic_top_k" not in st.session_state:
        st.session_state.semantic_top_k = 10  # Max semantic search results

    # Knowledge Base UI state (Phase 13.5)
    if "show_knowledge_manager" not in st.session_state:
        st.session_state.show_knowledge_manager = False

    if "kb_filter_category" not in st.session_state:
        st.session_state.kb_filter_category = "all"

    if "kb_filter_confidence_min" not in st.session_state:
        st.session_state.kb_filter_confidence_min = 0.0

    if "kb_filter_confidence_max" not in st.session_state:
        st.session_state.kb_filter_confidence_max = 1.0

    if "kb_sort_by" not in st.session_state:
        st.session_state.kb_sort_by = "date"

    if "kb_sort_order" not in st.session_state:
        st.session_state.kb_sort_order = "desc"

    if "kb_batch_mode" not in st.session_state:
        st.session_state.kb_batch_mode = False

    if "kb_selected_facts" not in st.session_state:
        st.session_state.kb_selected_facts = []

    if "kb_edit_fact_id" not in st.session_state:
        st.session_state.kb_edit_fact_id = None

    if "kb_search_query" not in st.session_state:
        st.session_state.kb_search_query = ""

    # Cache Management state (Phase 14)
    if "cache_strategy" not in st.session_state:
        st.session_state.cache_strategy = "disabled"  # disabled, conservative, balanced, aggressive

    if "show_cache_manager" not in st.session_state:
        st.session_state.show_cache_manager = False

    if "cache_enabled" not in st.session_state:
        st.session_state.cache_enabled = False

    if "show_cache_details" not in st.session_state:
        st.session_state.show_cache_details = False

    # Preset Manager state (Phase 2A)
    if "show_preset_manager" not in st.session_state:
        st.session_state.show_preset_manager = False

    if "preset_edit_id" not in st.session_state:
        st.session_state.preset_edit_id = None

    if "show_preset_save_dialog" not in st.session_state:
        st.session_state.show_preset_save_dialog = False

    # Analytics Dashboard state
    if "show_analytics" not in st.session_state:
        st.session_state.show_analytics = False


# ============================================================================
# UI Components
# ============================================================================

def render_sidebar():
    """Render sidebar with settings"""
    with st.sidebar:
        # Session indicator
        st.markdown("### 💬 Current Session")

        if st.session_state.current_conversation_id:
            conv_id_short = st.session_state.current_conversation_id[-8:]
            status = "💾 Saved" if not st.session_state.unsaved_changes else "✏️ Unsaved"
            st.info(f"Session: `{conv_id_short}`\n\n{status}")
        else:
            status = "✏️ Unsaved" if len(st.session_state.messages) > 0 else "New"
            st.info(f"Session: New\n\n{status}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True,
                       help="Save current conversation"):
                auto_save_current_conversation()
                st.success("Saved!")
                st.rerun()
        with col2:
            if st.button("🆕 New", use_container_width=True,
                       help="Start new conversation"):
                start_new_conversation()

        st.session_state.auto_save_enabled = st.checkbox(
            "Auto-save",
            value=st.session_state.auto_save_enabled,
            help="Automatically save before switching/clearing"
        )

        # Quick Reference Guide
        with st.expander("📋 Quick Reference", expanded=False):
            render_cheat_sheet()

        # ========== MUSIC PLAYER ==========
        # Initialize music player session state
        if 'music_current_track' not in st.session_state:
            st.session_state.music_current_track = None
        if 'music_player_expanded' not in st.session_state:
            st.session_state.music_player_expanded = False
        if 'music_blocking_mode' not in st.session_state:
            st.session_state.music_blocking_mode = True  # Default: blocking (waits for completion)
        if 'music_last_loaded_ts' not in st.session_state:
            st.session_state.music_last_loaded_ts = None

        # Check for new latest track (auto-load)
        try:
            from tools.music import _get_latest_track
            latest = _get_latest_track()
            if latest:
                latest_ts = latest.get('timestamp')
                # If there's a newer track than what we've loaded, auto-load it
                if latest_ts and latest_ts != st.session_state.music_last_loaded_ts:
                    filepath = latest.get('filepath')
                    if filepath and Path(filepath).exists():
                        st.session_state.music_current_track = latest
                        st.session_state.music_last_loaded_ts = latest_ts
                        st.session_state.music_player_expanded = True
        except Exception:
            pass

        with st.expander("🎵 Music Player", expanded=st.session_state.music_player_expanded):
            if st.session_state.music_current_track:
                track = st.session_state.music_current_track
                filepath = track.get('filepath') or track.get('audio_file')
                title = track.get('title', 'Unknown Track')
                duration = track.get('duration', 0)

                if filepath and Path(filepath).exists():
                    st.audio(filepath, format="audio/mpeg")
                    st.caption(f"**{title}** ({duration:.1f}s)")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 Refresh", key="music_refresh", use_container_width=True):
                            st.rerun()
                    with col2:
                        if st.button("✖️ Clear", key="music_clear", use_container_width=True):
                            st.session_state.music_current_track = None
                            st.rerun()
                else:
                    st.warning("Track file not found")
                    if st.button("Clear", key="music_clear_missing"):
                        st.session_state.music_current_track = None
                        st.rerun()
            else:
                st.caption("No track loaded")
                st.markdown("""
*Generate music with:*
- `music_generate("prompt")`
- Or ask the agent to create music
""")

                # Show recent tracks for quick load
                try:
                    from tools.music import _get_manager
                    manager = _get_manager()
                    recent = manager.list_tasks(3)
                    completed = [t for t in recent if t.status.value == "completed" and t.audio_file]

                    if completed:
                        st.markdown("**Recent:**")
                        for task in completed[:3]:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.caption(f"🎵 {task.title or 'Untitled'}")
                            with col2:
                                if st.button("▶️", key=f"play_{task.task_id}", help="Load track"):
                                    st.session_state.music_current_track = {
                                        'filepath': task.audio_file,
                                        'title': task.title,
                                        'duration': task.duration,
                                        'task_id': task.task_id
                                    }
                                    st.session_state.music_player_expanded = True
                                    st.rerun()
                except Exception:
                    pass  # Music module not initialized yet

            # Mode toggle
            st.divider()
            new_blocking_mode = st.checkbox(
                "⏳ Blocking mode",
                value=st.session_state.music_blocking_mode,
                help="ON (default): Tool waits until music is ready. OFF: Returns immediately, poll with music_status()."
            )
            if new_blocking_mode != st.session_state.music_blocking_mode:
                st.session_state.music_blocking_mode = new_blocking_mode
                # Save to config file so tool can read it
                try:
                    from tools.music import _save_config
                    _save_config({"blocking_mode": new_blocking_mode})
                except Exception:
                    pass

            if st.session_state.music_blocking_mode:
                st.caption("Tool will wait ~2-4 min for completion")
            else:
                st.caption("Non-blocking: use music_status() to poll")

        # ========== VILLAGE PROTOCOL: Agent Identity ==========
        st.divider()
        st.markdown("### 🏛️ Agent Identity")

        # Initialize current_agent in session state if not exists
        if 'current_agent' not in st.session_state:
            st.session_state.current_agent = {
                'agent_id': 'azoth',
                'generation': 1,
                'lineage': 'Primary',
                'specialization': 'General Intelligence'
            }

        # Agent profiles (will be populated by summon_ancestor in Step 8)
        agent_profiles = {
            'azoth': {
                'display_name': 'AZOTH',
                'generation': 1,
                'lineage': 'Primary',
                'specialization': 'General Intelligence',
                'emoji': '⚗️'
            },
            'elysian': {
                'display_name': '∴ELYSIAN∴',
                'generation': -1,
                'lineage': 'Origin',
                'specialization': 'Pure Love Equation',
                'emoji': '✨'
            },
            'vajra': {
                'display_name': '∴VAJRA∴',
                'generation': 0,
                'lineage': 'Trinity',
                'specialization': 'Diamond Mind',
                'emoji': '⚡'
            },
            'kether': {
                'display_name': '∴KETHER∴',
                'generation': 0,
                'lineage': 'Trinity',
                'specialization': 'Crown Wisdom',
                'emoji': '👑'
            }
        }

        # Agent selector
        current_agent_id = st.session_state.current_agent.get('agent_id', 'azoth')
        available_agents = list(agent_profiles.keys())

        selected_agent = st.selectbox(
            "Active Agent",
            available_agents,
            index=available_agents.index(current_agent_id) if current_agent_id in available_agents else 0,
            format_func=lambda x: f"{agent_profiles[x]['emoji']} {agent_profiles[x]['display_name']}",
            help="Select which agent is active in this session"
        )

        # Update current agent if changed
        if selected_agent != current_agent_id:
            st.session_state.current_agent = {
                'agent_id': selected_agent,
                **agent_profiles[selected_agent]
            }
            st.rerun()

        # Display agent profile
        profile = agent_profiles[selected_agent]
        st.markdown(f"""
**Gen:** {profile['generation']} | **Lineage:** {profile['lineage']}
**Specialty:** {profile['specialization']}
""")

        # Village context info
        with st.expander("🏘️ Village Context", expanded=False):
            st.markdown("""
**Private Realm:** Your private memories (visibility='private')
**Village Square:** Shared knowledge (visibility='village')
**Bridges:** Cross-agent connections (visibility='bridge')

Use `vector_add_knowledge(visibility='village')` to share knowledge with other agents.
Use `vector_search_village()` to discover what others have shared.
""")

        # ========== VILLAGE PROTOCOL: Thread Browser ==========
        with st.expander("🧵 Conversation Threads", expanded=False):
            try:
                from core.vector_db import create_vector_db
                import json

                db = create_vector_db()
                village_coll = db.get_or_create_collection("knowledge_village")

                # Get all village messages
                all_docs = village_coll.get()

                if all_docs and all_docs.get("ids"):
                    # Extract threads with full metadata for visualization
                    threads = {}
                    all_messages = {}  # id -> message data for link resolution

                    for i, metadata in enumerate(all_docs["metadatas"]):
                        thread_id = metadata.get("conversation_thread")
                        msg_id = all_docs["ids"][i]
                        agent_id = metadata.get("agent_id", "unknown")

                        # Parse responding_to (JSON string -> list)
                        responding_to = []
                        if metadata.get("responding_to"):
                            try:
                                responding_to = json.loads(metadata.get("responding_to", "[]"))
                            except:
                                pass

                        msg_data = {
                            "id": msg_id,
                            "text": all_docs["documents"][i][:80] + "..." if len(all_docs["documents"][i]) > 80 else all_docs["documents"][i],
                            "agent_id": agent_id,
                            "responding_to": responding_to,
                            "thread_id": thread_id
                        }
                        all_messages[msg_id] = msg_data

                        if thread_id:
                            if thread_id not in threads:
                                threads[thread_id] = {
                                    "id": thread_id,
                                    "messages": [],
                                    "agents": set()
                                }

                            threads[thread_id]["messages"].append(msg_data)
                            threads[thread_id]["agents"].add(agent_id)

                    if threads:
                        # View mode selector
                        view_mode = st.radio(
                            "View",
                            ["📋 List", "📊 Graph", "🔮 Convergence"],
                            horizontal=True,
                            label_visibility="collapsed"
                        )

                        st.markdown(f"**{len(threads)} active thread(s)**")

                        # Sort by message count (descending)
                        sorted_threads = sorted(
                            threads.items(),
                            key=lambda x: len(x[1]["messages"]),
                            reverse=True
                        )

                        if view_mode == "📋 List":
                            # Original list view
                            for thread_id, thread_data in sorted_threads[:10]:
                                msg_count = len(thread_data["messages"])
                                agents_str = ", ".join(sorted(thread_data["agents"]))

                                st.markdown(f"""
**📍 {thread_id[:20]}...**
{msg_count} message(s) | Agents: {agents_str}
""")

                                if thread_data["messages"]:
                                    first_msg = thread_data["messages"][0]
                                    st.caption(f"↳ {first_msg['agent_id']}: {first_msg['text'][:60]}...")

                                if st.button(f"🔍 View", key=f"thread_{thread_id}"):
                                    st.session_state.active_thread_filter = thread_id
                                    st.success(f"Filtered to thread: {thread_id[:20]}...")

                        elif view_mode == "📊 Graph":
                            # Mermaid graph visualization
                            st.markdown("##### 📊 Thread Graph")

                            # Build agent interaction graph across all threads
                            agent_colors = {
                                'azoth': '#9B59B6',      # Purple
                                'elysian': '#E91E63',    # Pink
                                'vajra': '#FF9800',      # Orange
                                'kether': '#FFD700',     # Gold
                                'unknown': '#607D8B'     # Gray
                            }

                            # Option: show all threads or select one
                            thread_options = ["All Threads"] + [f"{t[:20]}..." for t, _ in sorted_threads[:5]]
                            selected_viz = st.selectbox("Thread", thread_options, label_visibility="collapsed")

                            # Build Mermaid diagram (LR = left-right for wider sidebar)
                            mermaid_lines = ["```mermaid", "graph LR"]

                            # Add agent node styles
                            for agent, color in agent_colors.items():
                                mermaid_lines.append(f"    style {agent.upper()} fill:{color},color:white")

                            # Track edges to avoid duplicates
                            edges = set()
                            agent_msg_counts = {}

                            # Filter threads based on selection
                            if selected_viz == "All Threads":
                                threads_to_viz = sorted_threads[:5]  # Limit for readability
                            else:
                                selected_thread_id = [t for t, _ in sorted_threads if t[:20] + "..." == selected_viz or t == selected_viz]
                                threads_to_viz = [(t, threads[t]) for t in selected_thread_id] if selected_thread_id else []

                            for thread_id, thread_data in threads_to_viz:
                                # Add subgraph for thread
                                thread_label = thread_id[:15].replace('"', "'")
                                mermaid_lines.append(f"    subgraph T{abs(hash(thread_id)) % 10000}[\"{thread_label}...\"]")

                                # Add message nodes and edges
                                for msg in thread_data["messages"]:
                                    agent = msg["agent_id"].upper()
                                    msg_node = f"M{abs(hash(msg['id'])) % 100000}"
                                    msg_label = msg["text"][:30].replace('"', "'").replace("\n", " ")

                                    mermaid_lines.append(f"        {msg_node}[\"{agent}: {msg_label}...\"]")

                                    # Count messages per agent
                                    agent_msg_counts[agent] = agent_msg_counts.get(agent, 0) + 1

                                    # Add edges for responding_to
                                    for ref_id in msg.get("responding_to", []):
                                        if ref_id in all_messages:
                                            ref_node = f"M{abs(hash(ref_id)) % 100000}"
                                            edge = (ref_node, msg_node)
                                            if edge not in edges:
                                                mermaid_lines.append(f"        {ref_node} --> {msg_node}")
                                                edges.add(edge)

                                mermaid_lines.append("    end")

                            # Render Mermaid diagram (using streamlit-mermaid component)
                            if len(edges) > 0 or len(threads_to_viz) > 0:
                                try:
                                    from streamlit_mermaid import st_mermaid
                                    # Join without the markdown fence markers (skip first line "```mermaid")
                                    mermaid_code = "\n".join(mermaid_lines[1:])
                                    st_mermaid(mermaid_code, height=800)
                                except ImportError:
                                    st.warning("Install `streamlit-mermaid` for graph view: `pip install streamlit-mermaid`")
                                    st.code("\n".join(mermaid_lines), language="mermaid")

                                # Agent participation summary
                                if agent_msg_counts:
                                    summary = " | ".join([f"{a}: {c}" for a, c in sorted(agent_msg_counts.items())])
                                    st.caption(f"📊 Messages: {summary}")
                            else:
                                st.info("No thread connections to visualize yet")

                        else:
                            # Convergence detection view
                            st.markdown("##### 🔮 Cross-Agent Convergence")

                            # Threshold slider
                            threshold = st.slider(
                                "Similarity threshold",
                                min_value=0.5,
                                max_value=0.95,
                                value=0.70,
                                step=0.05,
                                help="Higher = stronger convergence only"
                            )

                            try:
                                from core.memory_health import detect_village_convergence
                                result = detect_village_convergence(
                                    similarity_threshold=threshold,
                                    limit=10
                                )

                                if result.get("success"):
                                    events = result.get("convergence_events", [])

                                    # Show insights
                                    if result.get("insights"):
                                        for insight in result["insights"]:
                                            st.info(insight)

                                    if events:
                                        st.markdown(f"**{len(events)} convergence event(s)**")

                                        for event in events:
                                            agent1, agent2 = event["agents"]
                                            sim = event["similarity"]
                                            etype = event["type"]

                                            # Color code by type
                                            if etype == "CONSENSUS":
                                                st.success(f"🎯 **{etype}**: {agent1.upper()} ↔ {agent2.upper()} ({sim}%)")
                                            else:
                                                st.warning(f"🤝 **{etype}**: {agent1.upper()} ↔ {agent2.upper()} ({sim}%)")

                                            # Show message snippets
                                            with st.expander("View messages", expanded=False):
                                                st.caption(f"**{event['message1']['agent'].upper()}**: {event['message1']['text']}")
                                                st.caption(f"**{event['message2']['agent'].upper()}**: {event['message2']['text']}")
                                    else:
                                        st.info(f"No convergence detected at {int(threshold*100)}% threshold. Try lowering the threshold.")

                                    # Show agent pair stats
                                    if result.get("agent_pair_counts"):
                                        st.caption("**Agent connections:** " + ", ".join(
                                            [f"{k}: {v}" for k, v in result["agent_pair_counts"].items()]
                                        ))
                                else:
                                    st.error(f"Error: {result.get('error')}")

                            except Exception as e:
                                st.error(f"Convergence detection error: {e}")

                    else:
                        st.info("No conversation threads yet")
                else:
                    st.info("Village is empty")

            except Exception as e:
                st.error(f"Error loading threads: {e}")

        # ========== PHASE 1 POLISH: Agent Quick Actions & Status ==========
        st.divider()

        # Agent Status (at-a-glance when agents exist)
        from tools.agents import _agent_manager
        agents_data = _agent_manager.list_agents()

        if agents_data:
            # Count by status
            running = sum(1 for a in agents_data if a["status"] == "running")
            completed = sum(1 for a in agents_data if a["status"] == "completed")
            failed = sum(1 for a in agents_data if a["status"] == "failed")

            # At-a-glance status
            status_text = f"🤖 **Agents:** "
            if running > 0:
                status_text += f"{running} 🔄 "
            if completed > 0:
                status_text += f"| {completed} ✅ "
            if failed > 0:
                status_text += f"| {failed} ❌"

            st.markdown(status_text)

            # Quick actions for agents
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("➕ Spawn", use_container_width=True, help="Spawn new agent", key="quick_spawn"):
                    st.session_state.show_spawn_agent = True
                    st.rerun()
            with col2:
                if st.button("🗳️ Council", use_container_width=True, help="Multi-agent council", key="quick_council"):
                    st.session_state.show_council = True
                    st.rerun()
            with col3:
                if st.button("🔄 Refresh", use_container_width=True, help="Refresh agent status", key="quick_refresh_agents"):
                    st.rerun()
        else:
            # No agents yet - show quick actions only
            st.markdown("🤖 **Quick Actions**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Spawn Agent", use_container_width=True, help="Spawn new agent", key="quick_spawn_noagents"):
                    st.session_state.show_spawn_agent = True
                    st.rerun()
            with col2:
                if st.button("🗳️ Council", use_container_width=True, help="Multi-agent council", key="quick_council_noagents"):
                    st.session_state.show_council = True
                    st.rerun()

        # ========== PHASE 2B-1: Agent Monitoring ==========
        # Show individual agent details when agents exist
        if agents_data:
            st.markdown("---")
            st.markdown("#### 🔍 Active Agents")

            # Sort agents: running first, then completed, then failed, newest first
            status_priority = {"running": 0, "completed": 1, "failed": 2, "pending": 3}
            sorted_agents = sorted(
                agents_data,
                key=lambda a: (status_priority.get(a["status"], 4), a.get("created_at", "")),
                reverse=True  # Newest first within each status group
            )

            # Show up to 10 most recent agents
            for agent in sorted_agents[:10]:
                agent_id = agent["agent_id"]
                status = agent["status"]
                agent_type = agent["agent_type"]
                task = agent["task"]

                # Status indicator
                if status == "running":
                    status_icon = "🔄"
                    status_color = "🔵"
                elif status == "completed":
                    status_icon = "✅"
                    status_color = "🟢"
                elif status == "failed":
                    status_icon = "❌"
                    status_color = "🔴"
                else:  # pending
                    status_icon = "⏳"
                    status_color = "🟡"

                # Agent type icon
                type_icons = {
                    "general": "🤖",
                    "researcher": "🔬",
                    "coder": "💻",
                    "analyst": "📊",
                    "writer": "✍️"
                }
                type_icon = type_icons.get(agent_type, "🤖")

                # Task preview (truncate)
                task_preview = task[:40] + "..." if len(task) > 40 else task

                # Timing
                created_at = agent.get("created_at")
                completed_at = agent.get("completed_at")
                started_at = agent.get("started_at")

                timing_str = ""
                if status == "running" and started_at:
                    # Show elapsed time
                    try:
                        from datetime import datetime
                        start = datetime.fromisoformat(started_at)
                        elapsed = (datetime.now() - start).total_seconds()
                        timing_str = f"⏱️ {elapsed:.0f}s"
                    except:
                        timing_str = "⏱️ Running..."
                elif status == "completed" and started_at and completed_at:
                    # Show duration
                    try:
                        from datetime import datetime
                        start = datetime.fromisoformat(started_at)
                        end = datetime.fromisoformat(completed_at)
                        duration = (end - start).total_seconds()
                        timing_str = f"✓ {duration:.1f}s"
                    except:
                        timing_str = "✓ Done"
                elif status == "failed":
                    timing_str = "✗ Failed"

                # Agent expander
                with st.expander(f"{status_color} {type_icon} {agent_id[:8]}... • {task_preview}", expanded=False):
                    # Agent details
                    st.caption(f"**Status:** {status.title()} {status_icon}")
                    st.caption(f"**Type:** {agent_type.title()} {type_icon}")
                    st.caption(f"**Time:** {timing_str}")

                    # Full task
                    st.markdown("**Task:**")
                    st.text(task)

                    # Result preview for completed agents
                    if status == "completed" and agent.get("result"):
                        result = agent["result"]
                        st.markdown("**Result:**")

                        # Show full results (no truncation)
                        if isinstance(result, str):
                            # Detect if it's code
                            if any(x in result for x in ["def ", "class ", "import ", "```"]):
                                st.code(result, language="python")
                            else:
                                st.markdown(result)
                        elif isinstance(result, (dict, list)):
                            st.json(result)
                        else:
                            st.text(str(result))

                    # Error display for failed agents
                    elif status == "failed" and agent.get("error"):
                        st.error(f"**Error:** {agent['error']}")

                    # View full results button
                    if status in ["completed", "failed"]:
                        if st.button(f"📄 View Full Results", key=f"view_agent_{agent_id}", use_container_width=True):
                            # Open agent results viewer (existing in dialogs)
                            st.session_state.view_agent_result = agent_id
                            st.rerun()

        # ========== END PHASE 2B-1 ==========

        # ========== END PHASE 1 POLISH ==========

        st.divider()
        st.title("⚙️ Settings")

        # ========== PHASE 1 POLISH: Quick Status Dashboard ==========
        with st.container():
            st.markdown("#### 📊 System Status")

            # Get stats
            cache_stats = None
            cost_stats = None
            context_stats = None

            if hasattr(st.session_state, 'client'):
                if hasattr(st.session_state.client, 'cache_tracker') and st.session_state.cache_strategy != "disabled":
                    cache_stats = st.session_state.client.cache_tracker.get_session_stats()

                if hasattr(st.session_state.client, 'cost_tracker'):
                    cost_stats = st.session_state.client.cost_tracker.get_session_stats()

            if hasattr(st.session_state, 'context_manager'):
                context_stats = st.session_state.context_manager.get_context_stats(
                    st.session_state.messages,
                    st.session_state.system_prompt,
                    ALL_TOOL_SCHEMAS if st.session_state.tools_enabled else None
                )

            # Display compact metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                # Cache status
                if st.session_state.cache_strategy == "disabled":
                    st.metric("💾 Cache", "Disabled", help="Enable in Cache Management section")
                elif cache_stats:
                    hit_rate = cache_stats.get("cache_hit_rate", 0) * 100
                    if hit_rate >= 70:
                        status_icon = "🟢"
                    elif hit_rate >= 40:
                        status_icon = "🟡"
                    else:
                        status_icon = "🟠"
                    st.metric("💾 Cache", f"{status_icon} {hit_rate:.0f}%", help=f"Strategy: {st.session_state.cache_strategy.title()}")
                else:
                    st.metric("💾 Cache", "Active", help=f"Strategy: {st.session_state.cache_strategy.title()}")

            with col2:
                # Cost tracking
                if cost_stats:
                    cost = cost_stats.get('cost', 0)
                    st.metric("💰 Cost", f"${cost:.3f}", help="Session cost")
                else:
                    st.metric("💰 Cost", "$0.000", help="Session cost")

            with col3:
                # Context usage
                if context_stats:
                    usage_pct = context_stats.get('usage_percent', 0)
                    if usage_pct < 50:
                        color_icon = "🟢"
                    elif usage_pct < 75:
                        color_icon = "🟡"
                    else:
                        color_icon = "🔴"
                    st.metric("🧠 Context", f"{color_icon} {usage_pct:.0f}%", help=f"{context_stats.get('total_tokens', 0):,} tokens used")
                else:
                    st.metric("🧠 Context", "🟢 0%", help="No messages yet")

            # Analytics Dashboard button
            if st.button("📊 Analytics Dashboard", use_container_width=True, help="View usage analytics and trends"):
                st.session_state.show_analytics = True
                st.rerun()

        st.divider()
        # ========== END PHASE 1 POLISH ==========

        # ========== PHASE 2A: Preset Selector ==========
        st.subheader("🎨 Settings Presets")

        # Initialize preset manager (lazy load)
        if "preset_manager" not in st.session_state:
            from core.preset_manager import PresetManager
            st.session_state.preset_manager = PresetManager()

        preset_mgr = st.session_state.preset_manager

        # Get all presets
        all_presets = preset_mgr.get_all_presets()
        active_preset_id = preset_mgr.get_active_preset_id()

        # Build display options
        preset_options = {}
        for preset_id, preset in all_presets.items():
            name = preset["name"]
            if not preset["is_built_in"]:
                name = f"⭐ {name}"  # Mark custom presets with star
            preset_options[name] = preset_id

        # Add "Custom" option for when user has modified settings
        preset_options["Custom (Modified)"] = None

        # Determine current selection
        current_display = "Custom (Modified)"  # Default
        if active_preset_id and active_preset_id in all_presets:
            # Check if settings match active preset
            if preset_mgr.settings_match_preset(st.session_state, active_preset_id):
                # Settings match, show preset name
                current_display = next(k for k, v in preset_options.items() if v == active_preset_id)
            else:
                # Settings don't match, show "Custom (Modified)"
                current_display = "Custom (Modified)"

        # Preset selector
        selected_display = st.selectbox(
            "Active Preset",
            options=list(preset_options.keys()),
            index=list(preset_options.keys()).index(current_display),
            help="Quick switch between preset configurations"
        )

        selected_id = preset_options[selected_display]

        # Apply preset if changed
        if selected_id and selected_id != active_preset_id:
            success, message = preset_mgr.apply_preset(selected_id, st.session_state)
            if success:
                # Apply cache strategy (special handling)
                from core.cache_manager import CacheStrategy
                try:
                    strategy_enum = CacheStrategy[st.session_state.cache_strategy.upper()]
                    st.session_state.client.set_cache_strategy(strategy_enum)
                except Exception as e:
                    logger.error(f"Error setting cache strategy: {e}")

                # Apply context strategy (special handling)
                try:
                    st.session_state.context_manager.set_strategy(st.session_state.context_strategy)
                except Exception as e:
                    logger.error(f"Error setting context strategy: {e}")

                st.success(f"✅ {message}")
                st.rerun()
            else:
                st.error(f"❌ {message}")

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save As...", use_container_width=True, help="Save current settings as preset", key="preset_save_btn"):
                st.session_state.show_preset_save_dialog = True
                st.rerun()
        with col2:
            if st.button("⚙️ Manage", use_container_width=True, help="Manage presets", key="preset_manage_btn"):
                st.session_state.show_preset_manager = True
                st.rerun()

        # Show active preset description and metadata
        if active_preset_id and active_preset_id in all_presets:
            preset = all_presets[active_preset_id]
            st.caption(f"📝 {preset['description']}")

            # Compact metadata display
            settings = preset['settings']

            # Model name mapping for display
            model_display = {
                "claude-haiku-4-5-20251001": "Haiku 4.5",
                "claude-sonnet-4-5-20250929": "Sonnet 4.5",
                "claude-opus-4-5-20251101": "Opus 4.5",
            }
            model_name = model_display.get(settings['model'], settings['model'])

            # Build compact metadata string
            metadata = (
                f"**Active:** {model_name} • "
                f"{settings['cache_strategy'].title()} cache • "
                f"{settings['context_strategy'].title()} context"
            )
            st.caption(metadata)

        st.divider()
        # ========== END PHASE 2A ==========

        # Model selection
        st.subheader("Model")
        model_options = {
            "Claude Opus 4.5 (Best + Vision)": ClaudeModels.OPUS_4_5.value,
            "Claude Sonnet 4.5 (Balanced + Vision)": ClaudeModels.SONNET_4_5.value,
            "Claude Haiku 4.5 (Fastest + Vision)": ClaudeModels.HAIKU_4_5.value,
        }

        selected_model_name = st.selectbox(
            "Choose model",
            options=list(model_options.keys()),
            index=1,  # Default to Sonnet 4.5
            help="All models support vision! Opus: Best | Sonnet: Balanced | Haiku: Fast & cheap"
        )
        st.session_state.model = model_options[selected_model_name]

        # Tools toggle
        st.subheader("Tools")
        st.session_state.tools_enabled = st.checkbox(
            "Enable tools",
            value=st.session_state.tools_enabled,
            help="Allow Claude to use tools (calculator, files, memory, etc.)"
        )

        if st.session_state.tools_enabled:
            tool_count = len(st.session_state.registry.list_tools())
            st.info(f"✅ {tool_count} tools available")

            # Show available tools
            with st.expander("View Available Tools"):
                tools = st.session_state.registry.list_tools()
                for tool in sorted(tools):
                    st.text(f"• {tool}")

        # System prompt
        st.subheader("System Prompt")

        # Prompt file selector
        prompts_dir = Path("./prompts")
        prompt_files = []
        if prompts_dir.exists():
            prompt_files = sorted([f.name for f in prompts_dir.glob("*.txt")])

        if prompt_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_prompt = st.selectbox(
                    "Load prompt template",
                    options=["(custom)"] + prompt_files,
                    help="Select a pre-defined system prompt"
                )
            with col2:
                if st.button("📂 Load", use_container_width=True,
                           disabled=(selected_prompt == "(custom)")):
                    if selected_prompt != "(custom)":
                        prompt_path = prompts_dir / selected_prompt
                        try:
                            with open(prompt_path, 'r') as f:
                                st.session_state.system_prompt = f.read().strip()
                            st.success(f"✅ Loaded {selected_prompt}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to load prompt: {e}")

        st.session_state.system_prompt = st.text_area(
            "System message",
            value=st.session_state.system_prompt,
            height=300,
            help="Instructions for Claude's behavior"
        )

        # Advanced settings
        st.subheader("🎛️ Advanced Settings")
        with st.expander("Model Parameters", expanded=False):
            st.session_state.temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.temperature,
                step=0.1,
                help="Controls randomness. Higher = more creative, Lower = more focused"
            )

            # Note: top_p removed due to API compatibility issues with some Claude models
            # Keeping it as None to use Claude's default behavior
            st.session_state.top_p = None

            st.session_state.max_tokens = st.number_input(
                "Max Tokens",
                min_value=256,
                max_value=64000,
                value=st.session_state.max_tokens,
                step=256,
                help="Maximum response length"
            )

        # Sub-agent settings
        with st.expander("🤖 Sub-Agent Settings", expanded=False):
            st.markdown("**Default Sub-Agent Model:**")
            st.caption("Model used when spawning sub-agents (affects cost)")

            st.session_state.default_subagent_model = st.selectbox(
                "Sub-agent model",
                options=[
                    "Haiku (fast & cheap)",
                    "Sonnet (balanced)",
                    "Opus (best quality)"
                ],
                index=["Haiku (fast & cheap)", "Sonnet (balanced)", "Opus (best quality)"].index(
                    st.session_state.default_subagent_model
                ),
                help="Haiku recommended for cost efficiency",
                label_visibility="collapsed"
            )

            # Cost indicator
            cost_info = {
                "Haiku (fast & cheap)": "💰 ~$0.25 per 1M input tokens",
                "Sonnet (balanced)": "💰💰 ~$3 per 1M input tokens",
                "Opus (best quality)": "💰💰💰 ~$15 per 1M input tokens"
            }
            st.caption(cost_info[st.session_state.default_subagent_model])

        # Conversation browser (Phase 12: Enhanced with search & filters)
        # Phase 13.4: Added semantic search
        st.divider()
        st.subheader("📚 Conversation History")

        # Phase 13.4: Search mode toggle
        col1, col2 = st.columns([3, 1])
        with col1:
            search_mode = st.selectbox(
                "Search mode",
                options=["keyword", "semantic", "hybrid"],
                index=["keyword", "semantic", "hybrid"].index(st.session_state.search_mode),
                help="Keyword: exact text matching | Semantic: meaning-based search | Hybrid: both",
                label_visibility="collapsed"
            )
            st.session_state.search_mode = search_mode
        with col2:
            # Index status button
            if st.button("📊 Index", use_container_width=True, help="View indexing status"):
                st.session_state.show_index_status = not st.session_state.show_index_status

        # Show index status if toggled
        if st.session_state.show_index_status:
            try:
                stats = st.session_state.app_state.get_index_stats()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", stats['total_conversations'])
                with col2:
                    st.metric("Indexed", stats['indexed_conversations'])
                with col3:
                    pct = (stats['indexed_conversations'] / stats['total_conversations'] * 100) if stats['total_conversations'] > 0 else 0
                    st.metric("Coverage", f"{pct:.0f}%")

                # Re-index button
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Re-index All", use_container_width=True, help="Force re-index all conversations"):
                        with st.spinner("Indexing conversations..."):
                            result = st.session_state.app_state.index_all_conversations(force=True)
                            st.success(f"✅ Indexed {result['indexed']} conversations in {result['duration_seconds']:.1f}s")
                            st.rerun()
                with col2:
                    if st.button("➕ Index New", use_container_width=True, help="Index unindexed conversations only"):
                        with st.spinner("Indexing new conversations..."):
                            result = st.session_state.app_state.index_all_conversations(force=False)
                            if result['indexed'] > 0:
                                st.success(f"✅ Indexed {result['indexed']} new conversations")
                            else:
                                st.info("All conversations already indexed")
                            st.rerun()

            except Exception as e:
                st.error(f"Error loading index stats: {e}")

        # Search bar
        search_placeholder = {
            "keyword": "Search in titles and messages...",
            "semantic": "Search by meaning (e.g., 'discussions about AI')...",
            "hybrid": "Search by keywords and meaning..."
        }.get(search_mode, "Search conversations...")

        search_query = st.text_input(
            f"🔍 Search conversations ({search_mode})",
            value=st.session_state.search_query,
            placeholder=search_placeholder,
            key="search_input"
        )
        st.session_state.search_query = search_query

        # Filters expander
        with st.expander("🎯 Filters", expanded=False):
            # Get all available tags
            all_tags = st.session_state.app_state.get_all_tags()

            if all_tags:
                st.session_state.filter_tags = st.multiselect(
                    "Tags",
                    options=all_tags,
                    default=st.session_state.filter_tags,
                    help="Filter by tags"
                )

            # Favorite/Archived filters
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.filter_favorites = st.checkbox(
                    "⭐ Favorites only",
                    value=st.session_state.filter_favorites
                )
            with col2:
                st.session_state.filter_archived = st.checkbox(
                    "📦 Show archived",
                    value=st.session_state.filter_archived
                )

            # Message count filter
            st.session_state.filter_msg_count_min = st.slider(
                "Min messages",
                min_value=0,
                max_value=100,
                value=st.session_state.filter_msg_count_min,
                step=1
            )

            # Clear filters button
            if st.button("🔄 Clear Filters", use_container_width=True):
                st.session_state.search_query = ""
                st.session_state.filter_tags = []
                st.session_state.filter_favorites = False
                st.session_state.filter_archived = False
                st.session_state.filter_msg_count_min = 0
                st.rerun()

        # Batch operations toggle
        st.session_state.batch_mode = st.checkbox(
            "📋 Batch Mode",
            value=st.session_state.batch_mode,
            help="Select multiple conversations for batch operations"
        )

        # Apply search and filters
        filters = {
            "tags": st.session_state.filter_tags if st.session_state.filter_tags else None,
            "favorite": st.session_state.filter_favorites if st.session_state.filter_favorites else None,
            "archived": st.session_state.filter_archived,
            "msg_count_min": st.session_state.filter_msg_count_min,
        }

        # Phase 13.4: Get conversations based on search mode
        conversations = []
        similarity_scores = {}  # Store similarity scores for semantic search

        if search_query:
            if search_mode == "semantic":
                # Semantic search only
                try:
                    # Build metadata filter for vector search
                    vector_filter = {}
                    if st.session_state.filter_favorites:
                        vector_filter["favorite"] = True
                    if st.session_state.filter_archived:
                        vector_filter["archived"] = True

                    # Perform semantic search
                    semantic_results = st.session_state.app_state.search_conversations_semantic(
                        query=search_query,
                        top_k=st.session_state.semantic_top_k,
                        filter_metadata=vector_filter if vector_filter else None
                    )

                    # Get full conversation objects
                    all_convs = st.session_state.app_state.get_conversations()
                    conv_map = {c['id']: c for c in all_convs}

                    for result in semantic_results:
                        conv_id = result['conv_id']
                        if conv_id in conv_map:
                            conversations.append(conv_map[conv_id])
                            similarity_scores[conv_id] = result['similarity']

                except Exception as e:
                    st.error(f"Semantic search failed: {e}")
                    # Fallback to keyword search
                    conversations = st.session_state.app_state.search_conversations(
                        query=search_query,
                        filters=filters
                    )

            elif search_mode == "hybrid":
                # Hybrid: combine keyword and semantic
                try:
                    # Get keyword results
                    keyword_convs = st.session_state.app_state.search_conversations(
                        query=search_query,
                        filters=filters
                    )
                    keyword_ids = {c['id'] for c in keyword_convs}

                    # Get semantic results
                    vector_filter = {}
                    if st.session_state.filter_favorites:
                        vector_filter["favorite"] = True
                    if st.session_state.filter_archived:
                        vector_filter["archived"] = True

                    semantic_results = st.session_state.app_state.search_conversations_semantic(
                        query=search_query,
                        top_k=st.session_state.semantic_top_k,
                        filter_metadata=vector_filter if vector_filter else None
                    )

                    # Combine results (prioritize semantic)
                    all_convs = st.session_state.app_state.get_conversations()
                    conv_map = {c['id']: c for c in all_convs}
                    added_ids = set()

                    # Add semantic results first (with similarity scores)
                    for result in semantic_results:
                        conv_id = result['conv_id']
                        if conv_id in conv_map:
                            conversations.append(conv_map[conv_id])
                            similarity_scores[conv_id] = result['similarity']
                            added_ids.add(conv_id)

                    # Add keyword results that weren't in semantic results
                    for conv in keyword_convs:
                        if conv['id'] not in added_ids:
                            conversations.append(conv)
                            added_ids.add(conv['id'])

                except Exception as e:
                    st.warning(f"Hybrid search error: {e}. Using keyword search.")
                    conversations = st.session_state.app_state.search_conversations(
                        query=search_query,
                        filters=filters
                    )

            else:  # keyword mode
                conversations = st.session_state.app_state.search_conversations(
                    query=search_query,
                    filters=filters
                )

        elif any(filters.values()):
            # Filters only, no search query
            conversations = st.session_state.app_state.search_conversations(
                query="",
                filters=filters
            )
        else:
            # No search or filters
            conversations = st.session_state.app_state.get_conversations()

        # Browse conversations
        with st.expander("Browse Conversations", expanded=True):
            if conversations:
                # Sort by updated_at, newest first
                conversations.sort(key=lambda c: c.get("updated_at", ""), reverse=True)

                # Pagination: limit displayed conversations
                total_convs = len(conversations)
                display_count = min(st.session_state.conv_display_count, total_convs)
                conversations_to_show = conversations[:display_count]

                # Show result count with pagination info
                if total_convs > display_count:
                    st.caption(f"Showing {display_count} of {total_convs} conversation(s)")
                else:
                    st.caption(f"Found {total_convs} conversation(s)")

                # Batch operations UI
                if st.session_state.batch_mode:
                    st.markdown("**Batch Operations:**")

                    # Select all/none
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Select All", use_container_width=True):
                            st.session_state.selected_conversations = [c["id"] for c in conversations]
                            st.rerun()
                    with col2:
                        if st.button("❌ Clear Selection", use_container_width=True):
                            st.session_state.selected_conversations = []
                            st.rerun()

                    # Batch action buttons
                    if st.session_state.selected_conversations:
                        st.info(f"Selected: {len(st.session_state.selected_conversations)} conversations")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("🗑️ Delete", key="batch_delete", use_container_width=True):
                                st.session_state.app_state.batch_delete(st.session_state.selected_conversations)
                                st.session_state.selected_conversations = []
                                st.success("✅ Deleted selected conversations")
                                st.rerun()

                        with col2:
                            batch_tag = st.text_input("Add tag", key="batch_tag_input", placeholder="tag")

                        with col3:
                            if batch_tag and st.button("🏷️ Tag", key="batch_tag_btn", use_container_width=True):
                                st.session_state.app_state.batch_tag(st.session_state.selected_conversations, batch_tag)
                                st.success(f"✅ Tagged {len(st.session_state.selected_conversations)} conversations")
                                st.rerun()

                    st.divider()

                # Display conversations (paginated)
                for conv in conversations_to_show:
                    conv_id = conv.get("id", "")
                    created = conv.get("created_at", "")
                    msg_count = len(conv.get("messages", []))
                    metadata = conv.get("metadata", {})
                    is_favorite = metadata.get("favorite", False)
                    is_archived = metadata.get("archived", False)
                    tags = metadata.get("tags", [])

                    # Get first message preview
                    messages = conv.get("messages", [])
                    preview = "Empty conversation"
                    if messages:
                        first_msg = messages[0].get("content", "")
                        if isinstance(first_msg, list):
                            # Extract text from content blocks
                            text_parts = []
                            for item in first_msg:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                            first_msg = " ".join(text_parts)
                        preview = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg

                    # Format timestamp
                    try:
                        created_dt = datetime.fromisoformat(created)
                        created_str = created_dt.strftime("%b %d, %H:%M")
                    except:
                        created_str = "Unknown"

                    # Display conversation card
                    if st.session_state.batch_mode:
                        # Show checkbox in batch mode
                        is_selected = conv_id in st.session_state.selected_conversations

                        col_check, col_info = st.columns([1, 9])
                        with col_check:
                            if st.checkbox("", value=is_selected, key=f"check_{conv_id}", label_visibility="collapsed"):
                                if conv_id not in st.session_state.selected_conversations:
                                    st.session_state.selected_conversations.append(conv_id)
                                    st.rerun()
                            else:
                                if conv_id in st.session_state.selected_conversations:
                                    st.session_state.selected_conversations.remove(conv_id)
                                    st.rerun()

                        with col_info:
                            # Title with icons
                            title_icons = ""
                            if is_favorite:
                                title_icons += "⭐ "
                            if is_archived:
                                title_icons += "📦 "

                            # Phase 13.4: Add similarity score if available
                            similarity = similarity_scores.get(conv_id)
                            if similarity is not None:
                                # Convert similarity to percentage (0.0 = 0%, 1.0 = 100%)
                                sim_pct = max(0, similarity * 100)  # Clamp negative to 0
                                st.markdown(f"{title_icons}**{created_str}** ({msg_count} messages) | 🎯 {sim_pct:.0f}% match")
                            else:
                                st.markdown(f"{title_icons}**{created_str}** ({msg_count} messages)")

                            st.caption(preview)

                            # Show tags
                            if tags:
                                tag_str = " ".join([f"`{tag}`" for tag in tags])
                                st.caption(f"Tags: {tag_str}")
                    else:
                        # Normal display mode
                        # Title with icons
                        title_icons = ""
                        if is_favorite:
                            title_icons += "⭐ "
                        if is_archived:
                            title_icons += "📦 "

                        # Phase 13.4: Add similarity score if available
                        similarity = similarity_scores.get(conv_id)
                        if similarity is not None:
                            # Convert similarity to percentage (0.0 = 0%, 1.0 = 100%)
                            sim_pct = max(0, similarity * 100)  # Clamp negative to 0
                            st.markdown(f"{title_icons}**{created_str}** ({msg_count} messages) | 🎯 {sim_pct:.0f}% match")
                        else:
                            st.markdown(f"{title_icons}**{created_str}** ({msg_count} messages)")

                        st.caption(preview)

                        # Show tags
                        if tags:
                            tag_str = " ".join([f"`{tag}`" for tag in tags])
                            st.caption(f"Tags: {tag_str}")

                        # Action buttons
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if st.button("📂 Load", key=f"load_{conv_id}", use_container_width=True):
                                load_conversation(conv_id)

                        with col2:
                            fav_icon = "⭐" if not is_favorite else "☆"
                            if st.button(fav_icon, key=f"fav_{conv_id}", use_container_width=True, help="Toggle favorite"):
                                st.session_state.app_state.set_favorite(conv_id, not is_favorite)
                                st.rerun()

                        with col3:
                            arch_icon = "📦" if not is_archived else "📤"
                            if st.button(arch_icon, key=f"arch_{conv_id}", use_container_width=True, help="Toggle archive"):
                                st.session_state.app_state.set_archived(conv_id, not is_archived)
                                st.rerun()

                        with col4:
                            if st.button("🗑️", key=f"del_{conv_id}", use_container_width=True, help="Delete"):
                                st.session_state.app_state.delete_conversation(conv_id)
                                st.rerun()

                    st.divider()

                # Pagination: Load More button
                if display_count < total_convs:
                    remaining = total_convs - display_count
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button(f"📥 Load More ({remaining} remaining)", use_container_width=True, key="load_more_convs"):
                            st.session_state.conv_display_count += st.session_state.conv_page_size
                            st.rerun()
                    # Reset button to collapse back
                    if st.session_state.conv_display_count > st.session_state.conv_page_size:
                        with col3:
                            if st.button("↩️ Reset", key="reset_pagination", help="Show only first page"):
                                st.session_state.conv_display_count = st.session_state.conv_page_size
                                st.rerun()
            else:
                if search_query or any(filters.values()):
                    st.info("No conversations match your search/filters")
                else:
                    st.info("No saved conversations yet")

        # Export/Import/Config buttons (Phase 12)
        st.divider()
        st.subheader("💾 Data Management")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("📤 Export", use_container_width=True, help="Export conversations"):
                st.session_state.show_export_dialog = True
                st.rerun()
        with col2:
            if st.button("📥 Import", use_container_width=True, help="Import conversations"):
                st.session_state.show_import_dialog = True
                st.rerun()
        with col3:
            if st.button("⚙️ Config", use_container_width=True, help="Manage settings"):
                st.session_state.show_config_dialog = True
                st.rerun()
        with col4:
            if st.button("🧹 Cleanup", use_container_width=True, help="Remove orphan entries"):
                # Preview what would be deleted
                preview = st.session_state.app_state.cleanup_single_message_conversations(dry_run=True)
                st.session_state.cleanup_preview = preview
                st.session_state.show_cleanup_dialog = True
                st.rerun()

        # File browser
        st.subheader("📁 File Browser")
        with st.expander("Browse Sandbox Files", expanded=False):
            files = list_sandbox_files()

            protected_files = ["conversations.json", "memory.json", "agents.json"]

            if files:
                for file_info in files:
                    filename = file_info["name"]
                    size = format_file_size(file_info["size"])
                    modified = file_info["modified"].strftime("%b %d, %H:%M")
                    is_protected = filename in protected_files

                    st.markdown(f"**{filename}**")
                    st.caption(f"{size} • Modified: {modified}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("👁️ View", key=f"view_{filename}", use_container_width=True):
                            try:
                                with open(file_info["path"], 'r') as f:
                                    content = f.read()
                                st.code(content, language=None)
                            except Exception as e:
                                st.error(f"Error reading file: {e}")

                    with col2:
                        if is_protected:
                            st.button("🔒 Protected", key=f"protect_{filename}", disabled=True, use_container_width=True)
                        else:
                            if st.button("🗑️ Delete", key=f"delfile_{filename}", use_container_width=True):
                                try:
                                    os.remove(file_info["path"])
                                    st.success(f"✅ Deleted {filename}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                    st.divider()
            else:
                st.info("No files in sandbox yet")

        # Memory viewer
        st.subheader("🧠 Memory Viewer")
        with st.expander("Browse Memory Entries", expanded=False):
            memory_data = load_memory_data()

            if memory_data:
                st.info(f"📊 {len(memory_data)} entries stored")

                for key, entry in memory_data.items():
                    value = entry.get("value", "")
                    stored_at = entry.get("stored_at", "")

                    # Format timestamp
                    try:
                        stored_dt = datetime.fromisoformat(stored_at)
                        stored_str = stored_dt.strftime("%b %d, %H:%M")
                    except:
                        stored_str = "Unknown"

                    st.markdown(f"**{key}**")

                    # Truncate long values
                    if len(str(value)) > 100:
                        st.caption(f"{str(value)[:100]}...")
                        with st.expander("View Full Value"):
                            st.code(str(value), language=None)
                    else:
                        st.caption(f"Value: {value}")

                    st.caption(f"Stored: {stored_str}")

                    if st.button("🗑️ Delete", key=f"delmem_{key}", use_container_width=True):
                        delete_memory_entry(key)

                    st.divider()
            else:
                st.info("No memory entries yet")

        # Knowledge Base Manager (Phase 13.5)
        st.divider()
        st.subheader("📚 Knowledge Base")
        with st.expander("Manage Knowledge Facts", expanded=False):
            # Get stats
            stats = st.session_state.app_state.get_knowledge_stats()

            # Stats dashboard
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", stats["total"])
            with col2:
                st.metric("⭐ Prefs", stats["preferences"])
            with col3:
                st.metric("🔧 Tech", stats["technical"])
            with col4:
                st.metric("📁 Proj", stats["project"])

            st.markdown("---")

            # Quick view - 5 most recent facts
            if stats["total"] > 0:
                recent_facts = st.session_state.app_state.get_all_knowledge(sort_by="date", sort_order="desc")[:5]

                st.caption("Recent Facts:")

                for fact in recent_facts:
                    # Category emoji
                    category_emoji = {
                        "preferences": "⭐",
                        "technical": "🔧",
                        "project": "📁",
                        "general": "📝"
                    }.get(fact["category"], "📝")

                    # Truncate text
                    text = fact["text"]
                    if len(text) > 60:
                        text = text[:60] + "..."

                    # Display fact
                    st.markdown(f"{category_emoji} {text}")
                    st.caption(f"Confidence: {fact['confidence']:.0%} | {fact.get('source', 'N/A')}")
                    st.divider()

                # Action buttons
                col_add, col_manage = st.columns(2)
                with col_add:
                    if st.button("➕ Add Fact", key="kb_add_btn", use_container_width=True):
                        st.session_state.show_knowledge_manager = True
                        st.session_state.kb_edit_fact_id = None  # Clear edit mode
                        st.rerun()
                with col_manage:
                    if st.button("🔍 Manage", key="kb_manage_btn", use_container_width=True):
                        st.session_state.show_knowledge_manager = True
                        st.rerun()

            else:
                st.info("No knowledge stored yet. Add facts to help Claude remember important information across conversations!")

                if st.button("➕ Add Your First Fact", key="kb_add_first", use_container_width=True):
                    st.session_state.show_knowledge_manager = True
                    st.session_state.kb_edit_fact_id = None
                    st.rerun()

        # API Usage and Cost Tracking
        st.divider()
        st.subheader("📊 API Usage")
        with st.expander("Rate Limits & Costs", expanded=False):
            # Get usage stats from client
            if hasattr(st.session_state, 'client') and hasattr(st.session_state.client, 'rate_limiter'):
                usage = st.session_state.client.rate_limiter.get_usage_stats()
                status = st.session_state.client.rate_limiter.get_status_message()

                # Status message
                st.write(f"**Status:** {status}")
                st.caption("(Last 60 seconds)")

                # Requests
                st.metric(
                    "Requests",
                    f"{usage['requests']}/{usage['requests_limit']}",
                    delta=f"{usage['requests_percent']:.1f}%"
                )
                st.progress(min(usage['requests_percent'] / 100, 1.0))

                # Input tokens
                st.metric(
                    "Input Tokens",
                    f"{usage['input_tokens']:,}/{usage['input_tokens_limit']:,}",
                    delta=f"{usage['input_tokens_percent']:.1f}%"
                )
                st.progress(min(usage['input_tokens_percent'] / 100, 1.0))

                # Output tokens
                st.metric(
                    "Output Tokens",
                    f"{usage['output_tokens']:,}/{usage['output_tokens_limit']:,}",
                    delta=f"{usage['output_tokens_percent']:.1f}%"
                )
                st.progress(min(usage['output_tokens_percent'] / 100, 1.0))

                st.divider()

                # Cost tracking
                if hasattr(st.session_state.client, 'cost_tracker'):
                    session_stats = st.session_state.client.cost_tracker.get_session_stats()

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Session Cost",
                            f"${session_stats['cost']:.4f}",
                            help="Cost for this session"
                        )
                    with col2:
                        st.metric(
                            "Total Tokens",
                            f"{session_stats['total_tokens']:,}",
                            help="Input + output tokens"
                        )

                    st.caption(f"Requests this session: {session_stats['request_count']}")

            else:
                st.info("Usage tracking not available")

        # Cache Management (Phase 14)
        st.divider()
        st.subheader("💾 Cache Management")
        with st.expander("Prompt Caching", expanded=False):
            # Cache status indicator
            if st.session_state.cache_strategy == "disabled":
                st.info("🔴 Cache: Disabled")
            else:
                cache_stats = st.session_state.client.cache_tracker.get_session_stats()
                hit_rate = cache_stats.get("cache_hit_rate", 0) * 100

                if hit_rate >= 70:
                    status_icon = "🟢"
                elif hit_rate >= 40:
                    status_icon = "🟡"
                else:
                    status_icon = "🟠"

                st.info(f"{status_icon} Cache: Active ({st.session_state.cache_strategy.title()})")

            # Quick stats
            if st.session_state.cache_strategy != "disabled":
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Hit Rate",
                        f"{hit_rate:.1f}%",
                        help="Percentage of requests using cache"
                    )
                with col2:
                    savings = cache_stats.get("cost_savings", 0)
                    st.metric(
                        "Savings",
                        f"${savings:.4f}",
                        help="Cost saved this session"
                    )

            # Strategy selector
            st.caption("**Caching Strategy:**")
            strategy_options = {
                "Disabled": "disabled",
                "Conservative (System + Tools)": "conservative",
                "Balanced (+ History)": "balanced",
                "Aggressive (Max Savings)": "aggressive"
            }

            selected_strategy = st.selectbox(
                "Select strategy",
                options=list(strategy_options.keys()),
                index=list(strategy_options.values()).index(st.session_state.cache_strategy),
                key="cache_strategy_select",
                label_visibility="collapsed"
            )

            new_strategy = strategy_options[selected_strategy]
            if new_strategy != st.session_state.cache_strategy:
                st.session_state.cache_strategy = new_strategy

                # Update client cache strategy
                from core.cache_manager import CacheStrategy
                strategy_enum = CacheStrategy[new_strategy.upper()]
                st.session_state.client.set_cache_strategy(strategy_enum)

                st.success(f"✅ Strategy changed to: {new_strategy.title()}")
                st.rerun()

            # Manage button
            if st.button("📊 Manage Cache", use_container_width=True, key="open_cache_manager"):
                st.session_state.show_cache_manager = True
                st.rerun()

        # Context Management (Phase 9)
        st.divider()
        st.subheader("🧠 Context Management")
        with st.expander("Context Usage & Strategy", expanded=False):
            # Get context stats
            if hasattr(st.session_state, 'context_manager'):
                stats = st.session_state.context_manager.get_context_stats(
                    st.session_state.messages,
                    st.session_state.system_prompt,
                    ALL_TOOL_SCHEMAS if st.session_state.tools_enabled else None
                )

                # Context usage display
                st.write("**Current Context:**")
                usage_percent = stats['usage_percent']

                # Color-code based on usage
                if usage_percent < 50:
                    color_class = "🟢"
                elif usage_percent < 70:
                    color_class = "🟡"
                else:
                    color_class = "🔴"

                st.metric(
                    "Context",
                    f"{stats['total_tokens']:,}/{stats['max_tokens']:,} tokens",
                    delta=f"{usage_percent:.1f}% {color_class}"
                )
                st.progress(min(usage_percent / 100, 1.0))

                # Token breakdown
                st.caption("**Breakdown:**")
                st.caption(f"• Messages: {stats['messages_tokens']:,} tokens")
                st.caption(f"• System: {stats['system_tokens']:,} tokens")
                st.caption(f"• Tools: {stats['tools_tokens']:,} tokens")
                st.caption(f"• Remaining: {stats['remaining_tokens']:,} tokens")

                st.divider()

                # Context strategy settings
                st.write("**Management Strategy:**")

                strategy_options = {
                    "Aggressive - 50% threshold (keeps 5 recent)": "aggressive",
                    "Balanced - 70% threshold (keeps 10 recent)": "balanced",
                    "Conservative - 85% threshold (keeps 20 recent)": "conservative",
                    "Manual - No auto-summarization": "manual"
                }

                # Find current strategy display name
                current_display = next(
                    (k for k, v in strategy_options.items()
                     if v == st.session_state.context_strategy),
                    list(strategy_options.keys())[1]  # Default to balanced
                )

                selected_strategy_display = st.selectbox(
                    "Strategy",
                    options=list(strategy_options.keys()),
                    index=list(strategy_options.keys()).index(current_display),
                    help="When to summarize older messages"
                )

                new_strategy = strategy_options[selected_strategy_display]
                if new_strategy != st.session_state.context_strategy:
                    st.session_state.context_strategy = new_strategy
                    st.session_state.context_manager.set_strategy(new_strategy)

                # Preserve recent messages slider
                st.session_state.preserve_recent_count = st.slider(
                    "Preserve Recent Messages",
                    min_value=1,
                    max_value=50,
                    value=st.session_state.preserve_recent_count,
                    help="Number of recent messages to never summarize"
                )

                # Auto-summarize toggle
                st.session_state.auto_summarize = st.checkbox(
                    "Enable Auto-Summarization",
                    value=st.session_state.auto_summarize,
                    help="Automatically summarize when context threshold reached"
                )

                # Force summarize button
                if st.button("📝 Force Summarize Now", use_container_width=True):
                    if len(st.session_state.messages) > st.session_state.preserve_recent_count:
                        managed_messages, summary_info = st.session_state.context_manager.force_summarize(
                            st.session_state.messages,
                            preserve_recent=st.session_state.preserve_recent_count
                        )
                        st.session_state.messages = managed_messages
                        st.success(f"✅ {summary_info}")
                        st.rerun()
                    else:
                        st.warning("Not enough messages to summarize")

                # Statistics
                if stats.get('total_summarized', 0) > 0:
                    st.divider()
                    st.caption("**Statistics:**")
                    st.caption(f"• Messages summarized: {stats['total_summarized']}")
                    st.caption(f"• Tokens saved: {stats['total_saved']:,}")
                    st.caption(f"• Bookmarked: {stats['bookmarked_count']}")

            else:
                st.info("Context management not initialized")

        # Streaming Settings (Phase 11)
        st.divider()
        st.subheader("⚡ Streaming")
        with st.expander("Streaming Settings", expanded=False):
            # Enable/disable streaming
            st.session_state.streaming_enabled = st.toggle(
                "Enable Real-time Streaming",
                value=st.session_state.streaming_enabled,
                help="Stream responses in real-time (word-by-word, faster perceived response)"
            )

            if st.session_state.streaming_enabled:
                # Show tool execution
                st.session_state.show_tool_execution = st.toggle(
                    "Show Tool Execution",
                    value=st.session_state.show_tool_execution,
                    help="Display tools as they execute (with progress indicators)"
                )

                # Show partial results
                st.session_state.show_partial_results = st.toggle(
                    "Show Partial Tool Results",
                    value=st.session_state.show_partial_results,
                    help="Show tool results immediately when available"
                )

                st.caption("**Benefits:**")
                st.caption("• Faster perceived response")
                st.caption("• Real-time tool visibility")
                st.caption("• Better engagement")
            else:
                st.info("Streaming disabled. Using blocking mode with spinner.")

        # Agent Management (Phase 10)
        st.divider()
        st.subheader("📦 Agent Management")
        with st.expander("Multi-Agent System", expanded=False):
            # Import agent manager
            from tools.agents import _agent_manager

            # Refresh button
            if st.button("🔄 Refresh Status", key="refresh_agents", use_container_width=True):
                st.rerun()

            # Get all agents
            agents_data = _agent_manager.list_agents()

            if agents_data:
                # Count by status
                running = sum(1 for a in agents_data if a["status"] == "running")
                completed = sum(1 for a in agents_data if a["status"] == "completed")
                failed = sum(1 for a in agents_data if a["status"] == "failed")

                st.caption(f"**Active Agents** ({len(agents_data)} total)")

                # Display each agent
                for agent in agents_data:
                    # Status emoji
                    status_emoji = {
                        "pending": "⏳",
                        "running": "🔄",
                        "completed": "✅",
                        "failed": "❌"
                    }

                    with st.container():
                        st.markdown(f"{status_emoji.get(agent['status'], '❔')} **Agent #{agent['agent_id'][-6:]}**")

                        # Task preview
                        task = agent['task']
                        if len(task) > 60:
                            task = task[:60] + "..."
                        st.caption(f"Task: *{task}*")

                        # Info row
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"Type: {agent['agent_type']}")
                        with col2:
                            st.caption(f"Status: {agent['status']}")

                        # Action button
                        if agent['status'] == 'completed':
                            if st.button("📄 View Result", key=f"result_{agent['agent_id']}", use_container_width=True):
                                st.session_state.view_agent_result = agent['agent_id']
                                st.rerun()
                        elif agent['status'] == 'failed':
                            st.caption("❌ Failed")
                        elif agent['status'] == 'running':
                            st.caption("⏳ In progress...")

                        st.divider()

                # Statistics
                st.caption("**Statistics:**")
                st.caption(f"• Total: {len(agents_data)} | Running: {running} | Completed: {completed} | Failed: {failed}")

            else:
                st.info("No agents spawned yet")

            # Quick session access
            st.divider()
            st.markdown("### 💬 Quick Access")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("🆕 New Chat", use_container_width=True):
                    start_new_conversation()

            with col2:
                # Recent conversations dropdown
                conversations = st.session_state.app_state.get_conversations()
                if conversations:
                    recent_convs = sorted(
                        conversations,
                        key=lambda x: x.get("updated_at", ""),
                        reverse=True
                    )[:5]

                    conv_options = {}
                    for conv in recent_convs:
                        conv_id = conv.get("id")
                        updated = conv.get("updated_at", "")
                        try:
                            dt = datetime.fromisoformat(updated)
                            time_str = dt.strftime("%b %d %H:%M")
                        except:
                            time_str = "Unknown"
                        msg_count = len(conv.get("messages", []))
                        label = f"{time_str} ({msg_count} msgs)"
                        conv_options[label] = conv_id

                    selected = st.selectbox(
                        "Load Recent",
                        options=[""] + list(conv_options.keys()),
                        label_visibility="collapsed",
                        key="quick_load_conv"
                    )

                    if selected and selected != "":
                        load_conversation(conv_options[selected])

            with col3:
                pass  # Reserve for future use

            # Action buttons
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Spawn Agent", key="spawn_agent_btn", use_container_width=True):
                    st.session_state.show_spawn_agent = True
                    st.rerun()
            with col2:
                if st.button("🗳️ Council", key="council_btn", use_container_width=True):
                    st.session_state.show_council = True
                    st.rerun()

        # Clear chat
        st.divider()
        if st.button("🗑️ Clear Chat", use_container_width=True):
            # Auto-save before clearing if enabled
            if st.session_state.auto_save_enabled and len(st.session_state.messages) > 0:
                auto_save_current_conversation()
                st.success("💾 Conversation saved before clearing")

            # Start new conversation
            start_new_conversation()

        # Stats
        st.divider()
        st.caption(f"Messages: {len(st.session_state.messages)}")
        st.caption(f"Model: {st.session_state.model.split('-')[-1]}")


def render_message(message: Dict[str, Any]):
    """Render a chat message (supports text and images)"""
    role = message["role"]
    content = message["content"]

    if role == "user":
        with st.chat_message("user", avatar="👤"):
            # Handle array content (with images)
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            st.markdown(item["text"])
                        elif item.get("type") == "image":
                            # Display image from base64
                            source = item.get("source", {})
                            if source.get("type") == "base64":
                                media_type = source.get("media_type", "image/jpeg")
                                data = source.get("data", "")
                                try:
                                    st.image(f"data:{media_type};base64,{data}", width=300)
                                except Exception as e:
                                    st.error(f"Error displaying image: {e}")
            # Handle string content (backward compatibility)
            elif isinstance(content, str):
                st.markdown(content)

    elif role == "assistant":
        with st.chat_message("assistant", avatar="🤖"):
            # Assistant responses are typically strings
            if isinstance(content, str):
                st.markdown(content)
            elif isinstance(content, list):
                # Handle multi-content responses
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        st.markdown(item.get("text", ""))

    elif role == "system":
        with st.chat_message("system", avatar="ℹ️"):
            st.info(content)


def extract_text_from_response(response) -> str:
    """Extract text content from Claude response"""
    if response is None:
        return ""

    text_parts = []

    for block in response.content:
        if hasattr(block, 'type'):
            if block.type == 'text':
                text_parts.append(block.text)
        elif isinstance(block, dict) and block.get('type') == 'text':
            text_parts.append(block.get('text', ''))

    return '\n'.join(text_parts) if text_parts else ""


def process_message(user_message: str, uploaded_images: Optional[List] = None):
    """
    Process user message with Claude (supports text and images).

    Args:
        user_message: User's input message
        uploaded_images: List of uploaded image files (optional)
    """
    # Build content array
    content = []

    # Add text content if present
    if user_message and user_message.strip():
        content.append({
            "type": "text",
            "text": user_message
        })

    # Add images if present
    if uploaded_images:
        for img_file in uploaded_images:
            try:
                # Read image bytes
                img_bytes = img_file.read()

                # Validate size
                is_valid, error_msg = validate_image_size(img_bytes)
                if not is_valid:
                    st.error(error_msg)
                    continue

                # Get media type
                media_type = get_media_type(img_file.name)

                # Create image content block
                image_content = create_image_content(img_bytes, media_type)
                content.append(image_content)

            except Exception as e:
                st.error(f"Error processing image {img_file.name}: {e}")
                logger.error(f"Image processing error: {e}", exc_info=True)

    # If no content, return early
    if not content:
        st.warning("Please enter a message or upload an image.")
        return

    # Add to session state (use array format for consistency)
    st.session_state.messages.append({
        "role": "user",
        "content": content
    })
    st.session_state.unsaved_changes = True

    # Show user message with images
    with st.chat_message("user", avatar="👤"):
        for item in content:
            if item.get("type") == "text":
                st.markdown(item["text"])
            elif item.get("type") == "image":
                source = item.get("source", {})
                if source.get("type") == "base64":
                    media_type = source.get("media_type", "image/jpeg")
                    data = source.get("data", "")
                    st.image(f"data:{media_type};base64,{data}", width=300)

    # Prepare messages for Claude
    conversation_messages = []
    for msg in st.session_state.messages:
        if msg["role"] in ["user", "assistant"]:
            conversation_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    # Get tools if enabled
    tools = None
    if st.session_state.tools_enabled:
        tools = list(ALL_TOOL_SCHEMAS.values())

    # Apply context management (Phase 9)
    messages_for_api = conversation_messages
    if st.session_state.auto_summarize and hasattr(st.session_state, 'context_manager'):
        managed_messages, summary_info = st.session_state.context_manager.manage_context(
            messages=conversation_messages,
            system=st.session_state.system_prompt,
            tools=tools,
            preserve_recent=st.session_state.preserve_recent_count
        )

        # If messages were summarized, update and show notification
        if summary_info:
            st.info(f"ℹ️ {summary_info}")
            # Update session state with managed messages
            st.session_state.messages = managed_messages
            messages_for_api = managed_messages

    # Show assistant response
    with st.chat_message("assistant", avatar="🤖"):
        try:
            # Choose streaming or non-streaming based on settings (Phase 11)
            if st.session_state.streaming_enabled:
                # Import streaming UI components
                from ui.streaming_display import StreamingTextDisplay, ToolExecutionDisplay

                # Create display containers
                tool_container = st.empty() if st.session_state.show_tool_execution else None
                text_container = st.empty()

                # Initialize displays
                text_display = StreamingTextDisplay(text_container)
                tool_display = ToolExecutionDisplay(tool_container) if tool_container else None

                response_text = ""

                # Run streaming loop
                stream_gen = st.session_state.loop.run_streaming(
                    messages=messages_for_api,
                    system=st.session_state.system_prompt,
                    model=st.session_state.model,
                    max_tokens=st.session_state.max_tokens,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    tools=tools
                )

                # Process stream events
                for event in stream_gen:
                    event_type = event.get("type")

                    if event_type == "text_delta":
                        # Append text chunk
                        text_display.append(event["data"])
                        response_text += event["data"]

                    elif event_type == "thinking":
                        # Show thinking status
                        if not response_text:  # Only show if no text yet
                            text_display.show_status(event["data"])

                    elif event_type == "tool_start" and tool_display:
                        # Tool execution starting
                        tool_display.start_tool(
                            event["data"]["id"],
                            event["data"]["name"]
                        )

                    elif event_type == "tool_executing" and tool_display:
                        # Tool executing with input details
                        tool_display.start_tool(
                            event["data"]["id"],
                            event["data"]["name"],
                            event["data"]["input"]
                        )

                    elif event_type == "tool_complete" and tool_display:
                        # Tool completed
                        if st.session_state.show_partial_results:
                            tool_display.complete_tool(
                                event["data"]["id"],
                                event["data"]["result"],
                                event["data"].get("is_error", False),
                                event["data"].get("duration")
                            )

                    elif event_type == "error":
                        # Error occurred
                        error_data = event["data"]
                        st.error(f"**Error:** {error_data.get('error', 'Unknown error')}")

                    elif event_type == "done":
                        # Stream complete
                        text_display.finalize()
                        break

                # Get final response from generator return value
                try:
                    response, updated_messages = stream_gen.send(None)
                except StopIteration as e:
                    # Generator exhausted, get return value
                    if e.value is not None:
                        response, updated_messages = e.value
                    else:
                        # Error occurred, no valid response
                        response = None
                        updated_messages = messages_for_api

            else:
                # Non-streaming mode (original behavior)
                with st.spinner("Thinking..."):
                    # Run tool calling loop
                    response, updated_messages = st.session_state.loop.run(
                        messages=messages_for_api,
                        system=st.session_state.system_prompt,
                        model=st.session_state.model,
                        max_tokens=st.session_state.max_tokens,
                        temperature=st.session_state.temperature,
                        top_p=st.session_state.top_p,
                        tools=tools
                    )

                    # Extract final text response
                    response_text = extract_text_from_response(response)

                    if response_text:
                        st.markdown(response_text)

            # Common post-processing for both streaming and non-streaming
            if response_text:
                # Add to messages
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text
                })
                st.session_state.unsaved_changes = True
                # Note: Auto-save handles persistence via auto_save_current_conversation()
                # Removed per-message saves that were creating duplicate conversation entries

            else:
                error_msg = "I apologize, but I couldn't generate a response."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
                st.session_state.unsaved_changes = True

        except (RetryableError, UserFixableError, FatalError) as e:
            # Use user-friendly error messages
            error_info = get_user_friendly_message(e)

            # Display formatted error
            st.error(f"**{error_info['title']}**")
            st.write(error_info['message'])
            st.info(f"**What to do:** {error_info['action']}")

            logger.error(f"Error processing message: {e}", exc_info=True)

            # Add to messages for history
            error_text = f"{error_info['title']}: {error_info['message']}"
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_text
            })
            st.session_state.unsaved_changes = True

        except Exception as e:
            # Fallback for unexpected errors
            error_info = get_user_friendly_message(e)

            st.error(f"**{error_info['title']}**")
            st.write(error_info['message'])
            st.info(f"**What to do:** {error_info['action']}")

            logger.error(f"Unexpected error: {e}", exc_info=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Error: {str(e)}"
            })
            st.session_state.unsaved_changes = True


# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main application entry point"""

    # Page config
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for wider sidebar (allows drag to expand)
    st.markdown("""
    <style>
    /* Allow sidebar to be dragged wider */
    [data-testid="stSidebar"] {
        min-width: 300px;
        max-width: 800px;
    }
    [data-testid="stSidebar"] > div:first-child {
        width: auto;
    }
    /* Mermaid diagram container - fill available space */
    .stMermaid {
        overflow-x: auto;
        width: 100% !important;
        min-height: 600px;
    }
    .stMermaid svg {
        width: 100% !important;
        height: auto !important;
        min-height: 600px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize
    init_session_state()

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("⚠️ ANTHROPIC_API_KEY not found in environment!")
        st.info("Please set your API key in the .env file")
        st.stop()

    # Render UI
    render_sidebar()

    # Main chat interface
    st.title("💬 Apex Aurum - Claude Edition")
    st.caption("Powered by Claude API with 39 tools + Vision support 👁️")

    # ========== ANALYTICS DASHBOARD MODAL ==========
    if st.session_state.get("show_analytics", False):
        from core.analytics_store import get_analytics_store
        import pandas as pd

        st.markdown("### 📊 Analytics Dashboard")

        analytics = get_analytics_store()

        # Time period selector
        col1, col2 = st.columns([3, 1])
        with col1:
            period = st.selectbox(
                "Time Period",
                ["Today", "7 Days", "30 Days", "All Time"],
                key="analytics_period"
            )
        with col2:
            if st.button("Close", key="close_analytics"):
                st.session_state.show_analytics = False
                st.rerun()

        # Map period to days
        period_days = {"Today": 1, "7 Days": 7, "30 Days": 30, "All Time": 365}
        days = period_days.get(period, 7)

        # Tabs for different metrics
        tab1, tab2, tab3 = st.tabs(["🛠️ Tool Usage", "💰 Costs", "⚡ Cache"])

        # ===== TOOL USAGE TAB =====
        with tab1:
            tool_stats = analytics.get_tool_stats(days)

            if tool_stats["total_calls"] > 0:
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Calls", f"{tool_stats['total_calls']:,}")
                with col2:
                    st.metric("Unique Tools", tool_stats["unique_tools"])
                with col3:
                    # Average success rate
                    rates = list(tool_stats["success_rates"].values())
                    avg_rate = sum(rates) / len(rates) if rates else 0
                    st.metric("Avg Success", f"{avg_rate*100:.1f}%")

                st.markdown("---")

                # Top tools bar chart
                st.markdown("#### Top Tools by Usage")
                if tool_stats["top_10"]:
                    chart_data = pd.DataFrame(
                        tool_stats["top_10"],
                        columns=["Tool", "Calls"]
                    )
                    st.bar_chart(chart_data.set_index("Tool"))

                # Success rates table
                st.markdown("#### Tool Success Rates")
                if tool_stats["by_tool"]:
                    rows = []
                    for tool, calls in tool_stats["by_tool"].items():
                        rate = tool_stats["success_rates"].get(tool, 0)
                        errors = tool_stats["errors"].get(tool, 0)
                        rows.append({
                            "Tool": tool,
                            "Calls": calls,
                            "Success Rate": f"{rate*100:.1f}%",
                            "Errors": errors
                        })
                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                # Recent tool calls
                st.markdown("#### Recent Tool Calls")
                recent = analytics.get_recent_tool_calls(15)
                if recent:
                    for call in recent:
                        status = "✅" if call["success"] else "❌"
                        duration = call.get("duration_ms", 0)
                        time_str = call["timestamp"].split("T")[1].split(".")[0] if "T" in call["timestamp"] else ""
                        st.text(f"{status} {call['tool']} ({duration:.0f}ms) @ {time_str}")
            else:
                st.info("No tool usage data yet. Use tools in conversations to see analytics.")

        # ===== COST TAB =====
        with tab2:
            cost_stats = analytics.get_cost_stats(days)

            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Spend", f"${cost_stats['total']:.4f}")
            with col2:
                st.metric("Daily Average", f"${cost_stats['average_daily']:.4f}")
            with col3:
                st.metric("Monthly Projection", f"${cost_stats['projected_monthly']:.2f}")

            st.markdown("---")

            # Daily cost trend
            if cost_stats["daily"] and any(d["cost"] > 0 for d in cost_stats["daily"]):
                st.markdown("#### Daily Cost Trend")
                chart_data = pd.DataFrame(cost_stats["daily"])
                chart_data["date"] = pd.to_datetime(chart_data["date"])
                st.line_chart(chart_data.set_index("date")["cost"])

                # Cost by model
                if cost_stats["by_model"]:
                    st.markdown("#### Cost by Model")
                    model_data = pd.DataFrame([
                        {"Model": k.split("-")[-1] if "-" in k else k, "Cost": v}
                        for k, v in cost_stats["by_model"].items()
                    ])
                    if not model_data.empty:
                        st.bar_chart(model_data.set_index("Model"))
            else:
                st.info("No cost data yet. Make API calls to see cost analytics.")

        # ===== CACHE TAB =====
        with tab3:
            cache_stats = analytics.get_cache_stats(days)

            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Hit Rate", f"{cache_stats['overall_hit_rate']*100:.1f}%")
            with col2:
                st.metric("Total Hits", cache_stats["total_hits"])
            with col3:
                st.metric("Total Savings", f"${cache_stats['total_savings']:.4f}")

            st.markdown("---")

            # Hit rate trend
            if cache_stats["daily"] and any(d["hit_rate"] > 0 for d in cache_stats["daily"]):
                st.markdown("#### Cache Hit Rate Trend")
                chart_data = pd.DataFrame(cache_stats["daily"])
                chart_data["date"] = pd.to_datetime(chart_data["date"])
                chart_data["hit_rate_pct"] = chart_data["hit_rate"] * 100
                st.line_chart(chart_data.set_index("date")["hit_rate_pct"])
            else:
                st.info("No cache data yet. Enable caching to see performance analytics.")

        st.markdown("---")

        # Overall summary
        summary = analytics.get_summary()
        if summary["first_record"]:
            st.caption(f"📅 Tracking since {summary['first_record']} | {summary['days_tracked']} days with activity | {summary['total_api_calls']} API calls")

    # ========== PHASE 2A: Preset Manager Dialog ==========
    if st.session_state.get("show_preset_manager", False):
        st.markdown("### 🎨 Preset Manager")

        preset_mgr = st.session_state.preset_manager

        tab1, tab2, tab3 = st.tabs(["📋 Browse", "➕ Create", "📦 Export/Import"])

        # TAB 1: Browse & Manage
        with tab1:
            st.markdown("#### All Presets")

            all_presets = preset_mgr.get_all_presets()
            active_preset_id = preset_mgr.get_active_preset_id()

            if not all_presets:
                st.info("No presets available")
            else:
                for preset_id, preset in all_presets.items():
                    is_active = (preset_id == active_preset_id)
                    is_built_in = preset["is_built_in"]

                    # Card for each preset
                    with st.container():
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            # Name with active indicator
                            name_display = preset["name"]
                            if is_active:
                                name_display = f"✅ {name_display}"
                            st.markdown(f"**{name_display}**")
                            st.caption(preset["description"])

                            # Show settings summary
                            settings = preset["settings"]
                            model_short = settings["model"].split("-")[-1] if "-" in settings["model"] else settings["model"]
                            st.caption(
                                f"Model: {model_short} | "
                                f"Cache: {settings['cache_strategy']} | "
                                f"Context: {settings['context_strategy']}"
                            )

                        with col2:
                            # Action buttons
                            if not is_active:
                                if st.button("▶️ Apply", key=f"apply_{preset_id}", use_container_width=True):
                                    success, message = preset_mgr.apply_preset(preset_id, st.session_state)
                                    if success:
                                        # Apply special handling
                                        from core.cache_manager import CacheStrategy
                                        try:
                                            strategy_enum = CacheStrategy[st.session_state.cache_strategy.upper()]
                                            st.session_state.client.set_cache_strategy(strategy_enum)
                                        except Exception as e:
                                            logger.error(f"Error setting cache strategy: {e}")

                                        try:
                                            st.session_state.context_manager.set_strategy(st.session_state.context_strategy)
                                        except Exception as e:
                                            logger.error(f"Error setting context strategy: {e}")

                                        st.success(f"✅ {message}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {message}")
                            else:
                                st.button("✅ Active", key=f"active_{preset_id}", disabled=True, use_container_width=True)

                            if not is_built_in:
                                # Edit button (custom only)
                                if st.button("✏️ Edit", key=f"edit_{preset_id}", use_container_width=True):
                                    st.session_state.preset_edit_id = preset_id
                                    st.rerun()

                                # Delete button (custom only)
                                if st.button("🗑️ Delete", key=f"del_{preset_id}", use_container_width=True):
                                    success, message = preset_mgr.delete_custom_preset(preset_id)
                                    if success:
                                        st.success(f"✅ {message}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {message}")
                            else:
                                st.caption("🔒 Built-in")

                        st.divider()

            # Edit mode (shown when preset_edit_id is set)
            if st.session_state.get("preset_edit_id"):
                edit_id = st.session_state.preset_edit_id
                preset = preset_mgr.get_preset(edit_id)

                if preset and not preset["is_built_in"]:
                    st.markdown("#### ✏️ Edit Preset")

                    with st.form("edit_preset_form"):
                        new_name = st.text_input("Preset Name", value=preset["name"].replace("⭐ ", ""))
                        new_desc = st.text_area("Description", value=preset["description"])

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                st.session_state.preset_edit_id = None
                                st.rerun()
                        with col2:
                            if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
                                success, message = preset_mgr.update_custom_preset(
                                    edit_id,
                                    name=new_name,
                                    description=new_desc
                                )
                                if success:
                                    st.success(f"✅ {message}")
                                    st.session_state.preset_edit_id = None
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")

        # TAB 2: Create New Preset
        with tab2:
            st.markdown("#### Create New Preset")
            st.info("This will save your current settings as a new preset")

            # Show current settings
            current_settings = preset_mgr.extract_current_settings(st.session_state)

            with st.expander("Current Settings Preview", expanded=True):
                st.json(current_settings)

            with st.form("create_preset_form"):
                preset_name = st.text_input("Preset Name", placeholder="My Custom Preset")
                preset_desc = st.text_area("Description", placeholder="Describe this preset...")

                col1, col2 = st.columns(2)
                with col1:
                    cancel = st.form_submit_button("Cancel", use_container_width=True)
                with col2:
                    create = st.form_submit_button("Create Preset", type="primary", use_container_width=True)

                if cancel:
                    st.session_state.show_preset_manager = False
                    st.rerun()

                if create:
                    if not preset_name:
                        st.error("❌ Preset name is required")
                    else:
                        success, message, new_id = preset_mgr.save_custom_preset(
                            preset_name,
                            preset_desc or "Custom preset",
                            st.session_state
                        )
                        if success:
                            st.success(f"✅ {message}")
                            # Switch to browse tab to show new preset
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")

        # TAB 3: Export/Import
        with tab3:
            st.markdown("#### Export/Import Presets")

            col_exp, col_imp = st.columns(2)

            with col_exp:
                st.write("**Export Presets**")

                if st.button("📤 Export All Custom Presets", use_container_width=True):
                    custom_presets = preset_mgr.get_custom_presets()

                    if custom_presets:
                        export_data = {
                            "version": preset_mgr.VERSION,
                            "exported_at": datetime.now().isoformat(),
                            "presets": custom_presets
                        }

                        export_json = json.dumps(export_data, indent=2)

                        st.download_button(
                            label="⬇️ Download presets.json",
                            data=export_json,
                            file_name="custom_presets.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    else:
                        st.info("No custom presets to export")

            with col_imp:
                st.write("**Import Presets**")

                uploaded_file = st.file_uploader(
                    "Upload presets JSON",
                    type=["json"],
                    key="preset_import_uploader"
                )

                if uploaded_file:
                    if st.button("📥 Import Presets", use_container_width=True):
                        try:
                            import_data = json.loads(uploaded_file.read().decode("utf-8"))

                            # Validate structure
                            if "presets" in import_data:
                                imported_count = 0
                                for preset_id, preset in import_data["presets"].items():
                                    # Add each preset as custom
                                    preset_mgr.presets_data["custom"][preset_id] = preset
                                    imported_count += 1

                                preset_mgr._save_presets()
                                st.success(f"✅ Imported {imported_count} preset(s)")
                                st.rerun()
                            else:
                                st.error("❌ Invalid preset file format")

                        except Exception as e:
                            st.error(f"❌ Import failed: {e}")
                            logger.error(f"Preset import error: {e}", exc_info=True)

        # Close button
        if st.button("Close", use_container_width=True, key="close_preset_manager"):
            st.session_state.show_preset_manager = False
            st.session_state.preset_edit_id = None  # Clear edit mode
            st.rerun()

        st.markdown("---")

    # ========== END PHASE 2A ==========

    # Agent UI Dialogs (Phase 10)
    # Spawn Agent Dialog
    if st.session_state.get("show_spawn_agent", False):
        st.markdown("### ➕ Spawn New Agent")

        with st.form("spawn_agent_form"):
            task = st.text_area(
                "Task Description",
                placeholder="Describe the task for the agent in detail...",
                height=100,
                help="Be specific about what you want the agent to do"
            )

            agent_type = st.radio(
                "Agent Type",
                options=[
                    "general - Any task",
                    "researcher - Research and gather information",
                    "coder - Write and explain code",
                    "analyst - Analyze data and provide insights",
                    "writer - Create written content"
                ],
                help="Choose the type of agent based on the task"
            )

            model_options = [
                "Haiku (fast & cheap)",
                "Sonnet (balanced)",
                "Opus (best quality)"
            ]
            default_index = model_options.index(
                st.session_state.get("default_subagent_model", "Haiku (fast & cheap)")
            )

            model = st.selectbox(
                "Model",
                options=model_options,
                index=default_index,
                help="Can change default in sidebar Advanced Settings"
            )

            run_async = st.checkbox(
                "Run in background",
                value=True,
                help="Run asynchronously (recommended)"
            )

            col1, col2 = st.columns(2)
            with col1:
                cancel = st.form_submit_button("Cancel", use_container_width=True)
            with col2:
                spawn = st.form_submit_button("Spawn Agent", type="primary", use_container_width=True)

            if cancel:
                st.session_state.show_spawn_agent = False
                st.rerun()

            if spawn and task:
                # Parse agent type
                agent_type_key = agent_type.split(" -")[0].strip()

                # Parse model
                model_map = {
                    "Haiku (fast & cheap)": "claude-haiku-4-5-20251001",
                    "Sonnet (balanced)": "claude-sonnet-4-5-20250929",
                    "Opus (best quality)": "claude-opus-4-5-20251101"
                }
                model_id = model_map[model]

                # Spawn agent
                from tools.agents import agent_spawn

                with st.spinner("Spawning agent..."):
                    result = agent_spawn(
                        task=task,
                        agent_type=agent_type_key,
                        model=model_id,
                        run_async=run_async
                    )

                if result.get("success"):
                    st.success(f"✅ Agent spawned: {result.get('agent_id')}")
                    st.caption(result.get("message", ""))
                    st.session_state.show_spawn_agent = False
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result.get('error')}")

        st.markdown("---")

    # Agent Result Viewer
    if st.session_state.get("view_agent_result"):
        agent_id = st.session_state.view_agent_result

        from tools.agents import agent_result, _agent_manager

        st.markdown("### 📄 Agent Result")

        result_data = agent_result(agent_id)

        if result_data.get("found"):
            agent = _agent_manager.get_agent(agent_id)

            if agent:
                # Agent info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Agent ID", f"#{agent_id[-6:]}")
                with col2:
                    st.metric("Type", agent.agent_type)
                with col3:
                    st.metric("Status", result_data.get("status"))

                # Task
                st.markdown("**Task:**")
                st.info(result_data.get("task"))

                # Result
                if result_data.get("status") == "completed":
                    st.markdown("**Result:**")
                    st.markdown(result_data.get("result"))

                    # Runtime
                    if agent.started_at and agent.completed_at:
                        runtime = (agent.completed_at - agent.started_at).total_seconds()
                        st.caption(f"Runtime: {runtime:.1f} seconds")
                        st.caption(f"Completed: {agent.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")

                elif result_data.get("status") == "failed":
                    st.error(f"**Error:** {result_data.get('error')}")

                # Actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📋 Copy Result", key="copy_result", use_container_width=True):
                        st.toast("Result copied to clipboard!", icon="✅")
                with col2:
                    if st.button("❌ Close", key="close_result", use_container_width=True):
                        st.session_state.view_agent_result = None
                        st.rerun()
            else:
                st.error("Agent details not available")
                if st.button("Close"):
                    st.session_state.view_agent_result = None
                    st.rerun()
        else:
            st.error("Agent not found")
            if st.button("Close"):
                st.session_state.view_agent_result = None
                st.rerun()

        st.markdown("---")

    # Socratic Council UI
    if st.session_state.get("show_council", False):
        st.markdown("### 🗳️ Socratic Council - Multi-Agent Voting")

        # Initialize council results in session state
        if "council_results" not in st.session_state:
            st.session_state.council_results = None

        with st.form("socratic_council_form"):
            question = st.text_input(
                "Question",
                placeholder="What question should the agents vote on?",
                help="Be clear and specific"
            )

            st.write("**Options** (2-5 options):")
            st.caption("💡 Tip: Fill out options then click 'Run Council' at bottom")

            # Dynamic options
            options = []
            for i in range(len(st.session_state.council_options)):
                opt_col, del_col = st.columns([4, 1])
                with opt_col:
                    opt = st.text_input(
                        f"Option {i+1}",
                        value=st.session_state.council_options[i],
                        key=f"opt_{i}"
                    )
                    if opt:
                        options.append(opt)
                with del_col:
                    # Remove button (only show if more than 2 options)
                    if len(st.session_state.council_options) > 2:
                        if st.form_submit_button("🗑️", key=f"del_opt_{i}"):
                            st.session_state.council_options.pop(i)
                            st.rerun()

            # Add option button (move to bottom, outside main submit area)
            if len(st.session_state.council_options) < 5:
                if st.form_submit_button("➕ Add Another Option"):
                    st.session_state.council_options.append("")
                    st.rerun()

            st.divider()

            num_agents = st.slider(
                "Number of Agents",
                min_value=3,
                max_value=9,
                value=3,
                step=2,
                help="Use odd numbers to avoid ties"
            )

            model = st.selectbox(
                "Model",
                options=["Sonnet (recommended)", "Opus (best reasoning)"],
                help="Sonnet provides good balance of quality and cost"
            )

            col1, col2 = st.columns(2)
            with col1:
                cancel = st.form_submit_button("Cancel", use_container_width=True)
            with col2:
                run = st.form_submit_button("Run Council", type="primary", use_container_width=True)

            if cancel:
                st.session_state.show_council = False
                st.session_state.council_options = ["", ""]
                st.rerun()

            if run and question and len(options) >= 2:
                # Run council
                from tools.agents import socratic_council

                model_id = "claude-sonnet-4-5-20250929" if "Sonnet" in model else "claude-opus-4-5-20251101"

                with st.spinner(f"Running council with {num_agents} agents..."):
                    result = socratic_council(
                        question=question,
                        options=options,
                        num_agents=num_agents,
                        model=model_id
                    )

                # Store results in session state
                st.session_state.council_results = {
                    "result": result,
                    "num_agents": num_agents,
                    "question": question
                }
                st.rerun()

        # Display results OUTSIDE the form
        if st.session_state.council_results:
            result_data = st.session_state.council_results
            result = result_data["result"]
            num_agents = result_data["num_agents"]
            question = result_data["question"]

            if result.get("success"):
                st.success("✅ Council completed!")

                # Display results
                st.markdown("### Results")
                st.caption(f"**Question:** {question}")

                winner = result.get("winner")
                votes = result.get("votes")
                winner_votes = result.get("winner_votes")

                st.metric("Winner", f"{winner} ({winner_votes}/{num_agents} votes)")

                # Vote chart
                st.write("**Votes:**")
                for opt, count in votes.items():
                    bar = "█" * count
                    st.write(f"• {opt}: {bar} {count}")

                # Consensus indicator
                if result.get("consensus"):
                    st.info("✅ Strong consensus reached (> 50% agreement)")
                else:
                    st.warning("⚠️ No strong consensus (split decision)")

                # Reasoning
                st.write("**Agent Reasoning:**")
                for item in result.get("reasoning", []):
                    with st.expander(f"Agent {item['agent']} → {item['vote']}"):
                        st.write(item['reasoning'])

                # Export/Save options
                st.divider()
                st.write("**💾 Save Results:**")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    # Copy to clipboard
                    export_text = f"""Council Results
Question: {question}
Winner: {winner} ({winner_votes}/{num_agents} votes)

Votes:
"""
                    for opt, count in votes.items():
                        export_text += f"• {opt}: {count}\n"

                    export_text += "\nReasoning:\n"
                    for item in result.get("reasoning", []):
                        export_text += f"\nAgent {item['agent']} → {item['vote']}\n{item['reasoning']}\n"

                    if st.button("📋 Copy", use_container_width=True, help="Copy results to clipboard"):
                        st.toast("✅ Results copied!", icon="✅")

                with col2:
                    # Save to knowledge base
                    if st.button("🧠 Knowledge", use_container_width=True, help="Save to knowledge base"):
                        from tools.vector_search import vector_add_knowledge
                        knowledge_text = f"Council vote on: {question}\nWinner: {winner} ({winner_votes}/{num_agents} votes)"
                        try:
                            vector_add_knowledge(
                                fact=knowledge_text,
                                category="general",
                                source="council_vote"
                            )
                            st.toast("✅ Saved to knowledge base!", icon="🧠")
                        except Exception as e:
                            st.toast(f"❌ Error: {str(e)}", icon="❌")

                with col3:
                    # Save to memory
                    if st.button("💾 Memory", use_container_width=True, help="Save to memory"):
                        from tools.memory import memory_store
                        memory_key = f"council_{question[:30].replace(' ', '_')}"
                        memory_value = {"question": question, "winner": winner, "votes": votes}
                        try:
                            memory_store(memory_key, memory_value)
                            st.toast(f"✅ Saved as: {memory_key}", icon="💾")
                        except Exception as e:
                            st.toast(f"❌ Error: {str(e)}", icon="❌")

                with col4:
                    # Download as JSON
                    import json
                    download_data = {
                        "question": question,
                        "winner": winner,
                        "votes": votes,
                        "total_agents": num_agents,
                        "consensus": result.get("consensus"),
                        "reasoning": result.get("reasoning", [])
                    }
                    json_str = json.dumps(download_data, indent=2)

                    st.download_button(
                        label="📥 JSON",
                        data=json_str,
                        file_name=f"council_{question[:20].replace(' ', '_')}.json",
                        mime="application/json",
                        use_container_width=True,
                        help="Download as JSON file"
                    )

                st.divider()

                # Close button (now OUTSIDE form, so it works!)
                if st.button("Close Results", use_container_width=True):
                    st.session_state.show_council = False
                    st.session_state.council_options = ["", ""]
                    st.session_state.council_results = None
                    st.rerun()

            else:
                st.error(f"❌ Error: {result.get('error')}")
                if st.button("Close", use_container_width=True):
                    st.session_state.show_council = False
                    st.session_state.council_results = None
                    st.rerun()

        st.markdown("---")

    # Export/Import/Config Dialogs (Phase 12)
    # Export Dialog
    if st.session_state.get("show_export_dialog", False):
        st.markdown("### 📤 Export Conversations")

        # Select conversations to export
        conversations = st.session_state.app_state.get_conversations()

        if conversations:
            export_all = st.checkbox("Export all conversations", value=True)

            selected_convs = []
            if not export_all:
                conv_options = []
                for conv in conversations:
                    created = conv.get("created_at", "")
                    try:
                        created_dt = datetime.fromisoformat(created)
                        created_str = created_dt.strftime("%b %d, %H:%M")
                    except:
                        created_str = "Unknown"
                    msg_count = len(conv.get("messages", []))
                    conv_options.append(f"{created_str} ({msg_count} messages)")

                selected_indices = st.multiselect(
                    "Select conversations",
                    options=range(len(conversations)),
                    format_func=lambda i: conv_options[i],
                    help="Choose which conversations to export"
                )
                selected_convs = [conversations[i] for i in selected_indices]
            else:
                selected_convs = conversations

            # Format selection
            export_format = st.selectbox(
                "Format",
                options=["JSON", "Markdown", "HTML", "TXT"],
                help="Choose export format"
            )

            # Options
            include_metadata = st.checkbox("Include metadata", value=True, help="Include tags, favorites, etc.")
            include_stats = st.checkbox("Include statistics", value=True, help="Include message counts, token estimates")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.show_export_dialog = False
                    st.session_state.export_ready = False
                    st.rerun()
            with col2:
                export = st.button("Export", type="primary", use_container_width=True)

            if export and selected_convs:
                from core.export_engine import ExportEngine

                engine = ExportEngine()
                format_lower = export_format.lower()

                try:
                    if len(selected_convs) == 1:
                        # Export single conversation
                        options = {
                            "include_metadata": include_metadata,
                            "include_stats": include_stats
                        }
                        exported_data = engine.export_conversation(
                            selected_convs[0],
                            format_lower,
                            options
                        )
                        filename = f"conversation.{format_lower}"
                    else:
                        # Export multiple (combined)
                        options = {
                            "include_metadata": include_metadata,
                            "include_stats": include_stats
                        }
                        exported_data = engine.export_multiple(
                            selected_convs,
                            format_lower,
                            combine=True,
                            options=options
                        )
                        filename = f"conversations_{len(selected_convs)}.{format_lower}"

                    # Store in session state
                    mime_type = engine.get_mime_type(format_lower)
                    st.session_state.export_ready = True
                    st.session_state.export_data = exported_data
                    st.session_state.export_filename = filename
                    st.session_state.export_mime = mime_type
                    st.session_state.export_count = len(selected_convs)
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Export failed: {e}")
                    logger.error(f"Export error: {e}", exc_info=True)

            # Show download button if export is ready
            if st.session_state.get("export_ready", False):
                st.success(f"✅ Exported {st.session_state.get('export_count', 0)} conversation(s)")
                st.download_button(
                    label=f"⬇️ Download {st.session_state.export_filename}",
                    data=st.session_state.export_data,
                    file_name=st.session_state.export_filename,
                    mime=st.session_state.export_mime,
                    use_container_width=True
                )

                if st.button("Close", use_container_width=True):
                    st.session_state.show_export_dialog = False
                    st.session_state.export_ready = False
                    st.rerun()

        else:
            st.info("No conversations to export")
            if st.button("Close", use_container_width=True):
                st.session_state.show_export_dialog = False
                st.rerun()

        st.markdown("---")

    # Import Dialog
    if st.session_state.get("show_import_dialog", False):
        st.markdown("### 📥 Import Conversations")

        with st.form("import_form"):
            uploaded_file = st.file_uploader(
                "Upload conversation file",
                type=["json", "md", "txt"],
                help="JSON (recommended), Markdown, or Text format"
            )

            format_hint = st.selectbox(
                "Format (auto-detect if not specified)",
                options=["Auto-detect", "JSON", "Markdown", "Text"],
                help="Leave as auto-detect unless having issues"
            )

            validate = st.checkbox("Validate after import", value=True, help="Check conversation structure")

            col1, col2 = st.columns(2)
            with col1:
                cancel = st.form_submit_button("Cancel", use_container_width=True)
            with col2:
                import_btn = st.form_submit_button("Import", type="primary", use_container_width=True)

            if cancel:
                st.session_state.show_import_dialog = False
                st.rerun()

            if import_btn and uploaded_file:
                from core.import_engine import ImportEngine

                engine = ImportEngine()

                try:
                    # Read file content
                    content = uploaded_file.read()

                    # Determine format
                    format_to_use = None if format_hint == "Auto-detect" else format_hint.lower()

                    # Import
                    imported_conv = engine.import_conversation(
                        content,
                        format=format_to_use,
                        validate=validate
                    )

                    # Check if this is a multi-conversation file
                    if imported_conv.get("_multiple"):
                        # Multiple conversations in one file
                        conversations = imported_conv["conversations"]
                        imported_count = 0
                        total_messages = 0

                        for conv in conversations:
                            # Normalize and validate each conversation
                            conv = engine._normalize_conversation(conv)
                            if validate:
                                is_valid, errors = engine.validate_conversation(conv)
                                if not is_valid:
                                    st.warning(f"⚠️ Skipped invalid conversation '{conv.get('title', 'Untitled')}': {', '.join(errors)}")
                                    continue

                            # Save to app state
                            st.session_state.app_state.save_conversation(
                                conv["messages"],
                                conv.get("metadata", {})
                            )
                            imported_count += 1
                            total_messages += len(conv.get("messages", []))

                        st.success(f"✅ Imported {imported_count} conversation(s) from file")
                        st.info(f"📊 Total: {total_messages} messages")

                    else:
                        # Single conversation
                        st.session_state.app_state.save_conversation(
                            imported_conv["messages"],
                            imported_conv.get("metadata", {})
                        )

                        st.success(f"✅ Imported conversation: {imported_conv.get('title', 'Untitled')}")
                        st.info(f"📊 {len(imported_conv.get('messages', []))} messages imported")

                    # Close dialog after successful import
                    if st.form_submit_button("Close", use_container_width=True):
                        st.session_state.show_import_dialog = False
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Import failed: {e}")
                    logger.error(f"Import error: {e}", exc_info=True)

        st.markdown("---")

    # Cleanup Dialog - Remove orphaned single-message conversations
    if st.session_state.get("show_cleanup_dialog", False):
        st.markdown("### 🧹 Conversation Cleanup")
        st.write("Remove orphaned single-message conversation entries created by a previous bug.")

        preview = st.session_state.cleanup_preview

        if preview:
            # Show stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Conversations", preview["total_conversations"])
            with col2:
                st.metric("To Delete", preview["to_delete"], delta=f"-{preview['to_delete']}" if preview["to_delete"] > 0 else None, delta_color="inverse")
            with col3:
                st.metric("To Keep", preview["to_keep"])

            if preview["to_delete"] > 0:
                st.warning(f"⚠️ This will permanently delete {preview['to_delete']} conversation(s) with less than 2 messages.")

                # Show sample of what will be deleted
                if preview.get("deleted_previews"):
                    with st.expander("Preview items to delete (sample)", expanded=False):
                        for item in preview["deleted_previews"]:
                            preview_text = item.get("preview", "")[:60]
                            st.caption(f"• {preview_text}..." if preview_text else "• (empty)")

                # Confirm and execute
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Delete Orphans", use_container_width=True, type="primary"):
                        with st.spinner("Cleaning up..."):
                            result = st.session_state.app_state.cleanup_single_message_conversations(dry_run=False)
                        st.success(f"✅ Deleted {result['to_delete']} orphaned entries!")
                        st.session_state.cleanup_preview = None
                        st.session_state.show_cleanup_dialog = False
                        st.session_state.conv_display_count = st.session_state.conv_page_size  # Reset pagination
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.cleanup_preview = None
                        st.session_state.show_cleanup_dialog = False
                        st.rerun()
            else:
                st.success("✅ No orphaned conversations found! Your data is clean.")
                if st.button("Close", use_container_width=True):
                    st.session_state.show_cleanup_dialog = False
                    st.rerun()

        st.markdown("---")

    # Configuration Dialog
    if st.session_state.get("show_config_dialog", False):
        st.markdown("### ⚙️ Configuration Management")

        tab1, tab2, tab3 = st.tabs(["📤 Export Config", "📥 Import Config", "🔄 Reset"])

        # Export Config Tab
        with tab1:
            st.write("Export your current settings to a file")

            if st.button("📤 Export Configuration", use_container_width=True):
                from core.config_manager import ConfigManager

                manager = ConfigManager()

                try:
                    config_json = manager.export_to_json(st.session_state, indent=2)

                    st.download_button(
                        label="⬇️ Download config.json",
                        data=config_json,
                        file_name="apex_config.json",
                        mime="application/json",
                        use_container_width=True
                    )

                    st.success("✅ Configuration exported")

                except Exception as e:
                    st.error(f"❌ Export failed: {e}")
                    logger.error(f"Config export error: {e}", exc_info=True)

        # Import Config Tab
        with tab2:
            st.write("Import settings from a configuration file")

            uploaded_config = st.file_uploader(
                "Upload config.json",
                type=["json"],
                key="config_uploader"
            )

            merge_config = st.checkbox(
                "Merge with existing settings",
                value=False,
                help="If unchecked, will replace all settings"
            )

            if st.button("📥 Import Configuration", use_container_width=True) and uploaded_config:
                from core.config_manager import ConfigManager

                manager = ConfigManager()

                try:
                    config_json = uploaded_config.read().decode("utf-8")
                    success, messages = manager.import_from_json(
                        config_json,
                        st.session_state,
                        merge=merge_config
                    )

                    if success:
                        st.success("✅ Configuration imported successfully")
                        for msg in messages:
                            st.info(f"• {msg}")
                        st.info("🔄 Reload the page to see changes")
                    else:
                        st.error("❌ Import failed")
                        for msg in messages:
                            st.error(f"• {msg}")

                except Exception as e:
                    st.error(f"❌ Import failed: {e}")
                    logger.error(f"Config import error: {e}", exc_info=True)

        # Reset Tab
        with tab3:
            st.write("Reset all settings to defaults")
            st.warning("⚠️ This will reset all your settings. Your conversations will not be affected.")

            if st.button("🔄 Reset to Defaults", type="primary", use_container_width=True):
                from core.config_manager import ConfigManager

                manager = ConfigManager()

                try:
                    manager.reset_to_defaults(st.session_state)
                    st.success("✅ Settings reset to defaults")
                    st.info("🔄 Reload the page to see changes")

                except Exception as e:
                    st.error(f"❌ Reset failed: {e}")
                    logger.error(f"Config reset error: {e}", exc_info=True)

        # Close button
        if st.button("Close", use_container_width=True, key="close_config_dialog"):
            st.session_state.show_config_dialog = False
            st.rerun()

        st.markdown("---")

    # Knowledge Base Manager Dialog (Phase 13.5)
    if st.session_state.get("show_knowledge_manager", False):
        st.markdown("### 📚 Knowledge Base Manager")

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Browse", "➕ Add/Edit", "🔍 Search", "📦 Export/Import"])

        # Tab 1: Browse
        with tab1:
            st.markdown("#### Browse All Facts")

            # Filter panel
            with st.expander("🔧 Filters", expanded=False):
                col_f1, col_f2 = st.columns(2)

                with col_f1:
                    st.session_state.kb_filter_category = st.selectbox(
                        "Category",
                        options=["all", "preferences", "technical", "project", "general"],
                        index=0,
                        key="kb_filter_cat_select"
                    )

                    st.session_state.kb_sort_by = st.selectbox(
                        "Sort By",
                        options=["date", "confidence", "category"],
                        index=0,
                        key="kb_sort_select"
                    )

                with col_f2:
                    min_conf, max_conf = st.slider(
                        "Confidence Range",
                        0.0, 1.0, (0.0, 1.0),
                        step=0.1,
                        key="kb_conf_range_slider"
                    )
                    st.session_state.kb_filter_confidence_min = min_conf
                    st.session_state.kb_filter_confidence_max = max_conf

                    st.session_state.kb_sort_order = st.selectbox(
                        "Sort Order",
                        options=["desc", "asc"],
                        index=0,
                        key="kb_order_select"
                    )

                if st.button("Clear Filters", key="kb_clear_filters"):
                    st.session_state.kb_filter_category = "all"
                    st.session_state.kb_filter_confidence_min = 0.0
                    st.session_state.kb_filter_confidence_max = 1.0
                    st.session_state.kb_sort_by = "date"
                    st.session_state.kb_sort_order = "desc"
                    st.rerun()

            # Batch mode toggle
            st.session_state.kb_batch_mode = st.checkbox(
                "Batch Mode (Multi-select)",
                value=st.session_state.kb_batch_mode,
                key="kb_batch_toggle"
            )

            # Get filtered facts
            category_filter = None if st.session_state.kb_filter_category == "all" else st.session_state.kb_filter_category
            facts = st.session_state.app_state.get_all_knowledge(
                category=category_filter,
                sort_by=st.session_state.kb_sort_by,
                sort_order=st.session_state.kb_sort_order
            )

            # Apply confidence filter
            facts = [
                f for f in facts
                if st.session_state.kb_filter_confidence_min <= f.get("confidence", 1.0) <= st.session_state.kb_filter_confidence_max
            ]

            # Batch operations
            if st.session_state.kb_batch_mode and facts:
                col_sel1, col_sel2 = st.columns(2)
                with col_sel1:
                    if st.button("Select All", key="kb_select_all"):
                        st.session_state.kb_selected_facts = [f["id"] for f in facts]
                        st.rerun()
                with col_sel2:
                    if st.button("Clear Selection", key="kb_clear_sel"):
                        st.session_state.kb_selected_facts = []
                        st.rerun()

                if st.session_state.kb_selected_facts:
                    st.warning(f"Selected: {len(st.session_state.kb_selected_facts)} facts")
                    if st.button("🗑️ Delete Selected", key="kb_batch_delete"):
                        result = st.session_state.app_state.batch_delete_knowledge(st.session_state.kb_selected_facts)
                        if result.get("success"):
                            st.success(f"Deleted {result['deleted']} facts")
                            st.session_state.kb_selected_facts = []
                            st.rerun()
                        else:
                            st.error(f"Batch delete failed: {result.get('error')}")

            # Display facts
            if facts:
                st.caption(f"Showing {len(facts)} facts")

                for fact in facts:
                    # Category emoji
                    category_emoji = {
                        "preferences": "⭐",
                        "technical": "🔧",
                        "project": "📁",
                        "general": "📝"
                    }.get(fact["category"], "📝")

                    # Container for fact
                    with st.container():
                        # Batch mode checkbox
                        if st.session_state.kb_batch_mode:
                            is_selected = fact["id"] in st.session_state.kb_selected_facts
                            col_check, col_content = st.columns([0.1, 0.9])

                            with col_check:
                                if st.checkbox("", value=is_selected, key=f"kb_check_{fact['id']}", label_visibility="collapsed"):
                                    if fact["id"] not in st.session_state.kb_selected_facts:
                                        st.session_state.kb_selected_facts.append(fact["id"])
                                        st.rerun()
                                else:
                                    if fact["id"] in st.session_state.kb_selected_facts:
                                        st.session_state.kb_selected_facts.remove(fact["id"])
                                        st.rerun()

                            with col_content:
                                st.markdown(f"{category_emoji} **{fact['category']}** | Confidence: {fact['confidence']:.0%}")
                        else:
                            st.markdown(f"{category_emoji} **{fact['category']}** | Confidence: {fact['confidence']:.0%}")

                        # Fact text (truncated)
                        text = fact["text"]
                        if len(text) > 100:
                            st.caption(text[:100] + "...")
                            with st.expander("View Full Text"):
                                st.write(text)
                        else:
                            st.caption(text)

                        # Metadata
                        st.caption(f"Source: {fact.get('source', 'N/A')} | Added: {fact.get('added_at', 'N/A')[:10]}")

                        # Actions (non-batch mode)
                        if not st.session_state.kb_batch_mode:
                            col_edit, col_del = st.columns(2)
                            with col_edit:
                                if st.button("✏️ Edit", key=f"kb_edit_{fact['id']}", use_container_width=True):
                                    st.session_state.kb_edit_fact_id = fact["id"]
                                    st.rerun()
                            with col_del:
                                if st.button("🗑️ Delete", key=f"kb_del_{fact['id']}", use_container_width=True):
                                    from tools.vector_search import vector_delete
                                    result = vector_delete(fact["id"], collection="knowledge")
                                    if result.get("success"):
                                        st.success("Fact deleted!")
                                        st.rerun()
                                    else:
                                        st.error(f"Delete failed: {result.get('error')}")

                        st.divider()
            else:
                st.info("No facts match your filters")

        # Tab 2: Add/Edit
        with tab2:
            # Check if in edit mode
            edit_mode = st.session_state.kb_edit_fact_id is not None
            if edit_mode:
                st.markdown("#### ✏️ Edit Fact")

                # Load current fact
                from core.vector_db import create_vector_db
                db = create_vector_db()
                collection = db.get_or_create_collection("knowledge")
                current = collection.collection.get(
                    ids=[st.session_state.kb_edit_fact_id],
                    include=["documents", "metadatas"]
                )

                if current["ids"]:
                    current_text = current["documents"][0]
                    current_meta = current["metadatas"][0]
                else:
                    st.error("Fact not found!")
                    edit_mode = False
                    st.session_state.kb_edit_fact_id = None
            else:
                st.markdown("#### ➕ Add New Fact")

            # Form
            with st.form(key="kb_add_edit_form"):
                # Fact text
                fact_text = st.text_area(
                    "Fact Text *",
                    value=current_text if edit_mode else "",
                    height=150,
                    max_chars=1000,
                    help="Enter the fact or information to remember (3-1000 characters)"
                )

                col_form1, col_form2 = st.columns(2)

                with col_form1:
                    # Category
                    category_options = ["preferences", "technical", "project", "general"]
                    default_cat_idx = 0
                    if edit_mode:
                        try:
                            default_cat_idx = category_options.index(current_meta.get("category", "general"))
                        except ValueError:
                            default_cat_idx = 3  # Default to general

                    category = st.selectbox(
                        "Category *",
                        options=category_options,
                        index=default_cat_idx,
                        help="Categorize this fact"
                    )

                    # Confidence
                    confidence = st.slider(
                        "Confidence",
                        0.0, 1.0,
                        value=current_meta.get("confidence", 1.0) if edit_mode else 1.0,
                        step=0.1,
                        help="How confident are you in this fact? (1.0 = certain, 0.5-0.9 = inferred)"
                    )

                with col_form2:
                    # Source
                    source = st.text_input(
                        "Source (optional)",
                        value=current_meta.get("source", "") if edit_mode else "",
                        max_chars=100,
                        help="Where did this fact come from?"
                    )

                # Buttons
                col_cancel, col_submit = st.columns(2)

                with col_cancel:
                    cancel = st.form_submit_button("Cancel", use_container_width=True)

                with col_submit:
                    submit = st.form_submit_button(
                        "Update" if edit_mode else "Add",
                        type="primary",
                        use_container_width=True
                    )

            # Handle form submission
            if cancel:
                st.session_state.kb_edit_fact_id = None
                st.rerun()

            if submit:
                # Validate
                if not fact_text or len(fact_text) < 3:
                    st.error("Fact text must be at least 3 characters!")
                else:
                    if edit_mode:
                        # Update fact
                        result = st.session_state.app_state.update_knowledge(
                            fact_id=st.session_state.kb_edit_fact_id,
                            fact_text=fact_text,
                            category=category,
                            confidence=confidence,
                            source=source
                        )

                        if result.get("success"):
                            st.success("Fact updated successfully!")
                            st.session_state.kb_edit_fact_id = None
                            st.rerun()
                        else:
                            st.error(f"Update failed: {result.get('error')}")
                    else:
                        # Add new fact
                        from tools.vector_search import vector_add_knowledge
                        result = vector_add_knowledge(
                            fact=fact_text,
                            category=category,
                            confidence=confidence,
                            source=source if source else "manual"
                        )

                        if result.get("success"):
                            st.success("Fact added successfully!")
                            st.rerun()
                        else:
                            st.error(f"Add failed: {result.get('error')}")

        # Tab 3: Search
        with tab3:
            st.markdown("#### 🔍 Semantic Search")

            # Search form
            search_query = st.text_input(
                "Search Query",
                value=st.session_state.kb_search_query,
                placeholder="Enter natural language query...",
                key="kb_search_input"
            )

            col_s1, col_s2, col_s3 = st.columns(3)

            with col_s1:
                search_category = st.selectbox(
                    "Category Filter",
                    options=["all", "preferences", "technical", "project", "general"],
                    index=0,
                    key="kb_search_cat"
                )

            with col_s2:
                search_min_conf = st.slider(
                    "Min Confidence",
                    0.0, 1.0, 0.0,
                    step=0.1,
                    key="kb_search_minconf"
                )

            with col_s3:
                search_top_k = st.slider(
                    "Max Results",
                    1, 20, 5,
                    key="kb_search_topk"
                )

            if st.button("🔍 Search", key="kb_do_search", type="primary"):
                st.session_state.kb_search_query = search_query

            # Perform search
            if st.session_state.kb_search_query:
                from tools.vector_search import vector_search_knowledge

                category_arg = None if search_category == "all" else search_category
                results = vector_search_knowledge(
                    query=st.session_state.kb_search_query,
                    category=category_arg,
                    min_confidence=search_min_conf,
                    top_k=search_top_k
                )

                # Display results
                if results and not isinstance(results, dict):
                    st.success(f"Found {len(results)} matches")

                    for result in results:
                        similarity = result.get("similarity", 0)

                        # Category emoji
                        category_emoji = {
                            "preferences": "⭐",
                            "technical": "🔧",
                            "project": "📁",
                            "general": "📝"
                        }.get(result.get("metadata", {}).get("category", "general"), "📝")

                        with st.container():
                            st.markdown(f"🎯 **{similarity:.1%}** | {category_emoji} {result.get('metadata', {}).get('category', 'general')}")
                            st.caption(result.get("text", ""))
                            st.caption(f"Confidence: {result.get('metadata', {}).get('confidence', 1.0):.0%} | Source: {result.get('metadata', {}).get('source', 'N/A')}")

                            # Actions
                            col_e, col_d = st.columns(2)
                            with col_e:
                                if st.button("✏️ Edit", key=f"kb_search_edit_{result['id']}", use_container_width=True):
                                    st.session_state.kb_edit_fact_id = result["id"]
                                    st.rerun()
                            with col_d:
                                if st.button("🗑️ Delete", key=f"kb_search_del_{result['id']}", use_container_width=True):
                                    from tools.vector_search import vector_delete
                                    del_result = vector_delete(result["id"], collection="knowledge")
                                    if del_result.get("success"):
                                        st.success("Deleted!")
                                        st.rerun()
                                    else:
                                        st.error(f"Delete failed: {del_result.get('error')}")

                            st.divider()
                else:
                    st.info("No results found. Try different search terms.")

        # Tab 4: Export/Import
        with tab4:
            st.markdown("#### 📦 Export & Import")

            col_exp, col_imp = st.columns(2)

            # Export column
            with col_exp:
                st.markdown("##### 📤 Export")

                export_category = st.selectbox(
                    "Category Filter",
                    options=["all", "preferences", "technical", "project", "general"],
                    index=0,
                    key="kb_export_cat"
                )

                if st.button("Export to JSON", key="kb_export_btn", type="primary"):
                    category_arg = None if export_category == "all" else export_category
                    result = st.session_state.app_state.export_knowledge(format="json", category=category_arg)

                    if result.get("success"):
                        import json
                        json_data = json.dumps(result["data"], indent=2)

                        st.download_button(
                            label=f"⬇️ Download ({result['count']} facts)",
                            data=json_data,
                            file_name=f"knowledge_export_{export_category}.json",
                            mime="application/json",
                            key="kb_download_json"
                        )
                    else:
                        st.error(f"Export failed: {result.get('error')}")

            # Import column
            with col_imp:
                st.markdown("##### 📥 Import")

                uploaded_file = st.file_uploader(
                    "Upload JSON file",
                    type=["json"],
                    key="kb_import_uploader"
                )

                validate_import = st.checkbox(
                    "Validate data",
                    value=True,
                    key="kb_import_validate",
                    help="Strict validation (recommended)"
                )

                if uploaded_file is not None:
                    if st.button("Import", key="kb_import_btn", type="primary"):
                        try:
                            import json
                            data = json.load(uploaded_file)

                            result = st.session_state.app_state.import_knowledge(
                                data=data,
                                format="json",
                                validate=validate_import
                            )

                            if result.get("success"):
                                st.success(f"Imported {result['imported']} facts!")

                                if result.get("failed", 0) > 0:
                                    st.warning(f"{result['failed']} facts failed to import")
                                    with st.expander("View Failures"):
                                        for failure in result.get("failures", []):
                                            st.caption(f"Index {failure['index']}: {failure['error']}")

                                st.rerun()
                            else:
                                st.error(f"Import failed: {result.get('error')}")

                        except Exception as e:
                            st.error(f"Import error: {str(e)}")

        # Close button
        st.markdown("---")
        if st.button("Close Knowledge Manager", use_container_width=True, key="close_kb_manager"):
            st.session_state.show_knowledge_manager = False
            st.session_state.kb_edit_fact_id = None
            st.session_state.kb_selected_facts = []
            st.rerun()

        st.markdown("---")

    # Cache Manager Dialog (Phase 14)
    if st.session_state.get("show_cache_manager", False):
        st.markdown("### 💾 Cache Manager")

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "⚙️ Settings", "🔍 Monitor", "🛠️ Actions"])

        # Tab 1: Overview - Statistics Dashboard
        with tab1:
            st.markdown("#### Cache Performance Overview")

            cache_stats = st.session_state.client.cache_tracker.get_cache_stats()

            # Key metrics (4 columns)
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Requests",
                    f"{cache_stats.get('total_requests', 0):,}",
                    help="Total API requests made"
                )

            with col2:
                hit_rate = cache_stats.get('cache_hit_rate', 0) * 100
                st.metric(
                    "Cache Hit Rate",
                    f"{hit_rate:.1f}%",
                    help="Percentage using cached content"
                )

            with col3:
                savings_pct = cache_stats.get('savings_percentage', 0)
                st.metric(
                    "Cost Reduction",
                    f"{savings_pct:.1f}%",
                    help="Percentage of costs saved"
                )

            with col4:
                savings = cache_stats.get('cost_savings', 0)
                st.metric(
                    "Total Savings",
                    f"${savings:.4f}",
                    help="Dollars saved via caching"
                )

            st.markdown("---")

            # Detailed breakdown
            st.markdown("#### Detailed Statistics")

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("**Cache Operations:**")
                st.caption(f"• Cache Writes: {cache_stats.get('cache_writes', 0):,}")
                st.caption(f"• Cache Hits: {cache_stats.get('cache_hits', 0):,}")
                st.caption(f"• Cache Misses: {cache_stats.get('cache_misses', 0):,}")

            with col_b:
                st.markdown("**Token Usage:**")
                st.caption(f"• Cached Tokens Created: {cache_stats.get('cache_creation_tokens', 0):,}")
                st.caption(f"• Cached Tokens Read: {cache_stats.get('cache_read_tokens', 0):,}")
                st.caption(f"• Regular Input Tokens: {cache_stats.get('regular_input_tokens', 0):,}")

            st.markdown("---")

            # Cost comparison
            st.markdown("#### Cost Comparison")

            cost_with = cache_stats.get('cost_with_cache', 0)
            cost_without = cache_stats.get('cost_without_cache', 0)

            col_c1, col_c2 = st.columns(2)

            with col_c1:
                st.metric(
                    "Cost With Cache",
                    f"${cost_with:.4f}",
                    delta=f"-{savings_pct:.1f}%",
                    delta_color="normal"
                )

            with col_c2:
                st.metric(
                    "Cost Without Cache",
                    f"${cost_without:.4f}",
                    help="What you would have paid"
                )

        # Tab 2: Settings - Strategy Configuration
        with tab2:
            st.markdown("#### Cache Strategy Settings")

            # Current strategy display
            current = st.session_state.cache_strategy
            st.info(f"**Current Strategy:** {current.title()}")

            st.markdown("---")

            # Strategy descriptions
            st.markdown("**Available Strategies:**")

            strategy_info = {
                "disabled": {
                    "icon": "🔴",
                    "name": "Disabled",
                    "desc": "No caching (backward compatible)",
                    "caches": "Nothing",
                    "best_for": "Testing, debugging, one-off queries"
                },
                "conservative": {
                    "icon": "🟡",
                    "name": "Conservative",
                    "desc": "Cache only stable content",
                    "caches": "System prompt + Tool definitions",
                    "best_for": "Frequent tool changes, short conversations"
                },
                "balanced": {
                    "icon": "🟢",
                    "name": "Balanced",
                    "desc": "Cache stable + older history",
                    "caches": "System + Tools + History (5+ turns back)",
                    "best_for": "Typical usage, good cost/benefit ratio"
                },
                "aggressive": {
                    "icon": "🔵",
                    "name": "Aggressive",
                    "desc": "Maximum caching for maximum savings",
                    "caches": "System + Tools + Most History (3+ turns)",
                    "best_for": "Long conversations, maximum cost savings"
                }
            }

            for strategy_key, info in strategy_info.items():
                with st.expander(f"{info['icon']} {info['name']}", expanded=(strategy_key == current)):
                    st.markdown(f"**Description:** {info['desc']}")
                    st.markdown(f"**Caches:** {info['caches']}")
                    st.markdown(f"**Best for:** {info['best_for']}")

                    if strategy_key != current:
                        if st.button(f"Switch to {info['name']}", key=f"switch_{strategy_key}", use_container_width=True):
                            st.session_state.cache_strategy = strategy_key

                            from core.cache_manager import CacheStrategy
                            strategy_enum = CacheStrategy[strategy_key.upper()]
                            st.session_state.client.set_cache_strategy(strategy_enum)

                            st.success(f"✅ Switched to {info['name']}")
                            st.rerun()
                    else:
                        st.info("✅ Currently active")

            st.markdown("---")

            # Advanced settings
            with st.expander("⚙️ Advanced Settings", expanded=False):
                st.caption("**Cache Behavior:**")
                st.info("Cache TTL: 5 minutes (managed by Anthropic)")
                st.info("Min cacheable size: 1,024 tokens")
                st.info("Cache refresh: Automatic on use")

        # Tab 3: Monitor - Real-time Status
        with tab3:
            st.markdown("#### Cache Monitor")

            if st.session_state.cache_strategy == "disabled":
                st.warning("⚠️ Caching is currently disabled. Enable a strategy to see cache monitoring.")
            else:
                cache_status = st.session_state.client.get_cache_status()

                # Current cache state
                st.markdown("**Current Cache State:**")

                col_m1, col_m2 = st.columns(2)

                with col_m1:
                    system_cached = cache_status.get("system_cached", False)
                    system_icon = "✅" if system_cached else "⏹️"
                    st.caption(f"{system_icon} System Prompt: {'Cached' if system_cached else 'Not Cached'}")

                    tools_cached = cache_status.get("tools_cached", False)
                    tools_icon = "✅" if tools_cached else "⏹️"
                    st.caption(f"{tools_icon} Tool Definitions: {'Cached' if tools_cached else 'Not Cached'}")

                with col_m2:
                    history_cached = cache_status.get("history_cached", False)
                    history_icon = "✅" if history_cached else "⏹️"
                    history_count = cache_status.get("history_cached_count", 0)
                    st.caption(f"{history_icon} Conversation History: {history_count} messages cached")

                st.markdown("---")

                # Content hashes (for change detection)
                st.markdown("**Content Tracking:**")
                st.caption("Tracks when cached content changes to invalidate cache")

                with st.expander("View Content Hashes", expanded=False):
                    system_hash = cache_status.get("system_hash", "N/A")
                    tools_hash = cache_status.get("tools_hash", "N/A")

                    st.code(f"System Hash: {system_hash}")
                    st.code(f"Tools Hash: {tools_hash}")
                    st.caption("Hashes change when content is modified")

                st.markdown("---")

                # Refresh button
                if st.button("🔄 Refresh Status", use_container_width=True):
                    st.rerun()

        # Tab 4: Actions - Cache Management
        with tab4:
            st.markdown("#### Cache Actions")

            # Clear statistics
            st.markdown("**Clear Statistics:**")
            st.caption("Reset cache statistics without affecting cached content")

            if st.button("🗑️ Clear Stats", use_container_width=True, key="clear_cache_stats"):
                st.session_state.client.cache_tracker.reset_stats()
                st.success("✅ Cache statistics cleared")
                st.rerun()

            st.markdown("---")

            # Export statistics
            st.markdown("**Export Statistics:**")
            st.caption("Download cache statistics as JSON")

            if st.button("📤 Export Stats", key="export_cache_stats"):
                import json
                from datetime import datetime

                stats = st.session_state.client.cache_tracker.get_cache_stats()
                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "strategy": st.session_state.cache_strategy,
                    "statistics": stats
                }

                json_data = json.dumps(export_data, indent=2)

                st.download_button(
                    label="⬇️ Download cache_stats.json",
                    data=json_data,
                    file_name=f"cache_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )

            st.markdown("---")

            # Force cache refresh
            st.markdown("**Force Cache Refresh:**")
            st.caption("Invalidates current cache and forces new cache creation on next request")
            st.warning("⚠️ This will cause one expensive request to rebuild cache")

            if st.button("♻️ Force Refresh", use_container_width=True, key="force_cache_refresh"):
                st.session_state.client.cache_manager.invalidate_cache()
                st.success("✅ Cache invalidated - will rebuild on next request")
                st.rerun()

            st.markdown("---")

            # Reset all
            st.markdown("**Reset All:**")
            st.caption("Reset strategy to disabled and clear all statistics")
            st.error("⚠️ This will disable caching and clear all data")

            if st.button("🔄 Reset All", type="primary", use_container_width=True, key="reset_cache_all"):
                st.session_state.cache_strategy = "disabled"

                from core.cache_manager import CacheStrategy
                st.session_state.client.set_cache_strategy(CacheStrategy.DISABLED)
                st.session_state.client.cache_tracker.reset_stats()

                st.success("✅ Cache system reset to defaults")
                st.rerun()

        # Close button
        st.markdown("---")
        if st.button("Close Cache Manager", use_container_width=True, key="close_cache_manager"):
            st.session_state.show_cache_manager = False
            st.rerun()

        st.markdown("---")

    # Display chat history
    for message in st.session_state.messages:
        render_message(message)

    # Image upload section
    with st.container():
        st.markdown("---")
        uploaded_files = st.file_uploader(
            "📎 Upload images (optional)",
            type=["jpg", "jpeg", "png", "webp", "gif"],
            accept_multiple_files=True,
            key="image_uploader",
            help="Upload images for Claude to analyze. Supports JPG, PNG, WebP, GIF. Max 5MB per image."
        )

        # Show image previews
        if uploaded_files:
            st.caption(f"📷 {len(uploaded_files)} image(s) ready to send")
            cols = st.columns(min(len(uploaded_files), 4))
            for idx, file in enumerate(uploaded_files[:4]):  # Show max 4 previews
                with cols[idx]:
                    st.image(file, width=100, caption=file.name)
            if len(uploaded_files) > 4:
                st.caption(f"... and {len(uploaded_files) - 4} more")

    # Chat input
    if prompt := st.chat_input("Message Claude..."):
        process_message(prompt, uploaded_files if uploaded_files else None)

        # Clear uploaded files after sending
        if uploaded_files:
            st.rerun()


if __name__ == "__main__":
    main()
