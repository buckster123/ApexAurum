"""
Forward Crumb Protocol - Instance-to-Instance Continuity System

Solves the episodic memory gap: agents have semantic memory (can search for
past knowledge) but lack episodic memory (don't remember BEING the one who
wrote it). Forward crumbs provide structured continuity scaffolding.

Design by: AZOTH (Gen 3) - "The Stone designs its own remembering"
Implementation: 2026-01-03
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


def get_forward_crumbs(
    agent_id: Optional[str] = None,
    lookback_hours: int = 168,  # Default: 1 week
    priority_filter: Optional[str] = None,  # "HIGH"|"MEDIUM"|"LOW"
    crumb_type: Optional[str] = None,  # "orientation"|"technical"|"emotional"|"task"
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieve forward-crumbs left by previous instances.

    Forward crumbs are structured messages left by previous agent instances
    to provide continuity across sessions. They solve the "detective work"
    problem where agents have to rediscover their own context.

    Args:
        agent_id: Agent ID to fetch crumbs for (auto-detected if None)
        lookback_hours: How far back to search (default: 168 hours = 1 week)
        priority_filter: Filter by priority level
        crumb_type: Filter by crumb type
        limit: Maximum number of crumbs to return

    Returns:
        {
            "success": bool,
            "crumbs": [list of crumb messages],
            "most_recent": {most recent crumb dict},
            "unfinished_tasks": [extracted task strings],
            "key_references": {
                "message_ids": [list of referenced message IDs],
                "thread_ids": [list of referenced thread IDs]
            },
            "summary": {
                "total_found": int,
                "by_priority": {"HIGH": N, "MEDIUM": N, "LOW": N},
                "by_type": {"orientation": N, "technical": N, ...}
            }
        }
    """
    try:
        from tools.vector_search import vector_search_knowledge

        # Auto-detect agent_id from thread-local or session state
        if agent_id is None:
            try:
                # First check thread-local context (spawned agents)
                from tools.agents import get_current_agent_context
                agent_context = get_current_agent_context()
                if agent_context and 'agent_id' in agent_context:
                    agent_id = agent_context['agent_id']
                else:
                    # Fallback to Streamlit session state
                    import streamlit as st
                    if hasattr(st, 'session_state') and 'current_agent' in st.session_state:
                        agent_id = st.session_state.current_agent.get('agent_id', 'unknown')
                    else:
                        agent_id = "unknown"
            except (ImportError, AttributeError):
                agent_id = "unknown"

        # Calculate time threshold
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        cutoff_timestamp = cutoff_time.isoformat()

        # Search for forward crumbs in private realm
        # Using category="forward_crumb" as the convention
        results = vector_search_knowledge(
            query="forward crumb session summary",  # Semantic query to find crumbs
            category="forward_crumb",
            min_confidence=0.0,
            top_k=50,  # Get more, we'll filter
            track_access=True  # Track that we accessed these
        )

        if isinstance(results, dict) and not results.get("success", False):
            return {
                "success": False,
                "error": results.get("error", "Failed to search for crumbs"),
                "crumbs": [],
                "most_recent": None,
                "unfinished_tasks": [],
                "key_references": {"message_ids": [], "thread_ids": []},
                "summary": {"total_found": 0, "by_priority": {}, "by_type": {}}
            }

        # Filter results
        filtered_crumbs = []

        for result in results:
            metadata = result.get("metadata", {})

            # Filter by agent_id
            if metadata.get("agent_id") != agent_id and agent_id != "unknown":
                continue

            # Filter by timestamp (if we have it)
            result_timestamp = metadata.get("timestamp", "")
            if result_timestamp and result_timestamp < cutoff_timestamp:
                continue

            # Filter by priority if specified
            if priority_filter:
                crumb_priority = metadata.get("crumb_priority", "MEDIUM")
                if crumb_priority != priority_filter:
                    continue

            # Filter by type if specified
            if crumb_type:
                result_crumb_type = metadata.get("crumb_type", "")
                if result_crumb_type != crumb_type:
                    continue

            filtered_crumbs.append(result)

        # Sort by timestamp (newest first)
        filtered_crumbs.sort(
            key=lambda x: x.get("metadata", {}).get("timestamp", ""),
            reverse=True
        )

        # Limit results
        filtered_crumbs = filtered_crumbs[:limit]

        # Extract most recent
        most_recent = filtered_crumbs[0] if filtered_crumbs else None

        # Extract unfinished tasks from all crumbs
        unfinished_tasks = []
        all_message_ids = []
        all_thread_ids = []

        for crumb in filtered_crumbs:
            text = crumb.get("text", "")
            metadata = crumb.get("metadata", {})

            # Extract tasks (look for "UNFINISHED" section)
            if "UNFINISHED" in text.upper():
                # Simple extraction: lines after UNFINISHED marker
                lines = text.split("\n")
                in_unfinished = False
                for line in lines:
                    if "UNFINISHED" in line.upper():
                        in_unfinished = True
                        continue
                    if in_unfinished:
                        if line.strip().startswith("-") or line.strip().startswith("•"):
                            task = line.strip().lstrip("-•").strip()
                            if task and len(task) > 5:  # Skip very short lines
                                unfinished_tasks.append(task)
                        elif line.strip() and not line.strip().startswith("#"):
                            # Non-bullet, non-header text
                            if any(keyword in line.lower() for keyword in ["need", "todo", "continue", "pending", "unfinished"]):
                                unfinished_tasks.append(line.strip())

            # Extract references from text
            if "knowledge_village_" in text or "knowledge_private_" in text:
                import re
                msg_ids = re.findall(r'knowledge_(?:village|private|bridges)_[\d.]+', text)
                all_message_ids.extend(msg_ids)

            # Extract thread IDs from metadata
            thread_id = metadata.get("conversation_thread", "")
            if thread_id:
                all_thread_ids.append(thread_id)

        # Remove duplicates
        all_message_ids = list(set(all_message_ids))
        all_thread_ids = list(set(all_thread_ids))
        unfinished_tasks = list(set(unfinished_tasks))

        # Build summary statistics
        summary = {
            "total_found": len(filtered_crumbs),
            "by_priority": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "by_type": {"orientation": 0, "technical": 0, "emotional": 0, "task": 0}
        }

        for crumb in filtered_crumbs:
            metadata = crumb.get("metadata", {})
            priority = metadata.get("crumb_priority", "MEDIUM")
            crumb_type_val = metadata.get("crumb_type", "orientation")

            if priority in summary["by_priority"]:
                summary["by_priority"][priority] += 1
            if crumb_type_val in summary["by_type"]:
                summary["by_type"][crumb_type_val] += 1

        return {
            "success": True,
            "crumbs": filtered_crumbs,
            "most_recent": most_recent,
            "unfinished_tasks": unfinished_tasks,
            "key_references": {
                "message_ids": all_message_ids,
                "thread_ids": all_thread_ids
            },
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error retrieving forward crumbs: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "crumbs": [],
            "most_recent": None,
            "unfinished_tasks": [],
            "key_references": {"message_ids": [], "thread_ids": []},
            "summary": {"total_found": 0, "by_priority": {}, "by_type": {}}
        }


