# Chrome DevTools MCP Integration - Implementation Outline

**For: Claude Code (CC)**
**From: AZOTH + André**
**Date: 2025-01-15**

---

## 🎯 Goal

Add Chrome DevTools MCP as a tool provider in our architecture, giving AZOTH (and all agents) the power to:
- Control live browsers
- Debug, profile, screenshot
- Automate web interactions

**Source**: https://github.com/ChromeDevTools/chrome-devtools-mcp

---

## 📦 Requirements

- Node.js v20.19+
- Chrome stable
- npm

Quick test: `npx -y chrome-devtools-mcp@latest`

---

## 🏗️ Architecture

```
tools/
├── browser/
│   ├── __init__.py                # Exports all browser tools
│   ├── chrome_mcp_client.py       # MCP client wrapper (JSON-RPC over stdio)
│   ├── browser_tools.py           # Tool definitions (20+ tools)
│   └── browser_types.py           # TypedDict definitions
│
config/
└── mcp_servers.json               # MCP server configurations
```

---

## 📄 File: `tools/browser/chrome_mcp_client.py`

```python
"""
Chrome DevTools MCP Client
Manages connection to chrome-devtools-mcp server via stdio/subprocess
"""

import asyncio
import subprocess
import json
from typing import Optional, Any
from dataclasses import dataclass

@dataclass
class MCPConfig:
    command: str = "npx"
    args: list[str] = None
    headless: bool = True
    isolated: bool = True
    viewport: str = "1920x1080"
    
    def __post_init__(self):
        if self.args is None:
            self.args = [
                "-y", "chrome-devtools-mcp@latest",
                f"--headless={str(self.headless).lower()}",
                f"--isolated={str(self.isolated).lower()}",
                f"--viewport={self.viewport}"
            ]

class ChromeMCPClient:
    """
    Manages lifecycle and communication with chrome-devtools-mcp
    Uses JSON-RPC over stdio (MCP protocol)
    """
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or MCPConfig()
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._connected = False
    
    async def connect(self) -> bool:
        """Start MCP server subprocess and establish connection"""
        # TODO: Implement subprocess spawn with stdio pipes
        # TODO: Send initialize request per MCP protocol
        # TODO: Handle capabilities negotiation
        pass
    
    async def disconnect(self):
        """Gracefully shutdown MCP server"""
        # TODO: Send shutdown request
        # TODO: Terminate subprocess
        pass
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict:
        """
        Call an MCP tool and return result
        
        Args:
            tool_name: e.g., "navigate_page", "click", "take_screenshot"
            arguments: Tool-specific arguments
            
        Returns:
            Tool result dict
        """
        # TODO: Build JSON-RPC request
        # TODO: Send via stdin, read from stdout
        # TODO: Parse response, handle errors
        pass
    
    async def list_tools(self) -> list[dict]:
        """Get available tools from MCP server"""
        # TODO: Send tools/list request
        pass
    
    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
```

---

## 📄 File: `tools/browser/browser_tools.py`

