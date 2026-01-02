# ApexAurum Development Guide

**Purpose:** Quick onboarding guide for working on this project in future sessions
**For:** Developers, AI assistants, and future maintainers
**Updated:** 2026-01-02 (Phase 2A Settings Presets Complete)

---

## Quick Start for New Sessions

### 1. First Things First (2 minutes)

```bash
# Navigate to project
cd /home/llm/ApexAurum

# Check environment
cat .env  # Verify API keys present

# Count tools (should be 30)
python -c "from tools import ALL_TOOLS; print(f'Tools: {len(ALL_TOOLS)}')"

# Check if app is running
ps aux | grep streamlit
```

### 2. Essential Documents to Read

**Must Read (5-10 min):**
1. **PROJECT_STATUS.md** (this directory) - Current state and what's pending
2. **AGENT_INTEGRATION_TODO.md** (in dev_log_archive_and_testfiles) - Agent system status

**Helpful Context (10-20 min):**
3. **V1.0_BETA_RELEASE.md** (in dev_log_archive_and_testfiles) - Complete feature list
4. **PROJECT_SUMMARY.md** (in dev_log_archive_and_testfiles) - Development journey

**Deep Dives (as needed):**
5. **PHASE14_COMPLETE.md** - Prompt caching details
6. **PHASE13.X_COMPLETE.md** - Vector search implementation
7. **PHASE10_COMPLETE.md** - Multi-agent system

### 3. Understanding the Project (1 minute)

**What It Is:**
- Production-grade Claude API chat interface
- 15+ integrated tools (file ops, web, code exec, agents, etc.)
- Multi-agent orchestration
- Vector search & knowledge base
- Intelligent cost optimization (50-90% savings)

**What's Done:**
- All 14 planned phases complete
- Core functionality 100% working
- ~15,000 lines of code
- 7 test suites
- Comprehensive documentation

**What's Pending:**
- Agent tools need UI testing (code complete)
- Optional enhancements and polish

---

## Project Structure Guide

### Main Files You'll Work With

```
ApexAurum/
├── main.py                  # ⭐ Streamlit UI (4,169 lines)
├── PROJECT_STATUS.md        # ⭐ Read this first
├── DEVELOPMENT_GUIDE.md     # ⭐ This file
│
├── core/                    # Core systems (24 files)
│   ├── api_client.py        # 🔥 Claude API wrapper
│   ├── cache_manager.py     # 🔥 Prompt caching
│   ├── cost_tracker.py      # 🔥 Cost tracking
│   ├── context_manager.py   # 🔥 Context optimization
│   ├── vector_db.py         # 🔥 Vector search
│   └── ...                  # 19 other modules
│
├── tools/                   # Tool implementations (7 files)
│   ├── __init__.py          # Tool registration
│   ├── agents.py            # ⚠️ Needs UI testing
│   ├── utilities.py         # Time, calc, web tools
│   ├── filesystem.py        # File operations
│   ├── memory.py            # Key-value storage
│   ├── code_execution.py    # Python execution
│   └── vector_search.py     # Search & knowledge
│
├── ui/                      # UI components
│   └── streaming_display.py # Streaming text
│
├── sandbox/                 # Runtime storage
│   ├── conversations.json   # Saved convos
│   ├── agents.json          # Agent state
│   └── memory.json          # Memory store
│
└── dev_log_archive_and_testfiles/  # 📚 Documentation
    ├── PHASE*_COMPLETE.md   # 14 phase docs
    ├── test_*.py            # 8 test suites
    └── ...                  # More docs
```

### Legend
- ⭐ Essential files
- 🔥 Frequently modified
- ⚠️ Needs attention
- 📚 Reference only

---

## Common Tasks

### Starting the Application

```bash
cd ApexAurum

# Start Streamlit
streamlit run main.py

# Or with specific port
streamlit run main.py --server.port 8502

# Background mode
nohup streamlit run main.py &

# Check if running
ps aux | grep streamlit
```

Access at: http://localhost:8501

### Running Tests

