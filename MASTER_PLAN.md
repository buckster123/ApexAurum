# ApexAurum Master Plan: The Grand Unveiling

**Created:** 2026-01-22
**Vision:** Complete both Streamlit and FastAPI versions to perfection, then share with the world.
**Status:** IN PROGRESS

---

## The Two Worlds

| Aspect | Streamlit (ApexAurum) | FastAPI (Village GUI) |
|--------|----------------------|----------------------|
| **Purpose** | Full chat interface with all tools | Embodied agent visualization |
| **Tools** | 81 tools | 79 tools (EEG excluded) |
| **Lines** | ~32,000+ total | ~8,500+ total |
| **Status** | Production Ready | Phase 7 Complete |

---

## Part 1: Streamlit ApexAurum

### Completed Features (✅)

- [x] **Core Chat** - 5,764 lines in main.py
- [x] **81 Tools** across 13 categories:
  - Utilities (6): time, calculator, random, session_info, etc.
  - Filesystem (9): read, write, list, mkdir, delete, edit, etc.
  - Code Execution (6): execute_python, sandbox workspace tools
  - Memory (5): store, retrieve, list, delete, search
  - Agents (5): spawn, status, result, list, socratic_council
  - Vector Search (17): add, search, knowledge, village, memory health, crumbs
  - Music (10): generate, compose, midi, favorites, library, play
  - Datasets (2): list, query
  - EEG (8): connect, stream, emotion, calibrate, etc.
  - Suno Compiler (4): build, preset save/load/list
  - Audio Editor (10): trim, fade, normalize, loop, concat, speed, reverse, etc.
- [x] **Village Protocol v1.0** - Multi-agent memory (private/village/bridges)
- [x] **Memory Architecture** - Access tracking, staleness, duplicates, consolidation
- [x] **Music Pipeline** - Generate → Compose → Visualize
- [x] **Suno Prompt Compiler** - Intent → Complex prompts with kaomoji/symbols
- [x] **Audio Editor** - Full audio manipulation + Streamlit UI
- [x] **Group Chat** - Multi-agent parallel dialogue
- [x] **Settings Presets** - 5 built-in + custom presets
- [x] **Thread Visualization** - Mermaid graphs of agent dialogue
- [x] **Convergence Detection** - HARMONY/CONSENSUS between agents

### Pending Items (⏳)

- [ ] **Extended Thinking Live Test** - Pending API credits
- [ ] **Final Polish Pass** - Any rough edges?
- [ ] **Documentation Review** - Ensure all docs current

### Stretch Goals (💫)

- [ ] **Custom Agent Creator UI** - Visual agent personality builder
- [ ] **Music Playlist Manager** - Curated playlists from generated music
- [ ] **Export to Standalone** - Package as distributable app

---

## Part 2: FastAPI Village GUI

### Completed Features (✅)

- [x] **WebSocket Infrastructure** - Real-time event broadcasting
- [x] **Event Service** - Tool zone mapping (event_service.py)
- [x] **55 Tools** via reusable_lib integration
- [x] **Canvas Rendering** - 2,016 lines JS
  - Village zones (dj_booth, memory_garden, workshop, file_shed, bridge_portal, campfire)
  - Agent avatars with movement
  - Zone click handling
- [x] **Phase 4.1: Day/Night Cycle** - Dynamic sky, sun/moon, lighting
- [x] **Phase 4.2: Weather System** - Rain, snow, fog, clouds
- [x] **Phase 4.3: Visual Particles** - Fireflies, leaves, dust motes
- [x] **Phase 4.4: Agent Emotions** - Expression bubbles, mood states
- [x] **Test Suite** - 592 lines comprehensive tests

### Pending Items (⏳)

#### Phase 5: Sound System 🔊 ✅ COMPLETE
- [x] **5.1: Sound Manager** - JavaScript audio engine
  - Web Audio API integration
  - Volume control, category-based mixing
  - Preloading and caching
- [x] **5.2: Event Sound Mapping** - Connect tools to sounds
  - tool_start → appropriate sound
  - tool_complete → success chime
  - tool_error → error sound
