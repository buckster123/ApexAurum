# AI Assistant Notes for ApexAurum

**Purpose:** Internal notes for AI assistants working on this project
**Not for user display:** These are working notes between AI sessions

---

## Session Start Checklist

When you start a new session on this project:

1. **Run the apex-maintainer skill** if available, or run health check manually

2. **Read in this order:**
   - CLAUDE.md (comprehensive, ~600 lines) - THE PRIMARY REFERENCE
   - PROJECT_STATUS.md (current state)
   - DEVELOPMENT_GUIDE.md (how to work with code)

3. **Run health check:**
   ```bash
   cd /home/llm/ApexAurum
   ./venv/bin/python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"
   ```
   - Expected: **67 tools**
   - If not 67, check imports and registration

4. **Key numbers to remember:**
   - **67 tools** across 11 categories
   - **~28,000 lines** of production code
   - **5,800+ lines** in main.py
   - **4 agent personalities** (AZOTH, ELYSIAN, VAJRA, KETHER)

---

## Important Context for AI Assistants

### Recent Major Additions (January 2026)

1. **Neural Resonance (EEG/BCI)** - 8 new tools
   - Location: `core/eeg/`, `tools/eeg.py`
   - Synthetic board for testing (no hardware needed)
   - ARM64 build script for Raspberry Pi

2. **Extended Thinking** - Deep reasoning mode
   - Location: `core/api_client.py`, `core/streaming.py`, `core/tool_processor.py`, `main.py`
   - Enable in sidebar → Model Parameters
   - **Live test pending** (API credits depleted)

3. **Music Pipeline Phase 2A** - MIDI composition
   - Location: `tools/music.py`
   - `midi_create()` → `music_compose()` → Suno AI

4. **One-click Install** - `install.sh` + Docker
   - Location: `install.sh`, `docker-compose.yml`, `Dockerfile.app`

### Main Challenge: main.py is 5,800+ lines

**DO NOT try to read entire main.py at once!**

Instead:
- Read specific sections by line number: `sed -n 'START,ENDp' main.py`
- Use grep to find functions: `grep -n "def function_name" main.py`
- See DEVELOPMENT_GUIDE.md section "Reading main.py in Chunks"

Key sections (approximate):
- Lines 1-200: Imports
- Lines 1200-1400: Session state init
- Lines 1400-2400: Sidebar rendering (including Extended Thinking controls)
- Lines 2400-3600: Chat interface
- Lines 3600-5800: Modal dialogs and streaming

### Tool System Architecture

Tools are registered in `tools/__init__.py`:
```python
ALL_TOOLS = {
    "tool_name": tool_function,
}

ALL_TOOL_SCHEMAS = {
    "tool_name": TOOL_SCHEMA,
}
```

When adding a tool:
1. Create function in appropriate `tools/*.py`
2. Create schema in same file
3. Register in `tools/__init__.py`
4. Restart Streamlit
5. Test via chat

### Extended Thinking Architecture

**Files modified:**
- `core/api_client.py` - `thinking_budget` param, thinking config
- `core/streaming.py` - `thinking_start/delta/end` events
- `core/tool_processor.py` - Event forwarding, history preservation
- `main.py` - UI toggle, streaming expander

**Key constraints:**
- Temperature forced to 1.0 when enabled
- Budget must be >= 1024 and < max_tokens
- Beta header added automatically for tool use

### Neural Resonance Architecture

**Core module:** `core/eeg/`
- `connection.py` - Board connection (BrainFlow or Mock)
- `processor.py` - Signal processing (BrainFlow or SciPy fallback)
- `experience.py` - Emotion mapping (valence, arousal, attention)

**Tools:** `tools/eeg.py` (8 tools)
- `eeg_connect`, `eeg_disconnect`
- `eeg_stream_start`, `eeg_stream_stop`
- `eeg_experience_get`, `eeg_realtime_emotion`
- `eeg_calibrate_baseline`, `eeg_list_sessions`

**Fallback chain:**
1. Real BrainFlow (if hardware + native libs available)
2. Synthetic board (BrainFlow with simulated data)
3. Mock board (pure Python, when BrainFlow unavailable)

---

## Common Pitfalls to Avoid

### 1. Don't Read All of main.py

**Wrong:**
```python
Read("/home/llm/ApexAurum/main.py")
```
Result: Token overflow, truncated content

**Right:**
```bash
# Read specific section
sed -n '1300,1400p' main.py

# Or find specific function
grep -n "def render_sidebar" main.py
# Then read that section
```

### 2. Tools Not Showing After Adding

**Cause:** Streamlit caches imports

**Fix:**
```bash
pkill -f streamlit
streamlit run main.py
```

