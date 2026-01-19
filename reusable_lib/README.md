# Reusable AI Library

A collection of production-grade modules extracted from ApexAurum for building AI applications with Claude, local LLMs, and other AI providers.

**Dual API Support:** Works with both Anthropic Claude API **and** OpenAI-compatible endpoints (Ollama, llama.cpp, vLLM, Together AI, Groq, etc.)

## Installation

Copy the `reusable_lib` folder to your project:

```bash
cp -r reusable_lib /path/to/your/project/
```

Dependencies (optional, depending on modules used):
- `anthropic` - For Anthropic-specific error classification
- `requests` - For OpenAI-compatible client (usually already installed)

## Modules

### 1. `api` - API Client Utilities

#### Rate Limiter
Sliding window rate limiting to respect API limits.

```python
from reusable_lib.api import RateLimiter

limiter = RateLimiter(
    max_requests_per_min=200,
    max_input_tokens_per_min=64000,
    safety_margin=0.9  # Use 90% of limits
)

# Check before making request
can_proceed, wait_time = limiter.can_make_request(
    estimated_input_tokens=1000,
    estimated_output_tokens=500
)

if not can_proceed:
    time.sleep(wait_time)

# Record after request
limiter.record_request(input_tokens=1000, output_tokens=500)

# Get status
print(limiter.get_status_message())  # "All systems normal"
```

#### Retry Handler
Exponential backoff decorator with jitter.

```python
from reusable_lib.api import retry_on_error, classify_anthropic_error

# Generic retry
@retry_on_error(max_retries=3, base_delay=1.0)
def call_api():
    return requests.get("https://api.example.com")

# With Anthropic error classification
@retry_on_error(
    max_retries=3,
    error_classifier=classify_anthropic_error
)
def call_claude():
    return client.messages.create(...)
```

#### Model Configuration
Claude model definitions and intelligent selection.

```python
from reusable_lib.api import (
    ClaudeModels,
    ModelSelector,
    resolve_model,
    get_model_list
)

# Select by task type
model = ModelSelector.select_for_task("complex")  # OPUS_4_5
model = ModelSelector.select_for_task("testing")  # HAIKU_4_5

# Resolve flexible input to model ID
model_id = resolve_model("opus")  # "claude-opus-4-5-20251101"
model_id = resolve_model("sonnet")  # "claude-sonnet-4-5-20250929"

# Get model list for UI dropdown
models = get_model_list()  # [("claude-opus-4-5-...", "Claude Opus 4.5"), ...]
```

#### OpenAI-Compatible Client (Local LLMs & Open Source)

Unified client for Ollama, llama.cpp, vLLM, LM Studio, and hosted providers.

```python
from reusable_lib.api import (
    # Client classes
    OpenAICompatibleClient,
    OllamaClient,
    ChatResponse,
    # Factory functions
    create_ollama_client,
    create_local_client,
    create_hosted_client,
    # Model utilities
    OpenAIModels,
    LocalModelSelector,
    resolve_local_model
)

# === Quick Start with Ollama ===
client = create_ollama_client()  # Defaults to localhost:11434

# Simple chat
response = client.chat("Explain quantum computing", model="llama3:8b")
print(response.content)

# With system prompt
response = client.chat(
    "Write a haiku about coding",
    model="mistral:7b",
    system="You are a creative poet."
)

# Streaming
for chunk in client.chat_stream("Tell me a story", model="llama3.1:8b"):
    print(chunk, end="", flush=True)

# === Local LLM Servers ===
# LM Studio
client = create_local_client("lmstudio")

# llama.cpp server
client = create_local_client("llamacpp", host="http://localhost:8080/v1")

# vLLM
client = create_local_client("vllm", host="http://localhost:8000/v1")

# === Hosted Providers ===
# Together AI
client = create_hosted_client("together", api_key="your-key")
response = client.chat("Hello", model="llama3:70b")  # Auto-maps to provider model ID

# Groq (fast inference)
client = create_hosted_client("groq", api_key="your-key")

# OpenRouter
client = create_hosted_client("openrouter", api_key="your-key")

# === Ollama-Specific Features ===
ollama = create_ollama_client()

# Pull a model
for progress in ollama.pull_model("llama3.1:8b"):
    print(f"Downloading: {progress.get('status')}")

# List local models
models = ollama.list_local_models()
for m in models:
    print(f"{m['name']}: {m['size'] / 1e9:.1f}GB")

# Get model info
info = ollama.show_model("llama3:8b")
print(f"Parameters: {info.get('parameters')}")

# Copy/rename model
ollama.copy_model("llama3:8b", "my-custom-llama")

# Delete model
ollama.delete_model("old-model:latest")

# === Model Selection ===
# Select by task
model = LocalModelSelector.select_for_task("coding")  # qwen2.5-coder:32b
model = LocalModelSelector.select_for_task("fast")    # llama3:8b
model = LocalModelSelector.select_for_task("best")    # llama3.3:70b

# Resolve flexible input
model_id = resolve_local_model("llama3")      # "llama3:8b"
model_id = resolve_local_model("codestral")   # "codestral:latest"
model_id = resolve_local_model("qwen-coder")  # "qwen2.5-coder:7b"

# === Tool/Function Calling ===
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
        }
    }
}]

response = client.chat(
    "What's the weather in Paris?",
    model="llama3.1:8b",
    tools=tools
)

if response.has_tool_calls:
    for tool_call in response.tool_calls:
        print(f"Call: {tool_call['function']['name']}")
        print(f"Args: {tool_call['function']['arguments']}")

# === Embeddings ===
embeddings = client.embeddings(
    ["Hello world", "How are you?"],
    model="nomic-embed-text:latest"
)
# Returns: [[0.123, 0.456, ...], [0.789, 0.012, ...]]

# === Health Check ===
if client.health_check():
    print("Server is running!")
```