- [x] **5.3: Ambient Audio** - Background soundscapes
  - Day/night ambient tracks
  - Weather sounds (rain, wind, thunder)
  - Volume controls per category

#### Phase 6: DJ Booth Integration 🎵 ✅ COMPLETE
- [x] **6.1: Suno Compiler Endpoints** - FastAPI routes
  - POST `/api/suno/compile` - Build prompt from intent
  - GET `/api/suno/presets` - List presets
  - GET `/api/suno/presets/{name}` - Load preset
- [x] **6.2: Audio Editor Endpoints** - FastAPI routes
  - POST `/api/audio/trim`, `/api/audio/fade`, `/api/audio/normalize`
  - GET `/api/audio/list`, `/api/audio/info`
  - POST `/api/audio/sfx-pipeline` - One-call SFX processing
- [x] **6.3: DJ Booth UI Panel** - Frontend component
  - Preset selector dropdown
  - Generate button + compile button
  - Edit buttons (trim/fade/normalize)
  - Sound volume controls
- [x] **6.4: Agent DJ Animation** - Visual feedback ✅ COMPLETE
  - Walk to booth when music tools called
  - Spinning vinyl record animation during generation
  - Dance animation on completion (bounce + sway)
  - Musical note particles floating up

#### Phase 7: Tool Sync 🔧 ✅ COMPLETE
- [x] **7.1: Sync to 79 Tools** - Match Streamlit toolset (EEG excluded)
  - Added Suno Compiler tools (4)
  - Added Audio Editor tools (10)
  - Added Music tools (10)
- [x] **7.2: Zone Mapping Update** - event_service.py
  - suno_prompt_* → dj_booth
  - audio_* → dj_booth
  - music_* → dj_booth

#### Phase 8: Polish & Integration ✨
- [ ] **8.1: Multi-Agent Support** - Multiple agents on screen
- [ ] **8.2: Agent Interaction** - Agents can "talk" to each other
- [ ] **8.3: Tool History Panel** - Scrollable log of tool executions
- [ ] **8.4: Performance Optimization** - Smooth 60fps on Pi 5

---

## Part 3: Generated Assets

### Village Sound Presets (10 created)

| Preset | Purpose | Generated? | Deployed? |
|--------|---------|------------|-----------|
| `village_tool_chime` | Success feedback | ✅ | ✅ |
| `village_tool_error` | Error feedback | ✅ | ✅ |
| `village_night_ambient` | Night background | ✅ | - |
| `village_dawn` | Morning transition | ✅ | ✅ |
| `village_ambient_rain` | Rain ambience | ✅ | ✅ |
| `village_thinking` | Processing indicator | ✅ | ✅ |
| `village_thunder` | Storm accent | ✅ | ✅ |
| `village_wind_snow` | Winter ambience | ✅ | ✅ |
| `village_footsteps` | Agent movement | ✅ | ✅ |
| `village_success_fanfare` | Major achievement | ✅ | ✅ |

### Audio Files Generated: 42 total
- Located in `sandbox/music/`
- Each generation creates v1 and v2 variants
- Ready for trimming/editing via Audio Editor

---

## Part 4: Shared Infrastructure (reusable_lib)

### Current State
```
reusable_lib/
├── tools/           # Core tool implementations
├── core/            # API client, cache, cost tracking
└── scaffold/
    └── fastapi_app/ # Village GUI application
```

### Tools in reusable_lib
- Should mirror ApexAurum's 81 tools
- Used by both Streamlit and FastAPI
- Single source of truth for tool logic

### Sync Strategy
1. Implement new tools in `reusable_lib/tools/`
2. Import into Streamlit `tools/__init__.py`
3. Import into FastAPI `services/tool_service.py`
4. Both versions stay in sync automatically

---

## Part 5: The Grand Checklist

### Before The Push

