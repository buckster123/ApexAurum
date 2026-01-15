"""
Tool Processor for Claude API

Handles tool execution, result formatting, and tool calling loops.

This module provides:
1. Tool registration and execution
2. Error handling for tool calls
3. Result formatting for Claude
4. Tool calling loop coordination
5. Streaming support for real-time updates
"""

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Generator

from .tool_adapter import (
    extract_tool_calls_from_response,
    format_tool_result_for_claude,
    format_multiple_tool_results_for_claude,
)
from .analytics_store import get_analytics_store

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for available tools.

    Tools can be registered with their implementation functions and
    executed by name with validated inputs.
    """

    def __init__(self):
        """Initialize empty tool registry."""
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        func: Callable,
        schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a tool function.

        Args:
            name: Tool name (must match schema name)
            func: Callable that implements the tool
            schema: Optional Claude tool schema (for validation)
        """
        self.tools[name] = func
        if schema:
            self.tool_schemas[name] = schema
        logger.info(f"Registered tool: {name}")

    def unregister(self, name: str) -> None:
        """
        Unregister a tool.

        Args:
            name: Tool name to remove
        """
        if name in self.tools:
            del self.tools[name]
        if name in self.tool_schemas:
            del self.tool_schemas[name]
        logger.info(f"Unregistered tool: {name}")

    def has_tool(self, name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            name: Tool name

        Returns:
            True if tool is registered
        """
        return name in self.tools

    def get_tool(self, name: str) -> Optional[Callable]:
        """
        Get a tool function by name.

        Args:
            name: Tool name

        Returns:
            Tool function or None if not found
        """
        return self.tools.get(name)

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a tool's schema.

        Args:
            name: Tool name

        Returns:
            Tool schema or None if not found
        """
        return self.tool_schemas.get(name)

    def list_tools(self) -> List[str]:
        """
        Get list of all registered tool names.

        Returns:
            List of tool names
        """
        return list(self.tools.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        Get all tool schemas.

        Returns:
            List of all Claude tool schemas
        """
        return list(self.tool_schemas.values())


class ToolExecutor:
    """
    Executes tools and formats results for Claude.

    Handles:
    - Tool execution with error handling
    - Argument validation and type coercion
    - Result formatting for Claude API
    - Execution logging and debugging
    """

    def __init__(self, registry: ToolRegistry):
        """
        Initialize tool executor.

        Args:
            registry: Tool registry to use
        """
        self.registry = registry

    def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_use_id: str
    ) -> Tuple[Any, bool]:
        """
        Execute a single tool and return the result.

        Args:
            tool_name: Name of tool to execute
            tool_input: Tool input parameters
            tool_use_id: Tool use ID from Claude

        Returns:
            Tuple of (result, is_error)
        """
        start_time = time.time()
        success = False

        try:
            # Get tool function
            tool_func = self.registry.get_tool(tool_name)
            if not tool_func:
                error_msg = f"Tool not found: {tool_name}"
                logger.error(error_msg)
                return error_msg, True

            # Execute tool
            logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
            result = tool_func(**tool_input)
            logger.info(f"Tool {tool_name} returned: {result}")

            success = True
            return result, False

        except TypeError as e:
            # Argument mismatch
            error_msg = f"Invalid arguments for {tool_name}: {str(e)}"
            logger.error(error_msg)
            return error_msg, True

        except Exception as e:
            # Tool execution error
            error_msg = f"Error executing {tool_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg, True

        finally:
            # Record analytics (non-blocking)
            try:
                duration_ms = (time.time() - start_time) * 1000
                analytics = get_analytics_store()
                analytics.record_tool_call(tool_name, success, duration_ms)
            except Exception as e:
                logger.debug(f"Analytics recording failed: {e}")

    def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls and format results.

        Args:
            tool_calls: List of tool_use blocks from Claude response

        Returns:
            List of result dicts with keys: tool_use_id, result, is_error

        Example:
            >>> tool_calls = [
            ...     {
            ...         "type": "tool_use",
            ...         "id": "toolu_123",
            ...         "name": "add",
            ...         "input": {"a": 2, "b": 3}
            ...     }
            ... ]
            >>> results = executor.execute_tool_calls(tool_calls)
            >>> results[0]
            {"tool_use_id": "toolu_123", "result": 5, "is_error": False}
        """
        results = []

        for tool_call in tool_calls:
            tool_use_id = tool_call["id"]
            tool_name = tool_call["name"]
            tool_input = tool_call.get("input", {})

            # Execute tool
            result, is_error = self.execute_tool(tool_name, tool_input, tool_use_id)

            # Add to results
            results.append({
                "tool_use_id": tool_use_id,
                "result": result,
                "is_error": is_error
            })

        return results

    def process_response_with_tools(
        self,
        response: Any
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Process a Claude response that may contain tool calls.

        Args:
            response: Claude Message object

        Returns:
            Tuple of (text_content, tool_results_message)
            - text_content: Any text content from the response
            - tool_results_message: User message with tool results (if any tools were called)

        Example:
            >>> text, tool_msg = executor.process_response_with_tools(response)
            >>> if tool_msg:
            ...     # Tools were called, append tool results to conversation
            ...     messages.append(tool_msg)
        """
        # Extract text content
        text_content = None
        if response.content:
            for block in response.content:
                if hasattr(block, 'type') and block.type == 'text':
                    text_content = block.text
                    break
                elif isinstance(block, dict) and block.get('type') == 'text':
                    text_content = block.get('text', '')
                    break

        # Extract and execute tool calls
        tool_calls = extract_tool_calls_from_response(response)

        if not tool_calls:
            # No tools called
            return text_content, None

        # Execute tools
        results = self.execute_tool_calls(tool_calls)

        # Format results for Claude
        tool_results_message = format_multiple_tool_results_for_claude(results)

        return text_content, tool_results_message


class ToolCallLoop:
    """
    Manages the tool calling loop for multi-step operations.

    Coordinates:
    1. Send message to Claude
    2. Check for tool calls
    3. Execute tools
    4. Append results
    5. Continue conversation
    6. Repeat until no more tool calls
    """

    def __init__(
        self,
        api_client: Any,
        tool_executor: ToolExecutor,
        max_iterations: int = 10
    ):
        """
        Initialize tool call loop.

        Args:
            api_client: Claude API client
            tool_executor: Tool executor instance
            max_iterations: Maximum number of tool calling iterations
        """
        self.api_client = api_client
        self.tool_executor = tool_executor
        self.max_iterations = max_iterations

    def run(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 64000,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[Any, List[Dict[str, Any]]]:
        """
        Run the tool calling loop until completion.

        Args:
            messages: Conversation messages
            system: System prompt
            model: Model to use
            max_tokens: Max tokens to generate
            tools: Tool schemas
            **kwargs: Additional API parameters

        Returns:
            Tuple of (final_response, updated_messages)

        Example:
            >>> response, messages = loop.run(
            ...     messages=[{"role": "user", "content": "What's 2+2?"}],
            ...     tools=[add_tool_schema]
            ... )
        """
        iteration = 0
        current_messages = messages.copy()

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Tool loop iteration {iteration}/{self.max_iterations}")

            # Call Claude
            response = self.api_client.create_message(
                messages=current_messages,
                system=system,
                model=model,
                max_tokens=max_tokens,
                tools=tools,
                **kwargs
            )

            # Check stop reason
            if not hasattr(response, 'stop_reason'):
                logger.warning("Response has no stop_reason")
                return response, current_messages

            # Add assistant response to messages
            # Extract full content for message history
            assistant_content = []
            for block in response.content:
                if hasattr(block, 'type'):
                    if block.type == 'text':
                        assistant_content.append({"type": "text", "text": block.text})
                    elif block.type == 'tool_use':
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input if hasattr(block, 'input') else {}
                        })

            current_messages.append({
                "role": "assistant",
                "content": assistant_content
            })

            # Check if we're done
            if response.stop_reason == 'end_turn':
                logger.info("Tool loop complete: end_turn")
                return response, current_messages

            elif response.stop_reason == 'tool_use':
                logger.info("Tool use detected, executing tools...")

                # Process tools
                text_content, tool_results_message = self.tool_executor.process_response_with_tools(response)

                if tool_results_message:
                    # Append tool results and continue loop
                    current_messages.append(tool_results_message)
                else:
                    # No tools to execute (shouldn't happen)
                    logger.warning("stop_reason=tool_use but no tools found")
                    return response, current_messages

            else:
                # Other stop reason (max_tokens, stop_sequence, etc.)
                logger.info(f"Tool loop stopped: {response.stop_reason}")
                return response, current_messages

        # Max iterations reached
        logger.warning(f"Tool loop reached max iterations ({self.max_iterations})")
        return response, current_messages

    def run_streaming(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 64000,
        tools: Optional[List[Dict[str, Any]]] = None,
        thinking_budget: Optional[int] = None,
        **kwargs
    ) -> Generator[Dict[str, Any], None, Tuple[Any, List[Dict[str, Any]]]]:
        """
        Run the tool calling loop with streaming support.

        Yields events during execution for real-time UI updates.

        Args:
            messages: Conversation messages
            system: System prompt
            model: Model to use
            max_tokens: Max tokens to generate
            tools: Tool schemas
            thinking_budget: Token budget for extended thinking (enables deep reasoning)
            **kwargs: Additional API parameters

        Yields:
            Event dicts with keys:
            - type: Event type (text_delta, thinking_delta, thinking_start, thinking_end,
                    tool_start, tool_complete, thinking, error, done)
            - data: Event-specific data
            - timestamp: Event timestamp

        Returns:
            Tuple of (final_response, updated_messages)

        Example:
            >>> for event in loop.run_streaming(messages, tools=tools):
            ...     if event['type'] == 'text_delta':
            ...         print(event['data'], end='', flush=True)
            ...     elif event['type'] == 'tool_start':
            ...         print(f"\\n[Running {event['data']['name']}...]")
        """
        from .streaming import StreamingResponseHandler, ToolExecutionTracker

        iteration = 0
        current_messages = messages.copy()
        stream_handler = StreamingResponseHandler(self.api_client)
        tool_tracker = ToolExecutionTracker()
        accumulated_text = ""

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Streaming tool loop iteration {iteration}/{self.max_iterations}")

            # Yield thinking event
            yield {
                "type": "thinking",
                "data": f"Processing (step {iteration})..." if iteration > 1 else "Thinking...",
                "timestamp": time.time()
            }

            # Track assistant content blocks for message history
            assistant_content = []
            tool_uses = []

            # Stream the response
            try:
                for stream_event in stream_handler.stream_message(
                    messages=current_messages,
                    system=system,
                    model=model,
                    max_tokens=max_tokens,
                    tools=tools,
                    thinking_budget=thinking_budget,
                    **kwargs
                ):
                    # Forward text deltas
                    if stream_event.event_type == "text_delta":
                        accumulated_text += stream_event.data
                        yield {
                            "type": "text_delta",
                            "data": stream_event.data,
                            "timestamp": stream_event.timestamp
                        }

                    # Extended thinking events
                    elif stream_event.event_type == "thinking_start":
                        yield {
                            "type": "thinking_start",
                            "data": {},
                            "timestamp": stream_event.timestamp
                        }

                    elif stream_event.event_type == "thinking_delta":
                        yield {
                            "type": "thinking_delta",
                            "data": stream_event.data,
                            "timestamp": stream_event.timestamp
                        }

                    elif stream_event.event_type == "thinking_end":
                        yield {
                            "type": "thinking_end",
                            "data": stream_event.data,
                            "timestamp": stream_event.timestamp
                        }

                    # Tool started
                    elif stream_event.event_type == "tool_start":
                        tool_id = stream_event.data["id"]
                        tool_name = stream_event.data["name"]
                        tool_tracker.start_tool(tool_id, tool_name, {})

                        yield {
                            "type": "tool_start",
                            "data": {
                                "id": tool_id,
                                "name": tool_name
                            },
                            "timestamp": stream_event.timestamp
                        }

                    # Tool input complete
                    elif stream_event.event_type == "tool_input_complete":
                        tool_use = stream_event.data
                        tool_uses.append(tool_use)

                    # Final message received
                    elif stream_event.event_type == "final_message":
                        response = stream_event.data

                        # Extract full content for message history
                        for block in response.content:
                            if hasattr(block, 'type'):
                                if block.type == 'thinking':
                                    # Include thinking blocks for multi-turn continuity
                                    assistant_content.append({
                                        "type": "thinking",
                                        "thinking": block.thinking if hasattr(block, 'thinking') else ""
                                    })
                                elif block.type == 'text':
                                    assistant_content.append({
                                        "type": "text",
                                        "text": block.text
                                    })
                                elif block.type == 'tool_use':
                                    assistant_content.append({
                                        "type": "tool_use",
                                        "id": block.id,
                                        "name": block.name,
                                        "input": block.input if hasattr(block, 'input') else {}
                                    })

                    # Error
                    elif stream_event.event_type == "error":
                        yield {
                            "type": "error",
                            "data": stream_event.data,
                            "timestamp": stream_event.timestamp
                        }
                        # Return early on error
                        return response if 'response' in locals() else None, current_messages

            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield {
                    "type": "error",
                    "data": {"error": str(e), "type": type(e).__name__},
                    "timestamp": time.time()
                }
                return None, current_messages

            # Add assistant message to history
            if assistant_content:
                current_messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })

            # Check stop reason
            if not hasattr(response, 'stop_reason'):
                logger.warning("Response has no stop_reason")
                yield {
                    "type": "done",
                    "data": {"text": accumulated_text},
                    "timestamp": time.time()
                }
                return response, current_messages

            # End of turn - we're done
            if response.stop_reason == 'end_turn':
                logger.info("Streaming tool loop complete: end_turn")
                yield {
                    "type": "done",
                    "data": {"text": accumulated_text},
                    "timestamp": time.time()
                }
                return response, current_messages

            # Tool use - execute tools and continue
            elif response.stop_reason == 'tool_use':
                logger.info("Tool use detected, executing tools...")

                # Extract tool calls from response
                tool_calls = extract_tool_calls_from_response(response)

                if tool_calls:
                    # Execute each tool
                    tool_results = []

                    for tool_call in tool_calls:
                        tool_id = tool_call["id"]
                        tool_name = tool_call["name"]
                        tool_input = tool_call.get("input", {})

                        # Yield tool execution start (with input details)
                        yield {
                            "type": "tool_executing",
                            "data": {
                                "id": tool_id,
                                "name": tool_name,
                                "input": tool_input
                            },
                            "timestamp": time.time()
                        }

                        # Execute tool
                        result, is_error = self.tool_executor.execute_tool(
                            tool_name,
                            tool_input,
                            tool_id
                        )

                        # Track completion
                        tool_tracker.complete_tool(tool_id, result, is_error)

                        # Yield tool completion
                        yield {
                            "type": "tool_complete",
                            "data": {
                                "id": tool_id,
                                "name": tool_name,
                                "result": result,
                                "is_error": is_error,
                                "duration": tool_tracker.get_elapsed_time(tool_id)
                            },
                            "timestamp": time.time()
                        }

                        # Add to results
                        tool_results.append({
                            "tool_use_id": tool_id,
                            "result": result,
                            "is_error": is_error
                        })

                    # Format results for Claude
                    tool_results_message = format_multiple_tool_results_for_claude(tool_results)
                    current_messages.append(tool_results_message)

                    # Continue loop for next iteration
                else:
                    # No tools to execute (shouldn't happen)
                    logger.warning("stop_reason=tool_use but no tools found")
                    yield {
                        "type": "done",
                        "data": {"text": accumulated_text},
                        "timestamp": time.time()
                    }
                    return response, current_messages

            else:
                # Other stop reason (max_tokens, stop_sequence, etc.)
                logger.info(f"Streaming tool loop stopped: {response.stop_reason}")
                yield {
                    "type": "done",
                    "data": {"text": accumulated_text, "stop_reason": response.stop_reason},
                    "timestamp": time.time()
                }
                return response, current_messages

        # Max iterations reached
        logger.warning(f"Streaming tool loop reached max iterations ({self.max_iterations})")
        yield {
            "type": "done",
            "data": {"text": accumulated_text, "max_iterations_reached": True},
            "timestamp": time.time()
        }
        return response, current_messages


# Global registry instance for convenience
_global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _global_registry


def register_tool(
    name: str,
    func: Callable,
    schema: Optional[Dict[str, Any]] = None
) -> None:
    """
    Register a tool in the global registry.

    Args:
        name: Tool name
        func: Tool implementation
        schema: Optional tool schema
    """
    _global_registry.register(name, func, schema)