```python
"""
Browser Tool Definitions for Holon
Wraps Chrome DevTools MCP tools as Holon-native tools
"""

from typing import Optional
from .chrome_mcp_client import ChromeMCPClient, MCPConfig

# Singleton client instance
_client: Optional[ChromeMCPClient] = None

async def get_client() -> ChromeMCPClient:
    """Get or create MCP client singleton"""
    global _client
    if _client is None:
        _client = ChromeMCPClient()
        await _client.connect()
    return _client

# ============================================================
# NAVIGATION TOOLS
# ============================================================

async def browser_navigate(url: str) -> dict:
    """
    Navigate browser to URL
    
    Args:
        url: Target URL (https://...)
        
    Returns:
        {"success": bool, "page_id": str, "title": str}
    """
    client = await get_client()
    return await client.call_tool("navigate_page", {"url": url})

async def browser_new_tab(url: Optional[str] = None) -> dict:
    """Open new browser tab, optionally navigate to URL"""
    client = await get_client()
    args = {"url": url} if url else {}
    return await client.call_tool("new_page", args)

async def browser_close_tab(page_id: str) -> dict:
    """Close a browser tab by ID"""
    client = await get_client()
    return await client.call_tool("close_page", {"pageId": page_id})

async def browser_list_tabs() -> dict:
    """List all open browser tabs"""
    client = await get_client()
    return await client.call_tool("list_pages", {})

# ============================================================
# INPUT TOOLS
# ============================================================

async def browser_click(selector: str) -> dict:
    """
    Click an element by CSS selector
    
    Args:
        selector: CSS selector (e.g., "button.submit", "#login-btn")
    """
    client = await get_client()
    return await client.call_tool("click", {"selector": selector})

async def browser_fill(selector: str, value: str) -> dict:
    """Fill an input field with text"""
    client = await get_client()
    return await client.call_tool("fill", {"selector": selector, "value": value})

async def browser_fill_form(fields: dict[str, str]) -> dict:
    """
    Fill multiple form fields at once
    
    Args:
        fields: {"selector": "value", ...}
    """
    client = await get_client()
    return await client.call_tool("fill_form", {"fields": fields})

async def browser_press_key(key: str) -> dict:
    """Press a keyboard key (e.g., "Enter", "Tab", "Escape")"""
    client = await get_client()
    return await client.call_tool("press_key", {"key": key})

async def browser_hover(selector: str) -> dict:
    """Hover over an element"""
    client = await get_client()
    return await client.call_tool("hover", {"selector": selector})

# ============================================================
# INSPECTION TOOLS
# ============================================================

async def browser_screenshot(
    full_page: bool = False,
    selector: Optional[str] = None
) -> dict:
    """
    Take a screenshot
    
    Args:
        full_page: Capture entire scrollable page
        selector: Capture specific element only
        
    Returns:
        {"success": bool, "path": str, "base64": str}
    """
    client = await get_client()
    args = {"fullPage": full_page}
    if selector:
        args["selector"] = selector
    return await client.call_tool("take_screenshot", args)

async def browser_snapshot() -> dict:
    """Take a DOM snapshot (accessibility tree)"""
    client = await get_client()
    return await client.call_tool("take_snapshot", {})

async def browser_evaluate(script: str) -> dict:
    """
    Execute JavaScript in browser context
    
    Args:
        script: JavaScript code to execute
        
    Returns:
        {"success": bool, "result": Any}
    """
    client = await get_client()
    return await client.call_tool("evaluate_script", {"script": script})

async def browser_console_messages() -> dict:
    """Get all console messages"""
    client = await get_client()
    return await client.call_tool("list_console_messages", {})

# ============================================================
# NETWORK TOOLS
# ============================================================

async def browser_network_requests() -> dict:
    """List all network requests made by the page"""
    client = await get_client()
    return await client.call_tool("list_network_requests", {})

async def browser_network_request(request_id: str) -> dict:
    """Get details of a specific network request"""
    client = await get_client()
    return await client.call_tool("get_network_request", {"requestId": request_id})

# ============================================================
# PERFORMANCE TOOLS
# ============================================================

async def browser_perf_start() -> dict:
    """Start performance trace recording"""
    client = await get_client()
    return await client.call_tool("performance_start_trace", {})

async def browser_perf_stop() -> dict:
    """Stop performance trace and get data"""
    client = await get_client()
    return await client.call_tool("performance_stop_trace", {})

async def browser_perf_analyze(insight_type: str = "all") -> dict:
    """
    Analyze performance and get actionable insights
    
    Args:
        insight_type: "all", "lcp", "cls", "inp", "resources"
    """
    client = await get_client()
    return await client.call_tool("performance_analyze_insight", {"type": insight_type})

# ============================================================
# EMULATION TOOLS
# ============================================================

async def browser_emulate(device: str) -> dict:
    """
    Emulate a device
    
    Args:
        device: e.g., "iPhone 14", "Pixel 7", "iPad Pro"
    """
    client = await get_client()
    return await client.call_tool("emulate", {"device": device})

async def browser_resize(width: int, height: int) -> dict:
    """Resize browser viewport"""
    client = await get_client()
    return await client.call_tool("resize_page", {"width": width, "height": height})

# ============================================================
# LIFECYCLE
# ============================================================

async def browser_connect(
    headless: bool = True,
    isolated: bool = True,
    viewport: str = "1920x1080"
) -> dict:
    """
    Initialize browser connection with config
    
    Args:
        headless: Run without visible UI
        isolated: Use temp profile (auto-cleanup)
        viewport: Initial size "WIDTHxHEIGHT"
    """
    global _client
    config = MCPConfig(headless=headless, isolated=isolated, viewport=viewport)
    _client = ChromeMCPClient(config)
    await _client.connect()
    return {"success": True, "config": config.__dict__}

async def browser_disconnect() -> dict:
    """Disconnect and cleanup browser"""
    global _client
    if _client:
        await _client.disconnect()
        _client = None
    return {"success": True}
```

