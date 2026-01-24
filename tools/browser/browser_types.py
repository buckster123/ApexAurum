"""
Type definitions for browser tools
Chrome DevTools MCP Integration
"""

from typing import TypedDict, Optional, Literal, List, Dict, Any


class PageInfo(TypedDict):
    """Information about a browser page/tab"""
    page_id: str
    url: str
    title: str


class ScreenshotResult(TypedDict):
    """Result from taking a screenshot"""
    success: bool
    path: str
    base64: Optional[str]


class NetworkRequest(TypedDict):
    """Information about a network request"""
    request_id: str
    url: str
    method: str
    status: int
    content_type: str
    size: int
    timing: Dict[str, Any]


class PerformanceInsight(TypedDict):
    """Performance analysis insight"""
    metric: str  # LCP, CLS, INP, etc.
    value: float
    rating: Literal["good", "needs-improvement", "poor"]
    recommendation: str


class ConsoleMessage(TypedDict):
    """Browser console message"""
    level: Literal["log", "warn", "error", "info", "debug"]
    text: str
    url: Optional[str]
    line: Optional[int]


class MCPToolResult(TypedDict):
    """Generic MCP tool result"""
    success: bool
    error: Optional[str]
    data: Optional[Any]
