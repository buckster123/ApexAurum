# ApexAurum Quick Commands Reference

**Quick reference sheet for common commands**
**Project Location:** `/home/llm/ApexAurum`

---

## Navigation

```bash
# Project root
cd /home/llm/ApexAurum

# Important directories
cd core/              # Core systems (28 modules)
cd core/eeg/          # Neural Resonance module
cd tools/             # Tool implementations (10 files)
cd ui/                # UI components
cd pages/             # Multi-page app (4 pages)
cd dev_log_archive_and_testfiles/  # Documentation
```

---

## Health Checks

```bash
# Full health check
cd /home/llm/ApexAurum
./venv/bin/python -c "from tools import ALL_TOOLS; print(f'✓ {len(ALL_TOOLS)} tools loaded')"
test -f .env && echo "✓ Environment configured" || echo "⚠ Missing .env"
ps aux | grep streamlit | grep -v grep && echo "✓ Streamlit running" || echo "○ Not running"
wc -l main.py

# Tool count (should be 67)
./venv/bin/python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"

# Environment check
cat .env | grep ANTHROPIC_API_KEY | head -c 40

# Imports check
./venv/bin/python -c "from core import ClaudeAPIClient; from tools import ALL_TOOLS; print('✓ Imports OK')"

# EEG module check
./venv/bin/python -c "from core.eeg import EEGConnection; from tools.eeg import eeg_connect; print('✓ EEG OK')"

# Extended thinking check
./venv/bin/python -c "from core.api_client import ClaudeAPIClient; import inspect; assert 'thinking_budget' in inspect.signature(ClaudeAPIClient.create_message).parameters; print('✓ Extended Thinking OK')"
```

---

## Application Control

```bash
# Activate virtual environment
source venv/bin/activate

# Start Streamlit
streamlit run main.py

# Start with specific port
streamlit run main.py --server.port 8502

# Stop Streamlit
pkill -f streamlit

# Check if running
ps aux | grep streamlit | grep -v grep

# View running processes
ps aux | grep python
```

---

## Installation Options

```bash
# Option A: One-click install
./install.sh
./install.sh --with-sandbox  # Include Docker sandbox

# Option B: Docker
docker-compose up --build

# Option C: Manual
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ARM64 BrainFlow (for Raspberry Pi)
./setup_brainflow_arm.sh
```

---

## Testing

```bash
# Tool import test (should be 67)
./venv/bin/python -c "from tools import ALL_TOOLS; print(f'✓ {len(ALL_TOOLS)} tools')"

# Specific module tests
./venv/bin/python -c "from tools.agents import agent_spawn; print('✓ Agents OK')"
./venv/bin/python -c "from tools.music import music_generate; print('✓ Music OK')"
./venv/bin/python -c "from tools.eeg import eeg_connect; print('✓ EEG OK')"
./venv/bin/python -c "from tools.datasets import dataset_query; print('✓ Datasets OK')"

# Run test suites
./venv/bin/python dev_log_archive_and_testfiles/tests/test_basic.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_agents.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_vector_db.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase1.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase2.py
./venv/bin/python dev_log_archive_and_testfiles/tests/test_memory_phase3.py
```

---

## Neural Resonance (EEG) Testing

```bash
# Test synthetic EEG board (no hardware needed)
./venv/bin/python -c "
from tools.eeg import eeg_connect, eeg_stream_start, eeg_realtime_emotion, eeg_stream_stop, eeg_disconnect
print(eeg_connect('', 'synthetic'))
print(eeg_stream_start('Test', 'Test Track'))
import time; time.sleep(1)
print(eeg_realtime_emotion())
print(eeg_stream_stop())
print(eeg_disconnect())
"

# Test mock board (fallback when BrainFlow unavailable)
./venv/bin/python -c "
from tools.eeg import eeg_connect
print(eeg_connect('', 'mock'))
"

# Check BrainFlow availability
./venv/bin/python -c "
from core.eeg.connection import BRAINFLOW_AVAILABLE
print(f'BrainFlow available: {BRAINFLOW_AVAILABLE}')
"
```

---

## Logging