#### Supported Providers

| Provider | Type | Default URL | Notes |
|----------|------|-------------|-------|
| Ollama | Local | `localhost:11434` | Full native API support |
| LM Studio | Local | `localhost:1234` | OpenAI-compatible |
| llama.cpp | Local | `localhost:8080` | OpenAI-compatible |
| vLLM | Local | `localhost:8000` | High-performance serving |
| LocalAI | Local | `localhost:8080` | Drop-in OpenAI replacement |
| text-gen-webui | Local | `localhost:5000` | OpenAI-compatible |
| Together AI | Hosted | `api.together.xyz` | Requires API key |
| Groq | Hosted | `api.groq.com` | Ultra-fast inference |
| OpenRouter | Hosted | `openrouter.ai` | Multi-model gateway |
| Fireworks | Hosted | `api.fireworks.ai` | Requires API key |
| Anyscale | Hosted | `api.endpoints.anyscale.com` | Requires API key |

#### Common Open Source Models

| Model | ID | Best For | VRAM |
|-------|-----|----------|------|
| Llama 3.3 70B | `llama3.3:70b` | State-of-art OSS | 40GB |
| Llama 3.1 8B | `llama3.1:8b` | General, long context | 6GB |
| Qwen 2.5 72B | `qwen2.5:72b` | Multilingual, reasoning | 45GB |
| Codestral | `codestral:latest` | Code generation | 14GB |
| Qwen 2.5 Coder 32B | `qwen2.5-coder:32b` | Best OSS coder | 20GB |
| Mistral 7B | `mistral:7b` | Efficient, fast | 5GB |
| Mixtral 8x7B | `mixtral:8x7b` | MoE, balanced | 26GB |
| Phi-3 Mini | `phi3:mini` | Edge/mobile | 3GB |

---

### 2. `costs` - Token Counting & Cost Tracking

#### Token Counter
Estimate tokens for rate limiting and cost prediction.

```python
from reusable_lib.costs import count_tokens, estimate_text_tokens

# Quick text estimate
tokens = estimate_text_tokens("Hello, world!")  # ~3 tokens

# Full request estimate
result = count_tokens(
    messages=[{"role": "user", "content": "Hello!"}],
    system="You are a helpful assistant.",
    tools=[{...}]
)
print(f"Input: {result['input_tokens']}, Output: {result['output_tokens']}")
```

#### Cost Tracker
Track token usage and calculate costs.

```python
from reusable_lib.costs import CostTracker

tracker = CostTracker()

# Record API usage
tracker.record_usage(
    model="claude-sonnet-4-5",
    input_tokens=1000,
    output_tokens=500,
    cache_creation_tokens=100,  # Optional: prompt caching
    cache_read_tokens=800
)

# Get statistics
stats = tracker.get_session_stats()
print(f"Session cost: ${stats['cost']:.4f}")
print(f"Total tokens: {stats['total_tokens']}")

# Cost breakdown by model
breakdown = tracker.get_cost_breakdown_by_model()
```

---

### 3. `messages` - Message Format Conversion

Convert between OpenAI and Claude message formats.

```python
from reusable_lib.messages import (
    prepare_messages_for_claude,
    format_tool_result_for_claude,
    create_simple_tool_schema
)

# Convert OpenAI messages to Claude format
openai_messages = [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello!"},
]

system_prompt, claude_messages = prepare_messages_for_claude(openai_messages)
# system_prompt = "You are helpful."
# claude_messages = [{"role": "user", "content": "Hello!"}]

# Format tool results
result_message = format_tool_result_for_claude(
    tool_use_id="toolu_123",
    tool_result={"answer": 42},
    is_error=False
)

# Create tool schemas
tool = create_simple_tool_schema(
    name="add",
    description="Add two numbers",
    properties={
        "a": {"type": "number", "description": "First number"},
        "b": {"type": "number", "description": "Second number"}
    },
    required=["a", "b"]
)
```

