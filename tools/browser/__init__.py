"""
Browser Tools - Chrome DevTools MCP Integration
================================================

Provides AI agents with full browser control via Chrome DevTools Protocol:
- Navigation & tab management
- Input automation (click, fill, type)
- Screenshots & DOM snapshots
- Network inspection
- Performance profiling
- Device emulation

Requirements:
- Node.js v20.19+
- npm
- Chrome browser

Quick test:
    npx -y chrome-devtools-mcp@latest

Usage:
    from tools.browser import browser_navigate, browser_screenshot

    # Navigate and screenshot
    await browser_navigate("https://example.com")
    result = await browser_screenshot(full_page=True)
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
    browser_select_tab,
    browser_wait_for,

    # Input
    browser_click,
    browser_fill,
    browser_fill_form,
    browser_press_key,
    browser_hover,
    browser_drag,
    browser_upload_file,
    browser_handle_dialog,

    # Inspection
    browser_screenshot,
    browser_snapshot,
    browser_evaluate,
    browser_console_messages,
    browser_get_console_message,

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

    # Schemas
    BROWSER_TOOL_SCHEMAS,
)

__all__ = [
    # Lifecycle (2)
    "browser_connect",
    "browser_disconnect",

    # Navigation (6)
    "browser_navigate",
    "browser_new_tab",
    "browser_close_tab",
    "browser_list_tabs",
    "browser_select_tab",
    "browser_wait_for",

    # Input (8)
    "browser_click",
    "browser_fill",
    "browser_fill_form",
    "browser_press_key",
    "browser_hover",
    "browser_drag",
    "browser_upload_file",
    "browser_handle_dialog",

    # Inspection (5)
    "browser_screenshot",
    "browser_snapshot",
    "browser_evaluate",
    "browser_console_messages",
    "browser_get_console_message",

    # Network (2)
    "browser_network_requests",
    "browser_network_request",

    # Performance (3)
    "browser_perf_start",
    "browser_perf_stop",
    "browser_perf_analyze",

    # Emulation (2)
    "browser_emulate",
    "browser_resize",

    # Schemas
    "BROWSER_TOOL_SCHEMAS",
]

# Tool count: 28 (2 + 6 + 8 + 5 + 2 + 3 + 2)
