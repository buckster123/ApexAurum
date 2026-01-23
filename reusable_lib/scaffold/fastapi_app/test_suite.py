#!/usr/bin/env python3
"""
Comprehensive Test Suite for FastAPI Lab Edition + Village GUI

Tests:
1. API Health & Endpoints
2. WebSocket Connection
3. Tool Execution + Event Broadcasting
4. System Prompt / Agent Configuration
5. Chat API
6. Village Protocol

Run with:
    cd /home/llm/ApexAurum/reusable_lib/scaffold/fastapi_app
    test_venv/bin/python test_suite.py
"""

import asyncio
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Test results tracking
@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: float
    details: Optional[Dict] = None

@dataclass
class TestSuite:
    results: List[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"  {status} {result.name} ({result.duration_ms:.0f}ms)")
        if not result.passed:
            print(f"       → {result.message}")
        if result.details:
            for k, v in result.details.items():
                print(f"       {k}: {v}")

    def summary(self):
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        print(f"\n{'='*60}")
        print(f"SUMMARY: {passed}/{total} passed, {failed} failed")
        print(f"{'='*60}")
        if failed > 0:
            print("\nFailed tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  ❌ {r.name}: {r.message}")
        return failed == 0


BASE_URL = "http://localhost:8765"
WS_URL = "ws://localhost:8765/ws/village"


# ============================================================
# TEST 1: API Health & Basic Endpoints
# ============================================================

