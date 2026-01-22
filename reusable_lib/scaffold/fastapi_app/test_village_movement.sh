#!/bin/bash
# Village GUI Movement Test Script
# Run this while watching http://localhost:8765/village/

API="http://localhost:8765/api/tools/execute"

echo "🏘️ Village GUI Movement Test"
echo "Watch the browser at http://localhost:8765/village/"
echo ""

# 1. Memory Garden (green - top)
echo "1️⃣  Moving to MEMORY GARDEN (memory_list)..."
curl -s -X POST "$API" -H "Content-Type: application/json" \
  -d '{"tool": "memory_list", "arguments": {}}' | python3 -c "import sys,json; print(f'   Result: {json.load(sys.stdin)[\"result\"]}')"
sleep 3

# 2. File Shed (gold - right)
echo "2️⃣  Moving to FILE SHED (fs_list_files)..."
curl -s -X POST "$API" -H "Content-Type: application/json" \
  -d '{"tool": "fs_list_files", "arguments": {"path": "."}}' | python3 -c "import sys,json; print(f'   Result: {json.load(sys.stdin)[\"result\"]}')"
sleep 3

# 3. Workshop (coral - bottom)
echo "3️⃣  Moving to WORKSHOP (execute_python)..."
curl -s -X POST "$API" -H "Content-Type: application/json" \
  -d '{"tool": "execute_python", "arguments": {"code": "print(\"Hello from Workshop!\")"}}' | python3 -c "import sys,json; print(f'   Result: {json.load(sys.stdin)[\"result\"]}')"
sleep 3

# 4. Bridge Portal (purple - top right)
echo "4️⃣  Moving to BRIDGE PORTAL (agent_list)..."
curl -s -X POST "$API" -H "Content-Type: application/json" \
  -d '{"tool": "agent_list", "arguments": {}}' | python3 -c "import sys,json; print(f'   Result: {json.load(sys.stdin)[\"result\"]}')"
sleep 3

# 5. Memory Garden again
echo "5️⃣  Moving to MEMORY GARDEN (memory_store)..."
curl -s -X POST "$API" -H "Content-Type: application/json" \
  -d '{"tool": "memory_store", "arguments": {"key": "village_test", "value": "Agent toured the village!"}}' | python3 -c "import sys,json; print(f'   Result: {json.load(sys.stdin)[\"result\"]}')"
sleep 3

# 6. Village Square (utility - center)
echo "6️⃣  Moving to VILLAGE SQUARE (get_current_time)..."
curl -s -X POST "$API" -H "Content-Type: application/json" \
  -d '{"tool": "get_current_time", "arguments": {"format": "human"}}' | python3 -c "import sys,json; print(f'   Result: {json.load(sys.stdin)[\"result\"]}')"

echo ""
echo "✅ Tour complete! CLAUDE visited all zones."
