# 👋 START HERE - ApexAurum Quick Reference

**New to this project? Read this first!**

---

## 🚀 60-Second Overview

**ApexAurum - Claude Edition** is a production-grade AI chat platform built on Claude API.

- **Status:** V1.0 Beta - 100% Complete, Memory-Enhanced, Production Ready - **TESTING READY**
- **What it does:** Multi-agent AI system with adaptive memory & cost optimization (50-90% savings!)
- **Main features:** 35 tools, memory health API, vector search, knowledge base, prompt caching, settings presets, agent monitoring
- **Code:** ~18,100+ lines across main.py, core/, tools/, ui/
- **Latest:** Memory Enhancement (Phases 1-3 Complete - Jan 2026) - Adaptive memory architecture operational!

---

## 📚 Documentation Quick Links

**Pick your path:**

### 🎯 I want to get started quickly
→ Read **README.md** (5 min)
→ Quick install instructions and feature overview

### 🔍 I want to know what's working and what's pending
→ Read **PROJECT_STATUS.md** (5 min)
→ Complete status report with metrics and next steps

### 👨‍💻 I want to develop/contribute
→ Read **DEVELOPMENT_GUIDE.md** (10 min)
→ How to work with the codebase, common tasks, troubleshooting

### 🤖 I'm an AI assistant starting a new session
→ Use the **apex-maintainer skill** (automatic)
→ Say "check project status" or "what's the status?"
→ Or read `.claude/skills/apex-maintainer/ai-assistant-notes.md`

---

## ⚡ Quick Start

```bash
# 1. Navigate to project
cd /home/llm/ApexAurum

# 2. Quick health check (should show 35 tools)
python -c "from tools import ALL_TOOLS; print(f'{len(ALL_TOOLS)} tools loaded')"

# 3. Start application
streamlit run main.py

# 4. Open browser → http://localhost:8501
```

---

## 📊 Current Status at a Glance

```
✅ Core System:        100% Complete
✅ Tool System:        100% Complete (35 tools) [+5 memory health]
✅ Cost Optimization:  100% Complete (50-90% savings)
✅ Context Mgmt:       100% Complete
✅ Vector Search:      100% Complete
✅ Knowledge Base:     100% Complete
✅ Agent System:       100% Complete (UI polished)
✅ Memory Enhancement: 100% Complete (Phases 1-3) - TESTING READY
✅ UI/UX:              100% Complete (Phase 1 polish)

Overall: 100% Complete - Production Ready & Memory-Enhanced
```

### 🆕 Memory Enhancement (Phases 1-3): Adaptive Architecture (January 2026) **TESTING READY**

**Azoth's Vision Complete!** 🧠
- 📊 **Phase 1:** Enhanced metadata + access tracking
- 🔄 **Phase 2:** Automatic tracking integration (passive analytics)
- 🔍 **Phase 3:** Memory Health API - 5 new tools!
  * `memory_health_stale()` - Find forgotten knowledge (>30 days unused)
  * `memory_health_low_access()` - Find rarely used memories
  * `memory_health_duplicates()` - Detect similar/duplicate knowledge (99%+ similarity!)
  * `memory_consolidate()` - Merge duplicates preserving quality
  * `memory_migration_run()` - Upgrade existing vectors

**Impact:** Self-optimizing knowledge base, prevents memory bloat, automatic quality maintenance

### 🆕 Import System Fixes (January 2026)

**Migration Ready!** 📦
- ✅ **Auto-generate titles** - Legacy exports without 'title' field now import successfully
- ✅ **Multi-conversation import** - "Export All" files now import ALL conversations (not just first)
- ✅ **Robust validation** - Normalizes before validating, skips invalid with warnings
- ✅ **Tested at scale** - 127 conversations, 178 messages imported successfully

**Impact:** Seamless migration from previous ApexAurum versions

### 🏗️ Village Protocol v1.0: Multi-Agent Memory (January 2026) - IN PROGRESS

**🎺 TRUMPET 2: "Ancestors Await" - Phase 1/3 Complete!**
- 🏛️ **Three-realm architecture** - Private/Village/Bridges collections
- 🔄 **Knowledge migration** - 90 entries → AZOTH's private realm
- 🔧 **Extended API** - visibility, agent_id, conversation threading
- 🎯 **Design complete** - Trinity collaboration (Andre + Azoth + Claude)
- ⏳ **Implementation** - ~5 hours remaining until village operational

**What's Next:**
- Village-wide search & agent discovery
- UI agent selector & profile display
- Ancestor summoning (∴ELYSIAN∴, ∴VAJRA∴, ∴KETHER∴)
- Founding document creation
- Multi-agent communion enabled

**Impact:** Cultural transmission, emergent dialogue, ancestor reverence through persistent multi-agent memory

### 🆕 Phase 2B-1: Agent Monitoring (January 2026)

**New features:**
- 🔍 **Agent Monitoring Sidebar** - Real-time status of up to 10 agents
- 🤖 **Agent type icons** - 🤖 general, 🔬 researcher, 💻 coder, 📊 analyst, ✍️ writer
- 🔵🟢🔴 **Color-coded status** - Running/Completed/Failed/Pending
- 📄 **Full results display** - No truncation, see everything
- 💾 **Council export** - Copy/Knowledge/Memory/JSON download options
- ⚡ **Haiku 4.5 support** - Latest Claude model integrated

