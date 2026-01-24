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


def _detect_browser_path() -> Optional[str]:
    """Auto-detect Chrome/Chromium executable path."""
    import os
    # Check common locations in order of preference
    candidates = [
        "/usr/bin/chromium",           # Debian/Raspberry Pi
        "/usr/bin/chromium-browser",   # Ubuntu
        "/usr/bin/google-chrome",      # Google Chrome
        "/opt/google/chrome/chrome",   # Google Chrome (alt)
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Try which for common names
    for name in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
        found = shutil.which(name)
        if found:
            return found
    return None


# Debug port for managed Chrome
CHROME_DEBUG_PORT = 9222


@dataclass
class MCPConfig:
    """Configuration for Chrome DevTools MCP server"""
    command: str = "npx"
    args: List[str] = field(default_factory=list)
    headless: bool = True
    isolated: bool = True
    viewport: str = "1920x1080"
    timeout: int = 30
    executable_path: Optional[str] = None  # Auto-detected if not specified
    use_managed_chrome: bool = True  # Pi/Linux: start Chrome ourselves, connect MCP to it

    def __post_init__(self):
        if not self.args:
            if self.use_managed_chrome:
                # Connect to externally managed Chrome via browserUrl
                self.args = [
                    "-y", "chrome-devtools-mcp@latest",
                    f"--browserUrl=http://127.0.0.1:{CHROME_DEBUG_PORT}",
                ]
                logger.info(f"MCP will connect to managed Chrome on port {CHROME_DEBUG_PORT}")
            else:
                # Let MCP launch Chrome (may have signal issues on Pi)
                browser_path = self.executable_path or _detect_browser_path()

                self.args = [
                    "-y", "chrome-devtools-mcp@latest",
                    f"--headless={str(self.headless).lower()}",
                    f"--isolated={str(self.isolated).lower()}",
                    f"--viewport={self.viewport}"
                ]

                if browser_path:
                    self.args.append(f"--executablePath={browser_path}")
                    logger.info(f"Using browser: {browser_path}")

                # Chrome args for headless on Linux/Pi
                self.args.extend([
                    "--chromeArg=--no-sandbox",
                    "--chromeArg=--disable-dev-shm-usage",
                    "--chromeArg=--disable-gpu",
                ])


class MCPError(Exception):
    """MCP protocol error"""
    pass


class ChromeMCPClient:
    """
    Manages lifecycle and communication with chrome-devtools-mcp.
    Uses JSON-RPC 2.0 over stdio (MCP protocol).

    On Pi/Linux, uses "managed Chrome" mode: starts Chrome ourselves with
    remote debugging, then connects MCP to it. This avoids signal propagation
    issues when MCP tries to spawn Chrome as a child process.
    """

    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or MCPConfig()
        self.process: Optional[asyncio.subprocess.Process] = None  # MCP server
        self.chrome_process: Optional[asyncio.subprocess.Process] = None  # Managed Chrome
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

    def _check_chrome_running(self) -> bool:
        """Check if Chrome is already running on debug port."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', CHROME_DEBUG_PORT))
            return result == 0
        except Exception:
            return False
        finally:
            sock.close()

    async def _start_managed_chrome(self) -> bool:
        """Start Chrome with remote debugging (managed mode for Pi/Linux).

        Uses subprocess.Popen with shell to properly detach Chrome from
        Python's process tree, avoiding signal propagation issues.
        """
        # Check if Chrome is already running
        if self._check_chrome_running():
            logger.info(f"Chrome already running on port {CHROME_DEBUG_PORT}")
            return True

        browser_path = _detect_browser_path()
        if not browser_path:
            logger.error("No Chrome/Chromium found")
            return False

        # Build Chrome command with all necessary flags for headless Pi
        width, height = self.config.viewport.split("x") if "x" in self.config.viewport else ("1920", "1080")

        # Use shell command with proper backgrounding to avoid signal issues
        chrome_cmd = (
            f'"{browser_path}" '
            f'--headless={"new" if self.config.headless else "false"} '
            f'--no-sandbox '
            f'--disable-dev-shm-usage '
            f'--disable-gpu '
            f'--remote-debugging-port={CHROME_DEBUG_PORT} '
            f'--window-size={width},{height} '
            f'--disable-extensions '
            f'--disable-background-networking '
            f'--no-first-run '
            f'about:blank '
            f'>/dev/null 2>&1 &'
        )

        logger.info(f"Starting managed Chrome: {browser_path}")
        try:
            # Use subprocess.Popen with shell=True to properly detach
            import os
            os.system(chrome_cmd)

            # Wait for Chrome to start and open debug port
            for _ in range(10):  # Wait up to 5 seconds
                await asyncio.sleep(0.5)
                if self._check_chrome_running():
                    logger.info(f"Managed Chrome started on port {CHROME_DEBUG_PORT}")
                    return True

            logger.error("Chrome did not start within timeout")
            return False

        except Exception as e:
            logger.error(f"Failed to start managed Chrome: {e}")
            return False

    async def connect(self) -> Dict[str, Any]:
        """
        Start MCP server subprocess and establish connection.

        In managed Chrome mode (default on Pi/Linux), starts Chrome ourselves
        then connects MCP to it via browserUrl.

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
            # Start managed Chrome if configured (Pi/Linux mode)
            if self.config.use_managed_chrome:
                if not await self._start_managed_chrome():
                    return {"success": False, "error": "Failed to start managed Chrome"}

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
        """Gracefully shutdown MCP server and managed Chrome"""
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

            # Stop managed Chrome if we started it (uses pkill since we used os.system)
            if self.config.use_managed_chrome and self._check_chrome_running():
                logger.info("Stopping managed Chrome...")
                try:
                    import os
                    os.system("pkill -f 'chromium.*--remote-debugging-port' >/dev/null 2>&1")
                except Exception:
                    pass

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

    async def _send_request(self, method: str, params: Dict[str, Any], _retry: bool = True) -> Dict[str, Any]:
        """Send JSON-RPC request and wait for response.

        Includes mid-flight transport death recovery (Streamlit fix).
        If stdin dies during await, reconnects and retries once.
        """
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
            # Send request - wrapped for mid-flight death recovery
            message = json.dumps(request) + "\n"
            try:
                self.process.stdin.write(message.encode())
                await self.process.stdin.drain()
            except (AttributeError, BrokenPipeError, ConnectionResetError, OSError) as write_err:
                # Transport died mid-flight! (Streamlit frame boundary issue)
                # Clean up the pending request
                self._pending_requests.pop(request_id, None)

                if _retry:
                    logger.warning(f"Transport died mid-flight ({type(write_err).__name__}), reconnecting...")
                    await self.reconnect()
                    # Retry once (with _retry=False to prevent infinite loop)
                    return await self._send_request(method, params, _retry=False)
                else:
                    raise MCPError(f"Transport died and retry failed: {write_err}")

            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=self.config.timeout)
            return result

        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise
        except MCPError:
            # Re-raise our own errors
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
        try:
            self.process.stdin.write(message.encode())
            await self.process.stdin.drain()
        except (AttributeError, BrokenPipeError, ConnectionResetError, OSError) as e:
            # Transport died - notifications are fire-and-forget, just log it
            logger.warning(f"Notification failed (transport dead): {e}")

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