---

### 4. `tools` - Ready-to-Use AI Tools

Pre-built tools with Claude-compatible schemas.

```python
from reusable_lib.tools import (
    # Utilities
    get_current_time,
    calculator,
    count_words,
    random_number,
    UTILITY_TOOL_SCHEMAS,
    # Memory
    memory_store,
    memory_retrieve,
    memory_search,
    MEMORY_TOOL_SCHEMAS
)

# Use tools directly
print(get_current_time("human"))  # "Wednesday, January 15, 2026 at 10:30:00 AM"
print(calculator("add", 5, 3))     # 8.0
print(count_words("Hello world"))  # {"words": 2, "characters": 11, ...}

# Memory persistence
memory_store("user_name", "Alice")
result = memory_retrieve("user_name")
print(result["value"])  # "Alice"

# Register tools with Claude
all_tools = list(UTILITY_TOOL_SCHEMAS.values()) + list(MEMORY_TOOL_SCHEMAS.values())
```

#### Custom Memory Path

```python
from reusable_lib.tools.memory import SimpleMemory, set_memory_path
from pathlib import Path

# Option 1: Use set_memory_path for default instance
set_memory_path(Path("./data/memory.json"))

# Option 2: Create custom instance
memory = SimpleMemory(storage_file=Path("./custom/path.json"))
memory.store("key", "value")
```

---

### 5. `utils` - Error Handling

Three-tier error hierarchy for robust error handling.

```python
from reusable_lib.utils import RetryableError, UserFixableError, FatalError

try:
    call_api()
except SomeAPIError as e:
    if is_rate_limit(e):
        raise RetryableError(
            "Rate limited",
            retry_after=60,
            original_error=e
        )
    elif is_auth_error(e):
        raise UserFixableError(
            "Invalid API key",
            help_text="Check your .env file",
            original_error=e
        )
    else:
        raise FatalError("Unexpected error", original_error=e)
```

---

### 6. `caching` - Prompt Caching for Claude API

Implements Anthropic's prompt caching for 90% cost savings on repeated content.

```python
from reusable_lib.caching import CacheManager, CacheStrategy

# Create cache manager
manager = CacheManager(
    strategy=CacheStrategy.BALANCED,  # or DISABLED, CONSERVATIVE, AGGRESSIVE
    min_cacheable_tokens=1024
)

# Prepare request with cache control
messages = [
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi there!"},
    {"role": "user", "content": "How are you?"}
]
system = "You are a helpful assistant."
tools = [{...}]

cached_request = manager.prepare_cached_request(messages, system, tools)
# Returns: {"messages": [...with cache_control...], "system": ..., "tools": ...}

# Get cache statistics
stats = manager.get_cache_stats()
print(f"Hit rate: {stats['cache_hit_rate']:.1%}")
print(f"Tokens saved: {stats['cache_tokens_saved']:,}")
```

#### Cache Strategies

- **DISABLED** - No caching
- **CONSERVATIVE** - Cache system prompt + tools only (safest)
- **BALANCED** - Cache system + tools + older history (recommended)
- **AGGRESSIVE** - Cache system + tools + more history (max savings)

---

### 7. `streaming` - Real-time Response Handling

Infrastructure for streaming AI responses with progress tracking.

```python
from reusable_lib.streaming import (
    StreamEvent,
    ToolExecutionTracker,
    ProgressIndicator,
    format_tool_display
)

# Track tool executions
tracker = ToolExecutionTracker()
tracker.start_tool("toolu_123", "calculator", {"a": 5, "b": 3})
# ... execute tool ...
tracker.complete_tool("toolu_123", result=8)

# Get summary
summary = tracker.get_summary()
print(f"Tools executed: {summary['completed_count']}")
print(f"Total duration: {summary['total_duration']:.2f}s")

# Progress indicator with spinner
progress = ProgressIndicator(style="braille")  # or "dots", "simple", "clock"
while working:
    status = progress.format_status("Processing...")
    print(f"\r{status}", end="")
    time.sleep(0.1)

# Format tool calls for display
display = format_tool_display(
    "calculator",
    {"a": 5, "b": 3},
    status="complete",
    duration=0.5,
    result=8
)
# Output: "✅ **calculator(a=5, b=3)  [0.50s]**\n   └─ 8"
```

---

### 8. `execution` - Sandboxed Filesystem Operations

Safe file operations within a sandbox directory.

