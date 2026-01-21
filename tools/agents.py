"""
Multi-Agent System for Claude

Implements sub-agents, swarms, and Socratic council:
- agent_spawn: Spawn a sub-agent to work on a task
- agent_get_status: Check agent status
- agent_get_result: Get agent results
- socratic_council: Multi-agent consensus voting

Tools:
- agent_spawn: Create and run a sub-agent
- agent_status: Check agent progress
- agent_result: Retrieve agent output
- socratic_council: Run multi-agent voting
"""

import logging
import json
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

# Thread-local storage for agent context
# This allows tools to know which agent is calling them
_agent_context = threading.local()


def get_current_agent_context() -> Optional[Dict[str, Any]]:
    """
    Get the current agent context from thread-local storage.

    Returns:
        Dict with agent_id, agent_type, etc. or None if not in agent thread
    """
    return getattr(_agent_context, 'current', None)


def set_current_agent_context(context: Optional[Dict[str, Any]]):
    """
    Set the current agent context in thread-local storage.

    Args:
        context: Dict with agent_id, agent_type, etc. or None to clear
    """
    _agent_context.current = context


class AgentStatus(Enum):
    """Agent execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Agent:
    """Represents a sub-agent working on a task"""

    def __init__(
        self,
        agent_id: str,
        task: str,
        agent_type: str = "general",
        model: Optional[str] = None,
        tools_enabled: bool = True
    ):
        """
        Initialize agent.

        Args:
            agent_id: Unique agent identifier
            task: Task description for the agent
            agent_type: Type of agent (general, researcher, coder, etc.)
            model: Claude model to use
            tools_enabled: Whether agent can use tools
        """
        self.agent_id = agent_id
        self.task = task
        self.agent_type = agent_type
        self.model = model
        self.tools_enabled = tools_enabled
        self.status = AgentStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.messages = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary"""
        return {
            "agent_id": self.agent_id,
            "task": self.task,
            "agent_type": self.agent_type,
            "model": self.model,
            "tools_enabled": self.tools_enabled,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "message_count": len(self.messages)
        }


class AgentManager:
    """Manages multiple agents and their execution"""

    def __init__(self):
        """Initialize agent manager"""
        self.agents: Dict[str, Agent] = {}
        self.storage_file = Path("./sandbox/agents.json")
        self._ensure_storage()
        self._load_agents()

    def _ensure_storage(self):
        """Ensure storage directory exists"""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_file.exists():
            self._save_agents()

    def _load_agents(self):
        """Load agents from storage"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    # Note: This loads metadata only, not full Agent objects
                    # Full agents are recreated on spawn
                    logger.info(f"Loaded {len(data)} agent records")
        except Exception as e:
            logger.error(f"Error loading agents: {e}")

    def _save_agents(self):
        """Save agents to storage"""
        try:
            data = {
                agent_id: agent.to_dict()
                for agent_id, agent in self.agents.items()
            }
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving agents: {e}")

    def create_agent(
        self,
        task: str,
        agent_type: str = "general",
        model: Optional[str] = None,
        tools_enabled: bool = True
    ) -> str:
        """
        Create a new agent.

        Args:
            task: Task for the agent
            agent_type: Type of agent
            model: Model to use
            tools_enabled: Enable tools

        Returns:
            Agent ID
        """
        agent_id = f"agent_{int(datetime.now().timestamp() * 1000)}"
        agent = Agent(agent_id, task, agent_type, model, tools_enabled)
        self.agents[agent_id] = agent
        self._save_agents()

        logger.info(f"Created agent {agent_id}: {task[:50]}...")
        return agent_id

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents"""
        return [agent.to_dict() for agent in self.agents.values()]

    def run_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Run an agent task.

        Args:
            agent_id: Agent ID

        Returns:
            Execution result
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}

        agent.status = AgentStatus.RUNNING
        agent.started_at = datetime.now()

        # Set thread-local agent context so tools know who's calling
        set_current_agent_context({
            'agent_id': agent_id,
            'agent_type': agent.agent_type,
            'model': agent.model
        })

        try:
            # Import here to avoid circular dependency
            from core import ClaudeAPIClient, ToolRegistry, ToolExecutor, ToolCallLoop
            from tools import register_all_tools, ALL_TOOL_SCHEMAS

            # Create client for this agent
            client = ClaudeAPIClient()

            # Setup tools if enabled
            tools = None
            if agent.tools_enabled:
                registry = ToolRegistry()
                register_all_tools(registry)
                executor = ToolExecutor(registry)
                loop = ToolCallLoop(client, executor, max_iterations=25)
                tools = list(ALL_TOOL_SCHEMAS.values())
            else:
                # No tools, just direct API call
                loop = None

            # Prepare message
            messages = [{"role": "user", "content": agent.task}]

            # System prompt based on agent type
            system_prompts = {
                "general": "You are a helpful AI assistant working on a specific task. Complete the task thoroughly and provide clear results.",
                "researcher": "You are a research assistant. Gather information, analyze it, and provide comprehensive findings with sources.",
                "coder": "You are a coding assistant. Write clean, well-documented code and explain your implementation.",
                "analyst": "You are a data analyst. Analyze the information provided and generate insights with supporting evidence.",
                "writer": "You are a content writer. Create clear, engaging, and well-structured content."
            }
            system_prompt = system_prompts.get(agent.agent_type, system_prompts["general"])

            # Run task
            if loop and tools:
                response, updated_messages = loop.run(
                    messages=messages,
                    system=system_prompt,
                    model=agent.model,
                    max_tokens=4096,
                    tools=tools
                )
            else:
                response = client.create_message(
                    messages=messages,
                    system=system_prompt,
                    model=agent.model,
                    max_tokens=4096
                )

            # Extract result
            result_text = ""
            for block in response.content:
                if hasattr(block, 'type') and block.type == 'text':
                    result_text += block.text

            agent.result = result_text
            agent.status = AgentStatus.COMPLETED
            agent.completed_at = datetime.now()

            logger.info(f"Agent {agent_id} completed successfully")

            self._save_agents()

            return {
                "success": True,
                "agent_id": agent_id,
                "result": result_text,
                "status": agent.status.value
            }

        except Exception as e:
            agent.status = AgentStatus.FAILED
            agent.error = str(e)
            agent.completed_at = datetime.now()

            logger.error(f"Agent {agent_id} failed: {e}")

            self._save_agents()

            return {
                "success": False,
                "agent_id": agent_id,
                "error": str(e),
                "status": agent.status.value
            }

        finally:
            # Clear thread-local agent context
            set_current_agent_context(None)


