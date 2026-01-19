"""
Training Data Extractor

Extract fine-tuning datasets from AI conversation logs.
Generates training examples for teaching small models to:
- Route user requests to appropriate tools
- Generate correct tool call arguments
- Handle multi-turn conversations

Output Formats:
- Alpaca: Instruction/input/output format (Llama fine-tuning)
- ChatML: OpenAI chat format (Qwen, Mistral)
- ShareGPT: Multi-turn conversation format
- ToolCall: Specialized function-calling format
- JSONL: Raw examples for custom processing

Usage:
    from reusable_lib.training import TrainingDataExtractor, ExportFormat

    # Load conversations and extract training data
    extractor = TrainingDataExtractor()
    extractor.load_conversations("./sandbox/conversations.json")

    # Generate dataset
    dataset = extractor.extract_tool_call_examples()

    # Export in different formats
    extractor.export(dataset, "training_data.jsonl", ExportFormat.ALPACA)
    extractor.export(dataset, "training_data_chatml.jsonl", ExportFormat.CHATML)
"""

import json
import logging
import hashlib
from pathlib import Path
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Generator
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats for training data."""
    ALPACA = "alpaca"           # Instruction/input/output (Llama)
    CHATML = "chatml"           # OpenAI chat format (Qwen, Mistral)
    SHAREGPT = "sharegpt"       # Multi-turn conversations
    TOOLCALL = "toolcall"       # Function-calling specific
    JSONL = "jsonl"             # Raw format for custom processing


@dataclass
class ToolCallExample:
    """A single tool call extracted from a conversation."""
    user_message: str                    # What the user said
    tool_name: str                       # Which tool was called
    tool_arguments: Dict[str, Any]       # Arguments passed to tool
    tool_result: Optional[str] = None    # Result (if available)
    assistant_response: Optional[str] = None  # Final response to user
    conversation_id: str = ""            # Source conversation
    timestamp: Optional[str] = None      # When it occurred

    # Context (optional, for multi-turn)
    previous_messages: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def get_hash(self) -> str:
        """Generate unique hash for deduplication."""
        content = f"{self.user_message}:{self.tool_name}:{json.dumps(self.tool_arguments, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class TrainingExample:
    """A formatted training example ready for export."""
    instruction: str                     # System instruction
    input: str                          # User input
    output: str                         # Expected output
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_alpaca(self) -> Dict[str, str]:
        """Convert to Alpaca format."""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output
        }

    def to_chatml(self) -> Dict[str, Any]:
        """Convert to ChatML format."""
        messages = []
        if self.instruction:
            messages.append({"role": "system", "content": self.instruction})
        messages.append({"role": "user", "content": self.input})
        messages.append({"role": "assistant", "content": self.output})
        return {"messages": messages}

    def to_sharegpt(self) -> Dict[str, Any]:
        """Convert to ShareGPT format."""
        conversations = []
        if self.instruction:
            conversations.append({"from": "system", "value": self.instruction})
        conversations.append({"from": "human", "value": self.input})
        conversations.append({"from": "gpt", "value": self.output})
        return {"conversations": conversations}

    def to_toolcall(self) -> Dict[str, Any]:
        """Convert to function-calling format."""
        return {
            "messages": [
                {"role": "user", "content": self.input}
            ],
            "tools": self.metadata.get("tools", []),
            "tool_calls": self.metadata.get("tool_calls", []),
            "tool_results": self.metadata.get("tool_results", [])
        }


class ConversationParser:
    """Parse conversation logs to extract structured data."""

    def __init__(self, conversations: List[Dict[str, Any]]):
        self.conversations = conversations
        self.tool_calls: List[ToolCallExample] = []

    def parse_all(self) -> List[ToolCallExample]:
        """Parse all conversations and extract tool calls."""
        self.tool_calls = []

        for conv in self.conversations:
            conv_id = conv.get("id", "unknown")
            messages = conv.get("messages", [])

            examples = self._parse_conversation(messages, conv_id)
            self.tool_calls.extend(examples)

        logger.info(f"Extracted {len(self.tool_calls)} tool call examples from {len(self.conversations)} conversations")
        return self.tool_calls

    def _parse_conversation(
        self,
        messages: List[Dict[str, Any]],
        conv_id: str
    ) -> List[ToolCallExample]:
        """Parse a single conversation for tool calls."""
        examples = []
        context_buffer = []  # Track conversation context

        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Track user messages for context
            if role == "user":
                user_text = self._extract_text_content(content)
                if user_text:
                    context_buffer.append({"role": "user", "content": user_text})

                    # Look ahead for assistant response with tool calls
                    if i + 1 < len(messages):
                        next_msg = messages[i + 1]
                        if next_msg.get("role") == "assistant":
                            tool_calls = self._extract_tool_calls(next_msg.get("content", ""))

                            for tool_call in tool_calls:
                                # Look for tool result
                                tool_result = self._find_tool_result(
                                    messages[i+2:i+5],
                                    tool_call.get("id", "")
                                )

                                # Look for final assistant response
                                final_response = self._find_final_response(
                                    messages[i+2:i+10]
                                )

                                example = ToolCallExample(
                                    user_message=user_text,
                                    tool_name=tool_call.get("name", ""),
                                    tool_arguments=tool_call.get("input", {}),
                                    tool_result=tool_result,
                                    assistant_response=final_response,
                                    conversation_id=conv_id,
                                    previous_messages=context_buffer[:-1].copy() if len(context_buffer) > 1 else []
                                )
                                examples.append(example)

            # Track assistant responses for context
            elif role == "assistant":
                assistant_text = self._extract_text_content(content)
                if assistant_text:
                    context_buffer.append({"role": "assistant", "content": assistant_text})

            # Keep context buffer reasonable size
            if len(context_buffer) > 10:
                context_buffer = context_buffer[-10:]

            i += 1

        return examples

    def _extract_text_content(self, content: Any) -> str:
        """Extract text from various content formats."""
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
            return " ".join(text_parts).strip()

        return ""

    def _extract_tool_calls(self, content: Any) -> List[Dict[str, Any]]:
        """Extract tool_use blocks from assistant content."""
        tool_calls = []

        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_calls.append({
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "input": item.get("input", {})
                    })

        return tool_calls

    def _find_tool_result(
        self,
        messages: List[Dict[str, Any]],
        tool_id: str
    ) -> Optional[str]:
        """Find tool result for a specific tool call."""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            if item.get("tool_use_id") == tool_id:
                                result = item.get("content", "")
                                if isinstance(result, str):
                                    return result[:500]  # Truncate long results
        return None

    def _find_final_response(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Find the final assistant text response after tool execution."""
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                text = self._extract_text_content(content)
                if text and len(text) > 10:  # Skip very short responses
                    return text[:1000]  # Truncate long responses
        return None


