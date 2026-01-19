"""
Synthetic Training Data Generator

Generate high-quality tool-calling training data using LLM APIs.
Supports both Claude (Anthropic) and OpenAI-compatible endpoints.

Usage:
    from training.synthetic_generator import SyntheticGenerator

    generator = SyntheticGenerator(api_key="sk-ant-...")
    examples = generator.generate_for_tools(tools, num_per_tool=20)
    generator.save(examples, "training_data.json")
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ToolSchema:
    """Simplified tool schema for generation."""
    name: str
    description: str
    parameters: Dict[str, Any]
    examples: List[str] = field(default_factory=list)  # Example queries

    @classmethod
    def from_anthropic_schema(cls, schema: Dict) -> 'ToolSchema':
        """Convert Anthropic tool schema format."""
        return cls(
            name=schema.get('name', ''),
            description=schema.get('description', ''),
            parameters=schema.get('input_schema', {}).get('properties', {}),
        )

    @classmethod
    def from_openai_schema(cls, schema: Dict) -> 'ToolSchema':
        """Convert OpenAI function schema format."""
        func = schema.get('function', schema)
        return cls(
            name=func.get('name', ''),
            description=func.get('description', ''),
            parameters=func.get('parameters', {}).get('properties', {}),
        )


@dataclass
class TrainingExample:
    """A single training example."""
    user_query: str
    tool_name: str
    tool_arguments: Dict[str, Any]
    assistant_response: Optional[str] = None

    def to_text(self, format: str = "chatml") -> str:
        """Convert to training text format."""
        tool_call = f"{self.tool_name}({json.dumps(self.tool_arguments)})"

        if format == "chatml":
            return f"<|im_start|>user\n{self.user_query}<|im_end|>\n<|im_start|>assistant\n<tool_call>{tool_call}</tool_call><|im_end|>"
        elif format == "alpaca":
            return f"### Instruction:\n{self.user_query}\n\n### Response:\n<tool_call>{tool_call}</tool_call>"
        elif format == "simple":
            return f"User: {self.user_query}\nAssistant: <tool_call>{tool_call}</tool_call>"
        else:
            return f"User: {self.user_query}\nAssistant: <tool_call>{tool_call}</tool_call>"

    def to_dict(self) -> Dict:
        return asdict(self)


# Default tools from reusable_lib
DEFAULT_TOOLS = [
    ToolSchema(
        name="calculator",
        description="Perform basic arithmetic operations",
        parameters={
            "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        examples=[
            "What is 5 plus 3?",
            "Calculate 100 divided by 4",
            "Multiply 7 by 9",
            "What's 15 minus 8?",
        ]
    ),
    ToolSchema(
        name="get_current_time",
        description="Get the current date and time",
        parameters={
            "format": {"type": "string", "enum": ["iso", "human", "date", "time", "timestamp"]},
        },
        examples=[
            "What time is it?",
            "What's today's date?",
            "Give me the current timestamp",
            "What day is it today?",
        ]
    ),
    ToolSchema(
        name="memory_store",
        description="Store information for later retrieval",
        parameters={
            "key": {"type": "string"},
            "value": {"type": "any"},
        },
        examples=[
            "Remember my name is Alice",
            "Save my email as bob@example.com",
            "Store my favorite color as blue",
            "Remember that I prefer dark mode",
        ]
    ),
    ToolSchema(
        name="memory_retrieve",
        description="Retrieve previously stored information",
        parameters={
            "key": {"type": "string"},
        },
        examples=[
            "What's my name?",
            "What's my email address?",
            "What's my favorite color?",
            "What preferences did I set?",
        ]
    ),
    ToolSchema(
        name="memory_search",
        description="Search through stored memories",
        parameters={
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        },
        examples=[
            "Search my memories for preferences",
            "Find anything about email",
            "What have I stored about colors?",
        ]
    ),
    ToolSchema(
        name="random_number",
        description="Generate a random number in a range",
        parameters={
            "min_value": {"type": "integer"},
            "max_value": {"type": "integer"},
        },
        examples=[
            "Give me a random number between 1 and 100",
            "Pick a random number from 1 to 10",
            "Generate a random number between 0 and 1000",
        ]
    ),
    ToolSchema(
        name="count_words",
        description="Count words, characters, and lines in text",
        parameters={
            "text": {"type": "string"},
        },
        examples=[
            "Count the words in 'Hello world how are you'",
            "How many characters in this sentence?",
            "Count words: The quick brown fox",
        ]
    ),
]


class SyntheticGenerator:
    """
    Generate synthetic training data for tool-calling models.

    Uses an LLM to generate diverse, realistic user queries for each tool.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "anthropic",  # "anthropic" or "openai"
        model: str = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the generator.

        Args:
            api_key: API key for the LLM provider
            provider: "anthropic" or "openai"
            model: Model to use for generation
            base_url: Optional custom base URL (for local models)
        """
        self.api_key = api_key
        self.provider = provider
        self.base_url = base_url
        self.model = model or self._default_model()
        self.client = None

        if api_key:
            self._init_client()

    def _default_model(self) -> str:
        if self.provider == "anthropic":
            return "claude-sonnet-4-20250514"
        else:
            return "gpt-4o-mini"

    def _init_client(self):
        """Initialize the API client."""
        if self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"Initialized Anthropic client with model {self.model}")
            except ImportError:
                raise ImportError("pip install anthropic")
        else:
            try:
                from openai import OpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self.client = OpenAI(**kwargs)
                logger.info(f"Initialized OpenAI client with model {self.model}")
            except ImportError:
                raise ImportError("pip install openai")

    def generate_queries_llm(
        self,
        tool: ToolSchema,
        num_examples: int = 20,
        temperature: float = 0.9,
    ) -> List[str]:
        """
        Use LLM to generate diverse user queries for a tool.

        Args:
            tool: Tool schema to generate queries for
            num_examples: Number of queries to generate
            temperature: Higher = more diverse

        Returns:
            List of user query strings
        """
        if not self.client:
            raise ValueError("No API client initialized. Provide api_key.")

        prompt = f"""Generate {num_examples} diverse, natural user queries that would require using this tool:

Tool: {tool.name}
Description: {tool.description}
Parameters: {json.dumps(tool.parameters, indent=2)}

Example queries for reference:
{chr(10).join(f'- {ex}' for ex in tool.examples[:3])}

Generate {num_examples} NEW, diverse queries. Include:
- Different phrasings and tones (casual, formal, urgent)
- Different parameter values
- Edge cases and variations
- Questions and commands

Output ONLY the queries, one per line, no numbering or bullets."""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.choices[0].message.content

            # Parse queries
            queries = [q.strip() for q in text.strip().split('\n') if q.strip()]
            queries = [q.lstrip('0123456789.-) ') for q in queries]  # Remove numbering

            logger.info(f"Generated {len(queries)} queries for {tool.name}")
            return queries[:num_examples]

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return tool.examples  # Fallback to built-in examples

    def generate_arguments_llm(
        self,
        tool: ToolSchema,
        query: str,
    ) -> Dict[str, Any]:
        """
        Use LLM to generate appropriate tool arguments for a query.
        """
        if not self.client:
            raise ValueError("No API client initialized")

        prompt = f"""Given this user query and tool, generate the exact arguments to call the tool.

User query: {query}

Tool: {tool.name}
Parameters: {json.dumps(tool.parameters, indent=2)}

Output ONLY valid JSON with the arguments. Example: {{"param1": "value1", "param2": 123}}"""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    temperature=0.3,  # Lower for accuracy
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=500,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.choices[0].message.content

            # Extract JSON
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            return json.loads(text)

        except Exception as e:
            logger.warning(f"Failed to generate arguments: {e}")
            return self._generate_arguments_rule_based(tool, query)

    def _generate_arguments_rule_based(
        self,
        tool: ToolSchema,
        query: str,
    ) -> Dict[str, Any]:
        """Rule-based argument generation as fallback."""
        import re
        args = {}
        query_lower = query.lower()

        if tool.name == "calculator":
            # Extract numbers and operation
            numbers = re.findall(r'\d+', query)
            if len(numbers) >= 2:
                args["a"] = int(numbers[0])
                args["b"] = int(numbers[1])
            else:
                args["a"] = random.randint(1, 100)
                args["b"] = random.randint(1, 100)

            if any(w in query_lower for w in ["add", "plus", "sum", "+"]):
                args["operation"] = "add"
            elif any(w in query_lower for w in ["subtract", "minus", "-"]):
                args["operation"] = "subtract"
            elif any(w in query_lower for w in ["multiply", "times", "*", "x"]):
                args["operation"] = "multiply"
            elif any(w in query_lower for w in ["divide", "divided", "/"]):
                args["operation"] = "divide"
            else:
                args["operation"] = random.choice(["add", "subtract", "multiply", "divide"])

        elif tool.name == "get_current_time":
            if "timestamp" in query_lower:
                args["format"] = "timestamp"
            elif "date" in query_lower:
                args["format"] = "date"
            elif "time" in query_lower and "date" not in query_lower:
                args["format"] = "time"
            else:
                args["format"] = "human"

        elif tool.name == "memory_store":
            # Try to extract key-value from query
            args["key"] = "user_preference"
            args["value"] = query

            if "name" in query_lower:
                args["key"] = "user_name"
                # Try to extract name
                match = re.search(r"(?:name is|i'm|i am|called)\s+(\w+)", query_lower)
                if match:
                    args["value"] = match.group(1).title()
            elif "email" in query_lower:
                args["key"] = "email"
                match = re.search(r'[\w\.-]+@[\w\.-]+', query)
                if match:
                    args["value"] = match.group(0)
            elif "color" in query_lower:
                args["key"] = "favorite_color"
                for color in ["red", "blue", "green", "yellow", "purple", "orange", "pink"]:
                    if color in query_lower:
                        args["value"] = color
                        break

        elif tool.name == "memory_retrieve":
            if "name" in query_lower:
                args["key"] = "user_name"
            elif "email" in query_lower:
                args["key"] = "email"
            elif "color" in query_lower:
                args["key"] = "favorite_color"
            else:
                args["key"] = "user_preference"

        elif tool.name == "random_number":
            numbers = re.findall(r'\d+', query)
            if len(numbers) >= 2:
                args["min_value"] = int(numbers[0])
                args["max_value"] = int(numbers[1])
            else:
                args["min_value"] = 1
                args["max_value"] = 100

        elif tool.name == "count_words":
            # Extract quoted text or use the query itself
            match = re.search(r"['\"](.+?)['\"]", query)
            if match:
                args["text"] = match.group(1)
            else:
                args["text"] = query

        return args

    def generate_for_tool(
        self,
        tool: ToolSchema,
        num_examples: int = 20,
        use_llm_for_queries: bool = True,
        use_llm_for_args: bool = False,  # Rule-based is often good enough
    ) -> List[TrainingExample]:
        """
        Generate training examples for a single tool.

        Args:
            tool: Tool schema
            num_examples: Number of examples to generate
            use_llm_for_queries: Use LLM to generate diverse queries
            use_llm_for_args: Use LLM to generate arguments (slower but more accurate)

        Returns:
            List of TrainingExample objects
        """
        examples = []

        # Get queries
        if use_llm_for_queries and self.client:
            queries = self.generate_queries_llm(tool, num_examples)
        else:
            # Use built-in examples with variations
            queries = tool.examples * (num_examples // len(tool.examples) + 1)
            queries = queries[:num_examples]

        # Generate arguments for each query
        for query in queries:
            if use_llm_for_args and self.client:
                args = self.generate_arguments_llm(tool, query)
            else:
                args = self._generate_arguments_rule_based(tool, query)

            examples.append(TrainingExample(
                user_query=query,
                tool_name=tool.name,
                tool_arguments=args,
            ))

        return examples

    def generate_for_tools(
        self,
        tools: List[ToolSchema] = None,
        num_per_tool: int = 20,
        use_llm: bool = True,
    ) -> List[TrainingExample]:
        """
        Generate training examples for multiple tools.

        Args:
            tools: List of tool schemas (defaults to DEFAULT_TOOLS)
            num_per_tool: Examples per tool
            use_llm: Use LLM for query generation

        Returns:
            List of all training examples
        """
        if tools is None:
            tools = DEFAULT_TOOLS

        all_examples = []

        for tool in tools:
            logger.info(f"Generating {num_per_tool} examples for {tool.name}...")
            examples = self.generate_for_tool(
                tool,
                num_examples=num_per_tool,
                use_llm_for_queries=use_llm,
            )
            all_examples.extend(examples)

            # Rate limiting
            if use_llm and self.client:
                time.sleep(1)

        # Shuffle
        random.shuffle(all_examples)

        logger.info(f"Generated {len(all_examples)} total examples")
        return all_examples

    def generate_without_llm(
        self,
        tools: List[ToolSchema] = None,
        num_per_tool: int = 50,
    ) -> List[TrainingExample]:
        """
        Generate examples using only rule-based methods (no API needed).

        Good for quick testing or when you want to avoid API costs.
        """
        if tools is None:
            tools = DEFAULT_TOOLS

        all_examples = []

        for tool in tools:
            # Use built-in examples with augmentation
            base_queries = tool.examples.copy()

            # Add variations
            augmented = []
            for q in base_queries:
                augmented.append(q)
                augmented.append(q.lower())
                augmented.append(q + " please")
                augmented.append("Can you " + q.lower())
                augmented.append("I need you to " + q.lower())
                augmented.append(q.rstrip('?') + " for me")

            # Sample to desired count
            queries = random.choices(augmented, k=num_per_tool)

            for query in queries:
                args = self._generate_arguments_rule_based(tool, query)
                all_examples.append(TrainingExample(
                    user_query=query,
                    tool_name=tool.name,
                    tool_arguments=args,
                ))

        random.shuffle(all_examples)
        logger.info(f"Generated {len(all_examples)} examples (rule-based)")
        return all_examples

    def save(
        self,
        examples: List[TrainingExample],
        path: str,
        format: str = "jsonl",
    ) -> int:
        """
        Save examples to file.

        Args:
            examples: List of training examples
            path: Output file path
            format: "jsonl", "json", or "text"

        Returns:
            Number of examples saved
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        if format == "jsonl":
            with open(path, 'w') as f:
                for ex in examples:
                    f.write(json.dumps(ex.to_dict()) + '\n')

        elif format == "json":
            with open(path, 'w') as f:
                json.dump([ex.to_dict() for ex in examples], f, indent=2)

        elif format == "text":
            with open(path, 'w') as f:
                for ex in examples:
                    f.write(ex.to_text("simple") + '\n\n')

        logger.info(f"Saved {len(examples)} examples to {path}")
        return len(examples)

    def load(self, path: str) -> List[TrainingExample]:
        """Load examples from file."""
        examples = []

        with open(path, 'r') as f:
            if path.endswith('.jsonl'):
                for line in f:
                    data = json.loads(line)
                    examples.append(TrainingExample(**data))
            else:
                data = json.load(f)
                for item in data:
                    examples.append(TrainingExample(**item))

        return examples