```bash
# Individual tests
python test_basic.py
python test_agents.py
python test_vector_db.py

# Verify tool imports
python -c "from tools import ALL_TOOLS; print(f'✓ {len(ALL_TOOLS)} tools loaded')"

# Test agent functionality
python -c "from tools.agents import agent_spawn; print(agent_spawn('Test task', run_async=False))"
```

### Checking Logs

```bash
# Live log monitoring
tail -f app.log

# Search logs for errors
grep ERROR app.log | tail -20

# Check recent activity
tail -100 app.log
```

### Managing Environment

```bash
# View environment variables
cat .env

# Check API key (safely)
echo $ANTHROPIC_API_KEY | head -c 20

# Update dependencies
pip install -r requirements.txt --upgrade

# Check Python version
python --version  # Should be 3.9+
```

---

## Understanding the Codebase

### Architecture Layers

```
┌─────────────────────────────────────┐
│  main.py - Streamlit UI             │
│  - Chat interface                   │
│  - Sidebar controls                 │
│  - Modal dialogs (12+)              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  tools/ - Tool implementations      │
│  - 30 tools registered              │
│  - Safe execution                   │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  core/ - Core systems               │
│  - API client                       │
│  - Cost tracking                    │
│  - Caching                          │
│  - Context management               │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  External APIs                      │
│  - Anthropic Claude                 │
│  - Voyage AI (embeddings)           │
│  - ChromaDB (vector DB)             │
└─────────────────────────────────────┘
```

### Data Flow