```python
from reusable_lib.execution import (
    FilesystemSandbox,
    fs_read_file,
    fs_write_file,
    fs_list_files,
    fs_edit,
    set_sandbox_path,
    FILESYSTEM_TOOL_SCHEMAS
)

# Option 1: Use singleton with custom path
set_sandbox_path("./my_sandbox")
content = fs_read_file("notes.txt")

# Option 2: Create custom sandbox instance
sandbox = FilesystemSandbox(base_path="./workspace")

# File operations (all paths are relative to sandbox)
sandbox.write_file("data.txt", "Hello, World!")
content = sandbox.read_file("data.txt")
files = sandbox.list_files(".")  # List all files in sandbox
info = sandbox.get_file_info("data.txt")

# Line-based operations
lines = sandbox.read_lines("log.txt", start=1, end=10)

# Edit with search/replace
result = sandbox.edit_file(
    "config.py",
    old_content="DEBUG = False",
    new_content="DEBUG = True"
)

# Register tools with Claude
tools = list(FILESYSTEM_TOOL_SCHEMAS.values())
```

#### Security Features

- All paths resolved relative to sandbox (no escape possible)
- Symlink attack prevention
- Path traversal blocked (`../` attempts fail)
- Binary file detection

---

### 9. `agents` - Multi-Agent Orchestration

Spawn and manage multiple AI agents working in parallel.

```python
from reusable_lib.agents import (
    AgentManager,
    AgentStatus,
    AGENT_TYPES,
    AGENT_TOOL_SCHEMAS
)

# Your API call function (backend-agnostic)
def my_api_call(messages, system, model, max_tokens):
    # Use any LLM API: Anthropic, OpenAI, local models, etc.
    response = client.messages.create(
        messages=messages,
        system=system,
        model=model,
        max_tokens=max_tokens
    )
    return response.content[0].text

# Create manager
manager = AgentManager(
    api_call_fn=my_api_call,
    storage_path="./agents.json",
    default_model="claude-sonnet-4-5"
)

# Spawn an agent
agent_id = manager.spawn_agent(
    task="Research Python async patterns and summarize best practices",
    agent_type="researcher",  # general, researcher, coder, analyst, writer
    run_async=True  # Background execution
)

# Check status
status = manager.get_status(agent_id)
print(f"Status: {status['status']}")  # pending, running, completed, failed

# Wait for completion
result = manager.wait_for_agent(agent_id, timeout=300)
print(result["result"])

# List all agents
agents = manager.list_agents(status_filter=AgentStatus.COMPLETED)

# Register agent tools with Claude
tools = list(AGENT_TOOL_SCHEMAS.values())
```

#### Agent Types

| Type | Description |
|------|-------------|
| `general` | General-purpose assistant |
| `researcher` | Research and information gathering |
| `coder` | Code writing and implementation |
| `analyst` | Data analysis and insights |
| `writer` | Content creation |

---

### 10. `vector` - Vector Database & Semantic Search

ChromaDB wrapper with memory health monitoring.

```python
from reusable_lib.vector import (
    VectorDB,
    VectorCollection,
    create_vector_db,
    MemoryHealth
)

# Create database
db = VectorDB(
    persist_directory="./data/vectors",
    model_name="all-MiniLM-L6-v2"  # or all-mpnet-base-v2 for higher quality
)

# Create/get collection
collection = db.get_or_create_collection("knowledge")

# Add documents with automatic metadata tracking
collection.add(
    texts=["Python is great", "AI is transformative", "Claude is helpful"],
    metadatas=[
        {"category": "tech", "source": "notes"},
        {"category": "tech", "source": "article"},
        {"category": "ai", "source": "docs"}
    ],
    ids=["doc1", "doc2", "doc3"]
)

# Semantic search
results = collection.query("programming languages", n_results=5)
for doc_id, text, metadata, distance in zip(
    results["ids"], results["documents"],
    results["metadatas"], results["distances"]
):
    similarity = 1.0 - distance
    print(f"{doc_id}: {text[:50]}... ({similarity:.1%} match)")

# Track access (for memory health)
collection.track_access(["doc1", "doc2"])

# Memory health monitoring
health = MemoryHealth(db)

# Find stale memories (not accessed in 30 days)
stale = health.get_stale_memories(days_unused=30, collection="knowledge")
print(f"Found {stale['stale_count']} stale memories")

# Find duplicates
dupes = health.get_duplicate_candidates(
    collection="knowledge",
    similarity_threshold=0.95
)
for pair in dupes["duplicate_pairs"][:5]:
    print(f"Duplicate: {pair['id1']} ↔ {pair['id2']} ({pair['similarity']:.1%})")

# Consolidate duplicates
result = health.consolidate_memories(
    "doc1", "doc2",
    collection="knowledge",
    keep="higher_access"  # or "higher_confidence", "id1", "id2"
)

# Get health summary
summary = health.get_health_summary("knowledge")
print(f"Health score: {summary['health_score']}%")
```