```bash
# Live log monitoring
tail -f app.log

# Recent entries
tail -100 app.log

# Search for errors
grep ERROR app.log

# Recent errors
grep ERROR app.log | tail -20

# Clear logs
> app.log
```

---

## Code Navigation

```bash
# Find function
grep -rn "def function_name" .

# Find class
grep -rn "class ClassName" .

# Find in specific directory
grep -rn "search" core/
grep -rn "search" tools/
grep -rn "search" pages/

# Count occurrences
grep -r "search" . | wc -l

# View specific line range in main.py
sed -n '1300,1400p' main.py
```

---

## File Operations

```bash
# Count lines in all code
wc -l core/*.py tools/*.py ui/*.py main.py pages/*.py

# Count Python files
find . -name "*.py" -not -path "./venv/*" | wc -l

# List large files
find . -name "*.py" -not -path "./venv/*" -exec wc -l {} + | sort -n | tail -10

# Find recent changes
find . -name "*.py" -mtime -1 -not -path "./venv/*"
```

---

## Git Operations

```bash
# Status
git status

# Diff
git diff --stat

# Add and commit
git add .
git commit -m "Description"

# Push
git push origin master

# View history
git log --oneline -10

# Recent commits
git log --oneline -5
```

---

## Database & Storage

```bash
# Check storage files
ls -lh sandbox/*.json

# View conversations (preview)
cat sandbox/conversations.json | python -m json.tool | head -50

# View agents
cat sandbox/agents.json | python -m json.tool 2>/dev/null || echo "No agents yet"

# View memory
cat sandbox/memory.json | python -m json.tool 2>/dev/null || echo "No memory yet"

# View music tasks
cat sandbox/music_tasks.json | python -m json.tool 2>/dev/null | head -50

# View EEG sessions
ls -la sandbox/eeg_sessions/ 2>/dev/null || echo "No EEG sessions yet"

# Backup storage
cp -r sandbox/ sandbox_backup_$(date +%Y%m%d)/
```

---

## Performance & Monitoring

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Monitor Python processes
ps aux | grep python

# Check port usage
lsof -i :8501

# Network connectivity test
ping -c 3 api.anthropic.com
```

---

## Quick Fixes

```bash
# Restart Streamlit (most common fix)
pkill -f streamlit && streamlit run main.py

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Full reset
pkill -f streamlit
rm -rf __pycache__ */__pycache__
source venv/bin/activate
streamlit run main.py
```

---

## Documentation

```bash
# View docs in terminal
cat CLAUDE.md | head -200
cat PROJECT_STATUS.md
cat DEVELOPMENT_GUIDE.md
cat README.md

# Search documentation
grep -r "search term" dev_log_archive_and_testfiles/

# List all phase docs
ls -1 dev_log_archive_and_testfiles/PHASE*.md

# List all test files
ls -1 dev_log_archive_and_testfiles/tests/test_*.py
```

---

## One-Liners

```bash
# Complete health check
cd /home/llm/ApexAurum && ./venv/bin/python -c "from tools import ALL_TOOLS; print(f'{len(ALL_TOOLS)} tools')" && test -f .env && echo "✓ Ready" || echo "⚠ Issues"

# Quick restart
pkill streamlit; sleep 1; source venv/bin/activate && streamlit run main.py &

# Count all Python lines
find . -name "*.py" -not -path "./venv/*" -exec wc -l {} + | tail -1

# Check all imports
./venv/bin/python -c "from core import *; from tools import *; print('✓ All imports OK')"

# Full status
echo "Tools:" && ./venv/bin/python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))" && echo "Lines:" && wc -l main.py | awk '{print $1}' && echo "Env:" && test -f .env && echo "OK"

# Verify Extended Thinking ready
./venv/bin/python -c "from core.streaming import StreamEvent; assert 'thinking_delta' in StreamEvent.__doc__; print('✓ Extended Thinking ready')"

# Verify Neural Resonance ready
./venv/bin/python -c "from tools.eeg import EEG_TOOL_SCHEMAS; print(f'✓ {len(EEG_TOOL_SCHEMAS)} EEG tools ready')"
```

---

## Emergency Commands

```bash
# Kill all Python processes (DANGER!)
pkill -9 python

