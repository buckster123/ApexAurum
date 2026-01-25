# ApexAurum Ecosystem Restructuring Plan

**Created:** 2026-01-25
**Status:** Ready to execute

## Overview

Splitting the monolithic ApexAurum repo into a clean multi-repo ecosystem:

```
ApexAurum           → The OG Streamlit local version (cleanup)
ApexAurum-Cloud     → FastAPI + Vue cloud version (DONE ✅)
ApexAurum-Village   → Standalone 2D animated GUI (extract)
```

## Execution Order

### Phase 1: Extract ApexAurum-Village ⬅️ START HERE

**Source:** `sandbox/group_chat expansion/GUI-Village/`

**Steps:**
1. Create new GitHub repo `ApexAurum-Village`
2. Extract and restructure the GUI code
3. Set up clean project structure
4. Add CLAUDE.md and documentation
5. Push to new repo

**Target Structure:**
```
ApexAurum-Village/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI entry
│   │   ├── config.py         # Settings
│   │   ├── events.py         # EventBroadcaster
│   │   ├── websocket.py      # WebSocket handlers
│   │   └── tools/            # Tool service integration
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html            # Main HTML
│   ├── css/
│   │   └── village.css       # Styles
│   ├── js/
│   │   ├── main.js           # Entry point
│   │   ├── canvas.js         # Canvas rendering
│   │   ├── agents.js         # Agent sprites & movement
│   │   ├── zones.js          # Village zones (DJ Booth, Memory Garden, etc.)
│   │   └── websocket.js      # Real-time communication
│   └── assets/
│       ├── sprites/          # Agent avatars
│       └── backgrounds/      # Zone backgrounds
├── docs/
│   ├── ARCHITECTURE.md
│   └── VISION.md             # From the 6-voice council convergence
├── .claude/
│   └── skills/
│       └── village-dev.md
├── CLAUDE.md
├── HANDOVER.md
└── README.md
```

**Key Files to Extract:**
- `sandbox/group_chat expansion/GUI-Village/implementation/` → Planning docs
- `sandbox/group_chat expansion/GUI-Village/saved/` → Vision docs from council
- `reusable_lib/scaffold/fastapi_app/` → FastAPI base with WebSocket! Contains:
  - `main.py` - FastAPI entry with routes
  - `routes/` - Route definitions
  - `services/` - Service layer
  - `static/` & `templates/` - Frontend assets
  - `test_websocket_debug.py` - WebSocket testing
  - Working venv and requirements.txt

---

### Phase 2: Clean Up ApexAurum (Main Repo)

**Tasks:**

#### 2.1 Remove Extracted Code
```bash
rm -rf cloud/                                          # Now in ApexAurum-Cloud
rm -rf sandbox/group_chat\ expansion/GUI-Village/      # Now in ApexAurum-Village
```

#### 2.2 Archive Dev Logs Locally
```bash
# Create local archive (outside git)
mkdir -p ~/claude-root/Archives/ApexAurum-DevLogs

# Move old logs
mv dev_log_archive_and_testfiles/ ~/claude-root/Archives/ApexAurum-DevLogs/

# Or keep structure but gitignore
echo "dev_log_archive_and_testfiles/" >> .gitignore
```

#### 2.3 Clean Up Sandbox
Keep runtime data but clean old experiments:
```bash
# In sandbox/, keep:
# - conversations.json
# - agents.json
# - memory.json
# - music/
# - datasets/

# Remove or archive:
# - group_chat expansion/ (after Village extracted)
# - Old experiment folders
```

#### 2.4 Update Project Structure
Final clean structure:
```
ApexAurum/
├── main.py                 # Streamlit entry point
├── core/                   # Core systems (26 modules)
│   ├── api_client.py
│   ├── cache_manager.py
│   ├── vector_db.py
│   ├── memory_health.py
│   └── ...
├── tools/                  # All 106+ tools
│   ├── __init__.py
│   ├── utilities.py
│   ├── filesystem.py
│   ├── agents.py
│   ├── music.py
│   └── ...
├── pages/                  # Streamlit pages
│   ├── group_chat.py
│   ├── dataset_creator.py
│   └── music_visualizer.py
├── ui/                     # UI components
├── sandbox/                # Runtime data (gitignored except structure)
├── .claude/
│   └── skills/
├── requirements.txt
├── CLAUDE.md              # Updated for clean structure
├── HANDOVER.md
├── PROJECT_STATUS.md
└── README.md
```