#### Requirements

```bash
pip install chromadb sentence-transformers numpy
```

---

### 11. `config` - Preset Management

Generic settings preset system for quick configuration switching.

```python
from reusable_lib.config import PresetManager

# Define built-in presets
built_ins = {
    "fast": {
        "id": "fast",
        "name": "🚀 Fast Mode",
        "description": "Quick responses with lower quality",
        "settings": {"model": "haiku", "cache": True, "temperature": 0.7}
    },
    "quality": {
        "id": "quality",
        "name": "🧠 Quality Mode",
        "description": "Best output for complex tasks",
        "settings": {"model": "opus", "cache": False, "temperature": 1.0}
    }
}

# Optional: settings validator
def validate_settings(settings):
    errors = []
    if "model" not in settings:
        errors.append("model is required")
    if settings.get("temperature", 0) > 1.0:
        errors.append("temperature must be <= 1.0")
    return len(errors) == 0, errors

# Create manager
manager = PresetManager(
    storage_path="./presets.json",
    built_in_presets=built_ins,
    default_preset_id="fast",
    settings_validator=validate_settings
)

# Get all presets
all_presets = manager.get_all_presets()

# Get specific preset
preset = manager.get_preset("fast")
my_settings = preset["settings"]

# Save custom preset
success, msg, preset_id = manager.save_custom_preset(
    name="My Config",
    description="Custom setup for my workflow",
    settings={"model": "sonnet", "cache": True, "temperature": 0.9}
)

# List presets for UI
presets_list = manager.list_presets()
for p in presets_list:
    active = "✓" if p["is_active"] else " "
    builtin = "(built-in)" if p["is_built_in"] else ""
    print(f"[{active}] {p['name']} {builtin}")

# Export/import custom presets
json_data = manager.export_custom_presets()
manager.import_custom_presets(json_data, overwrite=True)
```

---

### 12. `eeg` - Neural Interface (EEG/BCI)

Read brain signals for emotional response detection. Supports OpenBCI hardware and mock mode.

```python
from reusable_lib.eeg import (
    EEGConnection,
    EEGProcessor,
    EmotionMapper,
    ListeningSession,
    BRAINFLOW_AVAILABLE
)

# Connect to hardware (or mock for testing)
conn = EEGConnection()
result = conn.connect('', 'mock')  # Use 'synthetic' or 'cyton' for real hardware
print(f"Channels: {result['channel_names']}")

# Start streaming
conn.start_stream()

# Get data (1 second at 250Hz)
import time
time.sleep(1)
data = conn.get_current_data(250)

# Process EEG signals
processor = EEGProcessor(sampling_rate=250)
results = processor.process_window(data, conn.eeg_channels, conn.channel_names)

# Map to emotions
mapper = EmotionMapper()
moment = mapper.process_moment(results["band_powers"], timestamp_ms=1000)

print(f"Valence: {moment.valence:.2f} (-1=negative to +1=positive)")
print(f"Arousal: {moment.arousal:.2f} (0=calm to 1=excited)")
print(f"Attention: {moment.attention:.2f}")
print(f"Chills detected: {moment.possible_chills}")

# Stop streaming
conn.stop_stream()
conn.disconnect()

# Record a full session
session = ListeningSession(
    session_id="listen_001",
    track_id="track_123",
    track_title="My Song",
    listener="User",
    duration_ms=180000,
    moments=[moment1, moment2, ...]
)

# Generate AI-readable narrative
print(session.generate_narrative())
# Output: "User listened to 'My Song'. The experience was joyful and energizing
#          (valence: 0.65, arousal: 0.72). Musical chills detected 2 time(s)..."

# Save/load sessions
session.save_to_file("./sessions/listen_001.json")
loaded = ListeningSession.load_from_file("./sessions/listen_001.json")
```

#### Supported Hardware

| Board | Channels | Sample Rate | Notes |
|-------|----------|-------------|-------|
| Cyton | 8 | 250Hz | Full coverage (Fp1, Fp2, F3, F4, T7, T8, P3, P4) |
| Ganglion | 4 | 200Hz | Budget option (F3, F4, T7, T8) |
| Synthetic | 8 | 250Hz | BrainFlow test mode |
| Mock | 8 | 250Hz | Software simulation (no hardware needed) |

#### Emotional Dimensions

| Dimension | Range | Based On |
|-----------|-------|----------|
| Valence | -1 to +1 | Frontal alpha asymmetry (F4-F3) |
| Arousal | 0 to 1 | Beta/alpha ratio |
| Attention | 0 to 1 | Theta/beta ratio + gamma |
| Engagement | 0 to 1 | Geometric mean of arousal × attention |

