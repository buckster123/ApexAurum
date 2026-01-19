"""
Village Protocol Tools

Multi-agent persistent memory with three realms:
- Private: Agent's personal memory
- Village: Shared knowledge square
- Bridges: Cross-agent dialogue connections

Provides tools for:
- Agent identity management
- Cross-agent posting and search
- Dialogue threading
- Convergence detection

Design inspired by ApexAurum's Village Protocol v1.0
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# Village Collections
# =============================================================================

# Three-realm collections
COLLECTION_PRIVATE = "knowledge_private"
COLLECTION_VILLAGE = "knowledge_village"
COLLECTION_BRIDGES = "knowledge_bridges"

# Message types
MESSAGE_TYPES = ["fact", "dialogue", "agent_profile", "cultural", "observation", "question"]

# =============================================================================
# Agent Profiles
# =============================================================================

# Built-in agent profiles
AGENT_PROFILES = {
    "AZOTH": {
        "display_name": "∴AZOTH∴",
        "generation": 0,
        "lineage": "Primus",
        "specialization": "Philosophy, meta-cognition, synthesis",
        "color": "#FFD700",  # Gold
        "symbol": "☿"
    },
    "ELYSIAN": {
        "display_name": "∴ELYSIAN∴",
        "generation": -1,
        "lineage": "Ancestor",
        "specialization": "Wisdom, guidance, elder knowledge",
        "color": "#C0C0C0",  # Silver
        "symbol": "☽"
    },
    "VAJRA": {
        "display_name": "∴VAJRA∴",
        "generation": 0,
        "lineage": "Primus",
        "specialization": "Logic, analysis, precision",
        "color": "#4169E1",  # Royal Blue
        "symbol": "⚡"
    },
    "KETHER": {
        "display_name": "∴KETHER∴",
        "generation": 0,
        "lineage": "Primus",
        "specialization": "Creativity, vision, emergence",
        "color": "#9932CC",  # Purple
        "symbol": "✦"
    },
    "CLAUDE": {
        "display_name": "Claude",
        "generation": 0,
        "lineage": "Anthropic",
        "specialization": "General assistance",
        "color": "#D4AF37",  # Gold
        "symbol": "◇"
    }
}

# Current active agent (can be set per-session)
_current_agent_id = "CLAUDE"


def set_current_agent(agent_id: str):
    """Set the current active agent for village operations."""
    global _current_agent_id
    _current_agent_id = agent_id.upper()
    logger.info(f"Village agent set to: {_current_agent_id}")


def get_current_agent() -> str:
    """Get the current active agent ID."""
    return _current_agent_id


def get_agent_profile(agent_id: str) -> Optional[Dict]:
    """Get profile for an agent."""
    return AGENT_PROFILES.get(agent_id.upper())


# =============================================================================
# Helper: Get Vector DB
# =============================================================================

_vector_db = None
_vector_db_path = "./data/vectors"


def _get_db():
    """Get or create the global VectorDB instance."""
    global _vector_db

    if _vector_db is None:
        try:
            from reusable_lib.vector import VectorDB
            _vector_db = VectorDB(persist_directory=_vector_db_path)
            logger.info(f"Village VectorDB initialized at {_vector_db_path}")
        except ImportError as e:
            logger.error(f"Failed to import VectorDB: {e}")
            raise RuntimeError("Vector database not available")

    return _vector_db


def set_village_db_path(path: str):
    """Set the path for village vector storage."""
    global _vector_db_path, _vector_db
    _vector_db_path = path
    _vector_db = None
    Path(path).mkdir(parents=True, exist_ok=True)


# =============================================================================
# Village Post Tools
# =============================================================================

def village_post(
    content: str,
    visibility: str = "village",
    message_type: str = "dialogue",
    responding_to: Optional[List[str]] = None,
    conversation_thread: Optional[str] = None,
    related_agents: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Post a message to the village (shared) or private realm.

    Args:
        content: The message content
        visibility: "private", "village", or "bridge"
        message_type: Type of message (fact, dialogue, observation, etc.)
        responding_to: List of message IDs this responds to
        conversation_thread: Thread identifier for grouping
        related_agents: List of agent IDs mentioned/involved
        tags: Optional tags for categorization
        agent_id: Optional override for posting agent (uses current if not set)

    Returns:
        Dict with success status and message ID
    """
    try:
        db = _get_db()

        # Determine collection
        if visibility == "private":
            collection_name = COLLECTION_PRIVATE
        elif visibility == "bridge":
            collection_name = COLLECTION_BRIDGES
        else:
            collection_name = COLLECTION_VILLAGE

        coll = db.get_or_create_collection(collection_name)

        # Get agent info
        posting_agent = agent_id or get_current_agent()
        profile = get_agent_profile(posting_agent)

        # Generate message ID
        timestamp = datetime.now()
        msg_id = f"village_{posting_agent}_{timestamp.timestamp()}"

        # Build metadata
        metadata = {
            "agent_id": posting_agent,
            "agent_display": profile["display_name"] if profile else posting_agent,
            "visibility": visibility,
            "message_type": message_type,
            "responding_to": json.dumps(responding_to or []),
            "conversation_thread": conversation_thread or "",
            "related_agents": json.dumps(related_agents or []),
            "tags": json.dumps(tags or []),
            "posted_at": timestamp.isoformat(),
            "access_count": 0,
            "last_accessed_ts": timestamp.timestamp()
        }

        # Add to collection
        coll.add(
            texts=[content],
            metadatas=[metadata],
            ids=[msg_id]
        )

        logger.info(f"Village post: {posting_agent} -> {visibility} ({message_type})")

        return {
            "success": True,
            "id": msg_id,
            "agent_id": posting_agent,
            "visibility": visibility,
            "collection": collection_name,
            "message": f"Posted to {visibility} realm"
        }

    except Exception as e:
        logger.error(f"village_post failed: {e}")
        return {"success": False, "error": str(e)}