#### 2.5 Update Documentation
- Update CLAUDE.md to reflect new structure
- Remove references to cloud/ and GUI-Village
- Add cross-references to other repos
- Clean up PROJECT_STATUS.md

#### 2.6 Update .gitignore
```gitignore
# Runtime data
sandbox/conversations.json
sandbox/agents.json
sandbox/memory.json
sandbox/music/
sandbox/datasets/
sandbox/*.py

# Archives
dev_log_archive_and_testfiles/

# Environment
.env
venv/
__pycache__/

# Logs
*.log
app.log
```

---

### Phase 3: Cross-Reference Setup

Add to each repo's README:

**ApexAurum:**
```markdown
## Related Projects
- [ApexAurum-Cloud](https://github.com/buckster123/ApexAurum-Cloud) - Cloud deployment (FastAPI + Vue)
- [ApexAurum-Village](https://github.com/buckster123/ApexAurum-Village) - 2D Animated GUI
```

**ApexAurum-Cloud:**
```markdown
## Related Projects
- [ApexAurum](https://github.com/buckster123/ApexAurum) - Local Streamlit version
- [ApexAurum-Village](https://github.com/buckster123/ApexAurum-Village) - 2D Animated GUI
```

**ApexAurum-Village:**
```markdown
## Related Projects
- [ApexAurum](https://github.com/buckster123/ApexAurum) - Local Streamlit version
- [ApexAurum-Cloud](https://github.com/buckster123/ApexAurum-Cloud) - Cloud deployment
```

---

## File Reference: What Goes Where

| Current Location | Destination |
|-----------------|-------------|
| `main.py`, `core/`, `tools/`, `pages/`, `ui/` | Stay in ApexAurum |
| `cloud/` | ApexAurum-Cloud (already done) |
| `sandbox/group_chat expansion/GUI-Village/` | ApexAurum-Village |
| `dev_log_archive_and_testfiles/` | Local archive |
| `sandbox/` (runtime) | Stay, but gitignore contents |
| `reusable_lib/` | Evaluate - keep useful scaffolds |

---

## Commands Quick Reference

### Create ApexAurum-Village Repo
```bash
# On GitHub: Create new empty repo "ApexAurum-Village"

# Locally
cd /tmp
mkdir ApexAurum-Village
cd ApexAurum-Village
git init

# Copy and restructure files from ApexAurum
# (see Phase 1 for structure)

git add .
git commit -m "Initial commit - Village GUI extraction"
git remote add origin git@github.com:buckster123/ApexAurum-Village.git
git branch -M main
git push -u origin main
```

### Archive Dev Logs
```bash
mkdir -p ~/claude-root/Archives/ApexAurum-DevLogs
mv /home/hailo/claude-root/Projects/ApexAurum/dev_log_archive_and_testfiles/* \
   ~/claude-root/Archives/ApexAurum-DevLogs/
```

### Clean ApexAurum
```bash
cd /home/hailo/claude-root/Projects/ApexAurum
rm -rf cloud/
rm -rf "sandbox/group_chat expansion/GUI-Village/"
# Update .gitignore
# Commit cleanup
```

---

## Success Criteria

- [ ] ApexAurum-Village repo created and pushed
- [ ] GUI code extracted and structured
- [ ] cloud/ removed from ApexAurum
- [ ] GUI-Village removed from ApexAurum
- [ ] Dev logs archived locally
- [ ] .gitignore updated
- [ ] CLAUDE.md updated in ApexAurum
- [ ] Cross-references added to all READMEs
- [ ] All three repos have working CLAUDE.md and HANDOVER.md

---

## Notes

- **ApexAurum-Cloud** is already deployed on Railway - don't break it!
- The Streamlit app should keep working throughout cleanup
- Test after each major change
- Commit frequently with clear messages

---

*Let's make the ApexAurum ecosystem clean and professional! 🚀*