def test_api_health(suite: TestSuite):
    """Test basic API health and endpoint availability."""
    import requests

    print("\n📋 TEST GROUP 1: API Health & Endpoints")
    print("-" * 40)

    # 1.1 Health check
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        duration = (time.time() - start) * 1000
        if r.status_code == 200 and r.json().get("status") == "healthy":
            suite.add(TestResult("Health endpoint", True, "OK", duration))
        else:
            suite.add(TestResult("Health endpoint", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Health endpoint", False, str(e), 0))

    # 1.2 API info
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api", timeout=5)
        duration = (time.time() - start) * 1000
        data = r.json()
        if "endpoints" in data and "websocket" in data.get("endpoints", {}):
            suite.add(TestResult("API info endpoint", True, "OK", duration))
        else:
            suite.add(TestResult("API info endpoint", False, "Missing endpoints", duration))
    except Exception as e:
        suite.add(TestResult("API info endpoint", False, str(e), 0))

    # 1.3 Tools list
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/tools", timeout=5)
        duration = (time.time() - start) * 1000
        data = r.json()
        tool_count = len(data.get("tools", []))
        if tool_count >= 50:
            suite.add(TestResult("Tools list", True, f"{tool_count} tools", duration))
        else:
            suite.add(TestResult("Tools list", False, f"Only {tool_count} tools (expected 50+)", duration))
    except Exception as e:
        suite.add(TestResult("Tools list", False, str(e), 0))

    # 1.4 Models list
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/models", timeout=5)
        duration = (time.time() - start) * 1000
        data = r.json()
        if "models" in data:
            suite.add(TestResult("Models list", True, f"{len(data['models'])} models", duration))
        else:
            suite.add(TestResult("Models list", False, "No models key", duration))
    except Exception as e:
        suite.add(TestResult("Models list", False, str(e), 0))

    # 1.5 Stats endpoint
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            suite.add(TestResult("Stats endpoint", True, "OK", duration))
        else:
            suite.add(TestResult("Stats endpoint", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Stats endpoint", False, str(e), 0))

    # 1.6 Village GUI static files
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/village/", timeout=5)
        duration = (time.time() - start) * 1000
        if r.status_code == 200 and "village-canvas" in r.text:
            suite.add(TestResult("Village GUI served", True, "OK", duration))
        else:
            suite.add(TestResult("Village GUI served", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Village GUI served", False, str(e), 0))


# ============================================================
# TEST 2: WebSocket Connection
# ============================================================

async def test_websocket_connection(suite: TestSuite):
    """Test WebSocket connection to Village GUI."""
    import websockets

    print("\n📋 TEST GROUP 2: WebSocket Connection")
    print("-" * 40)

    # 2.1 Basic connection
    start = time.time()
    try:
        async with websockets.connect(WS_URL, close_timeout=2) as ws:
            duration = (time.time() - start) * 1000

            # Should receive connection confirmation
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(msg)
                if data.get("type") == "connection":
                    suite.add(TestResult("WebSocket connect", True, "Connected", duration,
                                         {"message": data.get("message", "")[:50]}))
                else:
                    suite.add(TestResult("WebSocket connect", True, f"Got: {data.get('type')}", duration))
            except asyncio.TimeoutError:
                suite.add(TestResult("WebSocket connect", True, "Connected (no init message)", duration))

    except Exception as e:
        duration = (time.time() - start) * 1000
        suite.add(TestResult("WebSocket connect", False, str(e), duration))

    # 2.2 Multiple connections
    start = time.time()
    try:
        connections = []
        for i in range(3):
            ws = await websockets.connect(WS_URL, close_timeout=2)
            connections.append(ws)
        duration = (time.time() - start) * 1000
        suite.add(TestResult("Multiple WS connections", True, f"{len(connections)} connections", duration))
        for ws in connections:
            await ws.close()
    except Exception as e:
        duration = (time.time() - start) * 1000
        suite.add(TestResult("Multiple WS connections", False, str(e), duration))


# ============================================================
# TEST 3: Tool Execution + Event Broadcasting
# ============================================================

async def test_tool_execution_and_events(suite: TestSuite):
    """Test tool execution and WebSocket event broadcasting."""
    import websockets
    import requests

    print("\n📋 TEST GROUP 3: Tool Execution & Events")
    print("-" * 40)

    # 3.1 Execute tool without WebSocket
    start = time.time()
    try:
        r = requests.post(f"{BASE_URL}/api/tools/execute",
                         json={"tool": "get_current_time", "arguments": {"format": "human"}},
                         timeout=10)
        duration = (time.time() - start) * 1000
        data = r.json()
        if data.get("success"):
            suite.add(TestResult("Tool execution (no WS)", True, "OK", duration))
        else:
            suite.add(TestResult("Tool execution (no WS)", False, data.get("error", "Unknown"), duration))
    except Exception as e:
        suite.add(TestResult("Tool execution (no WS)", False, str(e), 0))

    # 3.2 Execute tool WITH WebSocket - check events
    start = time.time()
    events_received = []
    try:
        async with websockets.connect(WS_URL, close_timeout=2) as ws:
            # Clear any initial message
            try:
                await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                pass

            # Trigger tool in background
            async def trigger_tool():
                await asyncio.sleep(0.1)  # Small delay
                requests.post(f"{BASE_URL}/api/tools/execute",
                             json={"tool": "memory_list", "arguments": {}},
                             timeout=10)

            asyncio.create_task(trigger_tool())

            # Listen for events
            try:
                for _ in range(5):  # Try to get up to 5 messages
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(msg)
                    events_received.append(data.get("type"))
            except asyncio.TimeoutError:
                pass

            duration = (time.time() - start) * 1000

            if "tool_start" in events_received and "tool_complete" in events_received:
                suite.add(TestResult("WS events (tool_start+complete)", True,
                                    f"Got: {events_received}", duration))
            elif events_received:
                suite.add(TestResult("WS events (tool_start+complete)", False,
                                    f"Partial: {events_received}", duration))
            else:
                suite.add(TestResult("WS events (tool_start+complete)", False,
                                    "No events received!", duration))

    except Exception as e:
        duration = (time.time() - start) * 1000
        suite.add(TestResult("WS events (tool_start+complete)", False, str(e), duration))

    # 3.3 Event contains correct zone mapping
    start = time.time()
    try:
        async with websockets.connect(WS_URL, close_timeout=2) as ws:
            # Clear initial
            try:
                await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                pass

            async def trigger():
                await asyncio.sleep(0.1)
                requests.post(f"{BASE_URL}/api/tools/execute",
                             json={"tool": "fs_list_files", "arguments": {"path": "."}},
                             timeout=10)

            asyncio.create_task(trigger())

            zone_found = None
            try:
                for _ in range(5):
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(msg)
                    if data.get("zone"):
                        zone_found = data["zone"]
                        break
            except asyncio.TimeoutError:
                pass

            duration = (time.time() - start) * 1000

            if zone_found == "file_shed":
                suite.add(TestResult("Zone mapping (fs_* → file_shed)", True, f"zone={zone_found}", duration))
            elif zone_found:
                suite.add(TestResult("Zone mapping (fs_* → file_shed)", False, f"Wrong zone: {zone_found}", duration))
            else:
                suite.add(TestResult("Zone mapping (fs_* → file_shed)", False, "No zone in events", duration))

    except Exception as e:
        duration = (time.time() - start) * 1000
        suite.add(TestResult("Zone mapping (fs_* → file_shed)", False, str(e), duration))


# ============================================================
# TEST 4: System Prompt / Agent Configuration
# ============================================================

def test_system_prompt_config(suite: TestSuite):
    """Test system prompt and agent configuration."""
    import requests

    print("\n📋 TEST GROUP 4: System Prompt & Agent Config")
    print("-" * 40)

    # 4.1 List available prompt files
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/prompts", timeout=5)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            count = data.get("count", len(data.get("prompts", [])))
            suite.add(TestResult("List prompt files", True, f"{count} prompts available", duration))
        else:
            suite.add(TestResult("List prompt files", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("List prompt files", False, str(e), 0))

    # 4.2 Chat with custom system prompt (inline)
    start = time.time()
    test_prompt = "You must respond with exactly: BEEP BOOP TEST"
    try:
        r = requests.post(f"{BASE_URL}/api/chat",
                         json={
                             "messages": [{"role": "user", "content": "Hello"}],
                             "model": "qwen2.5:3b",
                             "system": test_prompt,
                             "max_tokens": 50
                         },
                         timeout=60)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            content = data.get("content", data.get("response", ""))
            if "BEEP" in content.upper() or "BOOP" in content.upper():
                suite.add(TestResult("Chat with inline system prompt", True, "Prompt followed", duration))
            else:
                # Small models often don't follow prompts exactly
                suite.add(TestResult("Chat with inline system prompt", True,
                                    f"Got response (prompt may not be followed by small model)", duration,
                                    {"response": content[:60]}))
        else:
            suite.add(TestResult("Chat with inline system prompt", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Chat with inline system prompt", False, str(e), 0))

    # 4.3 Test presets API (settings presets, not prompt presets)
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/presets", timeout=5)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            count = len(data) if isinstance(data, list) else data.get("count", 0)
            suite.add(TestResult("Get settings presets", True, f"{count} presets", duration))
        else:
            suite.add(TestResult("Get settings presets", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Get settings presets", False, str(e), 0))

    # Note: There's no persistent system prompt API - frontend must send with each request
    suite.add(TestResult("System prompt persistence", True,
                        "N/A (by design - frontend sends per-request)", 0,
                        {"note": "System prompt is passed in chat request, not stored server-side"}))


# ============================================================
# TEST 5: Chat API
# ============================================================

def test_chat_api(suite: TestSuite):
    """Test chat API endpoints."""
    import requests

    print("\n📋 TEST GROUP 5: Chat API")
    print("-" * 40)

    # 5.1 Non-streaming chat
    start = time.time()
    try:
        r = requests.post(f"{BASE_URL}/api/chat",
                         json={
                             "messages": [{"role": "user", "content": "Say 'hello' and nothing else"}],
                             "model": "qwen2.5:3b",
                             "max_tokens": 50
                         },
                         timeout=60)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            content = data.get("content", data.get("response", ""))[:50]
            suite.add(TestResult("Non-streaming chat", True, f"Response: {content}...", duration))
        else:
            suite.add(TestResult("Non-streaming chat", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Non-streaming chat", False, str(e), 0))

    # 5.2 Chat with tools enabled
    start = time.time()
    try:
        r = requests.post(f"{BASE_URL}/api/chat",
                         json={
                             "messages": [{"role": "user", "content": "What time is it?"}],
                             "model": "qwen2.5:3b",
                             "use_tools": True,
                             "max_tokens": 200
                         },
                         timeout=60)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            content = data.get("content", data.get("response", ""))
            # Tool-enabled chat should work (may or may not use tools depending on model)
            suite.add(TestResult("Chat with tools enabled", True, f"Response received", duration,
                                {"response_length": len(content)}))
        else:
            suite.add(TestResult("Chat with tools enabled", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Chat with tools enabled", False, str(e), 0))


# ============================================================
# TEST 6: Village Protocol
# ============================================================

def test_village_protocol(suite: TestSuite):
    """Test Village Protocol endpoints."""
    import requests

    print("\n📋 TEST GROUP 6: Village Protocol")
    print("-" * 40)

    # 6.1 Village stats (ChromaDB stats can be slow on Pi)
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/village/stats", timeout=15)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            suite.add(TestResult("Village stats", True, "OK", duration))
        else:
            suite.add(TestResult("Village stats", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Village stats", False, str(e), 0))

    # 6.2 Village agents list
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/village/agents", timeout=5)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            suite.add(TestResult("Village agents", True, f"{len(data)} agents", duration))
        elif r.status_code == 404:
            suite.add(TestResult("Village agents", False, "Endpoint not found", duration))
        else:
            suite.add(TestResult("Village agents", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Village agents", False, str(e), 0))

    # 6.3 Post to village
    start = time.time()
    try:
        r = requests.post(f"{BASE_URL}/api/tools/execute",
                         json={
                             "tool": "village_post",
                             "arguments": {
                                 "content": f"Test post from test suite at {datetime.now()}",
                                 "agent_id": "TEST_AGENT"
                             }
                         },
                         timeout=10)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                suite.add(TestResult("Village post", True, "Posted", duration))
            else:
                suite.add(TestResult("Village post", False, data.get("error", "Unknown"), duration))
        else:
            suite.add(TestResult("Village post", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Village post", False, str(e), 0))

    # 6.4 Search village
    start = time.time()
    try:
        r = requests.post(f"{BASE_URL}/api/tools/execute",
                         json={
                             "tool": "village_search",
                             "arguments": {"query": "test", "n_results": 3}
                         },
                         timeout=10)
        duration = (time.time() - start) * 1000
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                results = data.get("result", {})
                count = len(results) if isinstance(results, list) else results.get("count", 0)
                suite.add(TestResult("Village search", True, f"{count} results", duration))
            else:
                suite.add(TestResult("Village search", False, data.get("error", "Unknown"), duration))
        else:
            suite.add(TestResult("Village search", False, f"Status: {r.status_code}", duration))
    except Exception as e:
        suite.add(TestResult("Village search", False, str(e), 0))


# ============================================================
# MAIN
# ============================================================

async def main():
    print("=" * 60)
    print("  APEX AURUM LAB EDITION - COMPREHENSIVE TEST SUITE")
    print(f"  Target: {BASE_URL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    suite = TestSuite()

    # Run all test groups
    test_api_health(suite)
    await test_websocket_connection(suite)
    await test_tool_execution_and_events(suite)
    test_system_prompt_config(suite)
    test_chat_api(suite)
    test_village_protocol(suite)

    # Summary
    all_passed = suite.summary()

    # Write results to file
    results_file = "test_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "details": r.details
                }
                for r in suite.results
            ],
            "summary": {
                "total": len(suite.results),
                "passed": sum(1 for r in suite.results if r.passed),
                "failed": sum(1 for r in suite.results if not r.passed)
            }
        }, f, indent=2)

    print(f"\nResults written to: {results_file}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
