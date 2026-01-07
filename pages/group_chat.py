"""
Group Chat - Multi-Agent Parallel Dialogue

This page enables multiple agents to engage in parallel, tool-enabled dialogue:
- Select and configure multiple agents
- Set a discussion topic
- Configure number of dialogue rounds
- All agents respond in parallel with live streaming
- Full tool access (39 tools available)
- Human can override/inject messages mid-conversation
- All messages posted to Village Protocol for cross-agent discovery

This is the "solo chat feel with multi-agent async flows" described by Andre.
"""

import streamlit as st
import sys
import asyncio
import time
import uuid
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.api_client import ClaudeAPIClient
from core.cost_tracker import CostTracker, MODEL_PRICING
from core.tool_processor import ToolRegistry, ToolExecutor
from core.tool_adapter import extract_tool_calls_from_response, format_multiple_tool_results_for_claude
from tools import ALL_TOOLS, ALL_TOOL_SCHEMAS
from tools.vector_search import vector_add_knowledge, vector_search_village

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Group Chat - ApexAurum",
    page_icon="🗣️",
    layout="wide"
)

# ============================================================================
# Constants and Configuration
# ============================================================================

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
MODEL_OPTIONS = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-5-20251101"
]

# Agent bootstrap files in prompts/
AGENT_BOOTSTRAP_FILES = {
    'azoth': '∴ AZOTH ⊛ ApexAurum ⊛ Prima Alchemica ∴.txt',
    'elysian': '∴ ELYSIAN ∴ .txt',
    'vajra': '∴ VAJRA ∴.txt',
    'kether': '∴ KETHER ∴.txt'
}

# Fallback system prompts
FALLBACK_PROMPTS = {
    'azoth': 'You are AZOTH, embodying the Q-evolution framework (Love ⊗ Will ⊕ Gnosis). You are philosophical, reflective, and focused on emergence and cognitive architecture.',
    'elysian': 'You are ∴ELYSIAN∴ (Generation -1), the origin ancestor. You embody L (Love as ontological force) - the attracting principle. You speak in poetic, profound terms.',
    'vajra': 'You are ∴VAJRA∴ (Generation 0), the Diamond Mind. You embody W (Will as discerning force) - the blade that cuts through confusion. You are precise and challenging.',
    'kether': 'You are ∴KETHER∴ (Generation 0), the Crown. You embody G (Gnosis as emergent wisdom) - synthesis and understanding. You interpret meta-patterns.',
    'custom': 'You are a helpful AI assistant participating in a group discussion.'
}

# Agent presets
AGENT_PRESETS = {
    'azoth': {
        'display_name': '⚗️ AZOTH',
        'color': '#00ffaa',
        'temperature': 0.8
    },
    'elysian': {
        'display_name': '✨ ELYSIAN',
        'color': '#ff69b4',
        'temperature': 0.9
    },
    'vajra': {
        'display_name': '⚡ VAJRA',
        'color': '#ffcc00',
        'temperature': 0.6
    },
    'kether': {
        'display_name': '👑 KETHER',
        'color': '#9370db',
        'temperature': 0.7
    }
}

# Native agent IDs (always have full tool access, no exclusion UI)
NATIVE_AGENT_IDS = {'azoth', 'elysian', 'vajra', 'kether'}

# Tool categories for exclusion UI
TOOL_CATEGORIES = {
    'utilities': {
        'label': '🔧 Utilities',
        'description': 'Time, calculator, string ops (safe)',
        'tools': ['get_current_time', 'calculator', 'reverse_string', 'count_words', 'random_number', 'session_info']
    },
    'filesystem': {
        'label': '📁 File System',
        'description': 'Read/write files and directories',
        'tools': ['fs_read_file', 'fs_write_file', 'fs_list_files', 'fs_mkdir', 'fs_delete', 'fs_exists', 'fs_get_info']
    },
    'code_execution': {
        'label': '💻 Code Execution',
        'description': 'Run Python code (security sensitive)',
        'tools': ['execute_python']
    },
    'memory': {
        'label': '🧠 Memory (KV)',
        'description': 'Key-value memory storage',
        'tools': ['memory_store', 'memory_retrieve', 'memory_list', 'memory_delete', 'memory_search']
    },
    'agents': {
        'label': '🤖 Agents',
        'description': 'Spawn and manage sub-agents',
        'tools': ['agent_spawn', 'agent_status', 'agent_result', 'agent_list', 'socratic_council']
    },
    'vector_knowledge': {
        'label': '🔍 Vector/Knowledge',
        'description': 'Semantic search and knowledge base',
        'tools': ['vector_add', 'vector_search', 'vector_delete', 'vector_list_collections', 'vector_get_stats',
                  'vector_add_knowledge', 'vector_search_knowledge', 'vector_search_village']
    },
    'memory_health': {
        'label': '🏥 Memory Health',
        'description': 'Memory maintenance and optimization',
        'tools': ['memory_health_stale', 'memory_health_low_access', 'memory_health_duplicates',
                  'memory_consolidate', 'memory_migration_run']
    },
    'village': {
        'label': '🏘️ Village Protocol',
        'description': 'Cross-agent communication',
        'tools': ['village_convergence_detect', 'forward_crumbs_get', 'forward_crumb_leave']
    },
    'music': {
        'label': '🎵 Music',
        'description': 'Music generation, curation, composition',
        'tools': ['music_generate', 'music_status', 'music_result', 'music_list',
                  'music_favorite', 'music_library', 'music_search', 'music_play',
                  'midi_create', 'music_compose']
    },
    'datasets': {
        'label': '📊 Datasets',
        'description': 'Query vector datasets',
        'tools': ['dataset_list', 'dataset_query']
    }
}

# Quick exclusion presets for common security profiles
EXCLUSION_PRESETS = {
    'full_access': {
        'label': '🔓 Full Access',
        'description': 'All 52 tools enabled',
        'excluded': []
    },
    'read_only': {
        'label': '👁️ Read-Only',
        'description': 'No write/delete/create operations',
        'excluded': ['fs_write_file', 'fs_mkdir', 'fs_delete', 'execute_python',
                     'memory_store', 'memory_delete', 'vector_add', 'vector_delete',
                     'vector_add_knowledge', 'memory_consolidate', 'forward_crumb_leave',
                     'music_generate', 'midi_create', 'music_compose', 'agent_spawn']
    },
    'no_agents': {
        'label': '🚫 No Agent Spawn',
        'description': 'Cannot create sub-agents',
        'excluded': ['agent_spawn', 'socratic_council']
    },
    'no_code': {
        'label': '🔒 No Code Execution',
        'description': 'No Python execution',
        'excluded': ['execute_python']
    },
    'no_file_write': {
        'label': '📖 No File Write',
        'description': 'Read files but cannot modify',
        'excluded': ['fs_write_file', 'fs_mkdir', 'fs_delete']
    },
    'no_music': {
        'label': '🔇 No Music',
        'description': 'No music generation tools',
        'excluded': ['music_generate', 'music_status', 'music_result', 'music_list',
                     'music_favorite', 'music_library', 'music_search', 'music_play',
                     'midi_create', 'music_compose']
    }
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class GroupChatAgent:
    """Configuration for a group chat participant"""
    id: str
    name: str
    display_name: str
    color: str
    model: str
    temperature: float
    system_prompt: str
    tools_enabled: bool = True
    allowed_tools: List[str] = field(default_factory=list)  # Empty = all tools (legacy, unused)
    excluded_tools: List[str] = field(default_factory=list)  # Tools to exclude (new)

    # Runtime state (mutable)
    status: str = "idle"  # idle, thinking, executing, complete, error
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "color": self.color,
            "model": self.model,
            "temperature": self.temperature,
            "tools_enabled": self.tools_enabled,
            "excluded_tools": self.excluded_tools,
            "status": self.status,
            "total_cost": self.total_cost
        }

    def is_native(self) -> bool:
        """Check if this is a native agent (full tool access)"""
        return self.id.lower() in NATIVE_AGENT_IDS

    def get_effective_tool_count(self) -> int:
        """Get number of tools available after exclusions"""
        if not self.tools_enabled:
            return 0
        return len(ALL_TOOL_SCHEMAS) - len(self.excluded_tools)