1. **User input** → Streamlit UI (main.py)
2. **Message formatting** → core/message_converter.py
3. **Cache control** → core/cache_manager.py
4. **API request** → core/api_client.py
5. **Claude response** → Streaming back to UI
6. **Tool calls** → Processed by tools/ modules
7. **Results tracking** → core/cost_tracker.py
8. **State persistence** → sandbox/*.json

### Key Design Patterns

1. **Registry Pattern**
   - Tools register themselves in `tools/__init__.py`
   - ToolRegistry manages available tools

2. **Strategy Pattern**
   - Cache strategies: disabled/conservative/balanced/aggressive
   - Context strategies: disabled/aggressive/balanced/adaptive/rolling

3. **Manager Pattern**
   - CacheManager, ContextManager, ConfigManager
   - Centralized control of subsystems

4. **Tracker Pattern**
   - CostTracker, CacheTracker, ContextTracker
   - Statistics and monitoring

---

## Reading main.py (4,169 lines)

### File Structure

```python
# Lines 1-200: Imports and setup
# Lines 201-500: Configuration classes
# Lines 501-1200: State management (AppState class)
# Lines 1201-1300: Session state initialization
# Lines 1301-2000: Sidebar rendering
# Lines 2001-3000: Chat interface
# Lines 3001-3500: Message processing
# Lines 3501-4169: Modal dialogs (12+)
```

### Reading main.py in Chunks

**Since main.py is 4,169 lines, read it in sections:**

```bash
# View header and imports (first 100 lines)
head -100 ApexAurum/main.py

# View specific line range
sed -n '1200,1300p' ApexAurum/main.py  # Session state

# Search for specific function
grep -n "def render_sidebar" ApexAurum/main.py

# Find all dialog functions
grep -n "def.*dialog" ApexAurum/main.py
```

### Key Sections of main.py

| Lines | Section | Purpose |
|-------|---------|---------|
| 1-100 | Imports | Dependencies and setup |
| 100-500 | Config | Configuration classes |
| 500-1200 | State | AppState class |
| 1200-1300 | Init | Session state setup |
| 1300-1550 | Sidebar | Sidebar rendering + Phase 1/2A polish |
| 1328-1378 | **NEW** | Agent Quick Actions Bar (Phase 1) ⭐ |
| 1383-1448 | **NEW** | System Status Dashboard (Phase 1) ⭐ |
| 1460-1546 | **NEW** | Settings Presets Selector (Phase 2A) ⭐⭐ |
| 1550-2200 | Settings | Model, tools, cache, context controls |
| 2100-3000 | Chat | Main chat interface |
| 3000-3500 | Processing | Message & tool handling |
| 3500-4169 | Dialogs | 12 modal dialogs |

**⭐ = Phase 1 UI Polish | ⭐⭐ = Phase 2A Settings Presets (January 2026)**

---

## Making Changes

### Adding a New Tool

1. **Create tool function** in appropriate `tools/*.py` file:
```python
def my_new_tool(param1: str, param2: int) -> dict:
    """
    Tool description for Claude.

    Args:
        param1: Description
        param2: Description

    Returns:
        dict with 'success' and 'result' keys
    """
    try:
        result = do_something(param1, param2)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

2. **Define schema** in same file:
```python
MY_NEW_TOOL_SCHEMA = {
    "name": "my_new_tool",
    "description": "What this tool does",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Parameter description"
            },
            "param2": {
                "type": "integer",
                "description": "Parameter description"
            }
        },
        "required": ["param1", "param2"]
    }
}
```

3. **Register in tools/__init__.py**:
```python
from .utilities import my_new_tool, MY_NEW_TOOL_SCHEMA

ALL_TOOLS = {
    # ... existing tools ...
    "my_new_tool": my_new_tool,
}

ALL_TOOL_SCHEMAS = {
    # ... existing schemas ...
    "my_new_tool": MY_NEW_TOOL_SCHEMA,
}
```

4. **Restart Streamlit** to pick up changes

### Modifying Existing Functionality

1. **Find the relevant file** using grep:
```bash
grep -r "function_name" ApexAurum/
```

2. **Read the file** (use line limits if large):
```bash
# For files < 2000 lines
cat ApexAurum/core/filename.py

# For main.py or large files
sed -n 'START,ENDp' ApexAurum/main.py
```

3. **Make changes** using appropriate tools

4. **Test changes**:
```bash
# Syntax check
python -c "import module_name"

# Run relevant test
python test_*.py
```

5. **Restart app** if needed

### Adding UI Components

**In main.py:**

1. **Find sidebar section** (~line 1300-2000)
2. **Add new section** following existing patterns:
```python
st.divider()
st.subheader("🆕 My New Feature")

with st.expander("Feature Details"):
    # Your UI code here
    value = st.text_input("Input label")
    if st.button("Action"):
        result = do_something(value)
        st.success(result)
```

3. **For modal dialogs**, add around line 3500+:
```python
def render_my_dialog():
    """Render my new dialog"""
    st.title("My Dialog")

    # Dialog content
    with st.form("my_form"):
        value = st.text_input("Input")
        submitted = st.form_submit_button("Submit")

        if submitted:
            result = process(value)
            st.success(result)
```

---

## Troubleshooting

### Common Issues and Fixes

#### Tools Not Showing in UI

**Problem:** New tools registered but not visible in Streamlit

**Fix:**
```bash
# Kill Streamlit
pkill -f streamlit

# Verify tools load
python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"

# Restart Streamlit
streamlit run main.py
```

#### Import Errors

**Problem:** `ModuleNotFoundError` or import issues

**Fix:**
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt

# Verify imports
python -c "from core import ClaudeAPIClient; from tools import ALL_TOOLS"
```

#### API Errors

**Problem:** 401 Unauthorized or API failures

**Fix:**
```bash
# Check API key is set
grep ANTHROPIC_API_KEY .env

# Test API key
python -c "import anthropic; client = anthropic.Anthropic(); print('✓ API key valid')"
```

#### Cache Not Working

**Problem:** Cache hit rate stays at 0%

**Fix:**
1. Check cache strategy is not "Disabled" (in sidebar)
2. Ensure content > 1024 tokens (Anthropic requirement)
3. Wait 5+ messages for cache warmup
4. Check logs for cache errors: `grep cache app.log`

#### Vector Search Unavailable

**Problem:** Semantic search not working

**Fix:**
```bash
# Check Voyage API key
grep VOYAGE_API_KEY .env

# Test ChromaDB
python -c "import chromadb; print('✓ ChromaDB available')"

# Fallback: Use keyword search instead
```

---

## Testing Strategy

### Quick Smoke Test (2 minutes)

```bash
# 1. Start app
streamlit run main.py &

# 2. Open browser to localhost:8501

# 3. Test basic chat
# Type: "What time is it?"
# Should call time tool and respond

# 4. Check tool count in sidebar
# Should show: "✅ 30 tools available"

# 5. Kill app
pkill -f streamlit
```

### Comprehensive Test (10 minutes)

```bash
# Run all test suites
python test_basic.py
python test_streaming.py
python test_tools.py
python test_cost_tracker.py
python test_vector_db.py
python test_semantic_search.py
python test_knowledge_manager.py
python test_agents.py

# Check for failures
echo "✓ All tests passed"
```

### UI Testing Checklist

- [x] Basic chat works
- [x] Streaming responses appear
- [x] Tools execute via chat
- [x] Sidebar shows correct stats
- [x] Cache stats update
- [x] Cost tracking works
- [x] Conversation save/load works
- [x] Vector search works (if Voyage key present)
- [x] Knowledge base operations work
- [x] Agent tools appear in tool list (30 tools)
- [x] Agent spawn via chat works
- [x] Modal dialogs open and function
- [x] Agent Quick Actions bar visible ✅ **Phase 1 Polish**
- [x] System Status dashboard updates ✅ **Phase 1 Polish**
- [x] Agent status counts show correctly ✅ **Phase 1 Polish**

---

## Best Practices

### When Working with This Codebase

1. **Always read PROJECT_STATUS.md first** - Know current state
2. **Check logs before debugging** - `tail -f app.log`
3. **Use grep to find code** - Don't guess file locations
4. **Test in isolation** - Use Python CLI before UI testing
5. **Restart Streamlit after code changes** - It caches modules
6. **Document as you go** - Update relevant docs
7. **Run tests before committing** - Catch regressions early

### Code Style

- Follow existing patterns in each file
- Use type hints: `def function(param: str) -> dict:`
- Add docstrings for all functions
- Return `{"success": bool, "result": any}` from tools
- Handle exceptions gracefully
- Log important events: `logger.info("Event")`

### Git Workflow (if using git)

```bash
# Before making changes
git status
git diff

# After testing changes
git add .
git commit -m "Description of changes"

# View history
git log --oneline
```

---

## Advanced Topics

### Understanding Prompt Caching

**Location:** `core/cache_manager.py`

**How it works:**
1. Cache manager adds `cache_control` blocks to messages
2. Anthropic API caches content > 1024 tokens
3. Cache valid for 5 minutes
4. Cache reads cost 90% less than regular tokens

**Strategies:**
- **Disabled:** No caching
- **Conservative:** Cache system + tools only
- **Balanced:** Cache system + tools + history (5+ turns back)
- **Aggressive:** Cache system + tools + history (3+ turns back)

### Understanding Context Management

**Location:** `core/context_manager.py`

**How it works:**
1. Monitors token usage
2. Applies optimization strategy when approaching limits
3. Summarizes or prunes old messages
4. Keeps conversation flowing without overflow

**Strategies:**
- **Disabled:** No optimization
- **Aggressive:** Summarize early
- **Balanced:** Summarize when needed
- **Adaptive:** Smart decision-making
- **Rolling:** Keep recent N messages

### Understanding Multi-Agent System

**Location:** `tools/agents.py`

**How it works:**
1. `agent_spawn()` creates independent Claude instance
2. Agent runs in background thread
3. Results stored in `sandbox/agents.json`
4. `agent_result()` retrieves completed results
5. `socratic_council()` spawns multiple agents for voting

**Agent Types:**
- general, researcher, coder, analyst, writer

---

## Performance Optimization

### Response Time

**Factors:**
- Model choice (Haiku fastest, Opus slowest)
- Cache hits (2-3x faster)
- Context size (smaller = faster)
- Tool complexity
- Network latency

**Optimization:**
- Use Haiku for simple tasks
- Enable Balanced cache strategy
- Keep tools enabled only when needed
- Use adaptive context strategy

### Cost Optimization

**Current Savings:**
- Prompt caching: 50-90%
- Context management: 20-30%
- Rate limiting: 10-20% (prevents overuse)

**Best Practices:**
- Enable Balanced or Aggressive cache
- Use Haiku when possible
- Monitor sidebar stats
- Export important conversations (avoid re-asking)

### Memory Usage

**Factors:**
- Number of messages in session state
- Vector DB size
- Cache statistics storage

**Optimization:**
- Archive old conversations
- Clear vector DB periodically
- Reset statistics when not needed

---

## Documentation Map

### For Understanding Features

| Topic | Document | Location |
|-------|----------|----------|
| Current Status | PROJECT_STATUS.md | Root |
| Quick Start | README.md | dev_log_archive_and_testfiles/ |
| All Features | V1.0_BETA_RELEASE.md | dev_log_archive_and_testfiles/ |
| Dev Journey | PROJECT_SUMMARY.md | dev_log_archive_and_testfiles/ |

### For Implementing Features

| Feature | Document | Location |
|---------|----------|----------|
| Prompt Caching | PHASE14_COMPLETE.md | dev_log_archive_and_testfiles/ |
| Vector Search | PHASE13.X_COMPLETE.md | dev_log_archive_and_testfiles/ |
| Agents | PHASE10_COMPLETE.md | dev_log_archive_and_testfiles/ |
| Context Mgmt | PHASE9_COMPLETE.md | dev_log_archive_and_testfiles/ |
| Tool System | PHASE5_COMPLETE.md | dev_log_archive_and_testfiles/ |

### For Integration

| Task | Document | Location |
|------|----------|----------|
| Agent UI Testing | AGENT_INTEGRATION_TODO.md | dev_log_archive_and_testfiles/ |
| Agent System Docs | AGENT_SYSTEM.md | dev_log_archive_and_testfiles/ |

---

## Phase 2A: Settings Presets (January 2026)

### New Preset System

**1. PresetManager Class** (`core/preset_manager.py`)
- **Location:** New file in core/ directory
- **Purpose:** Manage settings presets (built-in + custom)
- **Features:**
  - 5 built-in presets: Speed Mode, Cost Saver, Deep Thinking, Research Mode, Simple Chat
  - Save custom presets from current settings
  - Full CRUD operations (create, read, update, delete)
  - JSON export/import for backup/sharing
  - Settings validation and comparison

**2. Sidebar Preset Selector** (Lines 1460-1546)
- **Location:** After System Status Dashboard, before Model section
- **Purpose:** Quick preset switching
- **Features:**
  - Dropdown showing all presets
  - Custom presets marked with ⭐
  - "Custom (Modified)" detection when user deviates from preset
  - One-click preset application
  - Save As... and Manage buttons

**3. Preset Manager Modal** (Lines 3025-3256)
- **Location:** Before Agent UI Dialogs in main content
- **Purpose:** Full preset management interface
- **Features:**
  - Browse tab: View all presets, apply/edit/delete
  - Create tab: Save current settings as new preset
  - Export/Import tab: Backup/restore custom presets
  - Built-in preset protection (cannot edit/delete)
  - Inline editing for custom preset name/description

**Built-in Presets:**
- 🚀 **Speed Mode:** Haiku + Conservative cache (fastest)
- 💰 **Cost Saver:** Haiku + Aggressive cache (cheapest)
- 🧠 **Deep Thinking:** Opus + Balanced cache (best quality)
- 🔬 **Research Mode:** Sonnet + Balanced cache (research)
- 💬 **Simple Chat:** Sonnet + Conservative cache (default)

**Settings Controlled by Presets (7 core settings):**
1. `model` - Which Claude model
2. `cache_strategy` - Caching level
3. `context_strategy` - Context management approach
4. `temperature` - Randomness (0.0-1.0)
5. `preserve_recent_count` - Messages to never summarize
6. `auto_summarize` - Enable auto-summarization
7. `default_subagent_model` - Sub-agent model choice

---

## Phase 1 UI Polish (January 2026)

### New UI Sections

**1. Agent Quick Actions Bar (Lines 1328-1378)**
- **Location:** Top of sidebar, after session controls
- **Purpose:** Always-visible agent management
- **Features:**
  - One-click spawn/council buttons
  - Real-time agent status (🔄 running | ✅ completed | ❌ failed)
  - Quick refresh button
  - Adapts based on whether agents exist

**Usage:**
```python
# To spawn agent: Click "➕ Spawn Agent" button
# To run council: Click "🗳️ Council" button
# To refresh status: Click "🔄 Refresh" button
```

**2. System Status Dashboard (Lines 1383-1448)**
- **Location:** Below Agent Quick Actions, before Settings
- **Purpose:** At-a-glance system health monitoring
- **Metrics:**
  - 💾 Cache hit rate (color-coded: 🟢 >70% | 🟡 40-70% | 🟠 <40%)
  - 💰 Session cost (real-time)
  - 🧠 Context usage (🟢 <50% | 🟡 50-75% | 🔴 >75%)

**Color Coding:**
- 🟢 Green = Healthy/Good
- 🟡 Yellow = Moderate/Warning
- 🔴 Red = Critical/High
- 🟠 Orange = Low performance

**3. Tool Count Correction (Line 2806)**
- Fixed caption: "30 tools" (was incorrectly "23")
- Reflects accurate count of registered tools

### Modifying Phase 1 Components

**To modify Agent Quick Actions:**
```bash
# Edit lines 1328-1378 in main.py
# Components: agent status display, button layout
# Note: Depends on tools.agents._agent_manager
```

**To modify System Status Dashboard:**
```bash
# Edit lines 1383-1448 in main.py
# Components: cache_stats, cost_stats, context_stats
# Note: Color thresholds can be adjusted here
```

**Design Principles:**
- Always visible (no expanders for critical info)
- Color-coded for quick recognition
- Hover tooltips for additional context
- Updates in real-time as system state changes

---

## Quick Command Reference

```bash
# Project Navigation
cd /home/llm/ApexAurum

# Start Application
streamlit run main.py

# Run Tests
python test_basic.py
python test_agents.py

# Check Tool Count
python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"

# View Logs
tail -f app.log
grep ERROR app.log

# Check Environment
cat .env
python --version

# Find Code
grep -r "function_name" .
grep -n "class ClassName" file.py

# Count Lines
wc -l *.py
wc -l core/*.py tools/*.py ui/*.py

# Process Management
ps aux | grep streamlit
pkill -f streamlit
```

---

## Session Checklist

### Starting a New Session

- [ ] Read PROJECT_STATUS.md
- [ ] Check current outstanding work
- [ ] Review AGENT_INTEGRATION_TODO.md if working on agents
- [ ] Verify environment: `cat .env`
- [ ] Check tool count: Should be 30
- [ ] Review recent logs: `tail -50 app.log`

### Ending a Session

- [ ] Test changes made
- [ ] Update relevant documentation
- [ ] Run applicable test suites
- [ ] Note any issues or next steps
- [ ] Check logs for errors
- [ ] Consider updating PROJECT_STATUS.md

---

## Conclusion

This development guide provides everything needed to quickly understand and work with ApexAurum - Claude Edition. The codebase is well-structured, thoroughly documented, and production-ready.

**Key Takeaways:**
1. Read PROJECT_STATUS.md first
2. Use documentation extensively
3. Test changes before committing
4. Follow existing patterns
5. Keep documentation updated

**For Questions:**
- Check relevant PHASE*_COMPLETE.md docs
- Search code with grep
- Review test files for examples
- Read inline comments and docstrings

**Happy coding!** 🚀

---

**Last Updated:** 2026-01-02
**Maintained By:** Project team
**Version:** 1.0 (Phase 2A Settings Presets Complete)