#### Requirements

```bash
pip install numpy scipy          # Required
pip install brainflow            # Optional: for real hardware
```

---

### 13. `evaluation` - Model Benchmarking

Benchmark models to find the right one for each task. Essential for "how small can I go?" experiments.

```python
from reusable_lib.evaluation import (
    ModelBenchmark,
    TestCase,
    TestSuite,
    ToolCallEvaluator,
    JSONValidityEvaluator,
    CompositeEvaluator,
    compare_models
)
from reusable_lib.api import create_ollama_client

# === Quick Comparison ===
client = create_ollama_client()

report = compare_models(
    prompts=[
        "Remember my name is Alice",
        "What time is it?",
        "Calculate 15 * 7",
    ],
    models=["llama3:8b", "qwen2:0.5b", "phi3:mini"],
    client=client,
    evaluator=ToolCallEvaluator(),
    expected=[
        {"tool": "memory_store", "arguments": {"key": "name"}},
        {"tool": "get_current_time"},
        {"tool": "calculator", "arguments": {"operation": "multiply"}},
    ]
)

print(report.summary())
# === Model Comparison Report ===
# llama3:8b:    Accuracy: 100.0% (3/3), Latency: 450ms
# qwen2:0.5b:   Accuracy: 66.7% (2/3), Latency: 120ms
# phi3:mini:    Accuracy: 100.0% (3/3), Latency: 200ms
# 🏆 Best Overall: phi3:mini

# === Build Test Suites ===
suite = TestSuite(
    name="memory_tools",
    description="Test memory-related tool routing",
    default_system_prompt="Respond with tool calls in JSON format."
)

suite.add_case(TestCase(
    name="store_name",
    prompt="Remember that my favorite color is blue",
    expected={"tool": "memory_store", "arguments": {"key": "favorite_color"}},
    tags=["memory", "store"]
))

suite.add_case(TestCase(
    name="retrieve_name",
    prompt="What's my favorite color?",
    expected={"tool": "memory_retrieve", "arguments": {"key": "favorite_color"}},
    tags=["memory", "retrieve"]
))

# Run suite
bench = ModelBenchmark(client)
results = bench.run_suite(
    suite,
    models=["llama3:8b", "phi3:mini"],
    evaluator=ToolCallEvaluator(strict_args=False)
)

# Generate report
report = bench.compare_models(results, suite_name="memory_tools")
report.save("benchmark_results.json")

# === Evaluators ===

# Tool Call Evaluator - checks tool name and arguments
tool_eval = ToolCallEvaluator(
    strict_args=False,     # Only check arg names, not values
    required_args_only=True
)

# JSON Validity - is it valid JSON?
json_eval = JSONValidityEvaluator(
    schema={"type": "object", "required": ["tool"]}
)

# Semantic Similarity - meaning match (requires sentence-transformers)
from reusable_lib.evaluation import SemanticSimilarityEvaluator
sem_eval = SemanticSimilarityEvaluator(
    model_name="all-MiniLM-L6-v2",
    threshold=0.7
)

# Composite - combine multiple evaluators
combo = CompositeEvaluator([
    (ToolCallEvaluator(), 0.6),      # 60% weight on tool accuracy
    (JSONValidityEvaluator(), 0.2),   # 20% on valid JSON
    (ResponseQualityEvaluator(), 0.2) # 20% on response quality
])

# === Create Suite from Training Data ===
from reusable_lib.evaluation import create_tool_routing_suite
from reusable_lib.training import extract_tool_calls_from_conversations

# Extract examples from your conversations
examples = extract_tool_calls_from_conversations("sandbox/conversations.json")

# Convert to test suite
tool_examples = [
    {"prompt": e.user_message, "tool": e.tool_name, "arguments": e.tool_arguments}
    for e in examples[:50]  # Use first 50 as test cases
]

suite = create_tool_routing_suite(tool_examples, "real_world_tools")

# Now benchmark your fine-tuned model against base model
results = bench.run_suite(
    suite,
    models=["llama3:8b", "my-finetuned-llama:latest"],
    evaluator=ToolCallEvaluator()
)

# Did fine-tuning help?
report = bench.compare_models(results)
print(report.summary())
```

#### Evaluators

| Evaluator | Purpose | Key Options |
|-----------|---------|-------------|
| `ToolCallEvaluator` | Tool routing accuracy | `strict_args`, `required_args_only` |
| `JSONValidityEvaluator` | Valid JSON output | `schema` for validation |
| `ExactMatchEvaluator` | Exact string match | `case_sensitive` |
| `SemanticSimilarityEvaluator` | Meaning similarity | `threshold`, `model_name` |
| `ResponseQualityEvaluator` | Quality heuristics | `min_length`, `max_length` |
| `ContainsEvaluator` | Contains substring | `case_sensitive` |
| `CompositeEvaluator` | Weighted combination | List of (evaluator, weight) |

