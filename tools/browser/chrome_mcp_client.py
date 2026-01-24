"""
Chrome DevTools MCP Client
==========================
Manages connection to chrome-devtools-mcp server via stdio/subprocess.
Uses JSON-RPC 2.0 over stdio (MCP protocol).

Requirements:
- Node.js v20.19+
- npm
- Chrome browser (installed)

Usage:
    client = ChromeMCPClient()
    await client.connect()
    result = await client.call_tool("navigate_page", {"url": "https://example.com"})
    await client.disconnect()
"""

import asyncio
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class MCPConfig:
    """Configuration for Chrome DevTools MCP server"""
    command: str = "npx"
    args: List[str] = field(default_factory=list)
    headless: bool = True
    isolated: bool = True
    viewport: str = "1920x1080"
    timeout: int = 30

    def __post_init__(self):
        if not self.args:
            self.args = [
                "-y", "chrome-devtools-mcp@latest",
                f"--headless={str(self.headless).lower()}",
                f"--isolated={str(self.isolated).lower()}",
                f"--viewport={self.viewport}"
            ]


class MCPError(Exception):
    """MCP protocol error"""
    pass


class ChromeMCPClient:
    """
    Manages lifecycle and communication with chrome-devtools-mcp.
    Uses JSON-RPC 2.0 over stdio (MCP protocol).
    """

    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or MCPConfig()
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._connected = False
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None

    @property
    def connected(self) -> bool:
        return self._connected and self.process is not None

    def transport_alive(self) -> bool:
        """Check if the transport is actually alive (not just cached state)"""
        if not self._connected or self.process is None:
            return False
        # Check if process is still running
        if self.process.returncode is not None:
            logger.warning("MCP process has terminated")
            self._connected = False
            return False
        # Check if stdin is still writable
        if self.process.stdin is None or self.process.stdin.is_closing():
            logger.warning("MCP stdin is closed")
            self._connected = False
            return False
        return True

    async def reconnect(self) -> Dict[str, Any]:
        """Force reconnect - disconnect if needed, then connect fresh"""
        logger.info("Reconnecting to MCP server...")
        await self.disconnect()
        return await self.connect()

    async def connect(self) -> Dict[str, Any]:
        """
        Start MCP server subprocess and establish connection.

        Returns:
            Server capabilities and info
        """
        if self._connected:
            return {"success": True, "message": "Already connected"}

        # Check if npx is available
        if not shutil.which("npx"):
            return {
                "success": False,
                "error": "npx not found. Please install Node.js v20.19+"
            }

        try:
            # Start the MCP server process
            cmd = [self.config.command] + self.config.args
            logger.info(f"Starting MCP server: {' '.join(cmd)}")

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Start response reader task
            self._reader_task = asyncio.create_task(self._read_responses())

            # Send initialize request (MCP protocol)
            init_result = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "ApexAurum",
                    "version": "1.0.0"
                }
            })

            if init_result.get("error"):
                raise MCPError(f"Initialize failed: {init_result['error']}")

            # Send initialized notification
            await self._send_notification("notifications/initialized", {})

            self._connected = True
            logger.info("MCP connection established")

            return {
                "success": True,
                "server_info": init_result.get("result", {}),
                "config": {
                    "headless": self.config.headless,
                    "isolated": self.config.isolated,
                    "viewport": self.config.viewport
                }
            }

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.disconnect()
            return {"success": False, "error": str(e)}

    async def disconnect(self) -> Dict[str, Any]:
        """Gracefully shutdown MCP server"""
        try:
            if self._reader_task:
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass
                self._reader_task = None

            if self.process:
                # Try graceful shutdown first
                try:
                    self.process.stdin.close()
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except Exception:
                    self.process.kill()

                self.process = None

            self._connected = False
            self._pending_requests.clear()
            logger.info("MCP connection closed")
            return {"success": True}

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self._connected = False
            self.process = None
            return {"success": False, "error": str(e)}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None, auto_reconnect: bool = True) -> Dict[str, Any]:
        """
        Call an MCP tool and return result.

        Args:
            tool_name: Tool name (e.g., "navigate_page", "click", "take_screenshot")
            arguments: Tool-specific arguments
            auto_reconnect: If True, reconnect if transport is dead (Streamlit fix)

        Returns:
            Tool result dict with success/error and data
        """
        # Check if we need to reconnect (Streamlit transport fix)
        if not self.transport_alive():
            if auto_reconnect:
                logger.info(f"Transport dead before {tool_name}, auto-reconnecting...")
                reconnect_result = await self.reconnect()
                if not reconnect_result.get("success"):
                    return {"success": False, "error": f"Auto-reconnect failed: {reconnect_result.get('error')}"}
            else:
                return {"success": False, "error": "Not connected. Call connect() first."}

        try:
            result = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments or {}
            })

            if result.get("error"):
                return {
                    "success": False,
                    "error": result["error"].get("message", str(result["error"]))
                }

            # Extract content from MCP response format
            content = result.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                # MCP returns content as array of content blocks
                text_content = []
                for block in content:
                    if block.get("type") == "text":
                        text_content.append(block.get("text", ""))
                    elif block.get("type") == "image":
                        return {
                            "success": True,
                            "type": "image",
                            "data": block.get("data"),
                            "mimeType": block.get("mimeType")
                        }

                # Try to parse as JSON if it looks like JSON
                if text_content:
                    text = "\n".join(text_content)
                    try:
                        return {"success": True, "data": json.loads(text)}
                    except json.JSONDecodeError:
                        return {"success": True, "data": text}

            return {"success": True, "data": result.get("result")}

        except asyncio.TimeoutError:
            return {"success": False, "error": f"Tool call timed out after {self.config.timeout}s"}
        except Exception as e:
            logger.error(f"Tool call error: {e}")
            return {"success": False, "error": str(e)}

    async def list_tools(self) -> Dict[str, Any]:
        """Get available tools from MCP server"""
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        try:
            result = await self._send_request("tools/list", {})
            if result.get("error"):
                return {"success": False, "error": str(result["error"])}

            tools = result.get("result", {}).get("tools", [])
            return {
                "success": True,
                "tools": tools,
                "count": len(tools)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request and wait for response"""
        if not self.process or not self.process.stdin:
            raise MCPError("Process not running")

        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            # Send request
            message = json.dumps(request) + "\n"
            self.process.stdin.write(message.encode())
            await self.process.stdin.drain()

            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=self.config.timeout)
            return result

        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            raise MCPError(f"Request failed: {e}")

    async def _send_notification(self, method: str, params: Dict[str, Any]):
        """Send JSON-RPC notification (no response expected)"""
        if not self.process or not self.process.stdin:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }

        message = json.dumps(notification) + "\n"
        self.process.stdin.write(message.encode())
        await self.process.stdin.drain()

    async def _read_responses(self):
        """Background task to read responses from MCP server"""
        try:
            while self.process and self.process.stdout:
                line = await self.process.stdout.readline()
                if not line:
                    break

                try:
                    response = json.loads(line.decode().strip())

                    # Handle response to our request
                    if "id" in response:
                        request_id = response["id"]
                        if request_id in self._pending_requests:
                            future = self._pending_requests.pop(request_id)
                            if not future.done():
                                future.set_result(response)

                    # Handle server notifications (log them)
                    elif "method" in response:
                        logger.debug(f"MCP notification: {response['method']}")

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse MCP response: {e}")
                except Exception as e:
                    logger.error(f"Error processing MCP response: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Response reader error: {e}")
            self._connected = False

    def _next_request_id(self) -> int:
        """Generate next request ID"""
        self._request_id += 1
        return self._request_id


# Singleton client instance
_client: Optional[ChromeMCPClient] = None


async def get_client() -> ChromeMCPClient:
    """Get or create MCP client singleton"""
    global _client
    if _client is None:
        _client = ChromeMCPClient()
    return _client


async def ensure_connected(
    headless: bool = True,
    isolated: bool = True,
    viewport: str = "1920x1080"
) -> Dict[str, Any]:
    """Ensure client is connected with given config (checks actual transport, not just flag)"""
    global _client

    # Check if we need to create or reconnect
    if _client is None:
        config = MCPConfig(headless=headless, isolated=isolated, viewport=viewport)
        _client = ChromeMCPClient(config)
        return await _client.connect()

    # Check if transport is actually alive (Streamlit fix)
    if not _client.transport_alive():
        logger.info("Transport dead in ensure_connected, reconnecting...")
        return await _client.reconnect()

    return {"success": True, "message": "Already connected"}