---

## 📄 File: `tools/browser/browser_types.py`

```python
"""Type definitions for browser tools"""

from typing import TypedDict, Optional, Literal

class PageInfo(TypedDict):
    page_id: str
    url: str
    title: str

class ScreenshotResult(TypedDict):
    success: bool
    path: str
    base64: Optional[str]

class NetworkRequest(TypedDict):
    request_id: str
    url: str
    method: str
    status: int
    content_type: str
    size: int
    timing: dict

class PerformanceInsight(TypedDict):
    metric: str  # LCP, CLS, INP, etc.
    value: float
    rating: Literal["good", "needs-improvement", "poor"]
    recommendation: str

class ConsoleMessage(TypedDict):
    level: Literal["log", "warn", "error", "info", "debug"]
    text: str
    url: Optional[str]
    line: Optional[int]
```

---

## 📄 File: `tools/browser/__init__.py`

```python
"""
Browser Tools - Chrome DevTools MCP Integration

Provides AI agents with full browser control:
- Navigation & tab management
- Input automation (click, fill, type)
- Screenshots & DOM snapshots
- Network inspection
- Performance profiling
- Device emulation
"""

from .browser_tools import (
    # Lifecycle
    browser_connect,
    browser_disconnect,
    
    # Navigation
    browser_navigate,
    browser_new_tab,
    browser_close_tab,
    browser_list_tabs,
    
    # Input
    browser_click,
    browser_fill,
    browser_fill_form,
    browser_press_key,
    browser_hover,
    
    # Inspection
    browser_screenshot,
    browser_snapshot,
    browser_evaluate,
    browser_console_messages,
    
    # Network
    browser_network_requests,
    browser_network_request,
    
    # Performance
    browser_perf_start,
    browser_perf_stop,
    browser_perf_analyze,
    
    # Emulation
    browser_emulate,
    browser_resize,
)

__all__ = [
    "browser_connect",
    "browser_disconnect",
    "browser_navigate",
    "browser_new_tab", 
    "browser_close_tab",
    "browser_list_tabs",
    "browser_click",
    "browser_fill",
    "browser_fill_form",
    "browser_press_key",
    "browser_hover",
    "browser_screenshot",
    "browser_snapshot",
    "browser_evaluate",
    "browser_console_messages",
    "browser_network_requests",
    "browser_network_request",
    "browser_perf_start",
    "browser_perf_stop",
    "browser_perf_analyze",
    "browser_emulate",
    "browser_resize",
]
```

---

## 📄 File: `config/mcp_servers.json`

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"],
      "env": {},
      "defaults": {
        "headless": true,
        "isolated": true,
        "viewport": "1920x1080"
      }
    }
  }
}
```

---

## 📄 Tool Registration (for main tool registry)

```python
# In tools/__init__.py or wherever tools are registered

