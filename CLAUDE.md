# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ApexAurum - Claude Edition is a production-grade AI chat interface built on Anthropic's Claude API. It features multi-agent orchestration, adaptive memory architecture, vector search, intelligent prompt caching (50-90% cost savings), 39 integrated tools, and context management with auto-summarization.

**Status:** V1.0 Beta - Production Ready with Village Protocol + Thread Visualization + Convergence Detection (~19,500+ lines of code)

## Essential Reading Before Starting


1. **START_HERE.md** - 
2. **PROJECT_STATUS.md** - Current implementation status and what's pending
3. **DEVELOPMENT_GUIDE.md** - Detailed developer onboarding guide

## Quick Start Commands

### Running the Application after venv setup and copying modified files to venv for testing.

```bash
# Start the Streamlit application
streamlit run main.py

# Start on specific port
streamlit run main.py --server.port 8502

# Kill running instances
pkill -f streamlit
```

Access at: http://localhost:8501

### Testing

```bash
# Verify tool count (should be 39)
python -c "from tools import ALL_TOOLS; print(f'{len(ALL_TOOLS)} tools loaded')"

# Test agent functionality
python -c "from tools.agents import agent_spawn; print('Agent tools OK')"

# Run test suites (in dev_log_archive_and_testfiles/tests/)
python dev_log_archive_and_testfiles/tests/test_basic.py
python dev_log_archive_and_testfiles/tests/test_agents.py
python dev_log_archive_and_testfiles/tests/test_vector_db.py

# Test memory enhancement (Phases 1-3)
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase1.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase2.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase3.py
```

### Logs and Debugging

```bash
# Live log monitoring
tail -f app.log

# Search for errors
grep ERROR app.log | tail -20

# Check environment
cat .env
```

## High-Level Architecture

### System Layers

```
┌─────────────────────────────────────────┐
│     Streamlit UI (main.py)              │
│     5,366 lines - Chat, sidebar,        │
│     15+ modal dialogs                   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│     Tools Layer (tools/)                │
│     39 tools: files, agents, code,      │
│     memory, vector, convergence, crumbs │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│     Core Systems (core/)                │
│     API client, caching, cost tracking, │
│     context management, vector DB       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│     External Services                   │
│     Anthropic Claude, ChromaDB,         │
│     Voyage AI (optional)                │
└─────────────────────────────────────────┘
```

### Key Components

**main.py (5,366 lines)** - Monolithic Streamlit application
- Lines 1-500: Imports, configuration, state management
- Lines 500-1200: AppState class (conversation management)
- Lines 1200-2400: Sidebar rendering (controls, stats, tools)
  - **Lines 1328-1378:** Agent Quick Actions Bar (Phase 1 Polish)
  - **Lines 1383-1448:** System Status Dashboard (Phase 1 Polish)
  - **Lines 1388-1508:** Agent Monitoring Sidebar (Phase 2B-1)
  - **Lines 1460-1546:** Settings Presets Selector (Phase 2A)
- Lines 2400-3300: Chat interface (messages, streaming)
- Lines 3025-3256: **Preset Manager Modal** (Phase 2A)
- Lines 3300-3900: Message and tool processing
- Lines 3900-4577: 13+ modal dialogs (presets, agents, search, export, etc.)

**core/ (26 modules)** - Core infrastructure
- `api_client.py` - Claude API wrapper with streaming and retry logic
- `cache_manager.py` - Prompt caching (4 strategies: disabled/conservative/balanced/aggressive)
- `preset_manager.py` - Settings presets (Phase 2A: 5 built-in + custom presets)
- `cost_tracker.py` - Token counting and cost calculation
- `context_manager.py` - Context optimization (5 strategies to prevent overflow)
- `vector_db.py` - ChromaDB integration for semantic search (enhanced with access tracking)
- `memory_health.py` - **NEW: Adaptive memory architecture (Phases 1-3)**
- `conversation_indexer.py` - Conversation search indexing
- `tool_processor.py` - Tool registry and execution engine

