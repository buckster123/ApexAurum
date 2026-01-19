"""
Agent Tools

Provides AI-callable tools for multi-agent orchestration.
Wraps reusable_lib.agents.AgentManager for tool-based access.

Tools:
    - agent_spawn: Spawn a sub-agent to work on a task
    - agent_status: Check agent status
    - agent_result: Get agent results
    - agent_list: List all agents
    - socratic_council: Multi-agent voting system

Requirements:
    - An LLM API call function must be configured via set_agent_api()
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

# Global configuration - initialized lazily
_agent_manager = None
_api_call_fn: Optional[Callable] = None
_storage_path = "./data/agents.json"
_default_model: Optional[str] = None


def set_agent_api(api_call_fn: Callable):
    """
    Configure the API call function for agents.

    The function should have signature:
        fn(messages: List[Dict], system: str, model: Optional[str], max_tokens: int) -> str

    Args:
        api_call_fn: Function to make LLM API calls
    """
    global _api_call_fn, _agent_manager
    _api_call_fn = api_call_fn
    _agent_manager = None  # Reset to reinitialize with new function
    logger.info("Agent API function configured")


def set_agent_storage_path(path: str):
    """
    Set the path for agent state storage.

    Args:
        path: Path to JSON file for persistence
    """
    global _storage_path, _agent_manager
    _storage_path = path
    _agent_manager = None  # Reset to reinitialize with new path

    # Ensure directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Agent storage path set to: {path}")


def set_agent_default_model(model: str):
    """
    Set the default model for agents.

    Args:
        model: Model name/ID to use by default
    """
    global _default_model, _agent_manager
    _default_model = model
    _agent_manager = None
    logger.info(f"Agent default model set to: {model}")


def _get_manager():
    """Get or create the agent manager."""
    global _agent_manager

    if _agent_manager is None:
        try:
            from reusable_lib.agents import AgentManager
            _agent_manager = AgentManager(
                api_call_fn=_api_call_fn,
                storage_path=Path(_storage_path),
                default_model=_default_model
            )
            logger.info(f"Initialized AgentManager at {_storage_path}")
        except ImportError as e:
            logger.error(f"Failed to import AgentManager: {e}")
            raise RuntimeError("Agent system not available")

    return _agent_manager


# =============================================================================
# Agent Tools
# =============================================================================

def agent_spawn(
    task: str,
    agent_type: str = "general",
    model: Optional[str] = None,
    run_async: bool = True
) -> Dict[str, Any]:
    """
    Spawn a sub-agent to work on a task independently.

    The agent runs in the background and can be checked later with agent_status.

    Args:
        task: Detailed task description for the agent
        agent_type: Type of agent - general, researcher, coder, analyst, writer
        model: Model to use (optional, uses default if not specified)
        run_async: Run in background (True) or wait for completion (False)

    Returns:
        Dict with agent_id and status
    """
    try:
        manager = _get_manager()

        if not _api_call_fn:
            return {
                "success": False,
                "error": "Agent API not configured. Call set_agent_api() first."
            }

        agent_id = manager.spawn_agent(
            task=task,
            agent_type=agent_type,
            model=model,
            run_async=run_async
        )

        return {
            "success": True,
            "agent_id": agent_id,
            "task": task[:100] + "..." if len(task) > 100 else task,
            "agent_type": agent_type,
            "status": "running" if run_async else "completed",
            "message": f"Agent spawned successfully. Use agent_status('{agent_id}') to check progress."
        }

    except Exception as e:
        logger.error(f"agent_spawn failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def agent_status(agent_id: str) -> Dict[str, Any]:
    """
    Check the status of a spawned agent.

    Args:
        agent_id: Agent ID from agent_spawn

    Returns:
        Dict with agent status and metadata
    """
    try:
        manager = _get_manager()
        status = manager.get_status(agent_id)

        if status is None:
            return {
                "success": False,
                "found": False,
                "error": f"Agent {agent_id} not found"
            }

        return {
            "success": True,
            "found": True,
            **status
        }

    except Exception as e:
        logger.error(f"agent_status failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def agent_result(agent_id: str) -> Dict[str, Any]:
    """
    Get the result from a completed agent.

    Args:
        agent_id: Agent ID from agent_spawn

    Returns:
        Dict with agent result or error
    """
    try:
        manager = _get_manager()
        result = manager.get_result(agent_id)

        if result is None:
            return {
                "success": False,
                "found": False,
                "error": f"Agent {agent_id} not found"
            }

        return {
            "success": True,
            "found": True,
            **result
        }

    except Exception as e:
        logger.error(f"agent_result failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def agent_list(limit: int = 20) -> Dict[str, Any]:
    """
    List all spawned agents.

    Args:
        limit: Maximum number of agents to return (default: 20)

    Returns:
        Dict with list of agents
    """
    try:
        manager = _get_manager()
        agents = manager.list_agents(limit=limit)

        return {
            "success": True,
            "agents": agents,
            "count": len(agents)
        }

    except Exception as e:
        logger.error(f"agent_list failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "agents": []
        }


def socratic_council(
    question: str,
    options: List[str],
    num_agents: int = 3,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a Socratic council: multiple agents vote on the best option.

    Each agent independently analyzes the options and votes. The option
    with the most votes wins. Useful for decision-making and consensus.

    Args:
        question: Question or decision to make
        options: List of options to choose from (2-5 recommended)
        num_agents: Number of agents to participate (default: 3, use odd numbers)
        model: Model for agents (optional)

    Returns:
        Dict with winner, votes, and reasoning from each agent
    """
    try:
        if not _api_call_fn:
            return {
                "success": False,
                "error": "Agent API not configured. Call set_agent_api() first."
            }

        if len(options) < 2:
            return {
                "success": False,
                "error": "Need at least 2 options to vote on"
            }

        if num_agents < 1:
            return {
                "success": False,
                "error": "Need at least 1 agent"
            }

        # Format the question with options
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        prompt = f"""Question: {question}

Options:
{options_text}

Analyze each option carefully and choose the best one.
Respond with ONLY a number (1-{len(options)}) on the first line, then explain your reasoning briefly."""

        votes = {opt: 0 for opt in options}
        reasoning = []

        # System prompt for council agents
        system_prompt = (
            "You are a wise council member participating in a vote. "
            "Analyze options objectively and vote for the best one. "
            "Be concise but explain your reasoning."
        )

        # Run agents synchronously for voting
        for i in range(num_agents):
            logger.info(f"Council agent {i+1}/{num_agents} voting...")

            try:
                messages = [{"role": "user", "content": prompt}]
                vote_text = _api_call_fn(
                    messages,
                    system_prompt,
                    model,
                    1024  # Shorter responses for voting
                )

                # Parse vote (look for number at start)
                vote_choice = None
                vote_text_clean = vote_text.strip()

                # Try to find the vote number
                for j, opt in enumerate(options, 1):
                    # Check if response starts with the number
                    if vote_text_clean.startswith(str(j)):
                        vote_choice = opt
                        break
                    # Also check if option name is mentioned early
                    if opt.lower() in vote_text_clean[:150].lower():
                        vote_choice = opt
                        break

                if vote_choice:
                    votes[vote_choice] += 1
                    reasoning.append({
                        "agent": i + 1,
                        "vote": vote_choice,
                        "reasoning": vote_text[:300] + ("..." if len(vote_text) > 300 else "")
                    })
                    logger.info(f"Agent {i+1} voted for: {vote_choice}")
                else:
                    logger.warning(f"Agent {i+1} vote unclear: {vote_text[:100]}")
                    reasoning.append({
                        "agent": i + 1,
                        "vote": "unclear",
                        "reasoning": vote_text[:300] + ("..." if len(vote_text) > 300 else "")
                    })

            except Exception as e:
                logger.error(f"Council agent {i+1} failed: {e}")
                reasoning.append({
                    "agent": i + 1,
                    "vote": "error",
                    "reasoning": str(e)
                })
                continue

        # Check if any votes were cast
        total_votes = sum(votes.values())
        if total_votes == 0:
            return {
                "success": False,
                "error": "No agents were able to vote successfully",
                "reasoning": reasoning
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
            "votes_cast": total_votes,
            "winner_votes": winner_votes,
            "reasoning": reasoning,
            "consensus": winner_votes > num_agents / 2
        }

    except Exception as e:
        logger.error(f"socratic_council failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# Tool Schemas for LLM Integration
# =============================================================================

AGENT_TOOL_SCHEMAS = {
    "agent_spawn": {
        "name": "agent_spawn",
        "description": "Spawn a sub-agent to work on a task independently in the background. Useful for parallel work, research, or time-consuming tasks. Check status with agent_status().",
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
                    "description": "Type of agent: general (any task), researcher (research), coder (code), analyst (analysis), writer (content)"
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (optional, uses default if not specified)"
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
        "description": "Check the status of a spawned agent. Returns pending, running, completed, or failed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID from agent_spawn"
                }
            },
            "required": ["agent_id"]
        }
    },
    "agent_result": {
        "name": "agent_result",
        "description": "Get the result from a completed agent. Returns the agent's output or error.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID from agent_spawn"
                }
            },
            "required": ["agent_id"]
        }
    },
    "agent_list": {
        "name": "agent_list",
        "description": "List all spawned agents with their status. Shows recent agents first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of agents to return (default: 20)"
                }
            },
            "required": []
        }
    },
    "socratic_council": {
        "name": "socratic_council",
        "description": "Run a Socratic council where multiple AI agents independently vote on the best option. Great for decision-making, comparing alternatives, or building consensus.",
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
                    "description": "List of options to choose from (2-5 recommended)"
                },
                "num_agents": {
                    "type": "integer",
                    "description": "Number of agents to vote (default: 3, odd numbers recommended)",
                    "default": 3
                },
                "model": {
                    "type": "string",
                    "description": "Model for voting agents (optional)"
                }
            },
            "required": ["question", "options"]
        }
    }
}