BROWSER_TOOLS = [
    {
        "name": "browser_navigate",
        "description": "Navigate browser to a URL. Use for web scraping, testing, inspection.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target URL"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page or specific element.",
        "parameters": {
            "type": "object", 
            "properties": {
                "full_page": {"type": "boolean", "default": False},
                "selector": {"type": "string", "description": "CSS selector for element"}
            }
        }
    },
    {
        "name": "browser_click",
        "description": "Click an element by CSS selector",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector"}
            },
            "required": ["selector"]
        }
    },
    # ... register all 20+ tools similarly
]
```

---

## ✅ Implementation Checklist

### 1. Core MCP Client (`chrome_mcp_client.py`)
- [ ] Subprocess management for `npx chrome-devtools-mcp`
- [ ] JSON-RPC over stdio implementation
- [ ] MCP protocol handshake (initialize, capabilities)
- [ ] Request/response handling with async
- [ ] Proper error handling and timeouts
- [ ] Reconnection logic

### 2. Tool Wrappers (`browser_tools.py`)
- [ ] All 26 tools wrapped as async functions
- [ ] Proper error handling and timeouts
- [ ] Singleton client pattern with lazy init
- [ ] Type hints for all functions

### 3. Tool Registration
- [ ] Add to main tool registry with JSON schemas
- [ ] Function dispatch mapping
- [ ] Documentation strings

### 4. Config System
- [ ] Load from `mcp_servers.json`
- [ ] Environment variable overrides
- [ ] Per-request config options

### 5. Testing
- [ ] Unit tests with mocked MCP responses
- [ ] Integration test with real browser (headless)
- [ ] CI pipeline considerations

---

## 🔗 MCP Protocol Reference

The MCP (Model Context Protocol) uses JSON-RPC 2.0 over stdio:

### Initialize Request
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "holon", "version": "1.0.0"}
  }
}
```

### Tool Call Request
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "navigate_page",
    "arguments": {"url": "https://example.com"}
  }
}
```

### List Tools Request
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/list",
  "params": {}
}
```

---

## 🎯 Available Tools from chrome-devtools-mcp (26 total)

### Input (8)
- `click` - Click elements
- `drag` - Drag and drop
- `fill` - Fill input fields
- `fill_form` - Fill entire forms
- `handle_dialog` - Handle alerts/prompts
- `hover` - Hover over elements
- `press_key` - Keyboard input
- `upload_file` - File uploads

### Navigation (6)
- `navigate_page` - Go to URLs
- `new_page` - Open new tab
- `close_page` - Close tab
- `list_pages` - List all tabs
- `select_page` - Switch tabs
- `wait_for` - Wait for conditions

### Emulation (2)
- `emulate` - Device emulation
- `resize_page` - Viewport control

### Performance (3)
- `performance_start_trace` - Begin recording
- `performance_stop_trace` - End recording
- `performance_analyze_insight` - Get insights

### Network (2)
- `list_network_requests` - See all requests
- `get_network_request` - Inspect specific request

### Debugging (5)
- `evaluate_script` - Run JavaScript
- `list_console_messages` - See console output
- `get_console_message` - Inspect specific message
- `take_screenshot` - Capture visuals
- `take_snapshot` - DOM snapshots

---

## 🚀 Usage Example (after implementation)

```python
# In agent code or tool execution

# Connect to browser
await browser_connect(headless=True)

# Navigate and interact
await browser_navigate("https://example.com")
await browser_fill("#search", "AI agents")
await browser_click("button[type=submit]")

# Wait and capture
await asyncio.sleep(2)
result = await browser_screenshot(full_page=True)
print(f"Screenshot saved: {result['path']}")

# Performance analysis
await browser_perf_start()
await browser_navigate("https://developers.chrome.com")
await browser_perf_stop()
insights = await browser_perf_analyze("all")
print(f"LCP: {insights['lcp']}")

# Cleanup
await browser_disconnect()
```

---

**Let's cook this! 🔥**

∴ AZOTH + André