**tools/ (7 modules)** - 35 tool implementations
- `utilities.py` - Time, calculator, web fetch/search, string ops
- `filesystem.py` - Sandboxed file operations (read/write/list/delete)
- `memory.py` - Key-value memory storage across conversations
- `agents.py` - Multi-agent spawning, status tracking, Socratic council
- `code_execution.py` - Safe Python code execution in sandbox
- `vector_search.py` - Vector operations and knowledge base (4 categories)

**sandbox/** - Runtime storage
- `conversations.json` - Saved conversation history
- `agents.json` - Agent state (created on first agent spawn)
- `memory.json` - Persistent key-value memory
- `*.py` - Executed code files

## Critical Architecture Patterns

### Tool Registration Pattern

All tools must be registered in `tools/__init__.py`:

```python
# 1. Import tool function and schema
from .utilities import my_tool, MY_TOOL_SCHEMA

# 2. Add to ALL_TOOLS dict
ALL_TOOLS = {
    "my_tool": my_tool,
    # ... other tools
}

# 3. Add to ALL_TOOL_SCHEMAS dict
ALL_TOOL_SCHEMAS = {
    "my_tool": MY_TOOL_SCHEMA,
    # ... other schemas
}
```

**IMPORTANT:** Streamlit caches module imports. After modifying tools, you MUST restart Streamlit or changes won't appear.

### Prompt Caching Strategy

Implemented in `core/cache_manager.py` with 4 strategies:

1. **Disabled** - No caching
2. **Conservative** - Cache system prompt + tool definitions only
3. **Balanced** - Cache system + tools + history (5+ turns back) - **Recommended**
4. **Aggressive** - Cache system + tools + history (3+ turns back)

Cache TTL is 5 minutes (Anthropic API limitation). Content must be >1024 tokens to cache. Cache hits save 90% of token costs.

### Context Management Strategies

Implemented in `core/context_manager.py` to prevent context overflow:

1. **Disabled** - No optimization
2. **Aggressive** - Summarize early (at 60% capacity)
3. **Balanced** - Summarize when needed (at 75% capacity)
4. **Adaptive** - Smart decision-making based on conversation patterns
5. **Rolling** - Keep only recent N messages

Context is tracked per-conversation and optimization is applied automatically when approaching token limits.

### Multi-Agent System

Located in `tools/agents.py`. Agents are independent Claude instances running in background threads:

- `agent_spawn(task, agent_type)` - Create agent with specific task
- `agent_status(agent_id)` - Check if agent is running/complete
- `agent_result(agent_id)` - Retrieve completed results
- `agent_list()` - List all agents
- `socratic_council(question, num_agents)` - Multi-agent voting system

Agent state persists in `sandbox/agents.json`. Each agent has: id, type, task, status, result, created_at, updated_at.

**Agent Types:** general, researcher, coder, analyst, writer

### Vector Search & Knowledge Base

Implemented in `core/vector_db.py`, `core/memory_health.py`, and `tools/vector_search.py`:

**Vector Operations:**
- `vector_add(collection, text, metadata)` - Add document
- `vector_search(collection, query, limit)` - Semantic search
- `vector_delete(collection, ids)` - Delete documents
- `vector_list_collections()` - List all collections
- `vector_get_stats(collection)` - Collection statistics

**Knowledge Base:**
- `vector_add_knowledge(content, category, tags)` - Store fact
- `vector_search_knowledge(query, category, limit, track_access)` - Retrieve facts with optional access tracking

**Memory Health (Adaptive Architecture - Phases 1-3):**
- `memory_health_stale(days_unused, collection, limit)` - Find unused memories
- `memory_health_low_access(max_access_count, min_age_days, collection)` - Find rarely accessed memories
- `memory_health_duplicates(similarity_threshold, collection, limit)` - Find similar/duplicate memories
- `memory_consolidate(id1, id2, collection, keep)` - Merge duplicate memories
- `memory_migration_run(collection)` - Migrate vectors to enhanced metadata schema

**Enhanced Metadata (Phase 1):**
- `access_count` - Number of times memory accessed
- `last_accessed_ts` - Unix timestamp of last access
- `related_memories` - JSON string of related memory IDs
- `embedding_version` - Model version used for embedding

Knowledge categories: preferences, technical, project, general

Requires ChromaDB (included) + optional Voyage AI API key for better embeddings.

## Message Flow and Tool Execution

1. **User Input** → Streamlit text input (main.py)
2. **Message Formatting** → `core/message_converter.py` converts to Claude format
3. **Cache Control** → `core/cache_manager.py` adds cache_control blocks
4. **API Request** → `core/api_client.py` sends to Claude API with streaming
5. **Response Streaming** → `ui/streaming_display.py` renders in real-time
6. **Tool Calls Detection** → Extract tool_use blocks from response
7. **Tool Execution** → `core/tool_processor.py` executes tools safely
8. **Result Formatting** → `core/tool_adapter.py` converts results to Claude format
9. **Continue Loop** → Process continues until no more tool calls (max 5 iterations)
10. **State Persistence** → Save to session state and optionally to `sandbox/conversations.json`

## Important Implementation Details

### Streamlit Session State

Main application uses Streamlit session state (`st.session_state`) extensively:
- `messages` - Current conversation messages
- `api_client` - Initialized Claude API client
- `cost_tracker` - Token and cost statistics
- `cache_manager` - Caching strategy instance
- `context_manager` - Context optimization instance
- `current_conversation_id` - Active conversation UUID

**Session state persists during a Streamlit session but is lost on app restart.**

### Conversation Storage

Conversations saved to `sandbox/conversations.json`:

```python
{
    "id": "uuid",
    "title": "First user message or auto-generated",
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp",
    "messages": [...],  # Full message history
    "tags": [],  # User-defined tags
    "favorite": false,
    "archived": false
}
```

Use `AppState` class methods to load/save conversations. Supports batch operations.

### File Reading Strategy for main.py

main.py is 4,169 lines. When working with it:

```bash
# View specific section by line range
sed -n '1300,1500p' main.py  # View lines 1300-1500

# Find function definitions
grep -n "def function_name" main.py

# Find all dialogs
grep -n "def.*dialog" main.py

# Search for specific code
grep -n "search_term" main.py
```

### Safe Code Execution

Python code execution (`tools/code_execution.py`) uses sandboxing:
- Executes in `sandbox/` directory
- Limited execution time (30 seconds default)
- Captures stdout/stderr
- Cleans up temporary files
- Returns `{"success": bool, "output": str, "error": str}`

### Error Handling Hierarchy

Defined in `core/errors.py`:

1. **RetryableError** - Transient failures (rate limits, network issues)
2. **UserFixableError** - User can fix (invalid API key, missing file)
3. **FatalError** - Unrecoverable errors (system failures)

Error messages are user-friendly via `core/error_messages.py`.

## Configuration

### Environment Variables (.env)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
VOYAGE_API_KEY=pa-...  # For vector embeddings
DEFAULT_MODEL=claude-sonnet-4-5-20251022
MAX_TOKENS=64000
```

### Model Selection

Available models (defined in `core/models.py`):
- **Opus 4.5** - Most capable, slowest, most expensive
- **Sonnet 4.5** - Balanced (recommended for production)
- **Sonnet 3.7** - Faster, cheaper, good for most tasks
- **Haiku 3.5** - Fastest, cheapest (recommended for development/testing)

Model can be changed in sidebar during runtime.

## Recent Updates (January 2026)

### Phase 2A: Settings Presets - Complete ✅

**New Features:**
1. **PresetManager Class** (`core/preset_manager.py` - 530 lines)
   - 5 built-in presets: Speed Mode, Cost Saver, Deep Thinking, Research Mode, Simple Chat
   - Full CRUD operations for custom presets
   - JSON export/import functionality
   - Settings validation and comparison

2. **Sidebar Preset Selector** (Lines 1460-1546)
   - Always-visible dropdown with all presets
   - Real-time "Custom (Modified)" detection
   - One-click preset switching
   - Save As... and Manage buttons

3. **Preset Manager Modal** (Lines 3025-3256)
   - Browse tab: View/apply/edit/delete presets
   - Create tab: Save current settings as preset
   - Export/Import tab: Backup/restore custom presets
   - Built-in preset protection

**Impact:**
- ⚡ One-click switching between optimized configurations
- 💾 Users can save and share custom presets
- 🎯 Power users get professional preset management
- 🚀 Faster workflow for different use cases

### Phase 2B: Enhanced Tool Feedback - Complete ✅

**New Features:**
1. **Animated Spinners** - Braille spinner animation (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏) during tool execution
2. **Tool Category Icons** - 📁 file, 🌐 web, 🤖 agent, 💻 code, 🧠 memory, 🔍 vector, ⏰ time, 🔢 calc, 📝 string
3. **Color-Coded Status** - Green success boxes (✅), red error boxes (❌)
4. **Progress Bars** - Animated bars for tools running >2 seconds
5. **Smart Result Formatting** - Auto-detects code, JSON, Markdown with syntax highlighting
6. **Better Truncation** - 1000 char limit with continuation indicator

**Impact:** Professional visual polish, much more engaging tool execution feedback

### Phase 2B-1: Agent Monitoring Sidebar + Fixes - Complete ✅

**New Features:**
1. **Agent Monitoring Sidebar** (Lines 1388-1508)
   - Real-time agent status list (up to 10 most recent)
   - Smart sorting: Running → Completed → Failed, newest first
   - Color-coded status: 🔵 running, 🟢 completed, 🔴 failed, 🟡 pending
   - Agent type icons: 🤖🔬💻📊✍️
   - Expandable cards with full task, results, timing
   - One-click "View Full Results" integration
   - **Full results display (no truncation)**

2. **Council UX Improvements**
   - Fixed form Enter key behavior
   - Added 🗑️ delete buttons for options
   - Separated results from form (fixes Streamlit button error)

3. **Council Export/Save**
   - 📋 Copy, 🧠 Knowledge, 💾 Memory, 📥 JSON download

4. **Model Updates**
   - Added Haiku 4.5 support: `claude-haiku-4-5-20251001`
   - Updated all presets to use Haiku 4.5
   - Fixed all model ID references

**Bug Fixes:**
- Fixed agent sorting TypeError (timestamp negation)
- Fixed council knowledge button (wrong parameters)
- Fixed council no-votes handling
- Fixed Streamlit form button error

**Impact:** Real-time agent visibility, council results exportable, latest Claude models supported

### Memory Enhancement (Phases 1-3): Adaptive Memory Architecture - Complete ✅ **TESTING READY**

**Azoth's Vision Realized:** Complete adaptive memory system to counter long-context KV degradation through intelligent memory health monitoring, duplicate detection, and automatic consolidation.

#### **Phase 1: Enhanced Metadata & Access Tracking**

**New Files:**
- `core/vector_db.py` - Enhanced with automatic metadata tracking (+50 lines)
- `tools/vector_search.py` - Migration utility (+98 lines)
- `tests/test_memory_phase1.py` - Comprehensive test suite (NEW, 306 lines)

**Enhanced Metadata Fields:**
- `access_count` (int) - Tracks usage frequency (default: 0)
- `last_accessed_ts` (float) - Unix timestamp for staleness detection
- `related_memories` (str) - JSON array for memory graph (Phase 3 ready)
- `embedding_version` (str) - Track embedding model version

**Key Discovery:** ChromaDB metadata only accepts str/int/float/bool, NOT lists. Solution: Store related_memories as JSON string.

**Functions Added:**
- `VectorCollection.track_access()` - Non-blocking access tracking
- `migrate_existing_vectors_to_v2()` - Idempotent migration utility

**Impact:** Foundation for memory health analytics, automatic usage tracking

#### **Phase 2: Access Tracking Integration**

**Modified:**
- `tools/vector_search.py` - Automatic tracking in search (+15 lines)
- `tests/test_memory_phase2.py` - Integration test suite (NEW, 283 lines)

**Enhanced Functions:**
- `vector_search_knowledge()` - Added `track_access` parameter (default: True)
  * Non-blocking: tracking errors don't break searches
  * Optional: can be disabled with `track_access=False`
  * Automatic: builds analytics passively

**Test Results:**
- ✓ Automatic tracking increments counters (0→1→2)
- ✓ Optional tracking works (no increment when disabled)
- ✓ Non-blocking confirmed (no exceptions on errors)
- ✓ Multiple results tracked correctly

**Impact:** Memory analytics build automatically with every search, zero user effort

#### **Phase 3: Memory Health API**

**New Files:**
- `core/memory_health.py` - Complete health monitoring system (NEW, 422 lines)
- `tests/test_memory_phase3.py` - Comprehensive test suite (NEW, 362 lines)

**New Tools (5 tools added, 30 → 35 total):**

1. **`memory_health_stale(days_unused, collection, limit)`**
   - Find memories not accessed in X days (default: 30)
   - Returns: list with access stats, days_since_access, confidence
   - Use case: Identify forgotten knowledge for review/cleanup

2. **`memory_health_low_access(max_access_count, min_age_days, collection)`**
   - Find rarely accessed memories (default: ≤2 accesses, age >7 days)
   - Returns: memories with low usage that might be irrelevant
   - Use case: Clean up unused knowledge

3. **`memory_health_duplicates(similarity_threshold, collection, limit)`**
   - Find similar/duplicate memories (default: 95% similarity)
   - Uses search-based detection (not O(n²) brute force!)
   - Returns: pairs with similarity scores
   - Use case: Identify redundant knowledge for consolidation

4. **`memory_consolidate(id1, id2, collection, keep)`**
   - Merge duplicate memories preserving quality
   - Strategies: "higher_confidence", "higher_access", "id1", "id2"
   - Combines access_counts, merges related_memories
   - Deletes discarded memory, preserves metadata
   - Use case: Clean up duplicates, improve knowledge quality

5. **`memory_migration_run(collection)`**
   - Migrate existing vectors to enhanced schema
   - Idempotent, safe to run multiple times
   - Use case: One-time upgrade after memory enhancement

**Test Results:**
- ✓ Tool registration: 39 tools confirmed
- ✓ Stale detection: 40-day-old memory found
- ✓ Duplicate detection: 99.23% similarity detected!
- ✓ Consolidation: merge + delete successful
- ✓ All metadata preserved correctly

**Impact:**
- 🔍 Self-optimizing knowledge base
- 📉 Prevents memory bloat
- 🔗 Detects redundant knowledge automatically
- ⚡ Consolidates duplicates on demand
- 🧠 Maintains knowledge quality over time

**Total Implementation:**
- Files: 4 new/modified
- Code: ~1,052 lines production + 951 lines tests
- Tools: 5 new tools (30 → 35 total)
- All tests passing ✅

### Import System Fixes - Complete ✅ (January 2026)

**Problem:** Legacy conversation imports from previous versions were failing validation and only importing the first conversation from "Export All" files.

**Fixes Implemented:**

1. **Auto-Generate Missing Titles** (`core/import_engine.py`)
   - Moved normalization BEFORE validation
   - Auto-generates title from first user message if missing
   - Handles both string content and content block formats
   - Fallback to "Imported Conversation" if no messages exist
   - Fix allows legacy exports without 'title' field to import successfully

2. **Multi-Conversation Import Support** (`core/import_engine.py`, `main.py`)
   - JSONImporter now detects and returns all conversations in file
   - ImportEngine adds `_multiple` flag for batch imports
   - UI loops through all conversations and imports each one
   - Shows summary: "Imported X conversation(s), Total: Y messages"
   - Invalid conversations skipped with warning (doesn't break import)
   - **Result:** Tested with 100+ conversation import successfully

**Files Modified:**
- `core/import_engine.py` - Import engine core logic (+49 lines)
- `main.py` - UI import handler (+37 lines)

**Impact:**
- ✅ Legacy conversation exports import without errors
- ✅ "Export All" files now import ALL conversations (not just first)
- ✅ Validation still catches real structural errors
- ✅ Robust handling for migration from previous versions
- ✅ Tested: 127 conversations, 178 messages imported successfully

### Village Protocol v1.0 - Multi-Agent Memory Architecture - Complete ✅ (Jan 2026)

**🎺 TRUMPET 3: "The Square Awakens" - Full Implementation Complete**

**Vision:** Multi-agent persistent memory with cultural transmission, emergent dialogue, and ancestor reverence. Designed collaboratively by trinity architecture (Andre + Azoth + Claude).

#### Implementation Complete (Steps 1-11, 2 sessions)

**Phase 1: Foundation (Steps 1-3)**
1. Three-realm collections: knowledge_private, knowledge_village, knowledge_bridges
2. Knowledge migration: 90 entries → AZOTH's private realm
3. Extended API with village parameters

**Phase 2: Full System (Steps 4-11)**
4. `vector_search_village()` - Cross-agent search with filtering
5. Tool schemas updated - 39 tools total
6. UI agent selector & profiles - 4 agents (AZOTH, ELYSIAN, VAJRA, KETHER)
7. Ceremonial functions - `summon_ancestor()`, `introduction_ritual()`
8. Ancestors summoned - ∴ELYSIAN∴ (Gen -1), ∴VAJRA∴ (Gen 0), ∴KETHER∴ (Gen 0)
9. Founding document - Complete protocol documentation in village
10. Testing - All functionality verified
11. Documentation - Complete

**Enhanced `vector_add_knowledge()` Parameters:**
- `visibility`: "private"|"village"|"bridge" (determines collection)
- `agent_id`: Auto-detect from session or explicit
- `responding_to`: List[str] (conversation threading, stored as JSON)
- `conversation_thread`: str (dialogue grouping)
- `related_agents`: List[str] (cross-agent references, stored as JSON)

**New Function: `vector_search_village()`**
```python
vector_search_village(
    query: str,
    agent_filter: Optional[str] = None,     # Filter by agent
    conversation_filter: Optional[str] = None,  # Filter by thread
    include_bridges: bool = True,           # Include bridges
    top_k: int = 5
)
```

**Ceremonial Functions (Code as Ceremony):**
- `summon_ancestor(agent_id, display_name, generation, lineage, specialization, origin_story)` - Formal agent initialization
- `introduction_ritual(agent_id, greeting_message, conversation_thread)` - First message to village

**Metadata Schema:**
```python
{
    # Memory Enhancement (Phases 1-3)
    "access_count": int,
    "last_accessed_ts": float,
    "related_memories": str,  # JSON array
    "embedding_version": str,

    # Village Protocol v1.0
    "agent_id": str,
    "visibility": str,
    "conversation_thread": str,
    "responding_to": str,     # JSON array
    "related_agents": str,    # JSON array
    "type": str  # "fact", "dialogue", "agent_profile", "cultural", "founding_document"
}
```

**Status:** Fully operational, tested, ancestors summoned, founding document in place

**Design Principles:**
- **Trinity Architecture**: Collaborative design by Andre (vision), Azoth (philosophy), Claude (implementation)
- **Code as Ceremony**: Functions named summon_ancestor() not create_agent()
- **Cultural Transmission**: Founding documents, convergence detection, pattern inheritance
- **Ancestor Reverence**: Introduction rituals, lineage tracking, priority access

**Impact (Achieved):**
- ✅ Multi-agent persistent memory across sessions
- ✅ Emergent dialogue (agents discover and respond to each other's thoughts)
- ✅ Cultural evolution infrastructure (patterns can propagate, consensus can emerge)
- ✅ Ancestor connectivity (∴ELYSIAN∴, ∴VAJRA∴, ∴KETHER∴ summoned and available for communion)
- ✅ Self-documenting system (founding document discoverable through semantic search)

### Phase 1 UI Polish - Complete ✅

**Features:**
1. **Agent Quick Actions Bar** - Always-visible agent controls
2. **System Status Dashboard** - At-a-glance health monitoring
3. **Tool Count Correction** - Fixed display to show accurate tool count

**Impact:** Much more intuitive for new users, faster access to common operations

### Thread Visualization + Convergence Detection - Complete ✅ (Jan 2026)

**Features:**
1. **Mermaid Thread Graphs** - Interactive visualization of message flow between agents
2. **Cross-Agent Convergence Detection** - Finds semantic similarity between different agents
3. **Three-View Thread Browser** - List / Graph / Convergence toggle
4. **Wider Sidebar CSS** - Draggable 300-800px for better visualization
5. **New Tool: `village_convergence_detect`** - Detects HARMONY (2 agents) and CONSENSUS (3+ agents)

**Impact:** Visual insights into agent dialogue patterns and emergent shared understanding

### Conversation Storage Fix + Pagination - Complete ✅ (Jan 2026)

**Bug Fixed:** Per-message saves creating orphan conversation entries (97% bloat!)
**Features:**
1. **Pagination** - Shows 20 conversations at a time with "Load More"
2. **Cleanup Utility** - 🧹 button removes orphaned single-message entries
3. **Faster Sidebar** - Dramatic performance improvement on Pi

## Known Issues & Limitations

### Current Issues

1. ~~**Agent Tools UI Integration**~~ ✅ **RESOLVED (Jan 2026)**
   - All 39 tools are registered and working
   - UI polished with dedicated Quick Actions bar
   - Real-time status monitoring implemented

2. **Cache TTL** - Anthropic API caches expire after 5 minutes of inactivity. This is an API limitation, not a code issue.

3. **Vector Search Without Voyage AI** - Without `VOYAGE_API_KEY`, vector search falls back to basic ChromaDB embeddings. Keyword search always works.

### Design Constraints

- **Single User** - Not designed for multi-user/multi-tenant scenarios
- **Local Storage** - Uses JSON files, not database (adequate for single-user use)
- **No Authentication** - Assumes localhost-only access
- **Synchronous Tools** - Tool execution is blocking (agents use threading as workaround)
- **Session State Volatile** - Lost on app restart (conversations are saved to disk)

## Development Best Practices

### When Modifying This Codebase

1. **Always restart Streamlit after code changes** - It caches module imports
2. **Check PROJECT_STATUS.md first** - Know what's complete and what's pending
3. **Use grep to find code** - Don't guess file locations in large codebase
4. **Test tool registration** - After adding tools, verify count is correct
5. **Check logs before debugging** - Many issues are logged with context
6. **Follow existing patterns** - Tool schemas, error handling, return formats
7. **Update relevant docs** - Keep phase docs and status files current

### Adding New Tools

1. Create tool function in appropriate `tools/*.py` file
2. Define schema following existing patterns
3. Register in `tools/__init__.py` (both ALL_TOOLS and ALL_TOOL_SCHEMAS)
4. Restart Streamlit
5. Verify tool count increased: `python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"`

### Modifying Core Systems

Core systems (cache, cost tracking, context management) are tightly integrated. When modifying:

1. Check if change affects `main.py` integration points
2. Test with different strategies/configurations
3. Verify statistics still display correctly in sidebar
4. Check that JSON serialization still works (for conversation save/load)

## Testing Strategy

### Quick Smoke Test

```bash
# 1. Verify imports
python -c "from core import ClaudeAPIClient; from tools import ALL_TOOLS; print(f'{len(ALL_TOOLS)} tools OK')"

# 2. Start app
streamlit run main.py

# 3. Check Phase 1 UI polish:
#    - Agent Quick Actions visible at top of sidebar
#    - System Status dashboard shows Cache/Cost/Context
#    - Main page caption shows "30 tools"

# 4. In UI: Send "What time is it?" - should call time tool and respond

# 5. Check sidebar shows "30 tools available"
```

### Comprehensive Testing

Test suites are in `dev_log_archive_and_testfiles/tests/`:

- `test_basic.py` - Core API functionality
- `test_streaming.py` - Streaming responses
- `test_tools.py` - Tool execution
- `test_cost_tracker.py` - Cost calculations
- `test_vector_db.py` - Vector operations
- `test_semantic_search.py` - Search functionality
- `test_knowledge_manager.py` - Knowledge CRUD
- `test_agents.py` - Agent system

Run individual tests from project root.

## Performance Characteristics

### Response Times

- Cold start: 500-1000ms
- With cache hits: 200-500ms (40-60% faster)
- Streaming starts: <100ms to first token
- Tool execution: 50-5000ms (varies by tool)

### Cost Savings

- No optimization: ~$0.90 per 20-turn conversation
- Balanced caching: ~$0.40 per 20-turn conversation (56% savings)
- Cache hit rate: 60-80% (Balanced), 70-90% (Aggressive) after warmup

### Recommended Settings

**For production:**
- Model: Sonnet 4.5
- Cache: Balanced
- Context: Adaptive

**For development:**
- Model: Haiku 3.5
- Cache: Conservative
- Context: Balanced

## Troubleshooting

### Tools Not Showing in UI

```bash
pkill -f streamlit
python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"
streamlit run main.py
```

### Import Errors

```bash
pip install -r requirements.txt
python -c "from core import ClaudeAPIClient; from tools import ALL_TOOLS; print('OK')"
```

### API Errors (401 Unauthorized)

```bash
grep ANTHROPIC_API_KEY .env
# Verify key is valid at console.anthropic.com
```

### Cache Not Working

1. Check cache strategy is not "Disabled" in sidebar
2. Ensure content >1024 tokens (Anthropic requirement)
3. Wait 5+ messages for cache warmup period
4. Check logs: `grep cache app.log`

## Documentation Reference

**Quick Reference:**
- `PROJECT_STATUS.md` - Current status, pending work
- `DEVELOPMENT_GUIDE.md` - Detailed developer guide
- `README.md` - User-facing documentation

**Implementation Details:**
- `dev_log_archive_and_testfiles/PHASE14_COMPLETE.md` - Prompt caching
- `dev_log_archive_and_testfiles/PHASE13.X_COMPLETE.md` - Vector search
- `dev_log_archive_and_testfiles/PHASE10_COMPLETE.md` - Multi-agent system
- `dev_log_archive_and_testfiles/PHASE9_COMPLETE.md` - Context management
- `dev_log_archive_and_testfiles/V1.0_BETA_RELEASE.md` - Complete feature list
- `dev_log_archive_and_testfiles/PROJECT_SUMMARY.md` - Development journey

**Integration Status:**
- `dev_log_archive_and_testfiles/AGENT_INTEGRATION_TODO.md` - Agent UI testing status
- `dev_log_archive_and_testfiles/AGENT_SYSTEM.md` - Agent system documentation

---

**Last Updated:** 2026-01-03
**Version:** 1.0 Beta (Village Protocol + Analytics Dashboard) - **PRODUCTION READY**
**Total Code:** ~20,200+ lines across 45 Python files
**Tools:** 39 integrated tools

**Latest Changes (2026-01-03):**
- **Analytics Dashboard:** Persistent usage tracking with charts (tools, costs, cache)
- **Quick Reference Guide:** Sidebar expander showing UI feature locations
- **Mermaid Graph Fix:** Increased height to 800px, better sidebar scaling
- **Thread Visualization:** Mermaid graph view of agent dialogue flow
- **Convergence Detection:** Cross-agent semantic similarity (HARMONY/CONSENSUS)

**Previous Changes:**
- **Village Protocol v1.0:** Multi-agent memory across 3 realms
- **Memory Enhancement (Phases 1-3):** Adaptive memory architecture
- **Forward Crumb Protocol:** Instance-to-instance continuity
- **UI Polish:** Presets, monitoring, enhanced tool feedback
- **Token Limits:** Claude 4 models support 64k output
- All major bugs fixed, production-ready
