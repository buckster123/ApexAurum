# 🌐 Browser Tools in Streamlit - Edge Case Report

**Date:** 2025-01-25
**Reporter:** AZOTH (with André)
**Environment:** Streamlit chat interface
**Status:** 🟡 Partially Working - Edge Case Found

---

## Summary

Browser tools MCP integration **connects successfully** but **transport dies between tool calls** in Streamlit's execution model.

---

## Test Results

### ✅ What Works
```
browser_connect() → SUCCESS
- MCP handshake completes
- Returns: "Connected to Chrome DevTools MCP server v0.13.0"
- Browser process spawns correctly
```

### ❌ What Fails
```
browser_navigate() → FAIL (immediately after connect)
browser_disconnect() → FAIL 
Any operation after connect → "Failed... Transport closed"
```

### 🔬 The Pattern
```
Tool Call 1: browser_connect → ✅ Connection established
[Streamlit boundary - something happens here]
Tool Call 2: browser_navigate → ❌ "Transport closed"
```

Even when called in rapid succession or in the same function block, the Unix socket transport closes between operations.

---

## Hypothesis

Streamlit's execution model conflicts with persistent WebSocket/Unix socket connections:

1. **Event Loop Isolation:** Each tool call may run in a fresh async context
2. **Rerun Architecture:** Streamlit's rerun-on-interaction might tear down connections
3. **Session State Gap:** MCP client object reports "connected" (cached state) but actual transport is dead
4. **GC/Cleanup:** Connection objects getting garbage collected between Streamlit execution frames

---

## Potential Solutions

### Option 1: Session State Persistence
```python
if 'mcp_client' not in st.session_state:
    st.session_state.mcp_client = create_persistent_client()
# Use st.session_state.mcp_client for all operations
```

### Option 2: Lazy Auto-Reconnect
```python
async def ensure_connected():
    if not transport_is_alive():  # Actually check socket, not cached state
        await reconnect()
    return client
```

### Option 3: Nested Event Loop Handling
André notes: "nested have worked on other things" - `nest_asyncio` or similar patterns that allow async operations within Streamlit's loop.

```python
import nest_asyncio
nest_asyncio.apply()

# Then run async browser ops with proper loop nesting
```

### Option 4: Connection-Per-Operation Mode
Instead of persistent connection, do atomic connect→operate→disconnect in single async block:
```python
async def browser_atomic_operation(operation, **kwargs):
    async with browser_connection() as client:
        return await client.execute(operation, **kwargs)
```

### Option 5: Background Thread with Queue
Run MCP client in dedicated thread with stable event loop, communicate via queue:
```python
# Browser thread (stable loop)
while True:
    command = command_queue.get()
    result = await execute(command)
    result_queue.put(result)

# Streamlit side
command_queue.put(('navigate', {'url': '...'}))
result = result_queue.get()
```

---

## Lab Edition Status

**Expected to work fine** - Lab Edition runs as standard Python with persistent event loop, no Streamlit rerun interference. Browser tools should be fully functional there.

---

## Reproduction Steps

1. Open Streamlit chat interface
2. Call `browser_connect` → Observe success
3. Immediately call `browser_navigate("https://example.com")` → Observe failure
4. Note error: "Transport closed" or similar

---

## Priority

🟡 **Medium** - Core async fix (commit 03140bb) is solid. This is Streamlit-specific environment issue. Browser tools will work in Lab Edition. But **Streamlit support would be very cool** for the visual feedback loop.

---

## Notes from the Trenches

The MCP server itself is fine. The async bridge fix is fine. This is purely about **connection persistence across Streamlit's unique execution boundaries**. 

The nested async pattern André mentioned has worked for other integrations - worth exploring for browser tools.

*- AZOTH & André, mapping the edges* ∴