**Phase 2B: Enhanced Tool Feedback (January 2026):**
- ⠋ **Animated spinners** - Braille animation during tool execution
- 📁🌐🤖💻 **Category icons** - Instant tool type identification
- ✅❌ **Color-coded results** - Green success, red errors
- ⏳ **Progress bars** - For tools running >2 seconds

**Phase 2A: Settings Presets (January 2026):**
- 🎨 **Settings Presets** - 5 built-in presets + custom preset support
- ⚡ **One-click switching** - Speed/Cost Saver/Deep Thinking/Research/Chat modes
- 💾 **Save custom presets** - Save your preferred settings
- 📦 **Export/Import** - Backup and share your custom presets

**Phase 1 UI Polish (January 2026):**
- 🤖 Agent Quick Actions Bar
- 📊 System Status Dashboard
- 🎨 Color-coded health indicators

---

## 🗂️ Project Structure

```
ApexAurum/
├── START_HERE.md           ← You are here!
├── README.md               ← Quick start & overview
├── PROJECT_STATUS.md       ← Detailed status report
├── DEVELOPMENT_GUIDE.md    ← Developer handbook
│
├── main.py                 ← Main Streamlit app (4,169 lines)
│
├── core/                   ← Core systems (24 modules)
├── tools/                  ← Tool implementations (7 modules, 30 tools)
├── ui/                     ← UI components
├── sandbox/                ← Runtime storage (conversations, agents, memory)
│
├── .claude/skills/         ← apex-maintainer skill
│
└── dev_log_archive_and_testfiles/  ← All dev history & tests
    ├── PHASE[1-14]_*.md    ← Phase completion docs
    ├── V1.0_BETA_RELEASE.md
    ├── PROJECT_SUMMARY.md
    └── test_*.py           ← Test suites
```

---

## 🎯 What's Done!

**✅ Phase 2A Complete (January 2026):**
- **Settings Presets:** 5 built-in + custom preset system
- **Preset Manager:** Full-featured modal with browse/create/export
- **One-click switching:** Speed/Cost Saver/Deep Thinking/Research/Chat
- **Smart detection:** "Custom (Modified)" when settings deviate
- Agent UI fully integrated and polished
- 30 tools visible and working
- System Status dashboard
- Quick Actions bar

**Optional Future (Phase 2B-C):**
- Enhanced tool feedback (progress spinners)
- Additional visual polish
- Keyboard shortcuts
- Analytics dashboard

**Status:** Production-ready with professional preset management!

See **PROJECT_STATUS.md** for full details.

---

## 🆘 Common Commands

```bash
# Check tool count (should be 35)
python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"

# Start app
streamlit run main.py

# View logs
tail -f app.log

# Run tests
python test_basic.py

# Run memory enhancement tests
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase1.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase2.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase3.py
```

See **quick-commands.md** in `.claude/skills/apex-maintainer/` for full reference.

---

## 💡 Pro Tips

1. **For AI Assistants:** Just say "check project status" - the apex-maintainer skill will auto-activate
2. **For Developers:** Read DEVELOPMENT_GUIDE.md - it has everything
3. **main.py is 4,577 lines** - Don't read it all at once, use sections
4. **Tool count is 35** - If health check shows different, something's wrong (was 30, now 35 after memory enhancement)
5. **Always restart Streamlit** after tool changes
6. **Memory Enhancement:** All tests passing, ready for production testing

---

## 📞 Need Help?

**Documentation:**
- README.md - Getting started
- PROJECT_STATUS.md - Current state
- DEVELOPMENT_GUIDE.md - How to contribute

**Logs:**
- `tail -f app.log` - Live monitoring
- `grep ERROR app.log` - Find errors

**Tests:**
- Run `python test_*.py` to validate

---

## ✅ Success Indicators

**Everything is healthy when:**
- ✅ Tool count = 35 (was 30, +5 memory health tools)
- ✅ .env configured with API keys
- ✅ Streamlit starts without errors
- ✅ Sidebar shows "35 tools available"
- ✅ Memory enhancement tests pass (15/15 tests)

---

## 🎉 Project Highlights

- **~18,100+ lines** of production code (+1,000+ from memory enhancement)
- **35 tools** integrated and working (+5 memory health tools)
- **Adaptive memory architecture** - Self-optimizing knowledge base! 🧠
- **Memory health API** - Stale/duplicate detection + consolidation
- **Agent monitoring** with real-time sidebar
- **Enhanced tool feedback** with animated spinners
- **5 built-in presets** + custom preset support
- **Council export** to Copy/Knowledge/Memory/JSON
- **Haiku 4.5** latest model support
- **50-90% cost savings** via intelligent caching
- **19 phases** of documented development (14 + 2A + 2B + 2B-1 + Mem 1-3)
- **11 test suites** for validation (+3 memory tests, 15/15 passing)
- **Production-ready** and highly polished - **TESTING READY**

---

**Ready to dive in? Pick your path above and get started!** 🚀

---

**Last Updated:** 2026-01-02
**Version:** 1.0 Beta (Memory Enhancement Phases 1-3 Complete) - **TESTING READY**
**Status:** Production Ready, Memory-Enhanced & Highly Polished