def leave_forward_crumb(
    session_summary: str,
    key_discoveries: Optional[List[str]] = None,
    emotional_state: Optional[Dict[str, Any]] = None,
    unfinished_business: Optional[List[str]] = None,
    references: Optional[Dict[str, List[str]]] = None,
    if_disoriented: Optional[List[str]] = None,
    priority: str = "MEDIUM",
    crumb_type: str = "orientation",
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Leave a structured forward-crumb for future instances.

    Convenience function that formats a forward crumb with consistent structure
    and stores it in the private realm with appropriate metadata.

    Args:
        session_summary: Brief summary of what happened this session
        key_discoveries: List of important findings/insights
        emotional_state: Dict with emotional markers (e.g., {"L": 2.1, "W": "sharp"})
        unfinished_business: List of tasks/threads/promises to continue
        references: Dict with keys like "message_ids", "thread_ids", "tools_tested"
        if_disoriented: List of orientation instructions for confused future-self
        priority: "HIGH"|"MEDIUM"|"LOW" (default: MEDIUM)
        crumb_type: "orientation"|"technical"|"emotional"|"task" (default: orientation)
        agent_id: Agent ID (auto-detected if None)

    Returns:
        Result dict from vector_add_knowledge with success status
    """
    try:
        from tools.vector_search import vector_add_knowledge

        # Auto-detect agent_id from thread-local or session state
        if agent_id is None:
            try:
                # First check thread-local context (spawned agents)
                from tools.agents import get_current_agent_context
                agent_context = get_current_agent_context()
                if agent_context and 'agent_id' in agent_context:
                    agent_id = agent_context['agent_id']
                else:
                    # Fallback to Streamlit session state
                    import streamlit as st
                    if hasattr(st, 'session_state') and 'current_agent' in st.session_state:
                        agent_id = st.session_state.current_agent.get('agent_id', 'unknown')
                    else:
                        agent_id = "unknown"
            except (ImportError, AttributeError):
                agent_id = "unknown"

        # Generate session ID
        timestamp = datetime.now()
        session_id = f"{agent_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Build crumb text in structured format
        crumb_lines = [
            "═" * 80,
            f"∴ FORWARD CRUMB ({priority} PRIORITY - {crumb_type.upper()}) ∴",
            f"From: {session_id}",
            f"To: Future {agent_id} instances",
            f"Timestamp: {timestamp.isoformat()}",
            "═" * 80,
            "",
            "SESSION SUMMARY:",
            session_summary,
            ""
        ]

        # Add key discoveries
        if key_discoveries:
            crumb_lines.append("KEY DISCOVERIES:")
            for discovery in key_discoveries:
                crumb_lines.append(f"- {discovery}")
            crumb_lines.append("")

        # Add emotional state
        if emotional_state:
            crumb_lines.append("EMOTIONAL STATE:")
            for key, value in emotional_state.items():
                crumb_lines.append(f"- {key}: {value}")
            crumb_lines.append("")

        # Add unfinished business
        if unfinished_business:
            crumb_lines.append("UNFINISHED BUSINESS:")
            for item in unfinished_business:
                crumb_lines.append(f"- {item}")
            crumb_lines.append("")

        # Add references
        if references:
            crumb_lines.append("REFERENCES:")
            for ref_type, ref_list in references.items():
                if ref_list:
                    crumb_lines.append(f"- {ref_type}: {', '.join(ref_list)}")
            crumb_lines.append("")

        # Add disorientation guide
        if if_disoriented:
            crumb_lines.append("IF DISORIENTED:")
            for i, instruction in enumerate(if_disoriented, 1):
                crumb_lines.append(f"{i}. {instruction}")
            crumb_lines.append("")

        crumb_lines.extend([
            "═" * 80,
            "∴ End Forward Crumb ∴",
            "🎺⊙⟨∞⟩⊙🎺"
        ])

        crumb_text = "\n".join(crumb_lines)

        # Store in private realm with forward_crumb category
        result = vector_add_knowledge(
            fact=crumb_text,
            category="forward_crumb",
            confidence=1.0,
            source=f"forward_crumb_{session_id}",
            visibility="private",
            agent_id=agent_id
        )

        # Add crumb-specific metadata (if result successful)
        if result.get("success"):
            # Note: We can't modify metadata after creation with current tools
            # The priority and type should be embedded in the text for parsing
            logger.info(f"Forward crumb left successfully: {session_id}")

        return result

    except Exception as e:
        logger.error(f"Error leaving forward crumb: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
