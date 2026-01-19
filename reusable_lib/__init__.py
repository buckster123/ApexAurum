"""
Reusable AI Library
===================

A collection of production-grade modules extracted from ApexAurum for building
AI applications with Claude, local LLMs, and other AI providers.

Dual API Support: Works with both Anthropic Claude API and OpenAI-compatible
endpoints (Ollama, llama.cpp, vLLM, Together AI, Groq, etc.)

Modules:
--------
- **api**: Rate limiting, retry logic, model configuration, OpenAI-compatible client
- **costs**: Token counting and cost tracking
- **messages**: Message format conversion (OpenAI <-> Claude)
- **tools**: Ready-to-use AI tools with schemas
- **utils**: Error handling utilities
- **caching**: Prompt caching for Claude API (90% cost savings)
- **streaming**: Real-time response handling and progress tracking
- **execution**: Sandboxed filesystem operations
- **agents**: Multi-agent orchestration framework
- **vector**: ChromaDB wrapper and semantic search
- **config**: Settings preset management
- **training**: Generate fine-tuning datasets from conversation logs
- **eeg**: Neural interface for emotional response detection

Quick Start:
------------
    # Rate limiting
    from reusable_lib.api import RateLimiter
    limiter = RateLimiter(max_requests_per_min=200)
    can_go, wait = limiter.can_make_request(estimated_input_tokens=1000)

    # Retry with backoff
    from reusable_lib.api import retry_on_error
    @retry_on_error(max_retries=3)
    def call_api():
        return client.messages.create(...)

    # Cost tracking
    from reusable_lib.costs import CostTracker
    tracker = CostTracker()
    tracker.record_usage("claude-sonnet-4-5", input_tokens=1000, output_tokens=500)
    print(f"Cost: ${tracker.get_session_stats()['cost']:.4f}")

    # Prompt caching
    from reusable_lib.caching import CacheManager, CacheStrategy
    cache = CacheManager(strategy=CacheStrategy.BALANCED)
    cached_request = cache.prepare_cached_request(messages, system, tools)

    # Multi-agent orchestration
    from reusable_lib.agents import AgentManager
    manager = AgentManager(api_call_fn=my_api_call)
    agent_id = manager.spawn_agent(task="Research topic", agent_type="researcher")

    # Vector search
    from reusable_lib.vector import VectorDB
    db = VectorDB("./data/vectors")
    collection = db.get_or_create_collection("knowledge")
    collection.add(texts=["Hello world"], ids=["doc1"])
    results = collection.query("greeting", n_results=5)
"""

__version__ = "1.0.0"
__author__ = "ApexAurum Team"

# Core imports (pure Python, always available)
from .utils import RetryableError, UserFixableError, FatalError
from .api import RateLimiter, retry_on_error, ClaudeModels, resolve_model
from .api import OpenAICompatibleClient, OllamaClient, create_ollama_client, resolve_local_model
from .costs import CostTracker, count_tokens
from .messages import prepare_messages_for_claude, format_tool_result_for_claude
from .caching import CacheManager, CacheStrategy
from .streaming import StreamEvent, ToolExecutionTracker, ProgressIndicator
from .config import PresetManager
from .training import TrainingDataExtractor, ExportFormat, generate_training_dataset
from .evaluation import (
    ModelBenchmark, TestCase, TestSuite, ComparisonReport,
    ToolCallEvaluator, JSONValidityEvaluator, CompositeEvaluator,
    run_benchmark, compare_models
)

# These require additional dependencies (imported explicitly when needed)
# from .execution import FilesystemSandbox, fs_read_file, fs_write_file
# from .agents import AgentManager, Agent, AGENT_TYPES
# from .vector import VectorDB, MemoryHealth  # Requires: chromadb, sentence-transformers
# from .eeg import EEGConnection, EmotionMapper  # Requires: numpy, scipy, (brainflow optional)