#### Metrics Collected

- **Accuracy**: pass rate, mean score, std deviation
- **Latency**: mean, median, p90, p95, p99
- **Cost**: per request, per success (if token info available)

---

### 14. `training` - Fine-Tuning Dataset Generation

Extract training data from your conversation logs for fine-tuning small models.

```python
from reusable_lib.training import (
    TrainingDataExtractor,
    ExportFormat,
    generate_training_dataset,
    extract_tool_calls_from_conversations
)

# === Quick One-Shot Generation ===
stats = generate_training_dataset(
    conversations_path="./sandbox/conversations.json",
    output_path="./training_data.jsonl",
    format=ExportFormat.ALPACA,  # For Llama fine-tuning
    system_prompt="tool_routing"
)
print(f"Generated {stats['exported_count']} examples")
print(f"Tools covered: {list(stats['tool_counts'].keys())}")

# === Detailed Extraction ===
extractor = TrainingDataExtractor()

# Load your conversation history
extractor.load_conversations("./sandbox/conversations.json")

# Extract tool call examples
examples = extractor.extract_tool_call_examples(
    min_user_length=5,      # Skip very short messages
    deduplicate=True        # Remove duplicates
)

# See what you've got
stats = extractor.get_tool_statistics()
print(f"Total examples: {stats['total_examples']}")
print(f"Tools: {stats['tool_counts']}")
# Output: {'memory_store': 45, 'calculator': 32, 'web_search': 28, ...}

# Filter to specific tools (e.g., for a memory-specialist model)
memory_examples = extractor.filter_by_tools(
    ["memory_store", "memory_retrieve", "memory_search"]
)

# Filter by quality
quality_examples = extractor.filter_by_quality(
    require_result=True,    # Only examples where tool returned result
    require_response=True,  # Only examples with final assistant response
    min_args=1              # Tool must have at least 1 argument
)

# Convert to training format
training = extractor.to_training_examples(
    examples=memory_examples,
    system_prompt="tool_routing",  # Or custom: "You are a memory assistant..."
    include_context=True,          # Include previous conversation turns
    include_result=False           # Don't include tool results in output
)

# Split into train/val/test
train, val, test = extractor.generate_splits(
    training,
    train_ratio=0.8,
    val_ratio=0.1,
    test_ratio=0.1,
    shuffle=True,
    seed=42
)

# Export in your preferred format
extractor.export(train, "train.jsonl", ExportFormat.ALPACA)
extractor.export(val, "val.jsonl", ExportFormat.ALPACA)
extractor.export(test, "test.jsonl", ExportFormat.ALPACA)

# === Export Formats ===

# ALPACA (Llama, Mistral fine-tuning)
extractor.export(training, "data.jsonl", ExportFormat.ALPACA)
# {"instruction": "...", "input": "store my name", "output": "{\"tool\": \"memory_store\", ...}"}

# CHATML (Qwen, OpenAI format)
extractor.export(training, "data.jsonl", ExportFormat.CHATML)
# {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}

# SHAREGPT (Multi-turn conversations)
extractor.export(training, "data.jsonl", ExportFormat.SHAREGPT)
# {"conversations": [{"from": "human", ...}, {"from": "gpt", ...}]}

# TOOLCALL (Function-calling specific)
extractor.export(training, "data.jsonl", ExportFormat.TOOLCALL)
# {"messages": [...], "tools": [...], "tool_calls": [...]}
```

#### Training Data Structure

Each extracted example contains:

| Field | Description |
|-------|-------------|
| `user_message` | What the user asked |
| `tool_name` | Which tool was called |
| `tool_arguments` | Arguments passed to tool |
| `tool_result` | What the tool returned (if captured) |
| `assistant_response` | Final response to user |
| `previous_messages` | Conversation context (for multi-turn) |

#### Use Cases

1. **Tool Router Model**: Fine-tune a tiny model (Phi-3, Qwen 0.5B) just to route requests to tools
2. **Memory Specialist**: Train on memory_* tool calls for a dedicated memory manager
3. **Code Assistant**: Train on code execution and file operation tools
4. **Domain Expert**: Filter to specific tool categories for specialized models

#### Tips for Good Training Data

- More conversations = better data (aim for 1000+ tool call examples)
- Diverse examples matter more than quantity
- Filter out low-quality examples (very short, missing results)
- Balance tool distribution if possible
- Use `include_context=True` for multi-turn understanding

---

## Module Structure

