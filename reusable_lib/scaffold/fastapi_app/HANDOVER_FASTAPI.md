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

#### 1. Tools-Enabled Mode Timeout (MITIGATED)
- **Symptom:** When "Enable Instruments" checkbox is checked, requests timeout with 79 tools
- **Root Cause:** Tool prompt injection makes request too large for small 1.5B models
- **Mitigation:** Use Tool Selector (see below) to reduce active tool count
- **Recommendation:** Use "Minimal" preset (15 tools) or "Standard" (30 tools) for Hailo models

#### 2. sentence-transformers ✅ INSTALLED
- Now installed in venv with ARM64 support
- Runs on Pi 5 CPU (not Hailo accelerator - requires HEF format)

---

## New Feature: Tool Selector System

### Overview
Reduces tool count to prevent context overflow on small models.

### Presets (in UI sidebar)
| Preset | Tools | Use Case |
|--------|-------|----------|
| Minimal | 15 | Fast responses on 1.5B models |
| Standard | 30 | General purpose without heavy features |
| Creative | 38 | Music/audio focused |
| Research | 39 | Vector search, agents, Village |
| Full | 79 | All tools (use with larger models) |

### API Endpoints
```bash
# Get tool groups with states
GET /api/tools/settings/groups

# Get available presets
GET /api/tools/settings/presets

# Apply a preset
POST /api/tools/settings/presets/apply
{"preset_id": "minimal"}

# Toggle a group
PUT /api/tools/settings/groups/{group_id}
{"enabled": false}

# Toggle individual tool
PUT /api/tools/settings/tools/{tool_name}
{"enabled": false}

# Get enabled tools list
GET /api/tools/enabled
```

### Tool Groups (14 groups)
| Group | Tools | Description |
|-------|-------|-------------|
| utility | 5 | Time, calculator, word count |
| memory | 5 | Key-value persistent memory |
| filesystem | 9 | File operations in sandbox |
| code | 1 | Python execution |
| string | 6 | Text manipulation |
| web | 2 | Fetch URLs, web search |
| vector | 7 | Semantic search, knowledge |
| agent | 5 | Multi-agent orchestration |
| village | 8 | Village Protocol |
| memory_health | 5 | Memory maintenance |
| dataset | 2 | Vector dataset queries |
| suno | 4 | Music prompt generation |
| audio | 10 | Audio file editing |
| music | 10 | Suno AI music, MIDI |

### Settings Persistence
Tool exclusions saved to `data/tool_settings.json`

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

### 1. ✅ Tool Selector System - COMPLETE
- 14 tool groups with toggle UI
- 5 presets (Minimal, Standard, Creative, Research, Full)
- Settings persist to data/tool_settings.json
- UI in sidebar with collapsible groups

### 2. ✅ sentence-transformers - INSTALLED
- Installed with ARM64 support for Pi 5
- Runs on CPU (~slower than GPU but functional)

### 3. Test Tools-Enabled Mode with Reduced Tools
- [ ] Test "Minimal" preset (15 tools) with streaming
- [ ] Test "Standard" preset (30 tools) with streaming
- [ ] Compare response times with llama3.2:3b vs qwen2.5:1.5b
- [ ] Verify tool execution works

### 4. Test All Features
- [x] Simple chat (no tools) - WORKS
- [x] Streaming chat - WORKS
- [ ] Tools-enabled with Minimal preset
- [ ] Village Protocol search
- [ ] Conversations save/load
- [ ] Agent spawning

### 5. Future UI Improvements
- Add model info (parameter size) to selector
- Show Hailo-specific status (chip temp, memory)
- Individual tool toggles within groups

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
- `routes/tools.py` - Tool settings API endpoints
- `services/tool_service.py` - sys.path fix + Tool Groups + Presets
- `templates/index.html` - Tool selector UI
- `run_venv.sh` - Helper script (new)
- `HANDOVER_FASTAPI.md` - This file (new)
- `data/tool_settings.json` - Tool exclusion state (created at runtime)

29+ commits already in airlock from previous sessions.

---

## Related Documentation

- `/home/hailo/claude-root/Projects/ApexAurum/CLAUDE.md` - Main project docs
- `/home/hailo/claude-root/Projects/ApexAurum/HAILO_PI_SETUP.md` - Hardware setup
- `/home/hailo/claude-root/Projects/ApexAurum/reusable_lib/scaffold/fastapi_app/README.md` - FastAPI scaffold docs

---

*Handover prepared by Claude Opus 4.5 - Session 2026-01-23*