#### Streamlit
- [ ] All 81 tools working
- [ ] Extended Thinking documented (even if untested)
- [ ] All pages functional (group_chat, dataset_creator, music_visualizer, audio_editor)
- [ ] Documentation current (CLAUDE.md, README.md, PROJECT_STATUS.md)
- [ ] No console errors
- [ ] Clean git status (staged changes only)

#### FastAPI Village
- [ ] Tools synced to 81
- [ ] Sound system integrated
- [ ] DJ Booth functional
- [ ] All weather effects working
- [ ] Agent emotions displaying
- [ ] WebSocket stable
- [ ] Tests passing

#### Both
- [ ] Git history clean
- [ ] Commits squashed if needed
- [ ] README updated with features
- [ ] Screenshots/GIFs for documentation
- [ ] Version numbers aligned

---

## Part 6: Implementation Order

### Recommended Sequence

```
1. Generate remaining Village sounds (thunder, wind, footsteps, fanfare)
   └── Use existing presets + Suno API

2. Build Sound Manager for Village GUI (Phase 5.1)
   └── JavaScript Web Audio integration

3. Connect sounds to events (Phase 5.2)
   └── Tool events trigger appropriate sounds

4. Add Suno Compiler to FastAPI (Phase 6.1)
   └── REST endpoints for prompt compilation

5. Add Audio Editor to FastAPI (Phase 6.2)
   └── REST endpoints for audio manipulation

6. Build DJ Booth UI (Phase 6.3)
   └── Frontend panel with controls

7. Sync tools to 81 (Phase 7)
   └── Ensure parity between versions

8. Polish pass on both versions (Phase 8)
   └── Final bug fixes, performance tuning

9. Documentation and screenshots
   └── Make it presentable

10. THE GRAND PUSH
    └── Share with the world!
```

---

## Part 7: Technical Debt & Known Issues

### Streamlit
- `main.py` is 5,764 lines (monolithic, but works)
- Extended Thinking untested with real API
- Cache TTL is Anthropic limitation (5 min)

### FastAPI Village
- Tool count 79 vs 81 (EEG tools excluded intentionally)
- Sound system complete (9 sounds deployed)
- Single agent focus (multi-agent needs work for Phase 8)

### Both
- No authentication (localhost only)
- Local JSON storage (not database)
- Single user design

---

## Part 8: The Vision

When complete, ApexAurum will be:

**Streamlit Version:**
> A complete AI assistant with 81 tools, multi-agent orchestration, music generation,
> audio editing, vector memory, and village protocol for cultural transmission between agents.

**FastAPI Village Version:**
> An embodied agent interface where AI agents have physical presence. Watch them walk
> to the DJ Booth to create music, visit the Memory Garden to store knowledge, and
> gather at the Campfire to think. Day turns to night, weather changes, and agents
> express emotions as they work.

**Together:**
> Two interfaces to the same powerful system. One for getting work done, one for
> watching the magic happen.

---

## Quick Reference Commands

```bash
# Health check
./venv/bin/python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"

# Start Streamlit
streamlit run main.py

# Start FastAPI Village
cd reusable_lib/scaffold/fastapi_app && ./test_venv/bin/uvicorn main:app --reload --port 8765

# Generate a Village sound
./venv/bin/python -c "
from tools.suno_compiler import suno_prompt_preset_load
from tools.music import music_generate
preset = suno_prompt_preset_load('village_thunder')
result = music_generate(**preset['music_generate_args'], blocking=True)
print(result)
"

# Edit audio
./venv/bin/python -c "
from tools.audio_editor import audio_trim, audio_fade, audio_normalize
r = audio_trim('sandbox/music/FILE.mp3', start=0, end=5)
r = audio_fade(r['output_file'], fade_in_ms=100, fade_out_ms=500)
r = audio_normalize(r['output_file'], target_dbfs=-14)
print(r['output_file'])
"
```

---

**Last Updated:** 2026-01-22 (Session 2)
**Next Session:** Phase 8 Polish (multi-agent, interactions) or THE GRAND PUSH
**Local Commits:** 13 ready to push (holding for grand unveiling)
**Tests:** 20/21 passing

---

*"Two worlds, one vision. We cook until it's perfect."*