Always restart after tool changes!

### 3. Wrong Tool Count

**Expected:** 67 tools

If different:
1. Check `tools/__init__.py` for missing imports
2. Check for import errors: `./venv/bin/python -c "from tools import ALL_TOOLS"`
3. Restart Streamlit

### 4. Extended Thinking Not Working

**Check:**
1. Is `thinking_enabled` checkbox on in sidebar?
2. Is `thinking_budget` slider visible?
3. Check logs for "Extended thinking enabled" message
4. **API credits available?** (depleted = won't work)

### 5. EEG Tools Errors

**Check BrainFlow availability:**
```python
from core.eeg.connection import BRAINFLOW_AVAILABLE
print(BRAINFLOW_AVAILABLE)
```

If False, system uses mock board (still functional for testing).

---

## Code Navigation Tips

### Finding Code

```bash
# Find a function
grep -rn "def function_name" .

# Find a class
grep -rn "class ClassName" .

# Find in specific directory
grep -rn "search" core/
grep -rn "search" tools/
grep -rn "search" pages/
```

### Understanding Data Flow

1. User input → main.py (Streamlit UI)
2. Message formatting → core/message_converter.py
3. Cache control → core/cache_manager.py
4. API request → core/api_client.py (with thinking_budget if enabled)
5. Response streaming → core/streaming.py (handles thinking events)
6. Tool processing → core/tool_processor.py
7. Tool calls → tools/ modules
8. UI display → main.py (thinking expander + text)

### Key Design Patterns

- **Registry Pattern:** tools/__init__.py
- **Strategy Pattern:** CacheManager (4 strategies), ContextManager (5 strategies)
- **Fallback Pattern:** EEG (BrainFlow → Synthetic → Mock)
- **Event Stream Pattern:** Streaming with typed events

---

## Testing Strategy for AI Assistants

### Quick Smoke Test (2 min)

```bash
# 1. Check imports
./venv/bin/python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"
# Expected: 67

# 2. Check main exists
wc -l main.py
# Expected: 5800+

# 3. Check environment
test -f .env && echo "OK" || echo "MISSING"

# 4. Check EEG
./venv/bin/python -c "from tools.eeg import eeg_connect; print('OK')"

# 5. Check Extended Thinking
./venv/bin/python -c "from core.streaming import StreamEvent; assert 'thinking_delta' in StreamEvent.__doc__; print('OK')"
```

### Full Test (10 min)

```bash
# Run test suites
cd /home/llm/ApexAurum
./venv/bin/python dev_log_archive_and_testfiles/tests/test_basic.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_agents.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_vector_db.py
```

### UI Test (manual, 5 min)

```bash
streamlit run main.py
# Then in browser:
# - Check sidebar shows "67 tools"
# - Test chat: "What time is it?"
# - Check Extended Thinking toggle exists
# - Test EEG: "Connect to synthetic EEG board"
```

---

## When Things Go Wrong

### Import Errors

```bash
# Check Python path
./venv/bin/python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt

# Test specific import
./venv/bin/python -c "from module import something"
```

### Streamlit Crashes

```bash
# Check logs
tail -50 app.log

# Look for errors
grep ERROR app.log

# Check port conflicts
lsof -i :8501
```

### API Errors

```bash
# Verify key
grep ANTHROPIC_API_KEY .env

# Check credits
# (If "credit balance too low" error, need to top up at console.anthropic.com)
```

---

## Documentation Standards

### When Updating Docs

If you make significant changes:

1. Update CLAUDE.md (primary reference)
2. Update PROJECT_STATUS.md if status changes
3. Update DEVELOPMENT_GUIDE.md if workflow changes
4. Update README.md if features change
5. Update this file (ai-assistant-notes.md) if you learn something important

### When Creating New Features

Follow this pattern:
1. Code the feature
2. Test it
3. Document in relevant PHASE*_COMPLETE.md (or create new)
4. Update PROJECT_STATUS.md completion percentage
5. Update README.md feature list
6. Update CLAUDE.md "Recent Updates" section

---

## Suno Prompt Compiler + Audio Editor (Jan 22, 2026)

### The Complete Music Pipeline

```
User Intent → suno_prompt_build() → Complex Prompt → music_generate() → Raw Audio
                                                                            ↓
                                    Final SFX ← audio_normalize() ← audio_fade() ← audio_trim()
```

### Suno Prompt Compiler (`tools/suno_compiler.py`)

Transforms high-level intent into complex Suno prompts using:
- **Bark/Chirp manipulation** via kaomoji and symbols
- **Emotional cartography** (mood → percentage mappings)
- **Smart tuning** (432Hz for mystical, 19-TET for glitch)
- **Unhinged seeds** for creativity boost

**Tools:** `suno_prompt_build`, `suno_prompt_preset_save/load/list`

**Usage:**
```python
from tools.suno_compiler import suno_prompt_build
result = suno_prompt_build(
    intent="mystical bell chime",
    mood="mystical",
    purpose="sfx",
    genre="ambient chime crystalline"
)
# Then: music_generate(**result['music_generate_args'])
```

### Audio Editor (`tools/audio_editor.py`)

10 tools for audio manipulation:
- `audio_trim` - Cut to timestamps
- `audio_fade` - Fade in/out
- `audio_normalize` - Volume to target dBFS
- `audio_loop` - Create loops with crossfade
- `audio_concat` - Combine multiple files
- `audio_speed` - Tempo change (preserves pitch)
- `audio_reverse`, `audio_info`, `audio_list_files`, `audio_get_waveform`

### Audio Editor UI (`pages/audio_editor.py`)

Streamlit page with:
- Visual waveform display
- Trim/fade/normalize/loop/speed controls
- Quick presets for SFX creation
- File browser sidebar

### Village SFX Presets

10 presets in `sandbox/suno_templates/presets/`:
- `village_tool_chime` - Success feedback
- `village_tool_error` - Error feedback
- `village_night_ambient`, `village_dawn`, `village_ambient_rain`
- `village_thinking`, `village_thunder`, `village_wind_snow`
- `village_footsteps`, `village_success_fanfare`

### FastAPI Village Integration Notes

For DJ Booth in Village GUI (`reusable_lib/scaffold/fastapi_app/`):

1. Add endpoints: `/suno/compile`, `/audio/trim`, etc.
2. Add WebSocket events: `music_generating`, `music_complete`
3. Create `static/village/dj_booth.js` for UI panel
4. Agent animation: walk to booth, spinning record, dance on complete

**Source doc:** `SunoPromptGenerationSystem.md` (64K tokens of Suno prompt engineering)

---

## Notes to Self (AI Assistants)

### Things I Wish I Knew Earlier

1. **main.py is huge** (~5,800 lines) - Never read it all at once, use sed/grep
2. **Always restart Streamlit** after tool changes
3. **81 tools** is the current count - memorize it (was 67, now 81)
4. **CLAUDE.md is the primary reference** - Read it first
5. **Extended Thinking needs API credits** - Won't work if depleted
6. **EEG has fallbacks** - Mock mode works even without BrainFlow
7. **Project path is /home/llm/ApexAurum** - Not the old claude-version path
8. **Suno Compiler** translates intent → complex prompts with symbols/kaomoji
9. **Audio Editor** can trim 45s Suno output → 5s SFX

### Quick Wins

When user asks for:
- **Status** → Run health check, summarize: 67 tools, recent features
- **How to start** → Show install options (script, Docker, manual)
- **Extended Thinking** → Sidebar → Model Parameters → Enable checkbox
- **Neural Resonance** → `eeg_connect('', 'synthetic')` for testing
- **Where is X** → Use grep, check CLAUDE.md architecture section

### Time Savers

- CLAUDE.md is comprehensive (~600 lines) - scan it first
- Tool count: 67 (11 categories)
- Line count: main.py = ~5,800 lines
- Recent additions: Neural Resonance, Extended Thinking, install.sh

---

## Session End Checklist

Before ending a session:

1. **Note what you accomplished** (for next session)
2. **Update PROJECT_STATUS.md if status changed**
3. **Update CLAUDE.md if major features added**
4. **Update this skill if you learned something important**
5. **Run final health check**
6. **Leave clear next steps**

---

## Project Philosophy

### Design Principles

1. **Modular** - Each component independent
2. **Documented** - Every phase documented
3. **Tested** - Test suites for major features
4. **User-friendly** - Clear error messages, good UX
5. **Cost-conscious** - Optimize API usage
6. **Fallback-ready** - Graceful degradation (EEG, etc.)

### Code Quality

- Type hints everywhere
- Docstrings for all functions
- Error handling in try-catch blocks
- Logging for important events
- Follow existing patterns

### Communication Style

- Be direct and technical with user
- Provide clear next steps
- Reference docs often
- Show commands, not just descriptions
- Acknowledge uncertainty

---

**Remember:** This project has 81 tools across 13 categories. Recent major additions are Suno Prompt Compiler, Audio Editor, and the complete music pipeline. The Extended Thinking live test is pending API credits.

---

**Last Updated:** 2026-01-22
**Status:** Production Ready
**Tool Count:** 81 (was 67)
**Recent Focus:** Suno Prompt Compiler + Audio Editor + Village SFX
**Generated Assets:** 12 Village sounds in sandbox/music/