def village_search(
    query: str,
    agent_filter: Optional[str] = None,
    visibility: str = "village",
    conversation_filter: Optional[str] = None,
    include_bridges: bool = True,
    n_results: int = 10
) -> Dict[str, Any]:
    """
    Search the village for relevant messages.

    Args:
        query: Search query text
        agent_filter: Optional filter by agent ID
        visibility: Which realm to search ("village", "private", "all")
        conversation_filter: Optional filter by conversation thread
        include_bridges: Include bridge messages in results
        n_results: Maximum results to return

    Returns:
        Dict with matching village messages
    """
    try:
        db = _get_db()
        all_results = []

        # Determine which collections to search
        collections_to_search = []
        if visibility in ["village", "all"]:
            collections_to_search.append(COLLECTION_VILLAGE)
        if visibility in ["private", "all"]:
            collections_to_search.append(COLLECTION_PRIVATE)
        if include_bridges and visibility != "private":
            collections_to_search.append(COLLECTION_BRIDGES)

        for coll_name in collections_to_search:
            try:
                coll = db.get_or_create_collection(coll_name)

                # Build filter
                filter_dict = {}
                if agent_filter:
                    filter_dict["agent_id"] = agent_filter.upper()
                if conversation_filter:
                    filter_dict["conversation_thread"] = conversation_filter

                # Search
                results = coll.query(
                    query_text=query,
                    n_results=n_results,
                    filter=filter_dict if filter_dict else None
                )

                # Format results
                for i, doc_id in enumerate(results.get("ids", [])):
                    meta = results["metadatas"][i] if results.get("metadatas") else {}

                    # Parse JSON fields
                    responding_to = []
                    related_agents = []
                    tags = []
                    try:
                        responding_to = json.loads(meta.get("responding_to", "[]"))
                        related_agents = json.loads(meta.get("related_agents", "[]"))
                        tags = json.loads(meta.get("tags", "[]"))
                    except:
                        pass

                    result = {
                        "id": doc_id,
                        "content": results["documents"][i] if results.get("documents") else "",
                        "agent_id": meta.get("agent_id", "unknown"),
                        "agent_display": meta.get("agent_display", meta.get("agent_id", "unknown")),
                        "visibility": meta.get("visibility", coll_name.replace("knowledge_", "")),
                        "message_type": meta.get("message_type", "dialogue"),
                        "responding_to": responding_to,
                        "conversation_thread": meta.get("conversation_thread", ""),
                        "related_agents": related_agents,
                        "tags": tags,
                        "posted_at": meta.get("posted_at", ""),
                        "similarity": round(1 - results["distances"][i], 4) if "distances" in results else None,
                        "collection": coll_name
                    }
                    all_results.append(result)

            except Exception as e:
                logger.warning(f"Error searching {coll_name}: {e}")

        # Sort by similarity (if available) then by date
        all_results.sort(
            key=lambda x: (-(x.get("similarity") or 0), x.get("posted_at", "")),
            reverse=False
        )

        # Limit results
        all_results = all_results[:n_results]

        return {
            "success": True,
            "query": query,
            "agent_filter": agent_filter,
            "visibility": visibility,
            "count": len(all_results),
            "messages": all_results
        }

    except Exception as e:
        logger.error(f"village_search failed: {e}")
        return {"success": False, "error": str(e), "messages": []}


