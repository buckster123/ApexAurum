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
    allowed_tools: List[str] = field(default_factory=list)  # Empty = all tools

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
            "status": self.status,
            "total_cost": self.total_cost
        }


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

    # Get tool schemas if enabled
    tools = None
    if agent.tools_enabled:
        if agent.allowed_tools:
            tools = [ALL_TOOL_SCHEMAS[name] for name in agent.allowed_tools if name in ALL_TOOL_SCHEMAS]
        else:
            tools = list(ALL_TOOL_SCHEMAS.values())

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
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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

            if st.button("Create Agent"):
                agent_id = f"custom_{len(st.session_state.gc_agents)}"
                new_agent = GroupChatAgent(
                    id=agent_id,
                    name=custom_name,
                    display_name=f"🤖 {custom_name}",
                    color=custom_color,
                    model=st.session_state.gc_model,
                    temperature=custom_temp,
                    system_prompt=custom_prompt,
                    tools_enabled=st.session_state.gc_tools_enabled
                )
                st.session_state.gc_agents.append(new_agent)
                st.session_state.gc_show_add_agent = False
                st.rerun()

    # Current agents list
    st.caption(f"Active Agents: {len(st.session_state.gc_agents)}")
    for i, agent in enumerate(st.session_state.gc_agents):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                f"<span style='color: {agent.color}'>{agent.display_name}</span>",
                unsafe_allow_html=True
            )
        with col2:
            if st.button("✖️", key=f"remove_{i}", help="Remove agent"):
                st.session_state.gc_agents.pop(i)
                st.rerun()

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

    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.gc_history = []
        st.session_state.gc_round = 0
        st.session_state.gc_running = False
        st.session_state.gc_cost_ledger.reset()
        st.session_state.gc_message_ids = []
        st.rerun()


# ============================================================================
# Main Chat Area
# ============================================================================

st.title("🗣️ Group Chat")
st.caption("Multi-Agent Parallel Dialogue with Tool Access")

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
        st.success(f"✅ Round {st.session_state.gc_round} complete!")