```
reusable_lib/
├── __init__.py              # Main exports
├── README.md                # This file
│
├── api/                     # API client utilities
│   ├── __init__.py
│   ├── rate_limiter.py      # Sliding window rate limiting
│   ├── retry_handler.py     # Exponential backoff + RetryHandler class
│   ├── models.py            # Claude model configuration
│   ├── models_openai.py     # Open source model configuration
│   └── openai_client.py     # OpenAI-compatible client (Ollama, etc.)
│
├── costs/                   # Token & cost tracking
│   ├── __init__.py
│   ├── token_counter.py     # Token estimation
│   └── cost_tracker.py      # Usage & cost tracking
│
├── messages/                # Message conversion
│   ├── __init__.py
│   ├── message_converter.py # OpenAI <-> Claude messages
│   └── tool_adapter.py      # Tool schema conversion
│
├── tools/                   # AI tools
│   ├── __init__.py
│   ├── utilities.py         # Time, calculator, etc.
│   └── memory.py            # Key-value memory
│
├── utils/                   # Utilities
│   ├── __init__.py
│   └── errors.py            # Error classes
│
├── caching/                 # Prompt caching
│   ├── __init__.py
│   └── cache_manager.py     # Cache strategies
│
├── streaming/               # Streaming infrastructure
│   ├── __init__.py
│   └── streaming.py         # Events, tracking, progress
│
├── execution/               # Sandboxed execution
│   ├── __init__.py
│   └── filesystem.py        # Safe file operations
│
├── agents/                  # Multi-agent system
│   ├── __init__.py
│   └── agents.py            # Agent orchestration
│
├── vector/                  # Vector database
│   ├── __init__.py
│   ├── vector_db.py         # ChromaDB wrapper
│   └── memory_health.py     # Memory maintenance
│
├── config/                  # Configuration
│   ├── __init__.py
│   └── preset_manager.py    # Settings presets
│
├── evaluation/              # Model benchmarking
│   ├── __init__.py
│   ├── benchmark.py         # TestSuite, ModelBenchmark, ComparisonReport
│   ├── evaluators.py        # ToolCallEvaluator, JSONValidityEvaluator, etc.
│   └── metrics.py           # Accuracy, latency, cost calculations
│
├── training/                # Fine-tuning data generation
│   ├── __init__.py
│   └── data_extractor.py    # Extract training data from conversations
│
└── eeg/                     # Neural interface
    ├── __init__.py
    ├── connection.py        # OpenBCI hardware + mock
    ├── processor.py         # Signal processing
    └── experience.py        # Emotion mapping
```

---

## Dependencies

**Core (pure Python):**
- `api`, `costs`, `messages`, `tools`, `utils`, `caching`, `streaming`, `config` - No dependencies

**Optional:**
- `anthropic` - For error classification in retry handler
- `chromadb`, `sentence-transformers`, `numpy` - For vector module
- `numpy`, `scipy` - For eeg module (required)
- `brainflow` - For eeg module with real hardware (optional, mock mode works without)
- (No additional deps for agents - bring your own API client)

---

## Quick Reference

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| `api` | Rate limiting, retry, models, clients | `RateLimiter`, `retry_on_error`, `ClaudeModels`, `OpenAICompatibleClient`, `OllamaClient` |
| `costs` | Token counting, cost tracking | `CostTracker`, `count_tokens` |
| `messages` | Format conversion | `prepare_messages_for_claude`, `format_tool_result_for_claude` |
| `tools` | Pre-built AI tools | `get_current_time`, `calculator`, `memory_store` |
| `utils` | Error handling | `RetryableError`, `UserFixableError`, `FatalError` |
| `caching` | Prompt caching | `CacheManager`, `CacheStrategy` |
| `streaming` | Progress tracking | `StreamEvent`, `ToolExecutionTracker`, `ProgressIndicator` |
| `execution` | Sandboxed filesystem | `FilesystemSandbox`, `fs_read_file`, `fs_write_file` |
| `agents` | Multi-agent system | `AgentManager`, `Agent`, `AGENT_TYPES` |
| `vector` | Semantic search | `VectorDB`, `VectorCollection`, `MemoryHealth` |
| `config` | Preset management | `PresetManager` |
| `evaluation` | Model benchmarking | `ModelBenchmark`, `TestSuite`, `ToolCallEvaluator`, `compare_models` |
| `training` | Fine-tuning data | `TrainingDataExtractor`, `ExportFormat`, `generate_training_dataset` |
| `eeg` | Neural interface | `EEGConnection`, `EEGProcessor`, `EmotionMapper`, `ListeningSession` |

---

## Origin

Extracted from [ApexAurum - Claude Edition](https://github.com/...), a production-grade AI chat interface with 52 integrated tools, multi-agent orchestration, and prompt caching.

---

## License

MIT License - Use freely in your projects.