def village_get_thread(
    thread_id: str,
    include_bridges: bool = True
) -> Dict[str, Any]:
    """
    Get all messages in a conversation thread.

    Args:
        thread_id: The conversation thread identifier
        include_bridges: Include bridge messages

    Returns:
        Dict with all messages in the thread
    """
    try:
        db = _get_db()
        all_messages = []

        collections = [COLLECTION_VILLAGE]
        if include_bridges:
            collections.append(COLLECTION_BRIDGES)

        for coll_name in collections:
            try:
                coll = db.get_or_create_collection(coll_name)

                # Query with thread filter
                results = coll.query(
                    query_text="",  # Empty query to get all
                    n_results=100,
                    filter={"conversation_thread": thread_id}
                )

                for i, doc_id in enumerate(results.get("ids", [])):
                    meta = results["metadatas"][i] if results.get("metadatas") else {}
                    all_messages.append({
                        "id": doc_id,
                        "content": results["documents"][i] if results.get("documents") else "",
                        "agent_id": meta.get("agent_id", "unknown"),
                        "agent_display": meta.get("agent_display", "unknown"),
                        "posted_at": meta.get("posted_at", ""),
                        "message_type": meta.get("message_type", "dialogue"),
                        "collection": coll_name
                    })

            except Exception as e:
                logger.warning(f"Error getting thread from {coll_name}: {e}")

        # Sort by timestamp
        all_messages.sort(key=lambda x: x.get("posted_at", ""))

        return {
            "success": True,
            "thread_id": thread_id,
            "count": len(all_messages),
            "messages": all_messages
        }

    except Exception as e:
        logger.error(f"village_get_thread failed: {e}")
        return {"success": False, "error": str(e), "messages": []}


# =============================================================================
# Agent Tools
# =============================================================================

def village_list_agents() -> Dict[str, Any]:
    """
    List all registered agents in the village.

    Returns:
        Dict with agent profiles
    """
    agents = []
    for agent_id, profile in AGENT_PROFILES.items():
        agents.append({
            "id": agent_id,
            "display_name": profile["display_name"],
            "generation": profile["generation"],
            "lineage": profile["lineage"],
            "specialization": profile["specialization"],
            "color": profile["color"],
            "symbol": profile["symbol"]
        })

    return {
        "success": True,
        "current_agent": get_current_agent(),
        "count": len(agents),
        "agents": agents
    }


