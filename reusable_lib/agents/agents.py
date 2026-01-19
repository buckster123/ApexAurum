"""
Multi-Agent Orchestration Framework

A framework for spawning and managing multiple AI agents working on tasks.
Designed to be backend-agnostic - bring your own API client.

Features:
- Spawn sub-agents for parallel task execution
- Track agent status and results
- Multiple agent types with specialized prompts
- Persistent state storage
- Socratic council voting system

Usage:
    from reusable_lib.agents import AgentManager, AGENT_TYPES

    # Create manager with your API call function
    def my_api_call(messages, system, model, max_tokens):
        return your_client.create_message(...)

    manager = AgentManager(api_call_fn=my_api_call)

    # Spawn an agent
    agent_id = manager.spawn_agent(
        task="Research Python async patterns",
        agent_type="researcher"
    )

    # Check status
    status = manager.get_status(agent_id)

    # Get result when complete
    result = manager.get_result(agent_id)
"""

import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Agent type definitions with system prompts
AGENT_TYPES = {
    "general": {
        "name": "General Assistant",
        "system_prompt": (
            "You are a helpful AI assistant working on a specific task. "
            "Complete the task thoroughly and provide clear results."
        ),
    },
    "researcher": {
        "name": "Research Assistant",
        "system_prompt": (
            "You are a research assistant. Gather information, analyze it, "
            "and provide comprehensive findings with sources."
        ),
    },
    "coder": {
        "name": "Coding Assistant",
        "system_prompt": (
            "You are a coding assistant. Write clean, well-documented code "
            "and explain your implementation."
        ),
    },
    "analyst": {
        "name": "Data Analyst",
        "system_prompt": (
            "You are a data analyst. Analyze the information provided and "
            "generate insights with supporting evidence."
        ),
    },
    "writer": {
        "name": "Content Writer",
        "system_prompt": (
            "You are a content writer. Create clear, engaging, and "
            "well-structured content."
        ),
    },
}


