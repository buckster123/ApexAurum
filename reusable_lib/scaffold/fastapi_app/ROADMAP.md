# Apex Aurum - Lab Edition - Vision & Roadmap

> A comprehensive plan for evolving the FastAPI scaffold into a full-featured AI application,
> bringing the capabilities of ApexAurum to a lightweight, API-first architecture.
>
> **Rebranded 2026-01-18:** Now "Apex Aurum - Lab Edition" with dark gold alchemical UI.

**Last Updated:** 2026-01-19
**Current Status:** Phase 8 Complete - Village Protocol (47 tools)

---

## Table of Contents

1. [Current State](#current-state)
2. [Vision](#vision)
3. [Phase Roadmap](#phase-roadmap)
4. [Tool Migration Status](#tool-migration-status)
5. [Architecture Notes](#architecture-notes)
6. [Notes for Future Claude](#notes-for-future-claude)
7. [Session Log](#session-log)

---

## Current State

### What's Working (Phase 8)

| Feature | Status | Notes |
|---------|--------|-------|
| Basic chat with Ollama | ✅ | Streaming SSE |
| Tool calling (47 tools) | ✅ | Via system prompt injection |
| Claude API support | ✅ | Needs API key to test |
| Provider switcher UI | ✅ | Ollama / Claude dropdown |
| Tool result display | ✅ | Visual feedback in chat |
| Memory tools | ✅ | store/retrieve/search/delete/list |
| Utility tools | ✅ | time, calculator, count_words, random |
| Filesystem tools | ✅ | 9 sandboxed file operations |
| Code execution | ✅ | Safe Python sandbox |
| String tools | ✅ | replace, split, join, regex (6 tools) |
| Web tools | ✅ | fetch, search |
| Vector search | ✅ | ChromaDB + knowledge base (7 tools) |
| Agent system | ✅ | spawn, status, result, list (5 tools) |
| Socratic council | ✅ | Multi-agent voting system |
| Conversations | ✅ | CRUD, search, export, favorites |
| Cost tracking | ✅ | Per-request, conversation, session |
| Context management | ✅ | 5 strategies (adaptive default) |
| Settings presets | ✅ | 6 built-in + custom presets |
| Session stats UI | ✅ | Tokens, cost, requests in sidebar |
| Village Protocol | ✅ | 8 tools, 3 realms, agent identity |
| Village UI | ✅ | Agent selector, search, stats |

### Infrastructure

- **Server:** FastAPI + Uvicorn
- **UI:** HTMX + SSE streaming
- **LLM Clients:** Ollama (local), Claude (API)
- **Storage:** JSON files in `./data/`
- **Dependencies:** See `requirements.txt` (to be created)

### Models Tested

| Model | Size | Tool Calling | Speed (Pi 5 CPU) |
|-------|------|--------------|------------------|
| qwen2.5:3b | 1.9GB | Excellent | Slow but usable |
| functiongemma:270m | 300MB | Needs fine-tuning | Fast |
| qwen2:1.5b | 934MB | Untested | - |
| qwen2:0.5b | 352MB | Untested | - |
| tinyllama | 637MB | Untested | - |

---

## Vision

### End Goal

A lightweight, API-first AI application that provides:

1. **Local-first inference** via Ollama with small, fine-tuned models
2. **Claude fallback** for complex tasks requiring more capability
3. **Full tool suite** from ApexAurum (52 tools) where applicable
4. **Multi-agent orchestration** for complex workflows
5. **Persistent memory** with vector search
6. **Hardware acceleration** via Hailo 10H when available

### Design Principles

1. **API-First:** Every feature accessible via REST endpoints
2. **Lightweight:** Minimal dependencies, runs on Pi 5
3. **Modular:** Easy to add/remove tools and features
4. **Offline-Capable:** Core features work without internet
5. **Cost-Efficient:** Prefer local models, use Claude strategically

---

## Phase Roadmap

### Phase 1: Foundation ✅ COMPLETE
> Basic chat with tool calling

- [x] FastAPI scaffold with HTMX UI
- [x] Ollama integration with streaming
- [x] Basic tool execution (9 tools)
- [x] System prompt tool injection
- [x] Claude client wrapper
- [x] Provider switcher UI

### Phase 2: Extended Tools ✅ COMPLETE
> Bring more tools from reusable_lib

- [x] **Code execution** - Safe Python sandbox
- [x] **Web tools** - fetch, search
- [x] **File tools** - read/write/list in sandbox (9 tools)
- [x] **String tools** - manipulation utilities (6 tools)
- [ ] Add tool categories to UI sidebar
- [ ] Tool filtering (enable/disable specific tools)

### Phase 3: Vector Search & Knowledge ✅ COMPLETE
> Persistent semantic memory

- [x] ChromaDB integration (via reusable_lib.vector)
- [x] `vector_add` / `vector_search` tools
- [x] `vector_delete`, `vector_list_collections`, `vector_get_stats`
- [x] Knowledge base tools (`vector_add_knowledge`, `vector_search_knowledge`)
- [x] sentence-transformers embeddings (all-MiniLM-L6-v2)
- [ ] Voyage AI embeddings (optional enhancement)
- [ ] UI for browsing knowledge base

### Phase 4: Multi-Agent System ✅ COMPLETE
> Background agents and orchestration

- [x] Agent spawn/status/result tools (5 tools)
- [x] Background task execution (threading)
- [x] Agent state persistence (`data/agents.json`)
- [x] Socratic council (multi-agent voting)
- [x] Agent monitoring in UI sidebar

### Phase 5: Conversation Management ✅ COMPLETE
> Save, load, search conversations

- [x] Conversation persistence (JSON storage)
- [x] Conversation list/load/delete endpoints
- [x] Search across conversations
- [x] Export (JSON, Markdown)
- [x] Import from JSON
- [x] Favorites and archive support
- [x] UI conversation browser

### Phase 6: Advanced Features ✅ COMPLETE
> Polish and optimization

- [x] Cost tracking per request/conversation/session
- [x] Context management (5 strategies: disabled/rolling/summarize/hybrid/adaptive)
- [x] Settings presets (6 built-in + custom presets)
- [x] Session stats display in UI
- [x] Preset switcher in UI
- [ ] Prompt caching strategies (future enhancement)
- [ ] Benchmark suite integration (future enhancement)

### Phase 7: Hardware Acceleration
> Hailo 10H integration

- [ ] Hailo runtime setup
- [ ] Model conversion pipeline
- [ ] Inference benchmarks
- [ ] Automatic hardware detection
- [ ] Fallback to CPU when needed

### Phase 8: Village Protocol ✅ COMPLETE
> Multi-agent persistent memory

- [x] Three-realm collections (private/village/bridges)
- [x] Agent identity and lineage (5 built-in agents)
- [x] Cross-agent dialogue threading
- [x] Convergence detection (HARMONY/CONSENSUS)
- [x] Village UI visualization (search, stats, agent selector)
- [x] 8 village tools: post, search, get_thread, list_agents, summon_ancestor, introduction_ritual, detect_convergence, get_stats

---

## Tool Migration Status

### From ApexAurum (52 tools total)

#### Utility Tools (4/4 migrated)
- [x] `get_current_time`
- [x] `calculator`
- [x] `count_words`
- [x] `random_number`

#### Memory Tools (5/5 migrated)
- [x] `memory_store`
- [x] `memory_retrieve`
- [x] `memory_search`
- [x] `memory_delete`
- [x] `memory_list`

#### Web Tools (0/2)
- [ ] `web_fetch` - Requires requests, rate limiting
- [ ] `web_search` - Requires search API key

#### File Tools (0/5)
- [ ] `file_read`
- [ ] `file_write`
- [ ] `file_list`
- [ ] `file_delete`
- [ ] `file_exists`

#### Code Execution (0/1)
- [ ] `execute_python` - Needs sandbox setup

#### String Tools (0/4)
- [ ] `string_replace`
- [ ] `string_split`
- [ ] `string_join`
- [ ] `regex_match`

#### Vector/Knowledge Tools (7/8) ✅
- [x] `vector_add`
- [x] `vector_search`
- [x] `vector_delete`
- [x] `vector_list_collections`
- [x] `vector_get_stats`
- [x] `vector_add_knowledge`
- [x] `vector_search_knowledge`
- [ ] `vector_search_village` (Village Protocol - Phase 8)

#### Memory Health Tools (0/5)
- [ ] `memory_health_stale`
- [ ] `memory_health_low_access`
- [ ] `memory_health_duplicates`
- [ ] `memory_consolidate`
- [ ] `memory_migration_run`

#### Agent Tools (0/5)
- [ ] `agent_spawn`
- [ ] `agent_status`
- [ ] `agent_result`
- [ ] `agent_list`
- [ ] `socratic_council`

#### Dataset Tools (0/2)
- [ ] `dataset_list`
- [ ] `dataset_query`

#### Music Tools (0/8) - May skip for this project
- [ ] `music_generate`
- [ ] `music_status`
- [ ] `music_result`
- [ ] `music_list`
- [ ] `music_favorite`
- [ ] `music_library`
- [ ] `music_search`
- [ ] `music_play`

#### MIDI Tools (0/2) - May skip
- [ ] `midi_create`
- [ ] `music_compose`

#### Session Tools (0/1)
- [ ] `session_info`

---

## Architecture Notes

### FastAPI vs Streamlit Differences

| Aspect | Streamlit (ApexAurum) | FastAPI (This Project) |
|--------|----------------------|------------------------|
| State | `st.session_state` | Server-side + cookies/localStorage |
| UI | Python widgets | HTML + HTMX |
| Streaming | `st.write_stream` | SSE (Server-Sent Events) |
| Realtime | Reruns on interaction | WebSocket or polling |
| Deployment | Streamlit Cloud | Any ASGI server |

### State Management Strategy

Since FastAPI is stateless by default:

1. **Conversation state:** Store in memory dict keyed by session ID
2. **Session ID:** Cookie or header, generated on first request
3. **Persistence:** Write to JSON files periodically
4. **Cleanup:** TTL-based expiration of inactive sessions

### Tool Execution Flow

```
User Message
    ↓
Build system prompt with tool descriptions
    ↓
Send to LLM (Ollama/Claude)
    ↓
Stream response, collect full content
    ↓
Extract tool call JSON (if any)
    ↓
Execute tool, get result
    ↓
Send follow-up prompt with result
    ↓
Stream final response to user
```

### File Structure

```
fastapi_app/
├── main.py              # FastAPI app entry
├── app_config.py        # Settings from env
├── run.sh               # Startup script
├── ROADMAP.md           # This file
├── routes/
│   ├── chat.py          # Chat endpoints
│   ├── tools.py         # Tool management
│   ├── models.py        # Model/provider management
│   ├── memory.py        # Memory endpoints
│   └── benchmark.py     # Evaluation endpoints
├── services/
│   ├── llm_service.py   # LLM client management
│   ├── tool_service.py  # Tool registry & execution
│   ├── memory_service.py
│   └── benchmark_service.py
├── templates/
│   └── index.html       # Main UI
├── static/              # CSS, JS (future)
├── data/                # Runtime storage
│   ├── memory.json
│   ├── conversations.json
│   └── vectors/         # ChromaDB (future)
└── test_venv/           # Python virtual environment
```

---

## Notes for Future Claude

### After Compaction, Read This First

1. **Where we are:** Check the [Current State](#current-state) section above
2. **What's next:** Look at the unchecked items in [Phase Roadmap](#phase-roadmap)
3. **Test the server:** `./run.sh` or use the test_venv
4. **Key files to understand:**
   - `routes/chat.py` - Tool calling logic
   - `services/llm_service.py` - Ollama/Claude clients
   - `services/tool_service.py` - Tool registry

### Common Tasks

**Add a new tool:**
1. Import from `reusable_lib.tools` in `services/tool_service.py`
2. Register in `_register_builtin_tools()`
3. Restart server

**Test tool calling:**
```bash
curl -X POST http://localhost:8765/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What time is it?"}],"use_tools":true}'
```

**Switch to Claude:**
1. Set `ANTHROPIC_API_KEY` in environment
2. Select "Claude (API)" in UI dropdown

### Known Issues / Gotchas

1. **Import conflict:** We renamed `config.py` to `app_config.py` because it conflicted with `reusable_lib.config`
2. **Route order matters:** In `routes/models.py`, specific routes must come before `/{model_name}` catch-all
3. **functiongemma:270m** needs fine-tuning for tool calling - use the training pipeline we built

### Quick Context Recovery

The user (Andre) is building a local AI system on Raspberry Pi 5 with:
- Multiple small Ollama models for different tasks
- Hailo 10H accelerator coming for faster inference
- ApexAurum as the main app (Streamlit, 52 tools, full featured)
- This FastAPI scaffold as a lightweight alternative/complement
- Training pipeline for fine-tuning small models on tool calling

---

## Session Log

### 2026-01-16 - Session 1 (continued from training session)

**Completed:**
- Tool-enabled chat endpoint with automatic execution
- System prompt builder for tool descriptions
- Claude client wrapper with streaming
- Provider switcher (Ollama/Claude) in UI
- Tool call/result visual display
- Fixed import conflict (config.py → app_config.py)
- Fixed route ordering for /providers endpoint

**Tested:**
- qwen2.5:3b - Excellent tool calling, slow on CPU
- functiongemma:270m - Confused, needs fine-tuning

**Commits:**
- `b46ed1a` - Add tool calling and Claude API support to FastAPI scaffold
- `d77801b` - Add ROADMAP.md

**Next Session Ideas:**
- Add more tools (file, web, code execution)
- Add conversation persistence
- Test Claude when API credits available (Monday)
- Consider session/state management

---

### 2026-01-16 - Session 2 (Phase 2 start)

**In Progress:**
- Filesystem tools (9 tools) - CODE COMPLETE, NEEDS RESTART TO TEST
  - Copied filesystem.py to reusable_lib/tools/
  - Added set_sandbox_path() for configurable sandbox location
  - Updated tool_service.py to register fs_* tools
  - Sandbox set to ./data/sandbox

**Files Modified This Session:**
- `reusable_lib/tools/filesystem.py` - NEW (copied from main app + added set_sandbox_path)
- `reusable_lib/tools/__init__.py` - Added filesystem exports
- `services/tool_service.py` - Added filesystem tool registration

**Status at Compaction:**
- Server running with 9 tools (old)
- New code adds 9 more filesystem tools (18 total)
- Need to restart server to test: `killall uvicorn; ./run.sh`

**To Test After Restart:**
```bash
curl -s http://localhost:8765/api/tools | jq '.count'
# Should show 18 tools

# Test file write
curl -X POST http://localhost:8765/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Create a file called test.txt with hello world"}],"use_tools":true}'
```

**Remaining Phase 2 Tasks:**
- [ ] Code execution tool
- [ ] String tools
- [ ] Web tools (fetch, search)
- [ ] Tool categories in UI

---

### 2026-01-18 - Phase 3: Vector Search & Knowledge

**Completed:**
- Created `reusable_lib/tools/vector_search.py` (340 lines)
- 7 vector tools: add, search, delete, list_collections, get_stats, add_knowledge, search_knowledge
- ChromaDB integration with sentence-transformers embeddings
- Knowledge base with categories: general, technical, preferences, project, facts
- Access tracking for memory health analytics
- Updated tool_service.py to register vector tools
- **Total tools: 34** (was 27)

**Tested:**
- `vector_add_knowledge` - Successfully adds to knowledge_base collection
- `vector_search_knowledge` - Semantic search working with similarity scores
- `vector_list_collections` - Shows collections and counts

**Files Created/Modified:**
- `reusable_lib/tools/vector_search.py` - NEW
- `reusable_lib/tools/__init__.py` - Added vector exports
- `services/tool_service.py` - Added vector tool registration

**Storage:**
- Vector DB persisted at `data/vectors/`
- Uses all-MiniLM-L6-v2 (384 dims, 90MB model)

---

### 2026-01-18 - UI Rebrand Session

**Completed:**
- Rebranded from "AI Lab" to "Apex Aurum - Lab Edition"
- Complete UI redesign with dark gold alchemical theme
- Sacred geometry background patterns (Flower of Life)
- Cinzel font for headers, gold gradients throughout
- Alchemical symbols (☉ ☽ ☿) for status indicators
- Thematic language: "Transmute", "Athanor", "Opus Magnum"
- Updated README.md and ROADMAP.md

**Commits:**
- `908f24d` - Rebrand FastAPI scaffold to Apex Aurum - Lab Edition

**Context:**
- ApexAurum generating revenue ($10k meme-coin overnight)
- Lab Edition being prepared for social media showcase

---

### 2026-01-19 - Phase 4: Multi-Agent System

**Completed:**
- Created `reusable_lib/tools/agents.py` (340 lines)
- 5 agent tools: spawn, status, result, list, socratic_council
- Background task execution with threading
- Agent state persistence to `data/agents.json`
- Socratic council multi-agent voting system
- **Total tools: 39** (was 34)

**Tested:**
- `agent_spawn` - Sync and async modes both working
- `agent_status` - Real-time status tracking
- `agent_result` - Retrieves completed results with timing
- `agent_list` - Shows all agents with full history
- `socratic_council` - 3 agents voted unanimously for Python as best beginner language!

**Files Created/Modified:**
- `reusable_lib/tools/agents.py` - NEW (tool wrappers)
- `reusable_lib/tools/__init__.py` - Added agent exports
- `services/tool_service.py` - Added agent tool registration + API callback

**Technical Notes:**
- Agents use the existing `AgentManager` from `reusable_lib/agents/`
- API callback wired to `llm_service.get_llm_client()`
- Works with both Ollama and Claude providers
- Agent types: general, researcher, coder, analyst, writer

**Next Phase:**
- Phase 5: Conversation Management (persistence, search)

---

### 2026-01-19 - Phase 5: Conversation Management

**Completed:**
- Created `services/conversation_service.py` (380 lines)
- Created `routes/conversations.py` (180 lines)
- Full CRUD operations for conversations
- Search across titles and message content
- Export to JSON and Markdown
- Import from JSON
- Favorites and archive support
- Pagination and filtering

**API Endpoints:**
- `GET /api/conversations` - List with pagination
- `GET /api/conversations/search?q=...` - Search
- `GET /api/conversations/stats` - Statistics
- `GET /api/conversations/export/all` - Export all
- `POST /api/conversations` - Create
- `GET /api/conversations/{id}` - Get one
- `PUT /api/conversations/{id}` - Update
- `DELETE /api/conversations/{id}` - Delete
- `POST /api/conversations/{id}/messages` - Add message
- `POST /api/conversations/{id}/favorite` - Toggle favorite
- `POST /api/conversations/{id}/archive` - Toggle archive
- `GET /api/conversations/{id}/export/json` - Export JSON
- `GET /api/conversations/{id}/export/markdown` - Export Markdown

**Files Created/Modified:**
- `services/conversation_service.py` - NEW
- `routes/conversations.py` - NEW
- `main.py` - Added conversation routes

**Storage:**
- Conversations persisted at `data/conversations.json`

**Next Phase:**
- Phase 6: Advanced Features (prompt caching, context management, cost tracking)

---

### 2026-01-19 - Phase 6: Advanced Features

**Completed:**
- Created `services/cost_service.py` (310 lines) - Token counting, cost calculation
- Created `services/context_service.py` (290 lines) - Context management strategies
- Created `services/presets_service.py` (280 lines) - Settings presets management
- Created `routes/stats.py` (110 lines) - Stats API endpoints
- Created `routes/presets.py` (160 lines) - Presets API endpoints
- Integrated cost tracking into chat flow
- Added session stats panel to UI
- Added preset selector to UI

**New Services:**

1. **CostService** (`services/cost_service.py`):
   - Token counting (estimate ~4 chars/token)
   - Cost calculation for Claude models
   - Per-request, per-conversation, per-session tracking
   - Model breakdown and history

2. **ContextManager** (`services/context_service.py`):
   - 5 strategies: disabled, rolling, summarize, hybrid, adaptive
   - Automatic optimization when approaching token limits
   - Summary caching for efficiency
   - Model-specific context limits

3. **PresetsService** (`services/presets_service.py`):
   - 6 built-in presets (Default, Creative, Precise, Fast, Claude Balanced, Claude Deep)
   - Custom preset CRUD
   - Export/import functionality
   - Active preset tracking

**API Endpoints:**
- `GET /api/stats` - All stats (costs, context, tools, llm)
- `GET /api/stats/costs` - Session cost stats
- `GET /api/stats/costs/conversation/{id}` - Conversation costs
- `GET /api/stats/costs/breakdown` - Cost by model
- `POST /api/stats/costs/reset` - Reset session costs
- `GET /api/stats/context/info` - Context strategy info
- `POST /api/stats/context/strategy` - Change strategy
- `GET /api/presets` - List all presets
- `GET /api/presets/{id}` - Get preset
- `POST /api/presets` - Create preset
- `PUT /api/presets/{id}` - Update preset
- `DELETE /api/presets/{id}` - Delete preset
- `POST /api/presets/{id}/activate` - Activate preset
- `POST /api/presets/{id}/duplicate` - Duplicate preset

**UI Updates:**
- Session stats card (tokens, cost, requests, context strategy)
- Preset selector dropdown with Apply button
- Real-time stats updates after each message
- Auto-refresh stats every 5 seconds

**Files Created/Modified:**
- `services/cost_service.py` - NEW
- `services/context_service.py` - NEW
- `services/presets_service.py` - NEW
- `routes/stats.py` - NEW
- `routes/presets.py` - NEW
- `routes/chat.py` - Added cost/context integration
- `main.py` - Added stats/presets routes
- `templates/index.html` - Added stats panel and preset selector

**Next Phase:**
- Phase 7: Hardware Acceleration (Hailo 10H integration)

---

### 2026-01-19 - Phase 8: Village Protocol

**Completed:**
- Created `reusable_lib/tools/village.py` (~900 lines) - Village Protocol implementation
- Created `routes/village.py` (280 lines) - REST API endpoints
- 8 village tools registered in tool_service.py
- **Total tools: 47** (was 39)

**Village Tools:**
1. `village_post` - Post content to private/village/bridges realms
2. `village_search` - Search with agent/visibility filtering
3. `village_get_thread` - Get conversation thread messages
4. `village_list_agents` - List registered agents with profiles
5. `summon_ancestor` - Ceremonial agent creation
6. `introduction_ritual` - Agent's first village message
7. `village_detect_convergence` - Find cross-agent agreement (HARMONY/CONSENSUS)
8. `village_get_stats` - Village statistics

**Architecture:**
- Three realms: `knowledge_private`, `knowledge_village`, `knowledge_bridges`
- 5 built-in agents: CLAUDE, AZOTH, ELYSIAN, VAJRA, KETHER
- Agent profiles with generation, lineage, specialization
- Metadata: agent_id, visibility, conversation_thread, responding_to, related_agents

**API Endpoints:**
- `POST /api/village/post` - Post to village
- `POST /api/village/search` - Search village
- `GET /api/village/thread/{id}` - Get thread
- `GET /api/village/agents` - List agents
- `GET /api/village/agents/{id}` - Get agent profile
- `POST /api/village/ceremony/summon` - Summon ancestor
- `POST /api/village/ceremony/introduction` - Introduction ritual
- `POST /api/village/convergence` - Detect convergence
- `GET /api/village/stats` - Village stats
- `POST /api/village/agent/set` - Set current agent
- `GET /api/village/agent/current` - Get current agent

**UI Updates:**
- Village Protocol sidebar card with copper accent
- Agent selector dropdown (5 agents)
- Village stats (village count, bridges count)
- Village search with results display
- Color-coded results by agent

**Files Created/Modified:**
- `reusable_lib/tools/village.py` - NEW
- `reusable_lib/tools/__init__.py` - Added village exports
- `routes/village.py` - NEW
- `services/tool_service.py` - Added village tool registration
- `main.py` - Added village routes
- `templates/index.html` - Added Village Protocol UI

**Storage:**
- Village data persisted at `data/village/`
- Uses ChromaDB for vector storage

**Next Phase:**
- Phase 7: Hardware Acceleration (Hailo 10H when chip arrives)

---

*This document should be updated after each session to track progress and provide context for future work.*