def generate_training_data(
    output_path: str = "tool_training_data.jsonl",
    num_per_tool: int = 50,
    api_key: Optional[str] = None,
    use_llm: bool = False,
) -> List[TrainingExample]:
    """
    Convenience function to generate training data.

    Args:
        output_path: Where to save the data
        num_per_tool: Examples per tool
        api_key: Anthropic API key (optional, enables LLM generation)
        use_llm: Whether to use LLM for query generation

    Returns:
        List of generated examples
    """
    generator = SyntheticGenerator(api_key=api_key) if api_key else SyntheticGenerator()

    if use_llm and api_key:
        examples = generator.generate_for_tools(num_per_tool=num_per_tool, use_llm=True)
    else:
        examples = generator.generate_without_llm(num_per_tool=num_per_tool)

    generator.save(examples, output_path)

    return examples


# CLI
if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Generate synthetic training data")
    parser.add_argument("--output", "-o", default="training_data.jsonl", help="Output file")
    parser.add_argument("--num", "-n", type=int, default=50, help="Examples per tool")
    parser.add_argument("--api-key", help="Anthropic API key for LLM generation")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM for generation")
    parser.add_argument("--format", choices=["jsonl", "json", "text"], default="jsonl")

    args = parser.parse_args()

    examples = generate_training_data(
        output_path=args.output,
        num_per_tool=args.num,
        api_key=args.api_key,
        use_llm=args.use_llm,
    )

    print(f"\nGenerated {len(examples)} training examples")
    print(f"Saved to: {args.output}")

    # Show sample
    print("\nSample examples:")
    for ex in examples[:3]:
        print(f"  User: {ex.user_query}")
        print(f"  Tool: {ex.tool_name}({ex.tool_arguments})")
        print()