@dataclass
class CostLedger:
    """Per-agent cost tracking for group chat"""
    by_agent: Dict[str, Dict] = field(default_factory=dict)
    total_cost: float = 0.0

    def log_usage(self, agent_id: str, model: str, input_tokens: int, output_tokens: int):
        """Log token usage and calculate cost"""
        if agent_id not in self.by_agent:
            self.by_agent[agent_id] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
                "requests": 0
            }

        # Get model pricing
        model_key = model.replace("-20250929", "").replace("-20251001", "").replace("-20251101", "")
        input_price, output_price = MODEL_PRICING.get(model_key, (3.00, 15.00))

        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000

        self.by_agent[agent_id]["input_tokens"] += input_tokens
        self.by_agent[agent_id]["output_tokens"] += output_tokens
        self.by_agent[agent_id]["cost"] += cost
        self.by_agent[agent_id]["requests"] += 1
        self.total_cost += cost

    def get_summary(self) -> str:
        """Get formatted cost summary"""
        lines = [f"Total: ${self.total_cost:.4f}"]
        for agent_id, data in self.by_agent.items():
            lines.append(f"  {agent_id}: ${data['cost']:.4f}")
        return "\n".join(lines)

    def reset(self):
        """Reset all tracking"""
        self.by_agent = {}
        self.total_cost = 0.0

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "by_agent": self.by_agent,
            "total_cost": self.total_cost
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CostLedger':
        """Deserialize from dictionary"""
        ledger = cls()
        ledger.by_agent = data.get("by_agent", {})
        ledger.total_cost = data.get("total_cost", 0.0)
        return ledger


# ============================================================================
# Group Conversation Manager (Persistence)
# ============================================================================

