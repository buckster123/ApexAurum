"""
Browser Tool Definitions for ApexAurum
======================================
Wraps Chrome DevTools MCP tools as ApexAurum-native tools.

Provides 26 browser automation tools:
- Navigation (6): navigate, new_tab, close_tab, list_tabs, select_tab, wait_for
- Input (8): click, fill, fill_form, hover, press_key, drag, upload_file, handle_dialog
- Inspection (5): screenshot, snapshot, evaluate, console_messages, get_console_message
- Network (2): network_requests, network_request
- Performance (3): perf_start, perf_stop, perf_analyze
- Emulation (2): emulate, resize

All tools are async and return Dict[str, Any] with success/error status.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List

from .chrome_mcp_client import get_client, ensure_connected, ChromeMCPClient

logger = logging.getLogger(__name__)


# ============================================================
# LIFECYCLE TOOLS
# ============================================================

async def browser_connect(
    headless: bool = True,
    isolated: bool = True,
    viewport: str = "1920x1080"
) -> Dict[str, Any]:
    """
    Initialize browser connection with config.

    Args:
        headless: Run without visible UI (default True)
        isolated: Use temp profile, auto-cleanup (default True)
        viewport: Initial viewport size "WIDTHxHEIGHT"

    Returns:
        {"success": bool, "config": {...}, "server_info": {...}}
    """
    return await ensure_connected(headless=headless, isolated=isolated, viewport=viewport)


async def browser_disconnect() -> Dict[str, Any]:
    """
    Disconnect and cleanup browser.

    Returns:
        {"success": bool}
    """
    client = await get_client()
    return await client.disconnect()


# ============================================================
# NAVIGATION TOOLS
# ============================================================

async def browser_navigate(url: str) -> Dict[str, Any]:
    """
    Navigate browser to URL.

    Args:
        url: Target URL (https://...)

    Returns:
        {"success": bool, "data": {"pageId": str, "title": str, "url": str}}
    """
    client = await get_client()
    if not client.connected:
        conn_result = await client.connect()
        if not conn_result.get("success"):
            return conn_result

    return await client.call_tool("navigate_page", {"url": url})


async def browser_new_tab(url: Optional[str] = None) -> Dict[str, Any]:
    """
    Open new browser tab, optionally navigate to URL.

    Args:
        url: Optional URL to open in new tab

    Returns:
        {"success": bool, "data": {"pageId": str}}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected. Call browser_connect() first."}

    args = {"url": url} if url else {}
    return await client.call_tool("new_page", args)


async def browser_close_tab(page_id: str) -> Dict[str, Any]:
    """
    Close a browser tab by ID.

    Args:
        page_id: Page/tab ID to close

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("close_page", {"pageId": page_id})


async def browser_list_tabs() -> Dict[str, Any]:
    """
    List all open browser tabs.

    Returns:
        {"success": bool, "data": [{"pageId": str, "url": str, "title": str}, ...]}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("list_pages", {})


async def browser_select_tab(page_id: str) -> Dict[str, Any]:
    """
    Switch to a specific browser tab.

    Args:
        page_id: Page/tab ID to activate

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("select_page", {"pageId": page_id})


async def browser_wait_for(
    selector: Optional[str] = None,
    timeout: int = 30000,
    state: str = "visible"
) -> Dict[str, Any]:
    """
    Wait for a condition before proceeding.

    Args:
        selector: CSS selector to wait for
        timeout: Max wait time in milliseconds
        state: "visible", "hidden", "attached", "detached"

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    args = {"timeout": timeout, "state": state}
    if selector:
        args["selector"] = selector

    return await client.call_tool("wait_for", args)


# ============================================================
# INPUT TOOLS
# ============================================================

async def browser_click(selector: str) -> Dict[str, Any]:
    """
    Click an element by CSS selector.

    Args:
        selector: CSS selector (e.g., "button.submit", "#login-btn")

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("click", {"selector": selector})


async def browser_fill(selector: str, value: str) -> Dict[str, Any]:
    """
    Fill an input field with text.

    Args:
        selector: CSS selector for input element
        value: Text to fill

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("fill", {"selector": selector, "value": value})


async def browser_fill_form(fields: Dict[str, str]) -> Dict[str, Any]:
    """
    Fill multiple form fields at once.

    Args:
        fields: {"selector": "value", ...}

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("fill_form", {"fields": fields})


async def browser_press_key(key: str) -> Dict[str, Any]:
    """
    Press a keyboard key.

    Args:
        key: Key to press (e.g., "Enter", "Tab", "Escape", "ArrowDown")

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("press_key", {"key": key})


async def browser_hover(selector: str) -> Dict[str, Any]:
    """
    Hover over an element.

    Args:
        selector: CSS selector for element

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("hover", {"selector": selector})


async def browser_drag(
    source_selector: str,
    target_selector: str
) -> Dict[str, Any]:
    """
    Drag an element to another element.

    Args:
        source_selector: CSS selector for element to drag
        target_selector: CSS selector for drop target

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("drag", {
        "sourceSelector": source_selector,
        "targetSelector": target_selector
    })


async def browser_upload_file(selector: str, file_path: str) -> Dict[str, Any]:
    """
    Upload a file to a file input element.

    Args:
        selector: CSS selector for file input
        file_path: Path to file to upload

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("upload_file", {
        "selector": selector,
        "filePath": file_path
    })


async def browser_handle_dialog(action: str = "accept", prompt_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle browser dialogs (alert, confirm, prompt).

    Args:
        action: "accept" or "dismiss"
        prompt_text: Text to enter for prompt dialogs

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    args = {"action": action}
    if prompt_text:
        args["promptText"] = prompt_text

    return await client.call_tool("handle_dialog", args)


# ============================================================
# INSPECTION TOOLS
# ============================================================

async def browser_screenshot(
    full_page: bool = False,
    selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Take a screenshot.

    Args:
        full_page: Capture entire scrollable page
        selector: Capture specific element only

    Returns:
        {"success": bool, "type": "image", "data": base64, "mimeType": str}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    args = {"fullPage": full_page}
    if selector:
        args["selector"] = selector

    return await client.call_tool("take_screenshot", args)


async def browser_snapshot() -> Dict[str, Any]:
    """
    Take a DOM snapshot (accessibility tree).

    Returns:
        {"success": bool, "data": str} - Accessibility tree representation
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("take_snapshot", {})


async def browser_evaluate(script: str) -> Dict[str, Any]:
    """
    Execute JavaScript in browser context.

    Args:
        script: JavaScript code to execute

    Returns:
        {"success": bool, "data": Any} - Script return value
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("evaluate_script", {"script": script})


async def browser_console_messages() -> Dict[str, Any]:
    """
    Get all console messages.

    Returns:
        {"success": bool, "data": [{"level": str, "text": str, ...}, ...]}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("list_console_messages", {})


async def browser_get_console_message(message_id: str) -> Dict[str, Any]:
    """
    Get details of a specific console message.

    Args:
        message_id: Console message ID

    Returns:
        {"success": bool, "data": {"level": str, "text": str, ...}}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("get_console_message", {"messageId": message_id})


# ============================================================
# NETWORK TOOLS
# ============================================================

async def browser_network_requests() -> Dict[str, Any]:
    """
    List all network requests made by the page.

    Returns:
        {"success": bool, "data": [{"requestId": str, "url": str, "method": str, ...}, ...]}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("list_network_requests", {})


async def browser_network_request(request_id: str) -> Dict[str, Any]:
    """
    Get details of a specific network request.

    Args:
        request_id: Network request ID

    Returns:
        {"success": bool, "data": {"url": str, "status": int, "headers": {...}, ...}}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("get_network_request", {"requestId": request_id})


# ============================================================
# PERFORMANCE TOOLS
# ============================================================

async def browser_perf_start() -> Dict[str, Any]:
    """
    Start performance trace recording.

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("performance_start_trace", {})


async def browser_perf_stop() -> Dict[str, Any]:
    """
    Stop performance trace and get data.

    Returns:
        {"success": bool, "data": {...trace data...}}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("performance_stop_trace", {})


async def browser_perf_analyze(insight_type: str = "all") -> Dict[str, Any]:
    """
    Analyze performance and get actionable insights.

    Args:
        insight_type: "all", "lcp", "cls", "inp", "resources"

    Returns:
        {"success": bool, "data": {"lcp": {...}, "cls": {...}, ...}}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("performance_analyze_insight", {"type": insight_type})


# ============================================================
# EMULATION TOOLS
# ============================================================

async def browser_emulate(device: str) -> Dict[str, Any]:
    """
    Emulate a device.

    Args:
        device: Device name (e.g., "iPhone 14", "Pixel 7", "iPad Pro")

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("emulate", {"device": device})


async def browser_resize(width: int, height: int) -> Dict[str, Any]:
    """
    Resize browser viewport.

    Args:
        width: Viewport width in pixels
        height: Viewport height in pixels

    Returns:
        {"success": bool}
    """
    client = await get_client()
    if not client.connected:
        return {"success": False, "error": "Not connected"}

    return await client.call_tool("resize_page", {"width": width, "height": height})


# ============================================================
# TOOL SCHEMAS (for Claude tool calling)
# ============================================================

BROWSER_TOOL_SCHEMAS = {
    # Lifecycle
    "browser_connect": {
        "name": "browser_connect",
        "description": """Initialize browser connection for web automation.

Use this first before any other browser tools. Starts a Chrome instance
controlled via Chrome DevTools Protocol.

Args:
- headless: Run without visible UI (default true, set false for debugging)
- isolated: Use temp profile with auto-cleanup (default true)
- viewport: Initial size "WIDTHxHEIGHT" (default "1920x1080")""",
        "input_schema": {
            "type": "object",
            "properties": {
                "headless": {"type": "boolean", "default": True},
                "isolated": {"type": "boolean", "default": True},
                "viewport": {"type": "string", "default": "1920x1080"}
            }
        }
    },
    "browser_disconnect": {
        "name": "browser_disconnect",
        "description": "Disconnect and cleanup browser. Call when done with browser automation.",
        "input_schema": {"type": "object", "properties": {}}
    },

    # Navigation
    "browser_navigate": {
        "name": "browser_navigate",
        "description": """Navigate browser to a URL.

Auto-connects if not already connected. Use for:
- Loading web pages for scraping
- Starting automated workflows
- Testing websites""",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL including https://"}
            },
            "required": ["url"]
        }
    },
    "browser_new_tab": {
        "name": "browser_new_tab",
        "description": "Open new browser tab, optionally navigate to URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Optional URL to open"}
            }
        }
    },
    "browser_close_tab": {
        "name": "browser_close_tab",
        "description": "Close a browser tab by its page ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Page ID from browser_list_tabs"}
            },
            "required": ["page_id"]
        }
    },
    "browser_list_tabs": {
        "name": "browser_list_tabs",
        "description": "List all open browser tabs with their IDs, URLs, and titles.",
        "input_schema": {"type": "object", "properties": {}}
    },
    "browser_select_tab": {
        "name": "browser_select_tab",
        "description": "Switch to a specific browser tab.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Page ID to activate"}
            },
            "required": ["page_id"]
        }
    },
    "browser_wait_for": {
        "name": "browser_wait_for",
        "description": """Wait for an element or condition.

Use after navigation or interactions to ensure page is ready.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to wait for"},
                "timeout": {"type": "integer", "default": 30000, "description": "Max wait ms"},
                "state": {
                    "type": "string",
                    "enum": ["visible", "hidden", "attached", "detached"],
                    "default": "visible"
                }
            }
        }
    },

    # Input
    "browser_click": {
        "name": "browser_click",
        "description": """Click an element by CSS selector.

Examples: "#submit-btn", "button.primary", "[data-testid='login']" """,
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector"}
            },
            "required": ["selector"]
        }
    },
    "browser_fill": {
        "name": "browser_fill",
        "description": "Fill an input field with text. Clears existing content first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for input"},
                "value": {"type": "string", "description": "Text to enter"}
            },
            "required": ["selector", "value"]
        }
    },
    "browser_fill_form": {
        "name": "browser_fill_form",
        "description": "Fill multiple form fields at once. More efficient than multiple fill calls.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "description": "Map of selector -> value",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["fields"]
        }
    },
    "browser_press_key": {
        "name": "browser_press_key",
        "description": "Press a keyboard key. Use for Enter, Tab, Escape, arrows, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name (Enter, Tab, Escape, ArrowDown, etc.)"}
            },
            "required": ["key"]
        }
    },
    "browser_hover": {
        "name": "browser_hover",
        "description": "Hover over an element. Useful for dropdown menus or tooltips.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector"}
            },
            "required": ["selector"]
        }
    },
    "browser_drag": {
        "name": "browser_drag",
        "description": "Drag an element to another element (drag and drop).",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_selector": {"type": "string", "description": "Element to drag"},
                "target_selector": {"type": "string", "description": "Drop target"}
            },
            "required": ["source_selector", "target_selector"]
        }
    },
    "browser_upload_file": {
        "name": "browser_upload_file",
        "description": "Upload a file to a file input element.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "File input selector"},
                "file_path": {"type": "string", "description": "Path to file"}
            },
            "required": ["selector", "file_path"]
        }
    },
    "browser_handle_dialog": {
        "name": "browser_handle_dialog",
        "description": "Handle browser dialogs (alert, confirm, prompt).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["accept", "dismiss"], "default": "accept"},
                "prompt_text": {"type": "string", "description": "Text for prompt dialogs"}
            }
        }
    },

    # Inspection
    "browser_screenshot": {
        "name": "browser_screenshot",
        "description": """Take a screenshot of the page or specific element.

Returns base64-encoded image data.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "full_page": {"type": "boolean", "default": False, "description": "Capture full scrollable page"},
                "selector": {"type": "string", "description": "CSS selector to capture specific element"}
            }
        }
    },
    "browser_snapshot": {
        "name": "browser_snapshot",
        "description": "Take a DOM snapshot (accessibility tree). Useful for understanding page structure.",
        "input_schema": {"type": "object", "properties": {}}
    },
    "browser_evaluate": {
        "name": "browser_evaluate",
        "description": """Execute JavaScript in browser context.

Can access DOM, window, document, etc. Returns the script's return value.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "JavaScript code to execute"}
            },
            "required": ["script"]
        }
    },
    "browser_console_messages": {
        "name": "browser_console_messages",
        "description": "Get all console messages (logs, warnings, errors).",
        "input_schema": {"type": "object", "properties": {}}
    },
    "browser_get_console_message": {
        "name": "browser_get_console_message",
        "description": "Get details of a specific console message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "Console message ID"}
            },
            "required": ["message_id"]
        }
    },

    # Network
    "browser_network_requests": {
        "name": "browser_network_requests",
        "description": "List all network requests made by the page. Useful for debugging or scraping.",
        "input_schema": {"type": "object", "properties": {}}
    },
    "browser_network_request": {
        "name": "browser_network_request",
        "description": "Get details of a specific network request including headers and response.",
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string", "description": "Request ID from browser_network_requests"}
            },
            "required": ["request_id"]
        }
    },

    # Performance
    "browser_perf_start": {
        "name": "browser_perf_start",
        "description": "Start performance trace recording. Call before navigating to measure page load.",
        "input_schema": {"type": "object", "properties": {}}
    },
    "browser_perf_stop": {
        "name": "browser_perf_stop",
        "description": "Stop performance trace and get raw trace data.",
        "input_schema": {"type": "object", "properties": {}}
    },
    "browser_perf_analyze": {
        "name": "browser_perf_analyze",
        "description": """Analyze performance and get actionable insights.

Returns Core Web Vitals (LCP, CLS, INP) and recommendations.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "insight_type": {
                    "type": "string",
                    "enum": ["all", "lcp", "cls", "inp", "resources"],
                    "default": "all"
                }
            }
        }
    },

    # Emulation
    "browser_emulate": {
        "name": "browser_emulate",
        "description": """Emulate a device (viewport, user agent, touch).

Devices: "iPhone 14", "iPhone 14 Pro Max", "Pixel 7", "iPad Pro", etc.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device name"}
            },
            "required": ["device"]
        }
    },
    "browser_resize": {
        "name": "browser_resize",
        "description": "Resize browser viewport to specific dimensions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "width": {"type": "integer", "description": "Width in pixels"},
                "height": {"type": "integer", "description": "Height in pixels"}
            },
            "required": ["width", "height"]
        }
    },
}


# Synchronous wrappers for non-async contexts
def _run_async(coro):
    """Run async function in sync context"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# Create sync versions of all tools for compatibility
def browser_connect_sync(**kwargs):
    return _run_async(browser_connect(**kwargs))

def browser_disconnect_sync():
    return _run_async(browser_disconnect())

def browser_navigate_sync(url: str):
    return _run_async(browser_navigate(url))

def browser_click_sync(selector: str):
    return _run_async(browser_click(selector))

def browser_fill_sync(selector: str, value: str):
    return _run_async(browser_fill(selector, value))

def browser_screenshot_sync(**kwargs):
    return _run_async(browser_screenshot(**kwargs))