# Global agent manager
_agent_manager = AgentManager()


def agent_spawn(
    task: str,
    agent_type: str = "general",
    model: Optional[str] = None,
    run_async: bool = True
) -> Dict[str, Any]:
    """
    Spawn a sub-agent to work on a task.

    Args:
        task: Task description for the agent
        agent_type: Type of agent (general, researcher, coder, analyst, writer)
        model: Claude model to use (default: haiku for cost efficiency)
        run_async: Whether to run asynchronously (default: True)

    Returns:
        Dict with agent_id and status

    Example:
        >>> agent_spawn("Research the history of Python programming language", "researcher")
        {"agent_id": "agent_123", "status": "running", "message": "Agent spawned"}
    """
    try:
        # Use Haiku by default for sub-agents (cost-effective)
        if not model:
            from core import ClaudeModels
            model = ClaudeModels.HAIKU_3_5.value

        # Create agent
        agent_id = _agent_manager.create_agent(
            task=task,
            agent_type=agent_type,
            model=model,
            tools_enabled=True
        )

        # Run agent
        if run_async:
            # Run in background thread
            thread = threading.Thread(
                target=_agent_manager.run_agent,
                args=(agent_id,),
                daemon=True
            )
            thread.start()

            return {
                "success": True,
                "agent_id": agent_id,
                "status": "running",
                "message": f"Agent {agent_id} spawned and running in background. Use agent_status to check progress."
            }
        else:
            # Run synchronously
            result = _agent_manager.run_agent(agent_id)
            return result

    except Exception as e:
        logger.error(f"Error spawning agent: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def agent_status(agent_id: str) -> Dict[str, Any]:
    """
    Check the status of an agent.

    Args:
        agent_id: Agent ID to check

    Returns:
        Agent status information

    Example:
        >>> agent_status("agent_123")
        {"agent_id": "agent_123", "status": "completed", "progress": "Task finished"}
    """
    try:
        agent = _agent_manager.get_agent(agent_id)
        if not agent:
            return {
                "found": False,
                "error": f"Agent {agent_id} not found"
            }

        return {
            "found": True,
            "agent_id": agent_id,
            "status": agent.status.value,
            "task": agent.task,
            "agent_type": agent.agent_type,
            "created_at": agent.created_at.isoformat(),
            "has_result": agent.result is not None,
            "has_error": agent.error is not None
        }

    except Exception as e:
        logger.error(f"Error checking agent status: {e}")
        return {"error": str(e)}


def agent_result(agent_id: str) -> Dict[str, Any]:
    """
    Get the result from a completed agent.

    Args:
        agent_id: Agent ID

    Returns:
        Agent result or error

    Example:
        >>> agent_result("agent_123")
        {"agent_id": "agent_123", "result": "Python was created by...", "status": "completed"}
    """
    try:
        agent = _agent_manager.get_agent(agent_id)
        if not agent:
            return {
                "found": False,
                "error": f"Agent {agent_id} not found"
            }

        if agent.status == AgentStatus.COMPLETED:
            return {
                "found": True,
                "agent_id": agent_id,
                "status": "completed",
                "result": agent.result,
                "task": agent.task
            }
        elif agent.status == AgentStatus.FAILED:
            return {
                "found": True,
                "agent_id": agent_id,
                "status": "failed",
                "error": agent.error,
                "task": agent.task
            }
        else:
            return {
                "found": True,
                "agent_id": agent_id,
                "status": agent.status.value,
                "message": "Agent is still running. Check back later.",
                "task": agent.task
            }

    except Exception as e:
        logger.error(f"Error getting agent result: {e}")
        return {"error": str(e)}


def agent_list() -> Dict[str, Any]:
    """
    List all agents.

    Returns:
        List of all agents and their status

    Example:
        >>> agent_list()
        {"agents": [...], "count": 5}
    """
    try:
        agents = _agent_manager.list_agents()
        return {
            "success": True,
            "agents": agents,
            "count": len(agents)
        }
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return {"error": str(e)}


def socratic_council(
    question: str,
    options: List[str],
    num_agents: int = 3,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a Socratic council: multiple agents vote on the best option.

    Args:
        question: Question or decision to make
        options: List of options to choose from
        num_agents: Number of agents to participate (default: 3)
        model: Model for agents (default: Sonnet for better reasoning)

    Returns:
        Voting results with winner

    Example:
        >>> socratic_council(
        ...     "Which framework is best for web apps?",
        ...     ["FastAPI", "Flask", "Django"],
        ...     num_agents=3
        ... )
        {"winner": "FastAPI", "votes": {...}, "reasoning": [...]}
    """
    try:
        from core import ClaudeAPIClient, ClaudeModels

        if not model:
            model = ClaudeModels.SONNET_4_5.value  # Good balance of cost/quality

        # Format the question with options
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        prompt = f"""Question: {question}

Options:
{options_text}

Analyze each option carefully and choose the best one. Provide your choice as a number (1-{len(options)}) and explain your reasoning briefly."""

        votes = {opt: 0 for opt in options}
        reasoning = []

        # Run agents
        client = ClaudeAPIClient()

        for i in range(num_agents):
            logger.info(f"Council agent {i+1}/{num_agents} voting...")

            try:
                response = client.create_message(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    max_tokens=4096
                )

                # Extract vote
                vote_text = ""
                for block in response.content:
                    if hasattr(block, 'type') and block.type == 'text':
                        vote_text = block.text
                        break

                # Parse vote (look for number)
                vote_choice = None
                for j, opt in enumerate(options, 1):
                    if str(j) in vote_text[:20] or opt.lower() in vote_text[:100].lower():
                        vote_choice = opt
                        break

                if vote_choice:
                    votes[vote_choice] += 1
                    reasoning.append({
                        "agent": i + 1,
                        "vote": vote_choice,
                        "reasoning": vote_text[:200] + "..."
                    })
                    logger.info(f"Agent {i+1} voted for: {vote_choice}")

            except Exception as e:
                logger.error(f"Council agent {i+1} failed: {e}")
                continue

        # Check if any votes were cast
        total_votes = sum(votes.values())
        if total_votes == 0:
            return {
                "success": False,
                "error": "No agents were able to vote. Check logs for API errors."
            }

        # Determine winner
        winner = max(votes, key=votes.get)
        winner_votes = votes[winner]

        return {
            "success": True,
            "question": question,
            "winner": winner,
            "votes": votes,
            "total_agents": num_agents,
            "winner_votes": winner_votes,
            "reasoning": reasoning,
            "consensus": winner_votes > num_agents / 2
        }

    except Exception as e:
        logger.error(f"Error in Socratic council: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Tool schemas for registration
AGENT_TOOL_SCHEMAS = {
    "agent_spawn": {
        "name": "agent_spawn",
        "description": "Spawn a sub-agent to work on a task independently. The agent will work in the background and you can check its status later. Useful for parallel work or time-consuming research.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Detailed task description for the agent"
                },
                "agent_type": {
                    "type": "string",
                    "enum": ["general", "researcher", "coder", "analyst", "writer"],
                    "description": "Type of agent: 'general' for any task, 'researcher' for research, 'coder' for code, 'analyst' for analysis, 'writer' for content",
                    "default": "general"
                },
                "model": {
                    "type": "string",
                    "description": "Claude model to use (default: haiku for efficiency)",
                    "default": None
                },
                "run_async": {
                    "type": "boolean",
                    "description": "Run in background (true) or wait for completion (false)",
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
                    "description": "Agent ID to check (from agent_spawn)"
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
                    "description": "Agent ID (from agent_spawn)"
                }
            },
            "required": ["agent_id"]
        }
    },
    "agent_list": {
        "name": "agent_list",
        "description": "List all spawned agents and their status",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "socratic_council": {
        "name": "socratic_council",
        "description": "Run a Socratic council where multiple AI agents vote on the best option. Useful for making decisions, comparing alternatives, or getting consensus.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question or decision to make"
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of options to choose from (2-5 options recommended)"
                },
                "num_agents": {
                    "type": "integer",
                    "description": "Number of agents to participate in voting (default: 3, use odd numbers)",
                    "default": 3
                },
                "model": {
                    "type": "string",
                    "description": "Model for agents (default: Sonnet for good reasoning)",
                    "default": None
                }
            },
            "required": ["question", "options"]
        }
    }
}