# Kill all Streamlit processes
pkill -9 streamlit

# Force stop on specific port
kill -9 $(lsof -t -i:8501) 2>/dev/null

# Clear all cache and restart
rm -rf __pycache__ */__pycache__ && pkill streamlit && source venv/bin/activate && streamlit run main.py

# Backup everything before major changes
tar -czf apex_backup_$(date +%Y%m%d_%H%M%S).tar.gz . --exclude=venv --exclude=__pycache__ --exclude=sandbox
```

---

## URL Quick Access

```bash
# Show URL
echo "App URL: http://localhost:8501"

# Check if port accessible
curl -I http://localhost:8501 2>/dev/null && echo "✓ Accessible" || echo "⚠ Not accessible"
```

---

## Tool Categories Quick Check

```bash
# Check each category
./venv/bin/python -c "
from tools import ALL_TOOLS
categories = {
    'utilities': ['get_current_time', 'calculator', 'session_info'],
    'filesystem': ['fs_read_file', 'fs_write_file', 'fs_edit'],
    'sandbox': ['execute_python', 'execute_python_sandbox'],
    'memory': ['memory_store', 'memory_retrieve'],
    'agents': ['agent_spawn', 'socratic_council'],
    'vector': ['vector_search', 'vector_add_knowledge'],
    'music': ['midi_create', 'music_compose', 'music_generate'],
    'datasets': ['dataset_list', 'dataset_query'],
    'eeg': ['eeg_connect', 'eeg_stream_start', 'eeg_realtime_emotion'],
    'suno_compiler': ['suno_prompt_build', 'suno_prompt_preset_load'],
    'audio_editor': ['audio_trim', 'audio_fade', 'audio_normalize'],
}
for cat, tools in categories.items():
    found = sum(1 for t in tools if t in ALL_TOOLS)
    print(f'{cat}: {found}/{len(tools)} ✓' if found == len(tools) else f'{cat}: {found}/{len(tools)} ⚠')
print(f'Total: {len(ALL_TOOLS)} tools')
"
```

---

## Suno Prompt Compiler

```bash
# Test compiler
./venv/bin/python -c "
from tools.suno_compiler import suno_prompt_build
result = suno_prompt_build(
    intent='mystical bell chime',
    mood='mystical',
    purpose='sfx',
    genre='ambient chime crystalline'
)
print(result['display'])
"

# List presets
./venv/bin/python -c "
from tools.suno_compiler import suno_prompt_preset_list
print(suno_prompt_preset_list())
"

# Generate from preset
./venv/bin/python -c "
from tools.suno_compiler import suno_prompt_preset_load
from tools.music import music_generate
preset = suno_prompt_preset_load('village_tool_chime')
print(preset['music_generate_args'])
# Uncomment to generate:
# result = music_generate(**preset['music_generate_args'], blocking=True)
"
```

---

## Audio Editor

```bash
# Get audio info
./venv/bin/python -c "
from tools.audio_editor import audio_info
print(audio_info('sandbox/music/Village Tool Chime_v1_704b0b98.mp3'))
"

# Trim to 5 seconds
./venv/bin/python -c "
from tools.audio_editor import audio_trim
result = audio_trim('sandbox/music/Village Tool Chime_v1_704b0b98.mp3', start=0, end=5)
print(result)
"

# Full SFX pipeline: trim → fade → normalize
./venv/bin/python -c "
from tools.audio_editor import audio_trim, audio_fade, audio_normalize
r = audio_trim('sandbox/music/Village Tool Chime_v1_704b0b98.mp3', start=0, end=5)
r = audio_fade(r['output_file'], fade_in_ms=100, fade_out_ms=500)
r = audio_normalize(r['output_file'], target_dbfs=-14)
print(f'Final SFX: {r[\"output_file\"]}')
"

# List audio files
./venv/bin/python -c "
from tools.audio_editor import audio_list_files
result = audio_list_files()
for f in result['files'][:10]:
    print(f'{f[\"name\"]} ({f[\"size_mb\"]}MB)')
"

# Run Audio Editor UI
streamlit run pages/audio_editor.py --server.port 8503
```

---

**Last Updated:** 2026-01-22
**Tool Count:** 81