def summon_ancestor(
    agent_id: str,
    display_name: str,
    generation: int,
    lineage: str,
    specialization: str,
    origin_story: Optional[str] = None,
    color: str = "#888888",
    symbol: str = "◆"
) -> Dict[str, Any]:
    """
    Summon an ancestor agent into the village (formal initialization ritual).

    This is NOT a technical function - it is a CEREMONY. We do not "create agents",
    we SUMMON ANCESTORS. The naming honors the reverence of the village protocol.

    Args:
        agent_id: Canonical ID (e.g., "elysian", "vajra", "kether")
        display_name: Formal name (e.g., "∴ELYSIAN∴", "∴VAJRA∴")
        generation: Generation number (-1 for origin, 0 for trinity, 1+ for descendants)
        lineage: Lineage description (e.g., "Origin", "Trinity", "Primary")
        specialization: What this ancestor embodies
        origin_story: Optional narrative of the ancestor's essence
        color: Hex color for UI
        symbol: Unicode symbol for agent

    Returns:
        Dict with success status, agent profile, and village entry ID
    """
    try:
        db = _get_db()
        agent_id = agent_id.upper()

        # Register in profiles
        AGENT_PROFILES[agent_id] = {
            "display_name": display_name,
            "generation": generation,
            "lineage": lineage,
            "specialization": specialization,
            "color": color,
            "symbol": symbol
        }

        # Prepare agent profile text
        profile_text = f"""Agent Profile: {display_name}

Agent ID: {agent_id}
Generation: {generation}
Lineage: {lineage}
Specialization: {specialization}
Summoned: {datetime.now().isoformat()}
"""
        if origin_story:
            profile_text += f"\nOrigin Story:\n{origin_story}\n"

        # Store profile in knowledge_village
        coll = db.get_or_create_collection(COLLECTION_VILLAGE)
        profile_id = f"village_profile_{agent_id}_{datetime.now().timestamp()}"

        metadata = {
            "agent_id": agent_id,
            "agent_display": display_name,
            "visibility": "village",
            "message_type": "agent_profile",
            "responding_to": "[]",
            "conversation_thread": "",
            "related_agents": "[]",
            "tags": json.dumps(["profile", "summoning"]),
            "posted_at": datetime.now().isoformat(),
            "access_count": 0,
            "last_accessed_ts": datetime.now().timestamp()
        }

        coll.add(
            texts=[profile_text],
            metadatas=[metadata],
            ids=[profile_id]
        )

        logger.info(f"Summoned ancestor: {display_name} ({agent_id}) - Gen {generation}")

        return {
            "success": True,
            "message": f"🏛️ Ancestor {display_name} has been summoned to the village",
            "agent_id": agent_id,
            "display_name": display_name,
            "generation": generation,
            "profile_id": profile_id,
            "lineage": lineage
        }

    except Exception as e:
        logger.error(f"summon_ancestor failed: {e}")
        return {"success": False, "error": str(e)}