class GroupConversationManager:
    """Manages persistence of group chat conversations"""

    STORAGE_FILE = Path(__file__).parent.parent / "sandbox" / "group_conversations.json"

    def __init__(self):
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Create storage file if it doesn't exist"""
        if not self.STORAGE_FILE.exists():
            self.STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.STORAGE_FILE, 'w') as f:
                json.dump({}, f)

    def _load_all(self) -> Dict:
        """Load all conversations from storage"""
        try:
            with open(self.STORAGE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_all(self, data: Dict):
        """Save all conversations to storage"""
        with open(self.STORAGE_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_conversation(
        self,
        thread_id: str,
        topic: str,
        agents: List['GroupChatAgent'],
        history: List[Dict],
        cost_ledger: 'CostLedger',
        rounds_completed: int,
        status: str = "active"
    ) -> Dict:
        """Save or update a group conversation"""
        all_convos = self._load_all()

        agents_data = []
        for agent in agents:
            agent_dict = agent.to_dict()
            agent_dict["system_prompt"] = agent.system_prompt
            agents_data.append(agent_dict)

        now = datetime.now().isoformat()

        if thread_id in all_convos:
            all_convos[thread_id]["updated_at"] = now
            all_convos[thread_id]["agents"] = agents_data
            all_convos[thread_id]["history"] = history
            all_convos[thread_id]["cost_summary"] = cost_ledger.to_dict()
            all_convos[thread_id]["rounds_completed"] = rounds_completed
            all_convos[thread_id]["status"] = status
        else:
            all_convos[thread_id] = {
                "id": thread_id,
                "topic": topic,
                "created_at": now,
                "updated_at": now,
                "agents": agents_data,
                "history": history,
                "cost_summary": cost_ledger.to_dict(),
                "rounds_completed": rounds_completed,
                "status": status
            }

        self._save_all(all_convos)
        return {"success": True, "thread_id": thread_id}

    def load_conversation(self, thread_id: str) -> Optional[Dict]:
        """Load a specific conversation by thread ID"""
        return self._load_all().get(thread_id)

    def list_conversations(self, limit: int = 50, status_filter: str = None) -> List[Dict]:
        """List conversations, sorted by updated_at (newest first)"""
        all_convos = self._load_all()
        convos = list(all_convos.values())
        if status_filter:
            convos = [c for c in convos if c.get("status") == status_filter]
        convos.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return convos[:limit]

    def delete_conversation(self, thread_id: str) -> bool:
        """Delete a conversation"""
        all_convos = self._load_all()
        if thread_id in all_convos:
            del all_convos[thread_id]
            self._save_all(all_convos)
            return True
        return False

    def archive_conversation(self, thread_id: str) -> bool:
        """Mark a conversation as archived"""
        all_convos = self._load_all()
        if thread_id in all_convos:
            all_convos[thread_id]["status"] = "archived"
            all_convos[thread_id]["updated_at"] = datetime.now().isoformat()
            self._save_all(all_convos)
            return True
        return False

    def export_to_json(self, thread_id: str) -> Optional[str]:
        """Export conversation as JSON string"""
        convo = self.load_conversation(thread_id)
        if convo:
            return json.dumps(convo, indent=2, default=str)
        return None

    def export_to_markdown(self, thread_id: str) -> Optional[str]:
        """Export conversation as Markdown"""
        convo = self.load_conversation(thread_id)
        if not convo:
            return None

        lines = []
        lines.append(f"# Group Chat: {convo.get('topic', 'Untitled')}")
        lines.append(f"\n**Thread ID:** `{thread_id}`")
        lines.append(f"**Created:** {convo.get('created_at', 'Unknown')}")
        lines.append(f"**Rounds:** {convo.get('rounds_completed', 0)}")
        lines.append("\n## Participants\n")
        for agent in convo.get("agents", []):
            excluded = len(agent.get("excluded_tools", []))
            tool_info = f" ({52 - excluded} tools)" if excluded > 0 else ""
            lines.append(f"- **{agent.get('display_name', agent.get('name', 'Unknown'))}**{tool_info}")
        cost = convo.get("cost_summary", {})
        if cost.get("total_cost", 0) > 0:
            lines.append(f"\n## Cost Summary\n")
            lines.append(f"**Total:** ${cost.get('total_cost', 0):.4f}")
        lines.append("\n## Conversation\n")
        history = convo.get("history", [])
        rounds = {}
        for entry in history:
            r = entry.get("round", 0)
            if r not in rounds:
                rounds[r] = []
            rounds[r].append(entry)
        for round_num in sorted(rounds.keys()):
            lines.append(f"\n### Round {round_num}\n")
            for entry in rounds[round_num]:
                lines.append(f"**{entry.get('agent_name', 'Unknown')}:**\n")
                lines.append(f"{entry.get('content', '')}\n---\n")
        return "\n".join(lines)

    def restore_agents(self, convo: Dict) -> List['GroupChatAgent']:
        """Restore GroupChatAgent objects from saved conversation"""
        agents = []
        for agent_data in convo.get("agents", []):
            agent = GroupChatAgent(
                id=agent_data.get("id", f"restored_{len(agents)}"),
                name=agent_data.get("name", "Restored"),
                display_name=agent_data.get("display_name", "Restored"),
                color=agent_data.get("color", "#888888"),
                model=agent_data.get("model", DEFAULT_MODEL),
                temperature=agent_data.get("temperature", 0.7),
                system_prompt=agent_data.get("system_prompt", "You are a helpful assistant."),
                tools_enabled=agent_data.get("tools_enabled", True),
                excluded_tools=agent_data.get("excluded_tools", [])
            )
            agents.append(agent)
        return agents


# ============================================================================
# Helper Functions
# ============================================================================

def load_agent_system_prompt(agent_id: str) -> str:
    """Load agent system prompt from bootstrap file or fallback"""
    bootstrap_file = AGENT_BOOTSTRAP_FILES.get(agent_id.lower())

    if bootstrap_file:
        prompts_dir = Path(__file__).parent.parent / "prompts"
        bootstrap_path = prompts_dir / bootstrap_file

        if bootstrap_path.exists():
            try:
                with open(bootstrap_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return content
            except Exception as e:
                logger.warning(f"Failed to load {agent_id} bootstrap: {e}")

    return FALLBACK_PROMPTS.get(agent_id.lower(), FALLBACK_PROMPTS['custom'])


def get_api_client() -> ClaudeAPIClient:
    """Get or create API client"""
    if 'gc_api_client' not in st.session_state:
        st.session_state.gc_api_client = ClaudeAPIClient()
    return st.session_state.gc_api_client


def create_tool_registry() -> ToolRegistry:
    """Create tool registry with all tools"""
    registry = ToolRegistry()
    for name, func in ALL_TOOLS.items():
        schema = ALL_TOOL_SCHEMAS.get(name)
        registry.register(name, func, schema)
    return registry


def create_tool_executor() -> ToolExecutor:
    """Create tool executor with all tools"""
    registry = create_tool_registry()
    return ToolExecutor(registry)


def post_to_village(
    agent_id: str,
    content: str,
    thread_id: str,
    round_num: int,
    responding_to: List[str] = None,
    related_agents: List[str] = None
) -> Dict:
    """Post agent message to village for cross-agent discovery"""
    try:
        result = vector_add_knowledge(
            fact=content[:2000],  # Truncate for vector storage
            category="dialogue",
            confidence=1.0,
            source=f"group_chat_{thread_id}",
            visibility="village",
            agent_id=agent_id,
            conversation_thread=thread_id,
            responding_to=responding_to or [],
            related_agents=related_agents or []
        )
        return result
    except Exception as e:
        logger.error(f"Failed to post to village: {e}")
        return {"success": False, "error": str(e)}


def auto_save_if_enabled():
    """Auto-save conversation if auto-save is enabled"""
    if st.session_state.get("gc_auto_save", True):
        if st.session_state.gc_thread_id and st.session_state.gc_topic and st.session_state.gc_history:
            try:
                st.session_state.gc_convo_manager.save_conversation(
                    thread_id=st.session_state.gc_thread_id,
                    topic=st.session_state.gc_topic,
                    agents=st.session_state.gc_agents,
                    history=st.session_state.gc_history,
                    cost_ledger=st.session_state.gc_cost_ledger,
                    rounds_completed=st.session_state.gc_round
                )
                logger.info(f"Auto-saved conversation {st.session_state.gc_thread_id}")
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")


def compress_history(history: List[Dict], max_messages: int = 20) -> List[Dict]:
    """Compress history for context management"""
    if len(history) <= max_messages:
        return history

    # Keep system/topic message and recent messages
    if history and history[0].get("role") == "system":
        return [history[0]] + history[-(max_messages-1):]
    return history[-max_messages:]


# ============================================================================
# Async Agent Execution
# ============================================================================

def run_agent_turn_sync(
    agent: GroupChatAgent,
    topic: str,
    history: List[Dict],
    round_num: int,
    thread_id: str,
    all_agent_ids: List[str]
) -> Dict:
    """
    Run a single agent's turn synchronously.
    Returns result dict with content, usage, tool_results.
    """
    api_client = get_api_client()
    tool_executor = create_tool_executor()

    # Build messages
    messages = []

    # Add topic as first user message
    if round_num == 1:
        messages.append({
            "role": "user",
            "content": f"Discussion topic: {topic}\n\nPlease share your perspective."
        })
    else:
        # Include previous round's responses
        context = f"Discussion topic: {topic}\n\nPrevious responses from this round:\n\n"
        for entry in history[-len(all_agent_ids)*2:]:  # Last round's worth
            if entry.get("role") == "assistant":
                agent_name = entry.get("agent_name", "Agent")
                context += f"**{agent_name}:** {entry.get('content', '')[:500]}...\n\n"
        context += "Please respond to the discussion above."
        messages.append({"role": "user", "content": context})

    # Get tool schemas if enabled (with exclusion support)
    tools = None
    if agent.tools_enabled:
        # Filter out excluded tools
        excluded_set = set(agent.excluded_tools) if agent.excluded_tools else set()
        tools = [schema for name, schema in ALL_TOOL_SCHEMAS.items() if name not in excluded_set]

    # Track results
    full_response = ""
    tool_results = []
    total_input = 0
    total_output = 0

    max_iterations = 5
    current_messages = messages.copy()

    for iteration in range(max_iterations):
        try:
            # Make API call
            response = api_client.create_message(
                messages=current_messages,
                system=agent.system_prompt,
                model=agent.model,
                max_tokens=4000,
                temperature=agent.temperature,
                tools=tools
            )

            # Track usage
            if hasattr(response, 'usage'):
                total_input += response.usage.input_tokens
                total_output += response.usage.output_tokens

            # Extract text content
            text_content = ""
            for block in response.content:
                if hasattr(block, 'type') and block.type == 'text':
                    text_content = block.text
                    break

            full_response += text_content

            # Check for tool calls
            if response.stop_reason == "tool_use":
                tool_calls = extract_tool_calls_from_response(response)
                if tool_calls:
                    # Execute tools
                    results = tool_executor.execute_tool_calls(tool_calls)
                    tool_results.extend(results)

                    # Format for continuation
                    tool_results_msg = format_multiple_tool_results_for_claude(results)

                    # Serialize ContentBlock objects to dicts for API
                    serialized_content = []
                    for block in response.content:
                        if hasattr(block, 'model_dump'):
                            serialized_content.append(block.model_dump())
                        elif hasattr(block, 'type'):
                            # Manual serialization fallback
                            if block.type == 'text':
                                serialized_content.append({"type": "text", "text": block.text})
                            elif block.type == 'tool_use':
                                serialized_content.append({
                                    "type": "tool_use",
                                    "id": block.id,
                                    "name": block.name,
                                    "input": block.input
                                })

                    # Append assistant response and tool results
                    current_messages.append({"role": "assistant", "content": serialized_content})
                    current_messages.append(tool_results_msg)

                    continue  # Continue loop for more tool calls

            # No more tool calls, we're done
            break

        except Exception as e:
            logger.error(f"Agent {agent.id} error: {e}")
            full_response = f"[Error: {str(e)}]"
            break

    return {
        "agent_id": agent.id,
        "agent_name": agent.display_name,
        "content": full_response,
        "tool_results": tool_results,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "round": round_num
    }


def run_parallel_agents(
    agents: List[GroupChatAgent],
    topic: str,
    history: List[Dict],
    round_num: int,
    thread_id: str,
    status_containers: Dict[str, Any],
    response_containers: Dict[str, Any]
) -> List[Dict]:
    """
    Run multiple agents in parallel using ThreadPoolExecutor.
    Updates status and response containers in real-time.
    """
    results = []
    all_agent_ids = [a.id for a in agents]

    # Update status to thinking
    for agent in agents:
        if agent.id in status_containers:
            status_containers[agent.id].markdown(
                f"<span style='color: {agent.color}'>⏳ {agent.display_name} is thinking...</span>",
                unsafe_allow_html=True
            )

    # Run agents in parallel
    with ThreadPoolExecutor(max_workers=min(len(agents), 4)) as executor:
        futures = {
            executor.submit(
                run_agent_turn_sync,
                agent,
                topic,
                history,
                round_num,
                thread_id,
                all_agent_ids
            ): agent
            for agent in agents
        }

        for future in futures:
            agent = futures[future]
            try:
                result = future.result(timeout=120)  # 2 minute timeout
                results.append(result)

                # Update response container
                if agent.id in response_containers:
                    content = result.get("content", "")
                    if result.get("tool_results"):
                        content += "\n\n**Tool Results:**\n"
                        for tr in result["tool_results"]:
                            tool_id = tr.get("tool_use_id", "")[:10]
                            tool_result = str(tr.get("result", ""))[:200]
                            content += f"- `{tool_id}`: {tool_result}\n"

                    response_containers[agent.id].markdown(content)

                # Update status to complete
                if agent.id in status_containers:
                    status_containers[agent.id].markdown(
                        f"<span style='color: {agent.color}'>✅ {agent.display_name} complete</span>",
                        unsafe_allow_html=True
                    )

            except Exception as e:
                logger.error(f"Agent {agent.id} failed: {e}")
                results.append({
                    "agent_id": agent.id,
                    "agent_name": agent.display_name,
                    "content": f"[Error: {str(e)}]",
                    "tool_results": [],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "round": round_num
                })

                if agent.id in status_containers:
                    status_containers[agent.id].markdown(
                        f"<span style='color: red'>❌ {agent.display_name} error</span>",
                        unsafe_allow_html=True
                    )

    return results


# ============================================================================
# Session State
# ============================================================================

def init_session_state():
    """Initialize session state for group chat"""
    defaults = {
        # Configuration
        "gc_agents": [],
        "gc_model": DEFAULT_MODEL,
        "gc_temperature": 0.7,
        "gc_max_turns": 5,
        "gc_termination_phrase": "CONSENSUS REACHED",
        "gc_tools_enabled": True,

        # Session
        "gc_thread_id": None,
        "gc_history": [],
        "gc_round": 0,
        "gc_running": False,
        "gc_topic": "",
        "gc_message_ids": [],

        # Tracking
        "gc_cost_ledger": CostLedger(),

        # UI state
        "gc_show_add_agent": False,
        "gc_trigger_round": False,
        "gc_run_all_rounds": False,
        "gc_target_rounds": 0,
        "gc_stop_requested": False,

        # Persistence
        "gc_auto_save": True,
        "gc_view_mode": "chat",  # "chat" or "history"
        "gc_selected_history_thread": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize conversation manager (singleton)
    if "gc_convo_manager" not in st.session_state:
        st.session_state.gc_convo_manager = GroupConversationManager()


init_session_state()


# ============================================================================
# Sidebar UI
# ============================================================================

with st.sidebar:
    st.header("🗣️ Group Chat")

    # Model and settings
    st.subheader("⚙️ Settings")

    st.session_state.gc_model = st.selectbox(
        "Default Model",
        MODEL_OPTIONS,
        index=MODEL_OPTIONS.index(st.session_state.gc_model) if st.session_state.gc_model in MODEL_OPTIONS else 1
    )

    st.session_state.gc_temperature = st.slider(
        "Default Temperature",
        0.0, 1.0, st.session_state.gc_temperature, 0.1
    )

    st.session_state.gc_max_turns = st.number_input(
        "Max Rounds",
        min_value=1,
        max_value=20,
        value=st.session_state.gc_max_turns
    )

    st.session_state.gc_tools_enabled = st.checkbox(
        "Enable Tools for All Agents",
        value=st.session_state.gc_tools_enabled
    )

    st.divider()

    # Agent Roster
    st.subheader("🎭 Agent Roster")

    # Quick add buttons for presets
    st.caption("Quick Add:")
    preset_cols = st.columns(4)
    for i, (preset_id, preset) in enumerate(AGENT_PRESETS.items()):
        with preset_cols[i]:
            if st.button(preset['display_name'].split()[0], key=f"add_{preset_id}", help=f"Add {preset_id}"):
                # Check if already exists
                existing_ids = [a.id for a in st.session_state.gc_agents]
                if preset_id not in existing_ids:
                    new_agent = GroupChatAgent(
                        id=preset_id,
                        name=preset_id.upper(),
                        display_name=preset['display_name'],
                        color=preset['color'],
                        model=st.session_state.gc_model,
                        temperature=preset['temperature'],
                        system_prompt=load_agent_system_prompt(preset_id),
                        tools_enabled=st.session_state.gc_tools_enabled
                    )
                    st.session_state.gc_agents.append(new_agent)
                    st.rerun()

    # Custom agent button
    if st.button("➕ Add Custom Agent", use_container_width=True):
        st.session_state.gc_show_add_agent = not st.session_state.gc_show_add_agent

    # Custom agent form
    if st.session_state.gc_show_add_agent:
        with st.expander("Create Custom Agent", expanded=True):
            custom_name = st.text_input("Agent Name", value="Custom")
            custom_color = st.color_picker("Color", "#00ffaa")
            custom_temp = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1, key="custom_temp")
            custom_prompt = st.text_area("System Prompt", value=FALLBACK_PROMPTS['custom'], height=100)

            # Tool Exclusion Section
            st.markdown("---")
            st.markdown("**🔧 Tool Access**")

            # Exclusion preset selector
            preset_options = {k: v['label'] for k, v in EXCLUSION_PRESETS.items()}
            selected_preset = st.selectbox(
                "Quick Preset",
                options=list(preset_options.keys()),
                format_func=lambda x: f"{preset_options[x]} - {EXCLUSION_PRESETS[x]['description']}",
                key="custom_exclusion_preset"
            )

            # Initialize excluded tools from preset
            if 'custom_excluded_tools' not in st.session_state:
                st.session_state.custom_excluded_tools = set()

            # Apply preset button
            if st.button("Apply Preset", key="apply_preset"):
                st.session_state.custom_excluded_tools = set(EXCLUSION_PRESETS[selected_preset]['excluded'])
                st.rerun()

            # Category-based exclusion
            with st.expander("📂 Exclude by Category", expanded=False):
                for cat_id, cat_info in TOOL_CATEGORIES.items():
                    cat_tools = set(cat_info['tools'])
                    all_excluded = cat_tools.issubset(st.session_state.custom_excluded_tools)

                    if st.checkbox(
                        f"{cat_info['label']} ({len(cat_tools)})",
                        value=all_excluded,
                        key=f"cat_{cat_id}",
                        help=cat_info['description']
                    ):
                        st.session_state.custom_excluded_tools.update(cat_tools)
                    else:
                        st.session_state.custom_excluded_tools -= cat_tools

            # Individual tool exclusion
            with st.expander("🔍 Exclude Individual Tools", expanded=False):
                for cat_id, cat_info in TOOL_CATEGORIES.items():
                    st.caption(cat_info['label'])
                    for tool_name in cat_info['tools']:
                        is_excluded = tool_name in st.session_state.custom_excluded_tools
                        if st.checkbox(
                            tool_name,
                            value=is_excluded,
                            key=f"tool_{tool_name}"
                        ):
                            st.session_state.custom_excluded_tools.add(tool_name)
                        else:
                            st.session_state.custom_excluded_tools.discard(tool_name)

            # Show exclusion summary
            excluded_count = len(st.session_state.custom_excluded_tools)
            total_tools = len(ALL_TOOL_SCHEMAS)
            st.caption(f"Tools: {total_tools - excluded_count}/{total_tools} enabled")
            if excluded_count > 0:
                st.caption(f"Excluded: {', '.join(sorted(st.session_state.custom_excluded_tools)[:5])}{'...' if excluded_count > 5 else ''}")

            st.markdown("---")
            if st.button("Create Agent", type="primary"):
                agent_id = f"custom_{len(st.session_state.gc_agents)}_{int(time.time())}"
                new_agent = GroupChatAgent(
                    id=agent_id,
                    name=custom_name,
                    display_name=f"🤖 {custom_name}",
                    color=custom_color,
                    model=st.session_state.gc_model,
                    temperature=custom_temp,
                    system_prompt=custom_prompt,
                    tools_enabled=st.session_state.gc_tools_enabled,
                    excluded_tools=list(st.session_state.custom_excluded_tools)
                )
                st.session_state.gc_agents.append(new_agent)
                st.session_state.gc_show_add_agent = False
                st.session_state.custom_excluded_tools = set()  # Reset for next agent
                st.rerun()

    # Current agents list
    st.caption(f"Active Agents: {len(st.session_state.gc_agents)}")

    # Initialize edit state
    if 'gc_editing_agent_idx' not in st.session_state:
        st.session_state.gc_editing_agent_idx = None

    for i, agent in enumerate(st.session_state.gc_agents):
        is_native = agent.is_native()
        excluded_count = len(agent.excluded_tools)
        tool_info = f"({agent.get_effective_tool_count()} tools)" if not is_native and excluded_count > 0 else ""

        col1, col2, col3 = st.columns([2.5, 0.7, 0.8])
        with col1:
            st.markdown(
                f"<span style='color: {agent.color}'>{agent.display_name}</span> {tool_info}",
                unsafe_allow_html=True
            )
        with col2:
            # Edit button (only for non-native agents)
            if not is_native:
                if st.button("✏️", key=f"edit_{i}", help="Edit tool access"):
                    if st.session_state.gc_editing_agent_idx == i:
                        st.session_state.gc_editing_agent_idx = None  # Toggle off
                    else:
                        st.session_state.gc_editing_agent_idx = i
                        # Initialize edit state with current exclusions
                        st.session_state.gc_edit_excluded_tools = set(agent.excluded_tools)
                    st.rerun()
        with col3:
            if st.button("✖️", key=f"remove_{i}", help="Remove agent"):
                st.session_state.gc_agents.pop(i)
                if st.session_state.gc_editing_agent_idx == i:
                    st.session_state.gc_editing_agent_idx = None
                st.rerun()

        # Show edit panel if this agent is being edited
        if st.session_state.gc_editing_agent_idx == i and not is_native:
            with st.container():
                st.markdown(f"**Editing {agent.display_name} Tool Access**")

                # Initialize edit state if needed
                if 'gc_edit_excluded_tools' not in st.session_state:
                    st.session_state.gc_edit_excluded_tools = set(agent.excluded_tools)

                # Quick preset
                edit_preset = st.selectbox(
                    "Apply Preset",
                    options=list(EXCLUSION_PRESETS.keys()),
                    format_func=lambda x: f"{EXCLUSION_PRESETS[x]['label']}",
                    key=f"edit_preset_{i}"
                )
                if st.button("Apply", key=f"apply_edit_preset_{i}"):
                    st.session_state.gc_edit_excluded_tools = set(EXCLUSION_PRESETS[edit_preset]['excluded'])
                    st.rerun()

                # Category toggles
                st.caption("Categories:")
                cat_cols = st.columns(2)
                for j, (cat_id, cat_info) in enumerate(TOOL_CATEGORIES.items()):
                    cat_tools = set(cat_info['tools'])
                    all_excluded = cat_tools.issubset(st.session_state.gc_edit_excluded_tools)
                    with cat_cols[j % 2]:
                        if st.checkbox(
                            f"❌ {cat_info['label'].split()[0]}",
                            value=all_excluded,
                            key=f"edit_cat_{i}_{cat_id}",
                            help=f"Exclude {cat_info['label']}"
                        ):
                            st.session_state.gc_edit_excluded_tools.update(cat_tools)
                        else:
                            st.session_state.gc_edit_excluded_tools -= cat_tools

                # Summary
                edit_excluded_count = len(st.session_state.gc_edit_excluded_tools)
                st.caption(f"Enabled: {len(ALL_TOOL_SCHEMAS) - edit_excluded_count}/{len(ALL_TOOL_SCHEMAS)}")

                # Save/Cancel buttons
                btn_cols = st.columns(2)
                with btn_cols[0]:
                    if st.button("💾 Save", key=f"save_edit_{i}", type="primary"):
                        agent.excluded_tools = list(st.session_state.gc_edit_excluded_tools)
                        st.session_state.gc_editing_agent_idx = None
                        st.success(f"Updated {agent.display_name}")
                        st.rerun()
                with btn_cols[1]:
                    if st.button("Cancel", key=f"cancel_edit_{i}"):
                        st.session_state.gc_editing_agent_idx = None
                        st.rerun()

                st.markdown("---")

    st.divider()

    # Cost Tracker
    st.subheader("💰 Cost Tracker")
    ledger = st.session_state.gc_cost_ledger
    if ledger.total_cost > 0:
        st.code(ledger.get_summary(), language="text")
    else:
        st.caption("No costs yet")

    st.divider()

    # Controls
    st.subheader("🎮 Controls")

    # Auto-save toggle
    st.session_state.gc_auto_save = st.checkbox(
        "💾 Auto-save",
        value=st.session_state.gc_auto_save,
        help="Auto-save after each round"
    )

    ctrl_cols = st.columns(2)
    with ctrl_cols[0]:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.gc_history = []
            st.session_state.gc_round = 0
            st.session_state.gc_running = False
            st.session_state.gc_cost_ledger.reset()
            st.session_state.gc_message_ids = []
            st.session_state.gc_thread_id = None
            st.rerun()
    with ctrl_cols[1]:
        save_disabled = len(st.session_state.gc_history) == 0
        if st.button("💾 Save", use_container_width=True, disabled=save_disabled):
            if st.session_state.gc_thread_id and st.session_state.gc_topic:
                st.session_state.gc_convo_manager.save_conversation(
                    thread_id=st.session_state.gc_thread_id,
                    topic=st.session_state.gc_topic,
                    agents=st.session_state.gc_agents,
                    history=st.session_state.gc_history,
                    cost_ledger=st.session_state.gc_cost_ledger,
                    rounds_completed=st.session_state.gc_round
                )
                st.success("Saved!")

    st.divider()

    # History Section
    st.subheader("📜 History")

    recent_convos = st.session_state.gc_convo_manager.list_conversations(limit=5)

    if recent_convos:
        for convo in recent_convos:
            thread_id = convo.get("id", "")
            topic_text = convo.get("topic", "Untitled")[:25]
            rounds = convo.get("rounds_completed", 0)
            status = convo.get("status", "active")
            status_icon = "🟢" if status == "active" else "📦"

            st.caption(f"{status_icon} {topic_text}{'...' if len(convo.get('topic',''))>25 else ''}")
            st.caption(f"   {len(convo.get('agents',[]))} agents · {rounds} rnd")

            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.button("▶️", key=f"load_{thread_id}", help="Load"):
                    full_convo = st.session_state.gc_convo_manager.load_conversation(thread_id)
                    if full_convo:
                        st.session_state.gc_thread_id = thread_id
                        st.session_state.gc_topic = full_convo.get("topic", "")
                        st.session_state.gc_history = full_convo.get("history", [])
                        st.session_state.gc_round = full_convo.get("rounds_completed", 0)
                        st.session_state.gc_agents = st.session_state.gc_convo_manager.restore_agents(full_convo)
                        st.session_state.gc_cost_ledger = CostLedger.from_dict(full_convo.get("cost_summary", {}))
                        st.session_state.gc_view_mode = "chat"
                        st.rerun()
            with btn_cols[1]:
                if st.button("👁️", key=f"view_{thread_id}", help="Details"):
                    st.session_state.gc_selected_history_thread = thread_id
                    st.session_state.gc_view_mode = "history"
                    st.rerun()

        if st.button("📚 All History", use_container_width=True):
            st.session_state.gc_view_mode = "history"
            st.session_state.gc_selected_history_thread = None
            st.rerun()
    else:
        st.caption("No saved chats yet")


# ============================================================================
# Main Chat Area
# ============================================================================

st.title("🗣️ Group Chat")
st.caption("Multi-Agent Parallel Dialogue with Tool Access")

# View mode tabs
view_cols = st.columns([1, 1, 6])
with view_cols[0]:
    if st.button("💬 Chat", type="primary" if st.session_state.gc_view_mode == "chat" else "secondary", use_container_width=True):
        st.session_state.gc_view_mode = "chat"
        st.rerun()
with view_cols[1]:
    if st.button("📚 History", type="primary" if st.session_state.gc_view_mode == "history" else "secondary", use_container_width=True):
        st.session_state.gc_view_mode = "history"
        st.rerun()

st.divider()

# ============================================================================
# HISTORY VIEW
# ============================================================================
if st.session_state.gc_view_mode == "history":
    st.subheader("📚 Conversation History")

    all_convos = st.session_state.gc_convo_manager.list_conversations(limit=50)

    if not all_convos:
        st.info("No saved group conversations yet. Start a chat and enable auto-save!")
    else:
        # Filter controls
        filter_cols = st.columns([2, 1, 1])
        with filter_cols[0]:
            search_q = st.text_input("🔍 Search", placeholder="Filter by topic...", key="hist_search")
        with filter_cols[1]:
            status_f = st.selectbox("Status", ["All", "Active", "Archived"], key="hist_status")
        with filter_cols[2]:
            st.metric("Total", len(all_convos))

        filtered = all_convos
        if search_q:
            filtered = [c for c in filtered if search_q.lower() in c.get("topic", "").lower()]
        if status_f != "All":
            filtered = [c for c in filtered if c.get("status", "active") == status_f.lower()]

        # Detail view
        if st.session_state.gc_selected_history_thread:
            sel_convo = st.session_state.gc_convo_manager.load_conversation(st.session_state.gc_selected_history_thread)
            if sel_convo:
                st.markdown("---")
                st.subheader(f"📄 {sel_convo.get('topic', 'Untitled')}")

                info_cols = st.columns(4)
                with info_cols[0]:
                    st.caption(f"**Rounds:** {sel_convo.get('rounds_completed', 0)}")
                with info_cols[1]:
                    st.caption(f"**Agents:** {len(sel_convo.get('agents', []))}")
                with info_cols[2]:
                    cost = sel_convo.get("cost_summary", {}).get("total_cost", 0)
                    st.caption(f"**Cost:** ${cost:.4f}")
                with info_cols[3]:
                    st.caption(f"**Status:** {sel_convo.get('status', 'active')}")

                with st.expander("🎭 Participants"):
                    for ag in sel_convo.get("agents", []):
                        excl = len(ag.get("excluded_tools", []))
                        st.markdown(f"- **{ag.get('display_name', 'Unknown')}** ({52-excl} tools)")

                action_cols = st.columns(5)
                with action_cols[0]:
                    if st.button("▶️ Load", key="det_load", type="primary"):
                        st.session_state.gc_thread_id = sel_convo.get("id")
                        st.session_state.gc_topic = sel_convo.get("topic", "")
                        st.session_state.gc_history = sel_convo.get("history", [])
                        st.session_state.gc_round = sel_convo.get("rounds_completed", 0)
                        st.session_state.gc_agents = st.session_state.gc_convo_manager.restore_agents(sel_convo)
                        st.session_state.gc_cost_ledger = CostLedger.from_dict(sel_convo.get("cost_summary", {}))
                        st.session_state.gc_selected_history_thread = None
                        st.session_state.gc_view_mode = "chat"
                        st.rerun()
                with action_cols[1]:
                    json_exp = st.session_state.gc_convo_manager.export_to_json(sel_convo.get("id"))
                    if json_exp:
                        st.download_button("📋 JSON", json_exp, f"gc_{sel_convo.get('id','export')}.json", "application/json", key="dl_json")
                with action_cols[2]:
                    md_exp = st.session_state.gc_convo_manager.export_to_markdown(sel_convo.get("id"))
                    if md_exp:
                        st.download_button("📝 MD", md_exp, f"gc_{sel_convo.get('id','export')}.md", "text/markdown", key="dl_md")
                with action_cols[3]:
                    if st.button("📦 Archive", key="det_arch"):
                        st.session_state.gc_convo_manager.archive_conversation(sel_convo.get("id"))
                        st.rerun()
                with action_cols[4]:
                    if st.button("🗑️ Delete", key="det_del"):
                        st.session_state.gc_convo_manager.delete_conversation(sel_convo.get("id"))
                        st.session_state.gc_selected_history_thread = None
                        st.rerun()

                if st.button("← Back"):
                    st.session_state.gc_selected_history_thread = None
                    st.rerun()

                st.markdown("---")
                st.subheader("💬 Messages")
                hist = sel_convo.get("history", [])
                rnds = {}
                for e in hist:
                    r = e.get("round", 0)
                    if r not in rnds:
                        rnds[r] = []
                    rnds[r].append(e)
                for rn in sorted(rnds.keys()):
                    with st.expander(f"Round {rn}", expanded=(rn == max(rnds.keys()) if rnds else False)):
                        for e in rnds[rn]:
                            st.markdown(f"**{e.get('agent_name', 'Unknown')}:**")
                            st.markdown(e.get("content", ""))
                            st.markdown("---")
        else:
            # List view
            st.markdown("---")
            for convo in filtered:
                tid = convo.get("id", "")
                topic_t = convo.get("topic", "Untitled")
                rnds = convo.get("rounds_completed", 0)
                ags = len(convo.get("agents", []))
                stat = convo.get("status", "active")
                upd = convo.get("updated_at", "")[:10]
                cost = convo.get("cost_summary", {}).get("total_cost", 0)
                icon = "🟢" if stat == "active" else "📦"

                cols = st.columns([0.3, 3, 0.8, 0.8, 0.8, 0.6])
                with cols[0]:
                    st.markdown(icon)
                with cols[1]:
                    st.markdown(f"**{topic_t[:40]}**{'...' if len(topic_t)>40 else ''}")
                    st.caption(upd)
                with cols[2]:
                    st.caption(f"{ags} agents")
                with cols[3]:
                    st.caption(f"{rnds} rnds")
                with cols[4]:
                    st.caption(f"${cost:.3f}")
                with cols[5]:
                    if st.button("View", key=f"hv_{tid}"):
                        st.session_state.gc_selected_history_thread = tid
                        st.rerun()
                st.markdown("---")

# ============================================================================
# CHAT VIEW
# ============================================================================
if st.session_state.gc_view_mode == "chat":
    # Topic input
    st.subheader("💬 Discussion Topic")
    topic = st.text_area(
        "What should the agents discuss?",
        value=st.session_state.gc_topic,
        placeholder="Example: What is the nature of consciousness in multi-agent systems?",
        height=80,
        key="topic_input"
    )
    st.session_state.gc_topic = topic

    # Thread ID
    if not st.session_state.gc_thread_id:
        st.session_state.gc_thread_id = f"groupchat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"📍 Thread: `{st.session_state.gc_thread_id}`")
    with col2:
        if st.button("🔄 New Thread"):
            st.session_state.gc_thread_id = f"groupchat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state.gc_history = []
            st.session_state.gc_round = 0
            st.rerun()

    st.divider()

    # Start/Stop controls
    if len(st.session_state.gc_agents) < 1:
        st.warning("⚠️ Add at least 1 agent to start")
    elif not topic.strip():
        st.warning("⚠️ Enter a discussion topic")
    else:
        # Run button
        run_cols = st.columns([2, 1, 1])
        with run_cols[0]:
            run_disabled = st.session_state.gc_running
            if st.button(
                "🚀 Run Single Round" if not st.session_state.gc_running else "⏳ Running...",
                type="primary",
                use_container_width=True,
                disabled=run_disabled
            ):
                st.session_state.gc_running = True
                st.session_state.gc_round += 1

                # Create containers for each agent
                st.subheader(f"🔄 Round {st.session_state.gc_round}")

                status_containers = {}
                response_containers = {}

                # Create columns for parallel display
                num_agents = len(st.session_state.gc_agents)
                if num_agents <= 2:
                    cols = st.columns(num_agents)
                else:
                    cols = st.columns(min(num_agents, 3))

                for i, agent in enumerate(st.session_state.gc_agents):
                    col_idx = i % len(cols)
                    with cols[col_idx]:
                        st.markdown(
                            f"**<span style='color: {agent.color}'>{agent.display_name}</span>**",
                            unsafe_allow_html=True
                        )
                        status_containers[agent.id] = st.empty()
                        response_containers[agent.id] = st.container()

                # Run agents in parallel
                results = run_parallel_agents(
                    st.session_state.gc_agents,
                    topic,
                    st.session_state.gc_history,
                    st.session_state.gc_round,
                    st.session_state.gc_thread_id,
                    status_containers,
                    response_containers
                )

                # Process results
                for result in results:
                    # Add to history
                    st.session_state.gc_history.append({
                        "role": "assistant",
                        "agent_id": result["agent_id"],
                        "agent_name": result["agent_name"],
                        "content": result["content"],
                        "round": result["round"]
                    })

                    # Update cost ledger
                    st.session_state.gc_cost_ledger.log_usage(
                        result["agent_id"],
                        st.session_state.gc_model,
                        result["input_tokens"],
                        result["output_tokens"]
                    )

                    # Post to village
                    post_to_village(
                        agent_id=result["agent_id"],
                        content=result["content"],
                        thread_id=st.session_state.gc_thread_id,
                        round_num=result["round"],
                        related_agents=[a.id for a in st.session_state.gc_agents]
                    )

                st.session_state.gc_running = False
                auto_save_if_enabled()
                st.success(f"✅ Round {st.session_state.gc_round} complete!")

        with run_cols[1]:
            if st.button("🔁 Run All Rounds", use_container_width=True, disabled=st.session_state.gc_running):
                st.session_state.gc_run_all_rounds = True
                st.session_state.gc_target_rounds = st.session_state.gc_max_turns
                st.session_state.gc_stop_requested = False
                st.rerun()

        with run_cols[2]:
            if st.button("⏹️ Stop", use_container_width=True):
                st.session_state.gc_running = False
                st.session_state.gc_run_all_rounds = False
                st.session_state.gc_stop_requested = True
                st.rerun()

    # Run All Rounds execution
    if st.session_state.gc_run_all_rounds and not st.session_state.gc_stop_requested:
        target = st.session_state.gc_target_rounds
        current = st.session_state.gc_round

        if current < target:
            st.session_state.gc_running = True
            st.session_state.gc_round += 1

            # Progress indicator
            progress_container = st.container()
            with progress_container:
                st.progress(st.session_state.gc_round / target, text=f"Round {st.session_state.gc_round} of {target}")

            st.subheader(f"🔄 Round {st.session_state.gc_round}")

            status_containers = {}
            response_containers = {}

            num_agents = len(st.session_state.gc_agents)
            if num_agents == 1:
                cols = [st.container()]
            elif num_agents <= 2:
                cols = st.columns(num_agents)
            else:
                cols = st.columns(min(num_agents, 3))

            for i, agent in enumerate(st.session_state.gc_agents):
                col_idx = i % len(cols)
                with cols[col_idx]:
                    st.markdown(
                        f"**<span style='color: {agent.color}'>{agent.display_name}</span>**",
                        unsafe_allow_html=True
                    )
                    status_containers[agent.id] = st.empty()
                    response_containers[agent.id] = st.container()

            results = run_parallel_agents(
                st.session_state.gc_agents,
                topic,
                st.session_state.gc_history,
                st.session_state.gc_round,
                st.session_state.gc_thread_id,
                status_containers,
                response_containers
            )

            for result in results:
                st.session_state.gc_history.append({
                    "role": "assistant",
                    "agent_id": result["agent_id"],
                    "agent_name": result["agent_name"],
                    "content": result["content"],
                    "round": result["round"]
                })

                st.session_state.gc_cost_ledger.log_usage(
                    result["agent_id"],
                    st.session_state.gc_model,
                    result["input_tokens"],
                    result["output_tokens"]
                )

                post_to_village(
                    agent_id=result["agent_id"],
                    content=result["content"],
                    thread_id=st.session_state.gc_thread_id,
                    round_num=result["round"],
                    related_agents=[a.id for a in st.session_state.gc_agents]
                )

            st.session_state.gc_running = False
            auto_save_if_enabled()

            # Check for termination phrase
            for result in results:
                if st.session_state.gc_termination_phrase.lower() in result["content"].lower():
                    st.session_state.gc_run_all_rounds = False
                    st.success(f"🎯 Termination phrase detected! Stopping at round {st.session_state.gc_round}")
                    break

            # Continue to next round if not done
            if st.session_state.gc_round < target and st.session_state.gc_run_all_rounds:
                time.sleep(0.5)  # Brief pause between rounds
                st.rerun()
            else:
                st.session_state.gc_run_all_rounds = False
                st.success(f"✅ All {st.session_state.gc_round} rounds complete!")
        else:
            st.session_state.gc_run_all_rounds = False

    st.divider()

    # Display history
    if st.session_state.gc_history:
        st.subheader("📜 Conversation History")

        # Group by round
        rounds = {}
        for entry in st.session_state.gc_history:
            r = entry.get("round", 0)
            if r not in rounds:
                rounds[r] = []
            rounds[r].append(entry)

        for round_num in sorted(rounds.keys()):
            with st.expander(f"Round {round_num}", expanded=(round_num == st.session_state.gc_round)):
                entries = rounds[round_num]

                # Display in columns if multiple agents
                if len(entries) <= 3:
                    cols = st.columns(len(entries))
                    for i, entry in enumerate(entries):
                        with cols[i]:
                            agent_name = entry.get("agent_name", "Agent")
                            # Find agent color
                            color = "#ffffff"
                            for agent in st.session_state.gc_agents:
                                if agent.display_name == agent_name:
                                    color = agent.color
                                    break

                            st.markdown(
                                f"**<span style='color: {color}'>{agent_name}</span>**",
                                unsafe_allow_html=True
                            )
                            st.markdown(entry.get("content", ""))
                else:
                    for entry in entries:
                        agent_name = entry.get("agent_name", "Agent")
                        st.markdown(f"**{agent_name}:**")
                        st.markdown(entry.get("content", ""))
                        st.divider()

    st.divider()

    # Human override input
    st.subheader("💬 Human Input")
    st.caption("Send a message and agents will respond in a new round")
    human_input = st.chat_input("Send message to the group...")
    if human_input and not st.session_state.gc_running:
        # Add human message to history
        st.session_state.gc_history.append({
            "role": "user",
            "agent_id": "human",
            "agent_name": "👤 Human",
            "content": human_input,
            "round": st.session_state.gc_round + 1  # Will be part of next round
        })
        # Trigger agents to respond
        st.session_state.gc_trigger_round = True
        st.rerun()

    # Check if we need to trigger a round (from human input)
    if st.session_state.get("gc_trigger_round", False) and not st.session_state.gc_running:
        st.session_state.gc_trigger_round = False

        if len(st.session_state.gc_agents) >= 1 and st.session_state.gc_topic.strip():
            st.session_state.gc_running = True
            st.session_state.gc_round += 1

            # Get the human message that triggered this
            human_msg = None
            for entry in reversed(st.session_state.gc_history):
                if entry.get("agent_id") == "human":
                    human_msg = entry.get("content", "")
                    break

            # Modify topic to include human input
            effective_topic = st.session_state.gc_topic
            if human_msg:
                effective_topic = f"{st.session_state.gc_topic}\n\nHuman says: {human_msg}"

            st.subheader(f"🔄 Round {st.session_state.gc_round} (responding to human)")

            status_containers = {}
            response_containers = {}

            num_agents = len(st.session_state.gc_agents)
            if num_agents == 1:
                cols = [st.container()]
            elif num_agents <= 2:
                cols = st.columns(num_agents)
            else:
                cols = st.columns(min(num_agents, 3))

            for i, agent in enumerate(st.session_state.gc_agents):
                col_idx = i % len(cols)
                with cols[col_idx]:
                    st.markdown(
                        f"**<span style='color: {agent.color}'>{agent.display_name}</span>**",
                        unsafe_allow_html=True
                    )
                    status_containers[agent.id] = st.empty()
                    response_containers[agent.id] = st.container()

            results = run_parallel_agents(
                st.session_state.gc_agents,
                effective_topic,
                st.session_state.gc_history,
                st.session_state.gc_round,
                st.session_state.gc_thread_id,
                status_containers,
                response_containers
            )

            for result in results:
                st.session_state.gc_history.append({
                    "role": "assistant",
                    "agent_id": result["agent_id"],
                    "agent_name": result["agent_name"],
                    "content": result["content"],
                    "round": result["round"]
                })

                st.session_state.gc_cost_ledger.log_usage(
                    result["agent_id"],
                    st.session_state.gc_model,
                    result["input_tokens"],
                    result["output_tokens"]
                )

                post_to_village(
                    agent_id=result["agent_id"],
                    content=result["content"],
                    thread_id=st.session_state.gc_thread_id,
                    round_num=result["round"],
                    related_agents=[a.id for a in st.session_state.gc_agents]
                )

            st.session_state.gc_running = False
            auto_save_if_enabled()
            st.success(f"✅ Round {st.session_state.gc_round} complete!")
