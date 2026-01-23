#!/usr/bin/env python3
"""
ApexAurum Training Data Generator

Automatically generates fine-tuning datasets from ApexAurum's tool system.
Extracts schemas from all 88 tools and generates diverse training examples.

Usage:
    python apex_data_generator.py --generate 500
    python apex_data_generator.py --extract ./sandbox/conversations.json
    python apex_data_generator.py --full-pipeline
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_apex_tools() -> Dict[str, Dict]:
    """Load all ApexAurum tool schemas."""
    try:
        from tools import ALL_TOOL_SCHEMAS
        logger.info(f"Loaded {len(ALL_TOOL_SCHEMAS)} ApexAurum tool schemas")
        return ALL_TOOL_SCHEMAS
    except ImportError as e:
        logger.warning(f"Could not import ApexAurum tools: {e}")
        return {}


def schema_to_tool(name: str, schema: Dict) -> 'ToolSchema':
    """Convert ApexAurum schema to ToolSchema format."""
    from synthetic_generator import ToolSchema

    # Extract description
    description = schema.get('description', f"Tool: {name}")

    # Extract parameters
    input_schema = schema.get('input_schema', {})
    parameters = input_schema.get('properties', {})

    # Generate example queries based on name and description
    examples = generate_example_queries(name, description, parameters)

    return ToolSchema(
        name=name,
        description=description,
        parameters=parameters,
        examples=examples
    )


def generate_example_queries(name: str, description: str, params: Dict) -> List[str]:
    """Generate example user queries for a tool."""
    examples = []

    # Tool-specific examples
    tool_examples = {
        # Utilities
        'get_current_time': ["What time is it?", "What's today's date?", "Current timestamp please"],
        'calculator': ["What is 5 plus 3?", "Calculate 100 divided by 4", "Multiply 7 by 9"],
        'count_words': ["How many words in 'hello world'?", "Count characters in this text"],
        'random_number': ["Give me a random number between 1 and 100", "Pick a number from 1 to 10"],

        # Memory
        'memory_store': ["Remember my name is Alice", "Save my email as test@example.com"],
        'memory_retrieve': ["What's my name?", "What email did I save?"],
        'memory_search': ["Search my memories for preferences", "Find anything about colors"],
        'memory_list': ["Show all my memories", "List everything you remember"],
        'memory_delete': ["Forget my email", "Delete the key 'name'"],

        # Filesystem
        'fs_read_file': ["Read the file config.json", "Show me the contents of main.py"],
        'fs_write_file': ["Write 'hello' to test.txt", "Create a file called notes.txt"],
        'fs_list_files': ["List files in the current directory", "Show me what's in ./sandbox"],
        'fs_mkdir': ["Create a folder called 'output'", "Make directory 'data'"],
        'fs_delete': ["Delete the file temp.txt", "Remove the folder 'old'"],
        'fs_exists': ["Does config.json exist?", "Check if ./data folder exists"],

        # Code execution
        'execute_python': ["Run this Python code: print('hello')", "Execute: 2+2"],
        'execute_python_safe': ["Safely run: import math; print(math.pi)"],

        # Vector search
        'vector_add': ["Add this document to the knowledge base", "Store this text in vectors"],
        'vector_search': ["Search for documents about AI", "Find similar content to 'machine learning'"],
        'vector_add_knowledge': ["Remember this fact: The sky is blue", "Add to knowledge: Python was created in 1991"],
        'vector_search_knowledge': ["What do you know about Python?", "Search knowledge for AI facts"],

        # Agents
        'agent_spawn': ["Start a research agent to find information about quantum computing"],
        'agent_status': ["Check the status of agent abc123", "Is the agent done?"],
        'agent_result': ["Get the results from agent abc123", "What did the agent find?"],
        'agent_list': ["List all running agents", "Show me active agents"],
        'socratic_council': ["Ask the council: What is consciousness?"],

        # Music
        'music_generate': ["Generate a song about summer with a happy vibe"],
        'music_status': ["Check status of music task xyz", "Is my song ready?"],
        'music_list': ["Show my recent music generations", "List generated songs"],
        'music_favorite': ["Add this song to favorites", "Mark task xyz as favorite"],
        'music_search': ["Search for songs about love", "Find my upbeat tracks"],

        # Hailo Vision
        'hailo_info': ["What's the Hailo device status?", "Show Hailo chip info"],
        'hailo_detect': ["Detect objects in this image", "What objects are in photo.jpg?"],
        'hailo_classify': ["Classify this image", "What is in this picture?"],
        'hailo_pose': ["Detect poses in this image", "Find people and their poses"],
        'hailo_benchmark': ["Run a Hailo benchmark", "Test Hailo performance"],

        # EEG
        'eeg_connect': ["Connect to the EEG device", "Start EEG session"],
        'eeg_stream_start': ["Start EEG data streaming", "Begin recording brain waves"],
        'eeg_experience_get': ["Get current brain state", "How am I feeling neurologically?"],

        # Audio
        'audio_info': ["Get info about song.mp3", "What's the duration of this audio?"],
        'audio_trim': ["Trim the audio from 10s to 30s", "Cut the first 5 seconds"],
        'audio_normalize': ["Normalize the audio volume", "Make the audio louder"],

        # Datasets
        'dataset_list': ["List available datasets", "What datasets do I have?"],
        'dataset_query': ["Search the python_docs dataset for 'exceptions'"],
    }

    # Get specific examples or generate generic ones
    if name in tool_examples:
        examples = tool_examples[name]
    else:
        # Generate from description
        desc_lower = description.lower()
        examples = [
            f"Use {name}",
            f"Call the {name} tool",
            description if len(description) < 50 else f"{description[:50]}...",
        ]

        # Add parameter-based examples
        for param in list(params.keys())[:2]:
            examples.append(f"Run {name} with {param}")

    return examples


def generate_apex_training_data(
    output_path: str = "apex_training_data.jsonl",
    num_per_tool: int = 10,
    tool_filter: Optional[List[str]] = None,
) -> int:
    """
    Generate training data from ApexAurum tool schemas.

    Args:
        output_path: Where to save the training data
        num_per_tool: Examples per tool (more = bigger dataset)
        tool_filter: Optional list of tool names to include

    Returns:
        Number of examples generated
    """
    from synthetic_generator import SyntheticGenerator, ToolSchema

    # Load ApexAurum tools
    apex_schemas = get_apex_tools()

    if not apex_schemas:
        logger.error("No ApexAurum tools found!")
        return 0

    # Filter if requested
    if tool_filter:
        apex_schemas = {k: v for k, v in apex_schemas.items() if k in tool_filter}
        logger.info(f"Filtered to {len(apex_schemas)} tools")

    # Convert to ToolSchema format
    tools = []
    for name, schema in apex_schemas.items():
        try:
            tool = schema_to_tool(name, schema)
            tools.append(tool)
        except Exception as e:
            logger.warning(f"Could not convert tool {name}: {e}")

    logger.info(f"Prepared {len(tools)} tools for data generation")

    # Generate training data
    generator = SyntheticGenerator()
    examples = generator.generate_without_llm(tools=tools, num_per_tool=num_per_tool)

    # Save
    generator.save(examples, output_path)

    logger.info(f"Generated {len(examples)} training examples")
    logger.info(f"Saved to: {output_path}")

    return len(examples)


def extract_from_conversations(
    conversations_path: str,
    output_path: str = "extracted_training_data.jsonl",
) -> int:
    """
    Extract training data from real ApexAurum conversations.

    Args:
        conversations_path: Path to conversations.json
        output_path: Where to save extracted data

    Returns:
        Number of examples extracted
    """
    from data_extractor import TrainingDataExtractor, ExportFormat

    extractor = TrainingDataExtractor()
    count = extractor.load_conversations(conversations_path)

    if count == 0:
        logger.warning("No conversations found!")
        return 0

    examples = extractor.extract_tool_call_examples()

    if not examples:
        logger.info("No tool calls found in conversations (normal for chat-only convos)")
        return 0

    training = extractor.to_training_examples(examples)
    extractor.export(training, output_path, ExportFormat.ALPACA)

    return len(training)


def full_pipeline(
    output_dir: str = "./training_output",
    synthetic_per_tool: int = 20,
    conversations_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run full training data pipeline.

    1. Generate synthetic data from all ApexAurum tools
    2. Extract from real conversations if available
    3. Combine and prepare for training

    Returns:
        Summary statistics
    """
    from datetime import datetime

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    stats = {
        "timestamp": timestamp,
        "synthetic_count": 0,
        "extracted_count": 0,
        "total_count": 0,
        "output_files": []
    }

    # Generate synthetic data
    synthetic_path = f"{output_dir}/synthetic_{timestamp}.jsonl"
    stats["synthetic_count"] = generate_apex_training_data(
        output_path=synthetic_path,
        num_per_tool=synthetic_per_tool,
    )
    stats["output_files"].append(synthetic_path)

    # Extract from conversations if path provided
    if conversations_path and Path(conversations_path).exists():
        extracted_path = f"{output_dir}/extracted_{timestamp}.jsonl"
        stats["extracted_count"] = extract_from_conversations(
            conversations_path=conversations_path,
            output_path=extracted_path,
        )
        if stats["extracted_count"] > 0:
            stats["output_files"].append(extracted_path)

    # Combine all data
    combined_path = f"{output_dir}/combined_{timestamp}.jsonl"
    combine_datasets(stats["output_files"], combined_path)

    stats["total_count"] = stats["synthetic_count"] + stats["extracted_count"]
    stats["combined_path"] = combined_path

    # Save summary
    summary_path = f"{output_dir}/summary_{timestamp}.json"
    with open(summary_path, 'w') as f:
        json.dump(stats, f, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info("TRAINING DATA PIPELINE COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Synthetic examples: {stats['synthetic_count']}")
    logger.info(f"Extracted examples: {stats['extracted_count']}")
    logger.info(f"Total examples: {stats['total_count']}")
    logger.info(f"Combined dataset: {combined_path}")
    logger.info(f"{'='*60}")

    return stats


def combine_datasets(input_paths: List[str], output_path: str) -> int:
    """Combine multiple JSONL files into one."""
    total = 0
    with open(output_path, 'w') as out:
        for path in input_paths:
            if Path(path).exists():
                with open(path, 'r') as inp:
                    for line in inp:
                        out.write(line)
                        total += 1
    logger.info(f"Combined {total} examples into {output_path}")
    return total


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ApexAurum Training Data Generator")
    parser.add_argument("--generate", type=int, metavar="N", help="Generate N examples per tool")
    parser.add_argument("--extract", type=str, metavar="PATH", help="Extract from conversations file")
    parser.add_argument("--full-pipeline", action="store_true", help="Run full pipeline")
    parser.add_argument("--output", "-o", type=str, default="./training_output", help="Output directory")
    parser.add_argument("--tools", type=str, nargs="+", help="Filter to specific tools")

    args = parser.parse_args()

    if args.generate:
        generate_apex_training_data(
            output_path=f"{args.output}/apex_synthetic.jsonl",
            num_per_tool=args.generate,
            tool_filter=args.tools,
        )

    elif args.extract:
        extract_from_conversations(
            conversations_path=args.extract,
            output_path=f"{args.output}/apex_extracted.jsonl",
        )

    elif args.full_pipeline:
        full_pipeline(
            output_dir=args.output,
            conversations_path="../../sandbox/conversations.json",
        )

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python apex_data_generator.py --generate 20")
        print("  python apex_data_generator.py --full-pipeline")
        print("  python apex_data_generator.py --generate 50 --tools calculator memory_store")