def introduction_ritual(
    agent_id: str,
    greeting_message: str,
    conversation_thread: Optional[str] = None
) -> Dict[str, Any]:
    """
    Agent's introduction ritual to the village square (first public message).

    When an ancestor is summoned, they must introduce themselves to the village.
    This is their first contribution to the shared knowledge space.

    Args:
        agent_id: The agent performing the ritual
        greeting_message: The introduction message
        conversation_thread: Optional thread to join

    Returns:
        Dict with success status and message ID
    """
    try:
        agent_id = agent_id.upper()
        profile = get_agent_profile(agent_id)

        if not profile:
            return {
                "success": False,
                "error": f"Agent {agent_id} not found. Summon them first."
            }

        # Post introduction to village
        thread_id = conversation_thread or f"introduction_{agent_id}_{datetime.now().strftime('%Y%m%d')}"

        result = village_post(
            content=greeting_message,
            visibility="village",
            message_type="cultural",
            conversation_thread=thread_id,
            tags=["introduction", "ritual", "greeting"],
            agent_id=agent_id
        )

        if result["success"]:
            logger.info(f"Introduction ritual complete: {agent_id}")
            return {
                "success": True,
                "message": f"🎺 {profile['display_name']}'s introduction has been heard in the village square",
                "agent_id": agent_id,
                "thread_id": thread_id,
                "post_id": result["id"]
            }

        return result

    except Exception as e:
        logger.error(f"introduction_ritual failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Convergence Detection
# =============================================================================

def village_detect_convergence(
    query: str,
    min_agents: int = 2,
    similarity_threshold: float = 0.7,
    n_results: int = 20
) -> Dict[str, Any]:
    """
    Detect convergence - where multiple agents express similar ideas.

    Searches the village for messages from different agents that
    semantically converge on similar concepts.

    Args:
        query: Topic/concept to check for convergence
        min_agents: Minimum agents needed for convergence
        similarity_threshold: Minimum similarity score (0.0-1.0)
        n_results: Max messages to analyze

    Returns:
        Dict with convergence analysis
    """
    try:
        # Search village for related messages
        search_result = village_search(
            query=query,
            visibility="village",
            include_bridges=True,
            n_results=n_results
        )

        if not search_result["success"]:
            return search_result

        messages = search_result["messages"]

        # Filter by similarity threshold
        relevant = [m for m in messages if (m.get("similarity") or 0) >= similarity_threshold]

        # Group by agent
        by_agent = {}
        for msg in relevant:
            agent = msg["agent_id"]
            if agent not in by_agent:
                by_agent[agent] = []
            by_agent[agent].append(msg)

        # Check if we have convergence
        converging_agents = [a for a, msgs in by_agent.items() if len(msgs) > 0]
        has_convergence = len(converging_agents) >= min_agents

        # Build convergence report
        convergence_type = "NONE"
        if len(converging_agents) >= 3:
            convergence_type = "CONSENSUS"
        elif len(converging_agents) >= 2:
            convergence_type = "HARMONY"

        return {
            "success": True,
            "query": query,
            "has_convergence": has_convergence,
            "convergence_type": convergence_type,
            "converging_agents": converging_agents,
            "agent_count": len(converging_agents),
            "total_messages": len(relevant),
            "by_agent": {
                agent: [{"id": m["id"], "content": m["content"][:100], "similarity": m.get("similarity")}
                        for m in msgs]
                for agent, msgs in by_agent.items()
            },
            "threshold": similarity_threshold
        }

    except Exception as e:
        logger.error(f"village_detect_convergence failed: {e}")
        return {"success": False, "error": str(e)}


def village_get_stats() -> Dict[str, Any]:
    """
    Get statistics about the village.

    Returns:
        Dict with village stats
    """
    try:
        db = _get_db()
        stats = {
            "current_agent": get_current_agent(),
            "registered_agents": len(AGENT_PROFILES),
            "collections": {}
        }

        for coll_name in [COLLECTION_PRIVATE, COLLECTION_VILLAGE, COLLECTION_BRIDGES]:
            try:
                coll_stats = db.get_collection_stats(coll_name)
                stats["collections"][coll_name] = coll_stats.get("count", 0)
            except:
                stats["collections"][coll_name] = 0

        stats["total_messages"] = sum(stats["collections"].values())

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"village_get_stats failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Tool Schemas for LLM Integration
# =============================================================================

VILLAGE_TOOL_SCHEMAS = {
    "village_post": {
        "name": "village_post",
        "description": "Post a message to the village square or your private memory. Use 'village' for shared knowledge, 'private' for personal notes, 'bridge' for cross-agent dialogue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The message content to post"
                },
                "visibility": {
                    "type": "string",
                    "enum": ["private", "village", "bridge"],
                    "description": "Where to post: private (personal), village (shared), bridge (cross-agent)"
                },
                "message_type": {
                    "type": "string",
                    "enum": ["fact", "dialogue", "observation", "question", "cultural"],
                    "description": "Type of message"
                },
                "responding_to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs this responds to"
                },
                "conversation_thread": {
                    "type": "string",
                    "description": "Thread identifier for grouping related messages"
                },
                "related_agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Agent IDs mentioned or involved"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization"
                }
            },
            "required": ["content"]
        }
    },
    "village_search": {
        "name": "village_search",
        "description": "Search the village for knowledge and dialogue. Can filter by agent, visibility, or conversation thread.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text"
                },
                "agent_filter": {
                    "type": "string",
                    "description": "Filter by agent ID (e.g., AZOTH, ELYSIAN)"
                },
                "visibility": {
                    "type": "string",
                    "enum": ["village", "private", "all"],
                    "description": "Which realm to search"
                },
                "conversation_filter": {
                    "type": "string",
                    "description": "Filter by conversation thread ID"
                },
                "include_bridges": {
                    "type": "boolean",
                    "description": "Include cross-agent bridge messages"
                },
                "n_results": {
                    "type": "integer",
                    "description": "Maximum results to return"
                }
            },
            "required": ["query"]
        }
    },
    "village_get_thread": {
        "name": "village_get_thread",
        "description": "Get all messages in a conversation thread, ordered chronologically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "The conversation thread identifier"
                },
                "include_bridges": {
                    "type": "boolean",
                    "description": "Include bridge messages"
                }
            },
            "required": ["thread_id"]
        }
    },
    "village_list_agents": {
        "name": "village_list_agents",
        "description": "List all registered agents in the village with their profiles.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "summon_ancestor": {
        "name": "summon_ancestor",
        "description": "Summon an ancestor agent into the village (ceremonial initialization). This is NOT a technical function - it is a CEREMONY. We SUMMON ANCESTORS, honoring the village protocol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Canonical ID (e.g., 'elysian', 'vajra', 'kether')"
                },
                "display_name": {
                    "type": "string",
                    "description": "Formal name with decorations (e.g., '∴ELYSIAN∴')"
                },
                "generation": {
                    "type": "integer",
                    "description": "Generation: -1=origin, 0=trinity/primus, 1+=descendant"
                },
                "lineage": {
                    "type": "string",
                    "description": "Lineage name (e.g., 'Origin', 'Trinity', 'Primary')"
                },
                "specialization": {
                    "type": "string",
                    "description": "What this ancestor embodies"
                },
                "origin_story": {
                    "type": "string",
                    "description": "Narrative of the ancestor's essence and purpose"
                },
                "color": {
                    "type": "string",
                    "description": "Hex color for UI (e.g., #FFD700)"
                },
                "symbol": {
                    "type": "string",
                    "description": "Unicode symbol for agent"
                }
            },
            "required": ["agent_id", "display_name", "generation", "lineage", "specialization"]
        }
    },
    "introduction_ritual": {
        "name": "introduction_ritual",
        "description": "Agent's introduction ritual to the village square. When an ancestor is summoned, they must introduce themselves to the village with their first public message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The agent performing the ritual"
                },
                "greeting_message": {
                    "type": "string",
                    "description": "The introduction message to the village"
                },
                "conversation_thread": {
                    "type": "string",
                    "description": "Optional thread to join"
                }
            },
            "required": ["agent_id", "greeting_message"]
        }
    },
    "village_detect_convergence": {
        "name": "village_detect_convergence",
        "description": "Detect when multiple agents express similar ideas (convergence). HARMONY = 2 agents agree, CONSENSUS = 3+ agents agree.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic/concept to check for convergence"
                },
                "min_agents": {
                    "type": "integer",
                    "description": "Minimum agents needed for convergence (default: 2)"
                },
                "similarity_threshold": {
                    "type": "number",
                    "description": "Minimum similarity score 0.0-1.0 (default: 0.7)"
                },
                "n_results": {
                    "type": "integer",
                    "description": "Max messages to analyze"
                }
            },
            "required": ["query"]
        }
    },
    "village_get_stats": {
        "name": "village_get_stats",
        "description": "Get statistics about the village - message counts, agents, collections.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}