class TrainingDataExtractor:
    """
    Main class for extracting and formatting training data.

    Workflow:
    1. Load conversation logs
    2. Parse and extract tool call examples
    3. Apply filters and deduplication
    4. Format for target training framework
    5. Export to file
    """

    # Default system prompts for different training objectives
    SYSTEM_PROMPTS = {
        "tool_routing": (
            "You are an AI assistant with access to tools. "
            "When the user makes a request, determine if a tool should be called "
            "and respond with the appropriate tool call in JSON format."
        ),
        "tool_routing_detailed": (
            "You are an AI assistant with access to the following tools:\n"
            "{tools_description}\n\n"
            "Analyze the user's request and respond with a tool call if appropriate. "
            "Format: {{\"tool\": \"tool_name\", \"arguments\": {{...}}}}"
        ),
        "general_assistant": (
            "You are a helpful AI assistant. Respond to the user's request "
            "clearly and concisely."
        ),
    }

    def __init__(self, tool_schemas: Optional[Dict[str, Dict]] = None):
        """
        Initialize extractor.

        Args:
            tool_schemas: Optional dict of tool name -> schema for validation
        """
        self.conversations: List[Dict[str, Any]] = []
        self.tool_schemas = tool_schemas or {}
        self.tool_calls: List[ToolCallExample] = []

    def load_conversations(self, path: str) -> int:
        """
        Load conversations from JSON file.

        Args:
            path: Path to conversations.json file

        Returns:
            Number of conversations loaded
        """
        path = Path(path)
        if not path.exists():
            logger.warning(f"Conversations file not found: {path}")
            return 0

        with open(path, "r") as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, list):
            self.conversations = data
        elif isinstance(data, dict):
            self.conversations = list(data.values())
        else:
            logger.error(f"Unexpected data format in {path}")
            return 0

        logger.info(f"Loaded {len(self.conversations)} conversations from {path}")
        return len(self.conversations)

    def load_conversations_from_dict(self, conversations: List[Dict[str, Any]]) -> int:
        """Load conversations directly from a list."""
        self.conversations = conversations
        return len(self.conversations)

    def extract_tool_call_examples(
        self,
        min_user_length: int = 5,
        deduplicate: bool = True
    ) -> List[ToolCallExample]:
        """
        Extract tool call examples from loaded conversations.

        Args:
            min_user_length: Minimum user message length to include
            deduplicate: Remove duplicate examples

        Returns:
            List of ToolCallExample objects
        """
        parser = ConversationParser(self.conversations)
        examples = parser.parse_all()

        # Filter short messages
        examples = [e for e in examples if len(e.user_message) >= min_user_length]

        # Filter empty tool names
        examples = [e for e in examples if e.tool_name]

        # Deduplicate
        if deduplicate:
            seen = set()
            unique = []
            for e in examples:
                h = e.get_hash()
                if h not in seen:
                    seen.add(h)
                    unique.append(e)
            examples = unique
            logger.info(f"After deduplication: {len(examples)} unique examples")

        self.tool_calls = examples
        return examples

    def filter_by_tools(
        self,
        tool_names: List[str],
        examples: Optional[List[ToolCallExample]] = None
    ) -> List[ToolCallExample]:
        """Filter examples to only include specific tools."""
        examples = examples or self.tool_calls
        return [e for e in examples if e.tool_name in tool_names]

    def filter_by_quality(
        self,
        examples: Optional[List[ToolCallExample]] = None,
        require_result: bool = False,
        require_response: bool = False,
        min_args: int = 0
    ) -> List[ToolCallExample]:
        """Filter examples by quality criteria."""
        examples = examples or self.tool_calls
        filtered = []

        for e in examples:
            if require_result and not e.tool_result:
                continue
            if require_response and not e.assistant_response:
                continue
            if len(e.tool_arguments) < min_args:
                continue
            filtered.append(e)

        return filtered

    def to_training_examples(
        self,
        examples: Optional[List[ToolCallExample]] = None,
        system_prompt: str = "tool_routing",
        include_context: bool = False,
        include_result: bool = False
    ) -> List[TrainingExample]:
        """
        Convert tool call examples to training format.

        Args:
            examples: Tool call examples (uses self.tool_calls if None)
            system_prompt: Key from SYSTEM_PROMPTS or custom string
            include_context: Include previous conversation turns
            include_result: Include tool result in output

        Returns:
            List of TrainingExample objects
        """
        examples = examples or self.tool_calls
        training = []

        # Resolve system prompt
        if system_prompt in self.SYSTEM_PROMPTS:
            instruction = self.SYSTEM_PROMPTS[system_prompt]
        else:
            instruction = system_prompt

        for e in examples:
            # Build input
            if include_context and e.previous_messages:
                context = "\n".join([
                    f"{m['role'].title()}: {m['content']}"
                    for m in e.previous_messages[-3:]  # Last 3 turns
                ])
                input_text = f"Previous conversation:\n{context}\n\nUser: {e.user_message}"
            else:
                input_text = e.user_message

            # Build output (the tool call)
            tool_call = {
                "tool": e.tool_name,
                "arguments": e.tool_arguments
            }

            if include_result and e.tool_result:
                output = json.dumps({
                    "tool_call": tool_call,
                    "result": e.tool_result[:200]
                }, indent=2)
            else:
                output = json.dumps(tool_call, indent=2)

            # Metadata for toolcall format
            metadata = {
                "tool_name": e.tool_name,
                "conversation_id": e.conversation_id,
                "tools": [self.tool_schemas.get(e.tool_name, {"name": e.tool_name})],
                "tool_calls": [tool_call],
                "tool_results": [e.tool_result] if e.tool_result else []
            }

            training.append(TrainingExample(
                instruction=instruction,
                input=input_text,
                output=output,
                metadata=metadata
            ))

        logger.info(f"Generated {len(training)} training examples")
        return training

    def export(
        self,
        examples: List[TrainingExample],
        output_path: str,
        format: ExportFormat = ExportFormat.ALPACA,
        pretty: bool = False
    ) -> int:
        """
        Export training examples to file.

        Args:
            examples: Training examples to export
            output_path: Output file path
            format: Export format
            pretty: Pretty-print JSON (increases file size)

        Returns:
            Number of examples exported
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        indent = 2 if pretty else None

        with open(output_path, "w") as f:
            for example in examples:
                if format == ExportFormat.ALPACA:
                    data = example.to_alpaca()
                elif format == ExportFormat.CHATML:
                    data = example.to_chatml()
                elif format == ExportFormat.SHAREGPT:
                    data = example.to_sharegpt()
                elif format == ExportFormat.TOOLCALL:
                    data = example.to_toolcall()
                else:  # JSONL
                    data = {
                        "instruction": example.instruction,
                        "input": example.input,
                        "output": example.output,
                        "metadata": example.metadata
                    }

                f.write(json.dumps(data, indent=indent) + "\n")

        logger.info(f"Exported {len(examples)} examples to {output_path} ({format.value} format)")
        return len(examples)

    def get_tool_statistics(
        self,
        examples: Optional[List[ToolCallExample]] = None
    ) -> Dict[str, Any]:
        """Get statistics about extracted tool calls."""
        examples = examples or self.tool_calls

        tool_counts = {}
        arg_counts = {}

        for e in examples:
            tool_counts[e.tool_name] = tool_counts.get(e.tool_name, 0) + 1
            arg_counts[e.tool_name] = arg_counts.get(e.tool_name, [])
            arg_counts[e.tool_name].append(len(e.tool_arguments))

        # Calculate averages
        avg_args = {
            tool: sum(counts) / len(counts) if counts else 0
            for tool, counts in arg_counts.items()
        }

        return {
            "total_examples": len(examples),
            "unique_tools": len(tool_counts),
            "tool_counts": dict(sorted(tool_counts.items(), key=lambda x: -x[1])),
            "average_arguments_per_tool": avg_args,
            "examples_with_results": sum(1 for e in examples if e.tool_result),
            "examples_with_context": sum(1 for e in examples if e.previous_messages)
        }

    def generate_splits(
        self,
        examples: List[TrainingExample],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        shuffle: bool = True,
        seed: int = 42
    ) -> Tuple[List[TrainingExample], List[TrainingExample], List[TrainingExample]]:
        """
        Split examples into train/val/test sets.

        Args:
            examples: Examples to split
            train_ratio: Proportion for training
            val_ratio: Proportion for validation
            test_ratio: Proportion for testing
            shuffle: Randomly shuffle before splitting
            seed: Random seed for reproducibility

        Returns:
            Tuple of (train, val, test) example lists
        """
        import random

        if shuffle:
            random.seed(seed)
            examples = examples.copy()
            random.shuffle(examples)

        n = len(examples)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)

        train = examples[:train_end]
        val = examples[train_end:val_end]
        test = examples[val_end:]

        logger.info(f"Split: {len(train)} train, {len(val)} val, {len(test)} test")
        return train, val, test


# Convenience functions

def extract_tool_calls_from_conversations(
    conversations_path: str,
    tool_names: Optional[List[str]] = None,
    deduplicate: bool = True
) -> List[ToolCallExample]:
    """
    Quick extraction of tool calls from a conversations file.

    Args:
        conversations_path: Path to conversations.json
        tool_names: Optional filter for specific tools
        deduplicate: Remove duplicate examples

    Returns:
        List of ToolCallExample objects
    """
    extractor = TrainingDataExtractor()
    extractor.load_conversations(conversations_path)
    examples = extractor.extract_tool_call_examples(deduplicate=deduplicate)

    if tool_names:
        examples = extractor.filter_by_tools(tool_names, examples)

    return examples


def generate_training_dataset(
    conversations_path: str,
    output_path: str,
    format: ExportFormat = ExportFormat.ALPACA,
    tool_names: Optional[List[str]] = None,
    system_prompt: str = "tool_routing",
    include_context: bool = False
) -> Dict[str, Any]:
    """
    One-shot function to generate a training dataset.

    Args:
        conversations_path: Path to conversations.json
        output_path: Output file path
        format: Export format
        tool_names: Optional filter for specific tools
        system_prompt: System prompt key or custom string
        include_context: Include conversation context

    Returns:
        Statistics about the generated dataset
    """
    extractor = TrainingDataExtractor()
    extractor.load_conversations(conversations_path)

    examples = extractor.extract_tool_call_examples()

    if tool_names:
        examples = extractor.filter_by_tools(tool_names, examples)

    training = extractor.to_training_examples(
        examples,
        system_prompt=system_prompt,
        include_context=include_context
    )

    count = extractor.export(training, output_path, format)
    stats = extractor.get_tool_statistics(examples)
    stats["exported_count"] = count
    stats["output_path"] = str(output_path)
    stats["format"] = format.value

    return stats
