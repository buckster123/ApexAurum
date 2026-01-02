# 👋 START HERE - ApexAurum Quick Reference

**New to this project? Read this first!**

---

## 🚀 60-Second Overview

**ApexAurum - Claude Edition** is a production-grade AI chat platform built on Claude API.

- **Status:** V1.0 Beta - 100% Complete, Production Ready & Fully Featured
- **What it does:** Multi-agent AI system with cost optimization (50-90% savings!)
- **Main features:** 30 tools, vector search, knowledge base, prompt caching, settings presets
- **Code:** ~16,600 lines across main.py, core/, tools/, ui/
- **Latest:** Phase 2A Settings Presets (Jan 2026) - One-click preset switching + custom presets

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

# 2. Quick health check (should show 30 tools)
python -c "from tools import ALL_TOOLS; print(f'{len(ALL_TOOLS)} tools loaded')"

# 3. Start application
streamlit run main.py

# 4. Open browser → http://localhost:8501
```

---

## 📊 Current Status at a Glance

```
✅ Core System:        100% Complete
✅ Tool System:        100% Complete (30 tools)
✅ Cost Optimization:  100% Complete (50-90% savings)
✅ Context Mgmt:       100% Complete
✅ Vector Search:      100% Complete
✅ Knowledge Base:     100% Complete
✅ Agent System:       100% Complete (UI polished)
✅ UI/UX:              100% Complete (Phase 1 polish)

Overall: 100% Complete - Production Ready & Fully Featured
```

### 🆕 Phase 2A: Settings Presets (January 2026)

**New features:**
- 🎨 **Settings Presets** - 5 built-in presets + custom preset support
- ⚡ **One-click switching** - Speed/Cost Saver/Deep Thinking/Research/Chat modes
- 💾 **Save custom presets** - Save your preferred settings
- 📦 **Export/Import** - Backup and share your custom presets
- 🎯 **Smart detection** - Shows "Custom (Modified)" when you tweak settings

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
# Check tool count (should be 30)
python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"

# Start app
streamlit run main.py

# View logs
tail -f app.log

# Run tests
python test_basic.py
```

See **quick-commands.md** in `.claude/skills/apex-maintainer/` for full reference.

---

## 💡 Pro Tips

1. **For AI Assistants:** Just say "check project status" - the apex-maintainer skill will auto-activate
2. **For Developers:** Read DEVELOPMENT_GUIDE.md - it has everything
3. **main.py is 4,169 lines** - Don't read it all at once, use sections
4. **Tool count is 30** - If health check shows different, something's wrong
5. **Always restart Streamlit** after tool changes

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
- ✅ Tool count = 30
- ✅ .env configured with API keys
- ✅ Streamlit starts without errors
- ✅ Sidebar shows "30 tools available"

---

## 🎉 Project Highlights

- **~16,600 lines** of production code
- **30 tools** integrated and working
- **5 built-in presets** + custom preset support
- **50-90% cost savings** via intelligent caching
- **14 phases** + Phase 2A of documented development
- **8 test suites** for validation
- **Production-ready** and fully featured
- **Phase 2A presets** complete (Jan 2026)

---

**Ready to dive in? Pick your path above and get started!** 🚀

---

**Last Updated:** 2026-01-02
**Version:** 1.0 Beta (Phase 2A Settings Presets Complete)
**Status:** Production Ready & Fully Featured
