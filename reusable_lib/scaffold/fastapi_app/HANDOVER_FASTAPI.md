# FastAPI Lab Edition - Handover Notes

**Last Updated:** 2026-01-23
**Session:** Hailo-10H Integration with hailo-ollama

---

## Current State: WORKING (with known issues)

The FastAPI Lab Edition is now operational with hailo-ollama on the Raspberry Pi 5 + Hailo-10H setup.

### What's Working

| Feature | Status | Notes |
|---------|--------|-------|
| Server startup | OK | Port 8765 |
| Health check | OK | Uses native Ollama API |
| Model listing | OK | 5 Hailo models available |
| Simple chat | OK | `/api/chat/simple` |
| Streaming chat | OK | Uses native `/api/chat` endpoint |
| Tools listing | OK | 79 tools registered |
| Web UI | OK | Beautiful alchemical theme |
| Claude provider | OK | Works when API key set |

### Known Issues

#### 1. Tools-Enabled Mode Timeout (HIGH PRIORITY)
- **Symptom:** When "Enable Instruments" checkbox is checked, requests timeout
- **Likely Cause:** Tool prompt injection makes the request too large/slow for small 1.5B models
- **Location:** `routes/chat.py` - `chat_stream()` function
- **Investigation needed:**
  - Check if system prompt with 79 tool schemas exceeds context window
  - Consider reducing tool set for small models
  - Add timeout handling / streaming keepalive
  - Test with larger model (llama3.2:3b)

#### 2. sentence-transformers Not Installed
- **Symptom:** Vector DB stats fail silently
- **Fix:** `./venv/bin/pip install sentence-transformers`
- **Impact:** Low - vector search still works with ChromaDB defaults

---

## Architecture

### Hailo-Ollama Specifics

Hailo-ollama is NOT fully OpenAI-compatible:

| Endpoint | Supported | Notes |
|----------|-----------|-------|
| `/v1/chat/completions` | YES | Non-streaming only |
| `/v1/chat/completions` (stream) | NO | Returns error |
| `/v1/models` | NO | 404 error |
| `/api/tags` | YES | Native Ollama - model listing |
| `/api/chat` | YES | Native Ollama - streaming works |

### Fixes Applied This Session

1. **`services/tool_service.py`** - Fixed sys.path ordering
   - Problem: `tools.suno_compiler` not found
   - Cause: `reusable_lib/tools/` was searched before `ApexAurum/tools/`
   - Fix: Explicit path ordering with remove/insert

2. **`routes/models.py`** - Native Ollama API for health + models
   - `list_models()` uses `/api/tags` for Ollama
   - `check_llm_health()` uses `/api/tags` for Ollama

3. **`routes/chat.py`** - Native Ollama streaming
   - Added `native_ollama_stream()` function
   - `chat_stream()` detects provider and uses appropriate API
   - Both initial response and tool follow-up use native streaming

4. **`app_config.py`** - Default model fix
   - Changed from `qwen2.5:3b` (doesn't exist) to `qwen2.5-instruct:1.5b`

---

## Available Models on Hailo-10H

```
deepseek_r1_distill_qwen:1.5b  (2.4GB) - Reasoning model
llama3.2:3b                     (3.4GB) - Largest, best quality
qwen2.5-coder:1.5b             (1.8GB) - Code specialist
qwen2.5-instruct:1.5b          (2.4GB) - Default, general purpose
qwen2:1.5b                     (1.7GB) - Base model
```

Performance: ~7-8 tokens/sec on Hailo-10H

---

## Quick Start

```bash
cd /home/hailo/claude-root/Projects/ApexAurum/reusable_lib/scaffold/fastapi_app

# Start server
PYTHONPATH=/home/hailo/claude-root/Projects/ApexAurum \
  ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8765

# Or use the helper script
./run_venv.sh

# Access UI
http://192.168.0.114:8765
```

---

## File Locations

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app entry point |
| `routes/chat.py` | Chat endpoints + native Ollama streaming |
| `routes/models.py` | Model listing + health check |
| `services/llm_service.py` | LLM client management |
| `services/tool_service.py` | 79 tools registration |
| `templates/index.html` | Web UI (1385 lines) |
| `app_config.py` | Configuration |
| `server.log` | Runtime logs |
| `venv/` | Python virtual environment |

---

## Next Steps (Priority Order)

### 1. Fix Tools-Enabled Timeout
Options to investigate:
- Reduce tool schemas sent to model (category filter?)
- Increase timeout in `native_ollama_stream()`
- Add streaming keepalive pings
- Test if issue is model-specific (try llama3.2:3b)

### 2. Install sentence-transformers
```bash
./venv/bin/pip install sentence-transformers
```

### 3. Test All Features
- [ ] Simple chat (no tools) - WORKS
- [ ] Streaming chat - WORKS
- [ ] Tools-enabled chat - TIMEOUT (investigate)
- [ ] Village Protocol search
- [ ] Conversations save/load
- [ ] Presets
- [ ] Agent spawning

### 4. Consider UI Improvements
- Add model info (parameter size) to selector
- Show Hailo-specific status (chip temp, memory)
- Add tool category filter for small models

---

## Debugging Tips

### Check server logs
```bash
tail -f server.log
```

### Test native Ollama streaming directly
```bash
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-instruct:1.5b","messages":[{"role":"user","content":"Hi"}],"stream":true}'
```

### Test health check
```bash
curl http://localhost:8765/api/models/health/check
# Should return: {"healthy":true,"provider":"ollama","endpoint":"http://localhost:11434"}
```

### Test tools listing
```bash
curl http://localhost:8765/api/tools | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])"
# Should return: 79
```

---

## Git Status

Changes ready to commit:
- `app_config.py` - Default model fix
- `routes/chat.py` - Native Ollama streaming
- `routes/models.py` - Native Ollama health/models
- `services/tool_service.py` - sys.path fix
- `run_venv.sh` - Helper script (new)
- `HANDOVER_FASTAPI.md` - This file (new)

28+ commits already in airlock from previous sessions.

---

## Related Documentation

- `/home/hailo/claude-root/Projects/ApexAurum/CLAUDE.md` - Main project docs
- `/home/hailo/claude-root/Projects/ApexAurum/HAILO_PI_SETUP.md` - Hardware setup
- `/home/hailo/claude-root/Projects/ApexAurum/reusable_lib/scaffold/fastapi_app/README.md` - FastAPI scaffold docs

---

*Handover prepared by Claude Opus 4.5 - Session 2026-01-23*
