# Apex Aurum - Lab Edition

A clean, async-native FastAPI scaffold for building AI applications using `reusable_lib`.
Part of the Apex Aurum ecosystem.

## UI Theme

Dark mode with gold alchemical aesthetic:
- **Colors:** Deep void black (#0a0a0c) with gold accents (#D4AF37)
- **Typography:** Cinzel serif font for headers, Inter for body
- **Visual:** Sacred geometry patterns, corner accents, gold gradients
- **Symbols:** ☉ (Sun/Gold), ☽ (Moon/Silver), ☿ (Mercury)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install openai  # Required for LLM client

# 2. (Optional) Start Ollama if using local models
ollama serve
ollama pull llama3:8b

# 3. Run the app using the helper script
./run.sh

# Or manually with PYTHONPATH (required for reusable_lib imports):
PYTHONPATH=/path/to/reusable_lib/parent uvicorn main:app --host 0.0.0.0 --port 8765

# 4. Open browser
open http://localhost:8765
```

## Important: PYTHONPATH Setup

This scaffold imports from `reusable_lib`, which must be on your Python path.

**Option 1: Use the run.sh script** (recommended)
```bash
./run.sh                    # Default: port 8765
./run.sh --port 8000        # Custom port
./run.sh --reload           # Hot reload for development
```

**Option 2: Set PYTHONPATH manually**
```bash
# If reusable_lib is at /home/user/project/reusable_lib
# Then PYTHONPATH should include /home/user/project
export PYTHONPATH=/home/user/project:$PYTHONPATH
uvicorn main:app --host 0.0.0.0 --port 8765
```

**Option 3: Install reusable_lib as a package** (for production)
```bash
# From the reusable_lib directory:
pip install -e .  # Requires setup.py or pyproject.toml
```

## Configuration

Set via environment variables or edit `config.py`:

```bash
# LLM Provider
export LLM_PROVIDER=ollama              # ollama, llamacpp, vllm, together, groq
export LLM_BASE_URL=http://localhost:11434/v1
export DEFAULT_MODEL=llama3:8b

# For hosted providers
export LLM_API_KEY=your-api-key

# Server
export HOST=0.0.0.0
export PORT=8000
export DEBUG=true
```

## Project Structure

```
fastapi_app/
├── main.py              # Application entry point
├── config.py            # Configuration
├── requirements.txt     # Dependencies
│
├── routes/              # API endpoints
│   ├── chat.py          # /api/chat - Chat completions
│   ├── tools.py         # /api/tools - Tool execution
│   ├── models.py        # /api/models - Model management
│   ├── memory.py        # /api/memory - Storage
│   └── benchmark.py     # /api/benchmark - Evaluations
│
├── services/            # Business logic
│   ├── llm_service.py   # LLM client wrapper
│   ├── tool_service.py  # Tool execution
│   ├── memory_service.py # Memory operations
│   └── benchmark_service.py # Model benchmarking
│
├── templates/           # HTML templates
│   └── index.html       # Main chat UI (HTMX)
│
└── static/              # Static files
```

## API Endpoints

### Chat
```bash
# Simple chat
curl -X POST http://localhost:8000/api/chat/simple \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!", "model": "llama3:8b"}'

# Streaming
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Tell me a joke"}]}'
```

### Tools
```bash
# List tools
curl http://localhost:8000/api/tools

# Execute tool
curl -X POST http://localhost:8000/api/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "calculator", "arguments": {"operation": "add", "a": 5, "b": 3}}'

# Chat with tools
curl -X POST http://localhost:8000/api/tools/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What time is it?"}'
```

### Models
```bash
# List models
curl http://localhost:8000/api/models

# Pull model (Ollama)
curl -X POST http://localhost:8000/api/models/pull \
  -H "Content-Type: application/json" \
  -d '{"model": "phi3:mini"}'

# Health check
curl http://localhost:8000/api/models/health/check
```

### Memory
```bash
# Store
curl -X POST http://localhost:8000/api/memory/kv \
  -H "Content-Type: application/json" \
  -d '{"key": "user_name", "value": "Alice"}'

# Retrieve
curl http://localhost:8000/api/memory/kv/user_name

# Vector search
curl -X POST http://localhost:8000/api/memory/vector/search \
  -H "Content-Type: application/json" \
  -d '{"collection": "knowledge", "query": "python tips", "limit": 5}'
```

### Benchmark
```bash
# Quick comparison
curl -X POST http://localhost:8000/api/benchmark/quick \
  -H "Content-Type: application/json" \
  -d '{
    "prompts": ["What is 2+2?", "Tell me a joke"],
    "models": ["llama3:8b", "phi3:mini"],
    "evaluator": "json"
  }'
```

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Raspberry Pi
```bash
# Install dependencies
pip install -r requirements.txt

# Run with reduced workers for Pi
gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Extending

### Add Custom Tools
```python
# In services/tool_service.py

def my_custom_tool(param1: str, param2: int) -> dict:
    """My custom tool description."""
    return {"result": f"{param1} x {param2}"}

# Register in __init__
self.register("my_tool", my_custom_tool, {
    "name": "my_tool",
    "description": "Does something cool",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        },
        "required": ["param1"]
    }
})
```

### Add Routes
```python
# Create routes/my_routes.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint():
    return {"message": "Hello!"}

# In main.py
from routes import my_routes
app.include_router(my_routes.router, prefix="/api/my", tags=["My Feature"])
```

## Uses reusable_lib

This scaffold uses the following modules from `reusable_lib`:

- `api/` - OpenAI-compatible client for Ollama/local LLMs
- `tools/` - Pre-built AI tools
- `evaluation/` - Model benchmarking
- `vector/` - Semantic search (optional)
- `training/` - Dataset generation (via API if needed)