@dataclass
class Agent:
    """Represents a sub-agent working on a task."""

    agent_id: str
    task: str
    agent_type: str = "general"
    model: Optional[str] = None
    status: AgentStatus = AgentStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "task": self.task,
            "agent_type": self.agent_type,
            "model": self.model,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """Create agent from dictionary."""
        agent = cls(
            agent_id=data["agent_id"],
            task=data["task"],
            agent_type=data.get("agent_type", "general"),
            model=data.get("model"),
        )
        agent.status = AgentStatus(data.get("status", "pending"))
        agent.result = data.get("result")
        agent.error = data.get("error")
        agent.metadata = data.get("metadata", {})

        if data.get("created_at"):
            agent.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            agent.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            agent.completed_at = datetime.fromisoformat(data["completed_at"])

        return agent

    @property
    def duration(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None


# Type for API call function
APICallFn = Callable[
    [List[Dict], str, Optional[str], int],  # messages, system, model, max_tokens
    str  # Returns response text
]


class AgentManager:
    """
    Manages multiple agents and their execution.

    Requires an API call function to execute tasks. This makes the manager
    backend-agnostic - you can use any LLM API.
    """

    def __init__(
        self,
        api_call_fn: Optional[APICallFn] = None,
        storage_path: Optional[Path] = None,
        default_model: Optional[str] = None
    ):
        """
        Initialize agent manager.

        Args:
            api_call_fn: Function to make API calls. Signature:
                         fn(messages, system, model, max_tokens) -> str
            storage_path: Path to JSON file for persistence
            default_model: Default model for agents
        """
        self.api_call_fn = api_call_fn
        self.storage_path = storage_path or Path("./agents.json")
        self.default_model = default_model
        self.agents: Dict[str, Agent] = {}
        self._lock = threading.Lock()

        self._ensure_storage()
        self._load_agents()

    def _ensure_storage(self):
        """Ensure storage directory exists."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_agents()

    def _load_agents(self):
        """Load agents from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for agent_id, agent_data in data.items():
                        self.agents[agent_id] = Agent.from_dict(agent_data)
                logger.info(f"Loaded {len(self.agents)} agents from storage")
        except Exception as e:
            logger.error(f"Error loading agents: {e}")

    def _save_agents(self):
        """Save agents to storage."""
        try:
            with self._lock:
                data = {
                    agent_id: agent.to_dict()
                    for agent_id, agent in self.agents.items()
                }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving agents: {e}")

    def _generate_id(self) -> str:
        """Generate unique agent ID."""
        return f"agent_{int(datetime.now().timestamp() * 1000)}"

    def spawn_agent(
        self,
        task: str,
        agent_type: str = "general",
        model: Optional[str] = None,
        run_async: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Spawn a new agent to work on a task.

        Args:
            task: Task description
            agent_type: Type of agent (general, researcher, coder, analyst, writer)
            model: Model to use (uses default if None)
            run_async: Run in background thread
            metadata: Additional metadata for the agent

        Returns:
            Agent ID
        """
        agent_id = self._generate_id()
        agent = Agent(
            agent_id=agent_id,
            task=task,
            agent_type=agent_type,
            model=model or self.default_model,
            metadata=metadata or {}
        )

        with self._lock:
            self.agents[agent_id] = agent

        self._save_agents()
        logger.info(f"Spawned agent {agent_id}: {task[:50]}...")

        if run_async:
            thread = threading.Thread(
                target=self._run_agent,
                args=(agent_id,),
                daemon=True
            )
            thread.start()
        else:
            self._run_agent(agent_id)

        return agent_id

    def _run_agent(self, agent_id: str):
        """Execute agent task."""
        agent = self.agents.get(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return

        if not self.api_call_fn:
            agent.status = AgentStatus.FAILED
            agent.error = "No API call function configured"
            agent.completed_at = datetime.now()
            self._save_agents()
            return

        agent.status = AgentStatus.RUNNING
        agent.started_at = datetime.now()
        self._save_agents()

        try:
            # Get system prompt for agent type
            agent_config = AGENT_TYPES.get(agent.agent_type, AGENT_TYPES["general"])
            system_prompt = agent_config["system_prompt"]

            # Make API call
            messages = [{"role": "user", "content": agent.task}]
            result = self.api_call_fn(
                messages,
                system_prompt,
                agent.model,
                4096
            )

            agent.result = result
            agent.status = AgentStatus.COMPLETED
            agent.completed_at = datetime.now()

            logger.info(f"Agent {agent_id} completed successfully")

        except Exception as e:
            agent.status = AgentStatus.FAILED
            agent.error = str(e)
            agent.completed_at = datetime.now()
            logger.error(f"Agent {agent_id} failed: {e}")

        self._save_agents()

    def get_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent status.

        Args:
            agent_id: Agent ID

        Returns:
            Status dict or None if not found
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        return {
            "agent_id": agent_id,
            "status": agent.status.value,
            "task": agent.task,
            "agent_type": agent.agent_type,
            "created_at": agent.created_at.isoformat(),
            "duration": agent.duration,
            "has_result": agent.result is not None,
            "has_error": agent.error is not None,
        }

    def get_result(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent result.

        Args:
            agent_id: Agent ID

        Returns:
            Result dict or None if not found
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        return {
            "agent_id": agent_id,
            "status": agent.status.value,
            "task": agent.task,
            "result": agent.result,
            "error": agent.error,
            "duration": agent.duration,
        }

    def list_agents(
        self,
        status_filter: Optional[AgentStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all agents.

        Args:
            status_filter: Filter by status
            limit: Maximum number to return

        Returns:
            List of agent dicts
        """
        agents = list(self.agents.values())

        if status_filter:
            agents = [a for a in agents if a.status == status_filter]

        # Sort by created_at descending
        agents.sort(key=lambda a: a.created_at, reverse=True)

        return [a.to_dict() for a in agents[:limit]]

    def wait_for_agent(
        self,
        agent_id: str,
        timeout: float = 300,
        poll_interval: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for agent to complete.

        Args:
            agent_id: Agent ID
            timeout: Maximum wait time in seconds
            poll_interval: Time between status checks

        Returns:
            Result dict or None if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            agent = self.agents.get(agent_id)
            if not agent:
                return None

            if agent.status in (AgentStatus.COMPLETED, AgentStatus.FAILED):
                return self.get_result(agent_id)

            time.sleep(poll_interval)

        return None

    def cancel_agent(self, agent_id: str) -> bool:
        """
        Cancel a running agent (marks as failed).

        Args:
            agent_id: Agent ID

        Returns:
            True if cancelled, False if not found
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        if agent.status == AgentStatus.RUNNING:
            agent.status = AgentStatus.FAILED
            agent.error = "Cancelled by user"
            agent.completed_at = datetime.now()
            self._save_agents()
            logger.info(f"Agent {agent_id} cancelled")
            return True

        return False

    def clear_completed(self) -> int:
        """
        Remove completed agents from storage.

        Returns:
            Number of agents removed
        """
        with self._lock:
            to_remove = [
                aid for aid, agent in self.agents.items()
                if agent.status in (AgentStatus.COMPLETED, AgentStatus.FAILED)
            ]
            for aid in to_remove:
                del self.agents[aid]

        self._save_agents()
        logger.info(f"Cleared {len(to_remove)} completed agents")
        return len(to_remove)


# Tool schemas for AI API registration
AGENT_TOOL_SCHEMAS = {
    "agent_spawn": {
        "name": "agent_spawn",
        "description": (
            "Spawn a sub-agent to work on a task independently. "
            "The agent will work in the background."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Detailed task description"
                },
                "agent_type": {
                    "type": "string",
                    "enum": ["general", "researcher", "coder", "analyst", "writer"],
                    "description": "Type of agent",
                    "default": "general"
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (optional)"
                },
                "run_async": {
                    "type": "boolean",
                    "description": "Run in background",
                    "default": True
                }
            },
            "required": ["task"]
        }
    },
    "agent_status": {
        "name": "agent_status",
        "description": "Check the status of a spawned agent",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to check"
                }
            },
            "required": ["agent_id"]
        }
    },
    "agent_result": {
        "name": "agent_result",
        "description": "Get the result from a completed agent",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID"
                }
            },
            "required": ["agent_id"]
        }
    },
    "agent_list": {
        "name": "agent_list",
        "description": "List all spawned agents",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
}
