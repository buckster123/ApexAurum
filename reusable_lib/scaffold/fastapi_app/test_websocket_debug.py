#!/usr/bin/env python3
"""
Debug WebSocket connection issues.

Simulates the browser connecting from different hosts.
"""

import asyncio
import json
import time
import websockets

async def test_websocket(host="localhost", port=8765):
    """Test WebSocket connection and events."""
    uri = f"ws://{host}:{port}/ws/village"
    print(f"\n{'='*60}")
    print(f"Testing WebSocket: {uri}")
    print(f"{'='*60}")

    try:
        print(f"[1] Attempting connection...")
        start = time.time()

        async with websockets.connect(uri, close_timeout=5) as ws:
            duration = (time.time() - start) * 1000
            print(f"[2] ✅ Connected! ({duration:.0f}ms)")
            print(f"    State: {ws.state}")

            # Wait for connection event
            print(f"[3] Waiting for connection event...")
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(msg)
                print(f"[4] ✅ Received: {data}")
                if data.get("type") == "connection":
                    print(f"    → Connection confirmed by server")
            except asyncio.TimeoutError:
                print(f"[4] ⚠️  No message received (might be OK)")

            # Keep alive and listen
            print(f"[5] Listening for events (10 seconds)...")
            print(f"    (Trigger a tool to see events)")

            try:
                for i in range(10):
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(msg)
                    print(f"    Event: {data.get('type')} - {data.get('tool', 'N/A')}")
            except asyncio.TimeoutError:
                print(f"[6] Timeout (no events)")

            print(f"[7] Closing connection...")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"[!] ❌ Invalid status: {e}")
        print(f"    Server rejected the connection")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"[!] ❌ Connection closed: {e}")
    except ConnectionRefusedError:
        print(f"[!] ❌ Connection refused - is the server running?")
    except OSError as e:
        print(f"[!] ❌ OS Error: {e}")
    except Exception as e:
        print(f"[!] ❌ Error: {type(e).__name__}: {e}")

async def test_multiple_hosts():
    """Test connections from different hosts."""
    hosts = ["localhost", "127.0.0.1"]

    for host in hosts:
        uri = f"ws://{host}:8765/ws/village"
        try:
            async with websockets.connect(uri, close_timeout=2) as ws:
                # Try to receive the connection message
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(msg)
                    print(f"✅ {uri} - Connected (got: {data.get('type', 'unknown')})")
                except asyncio.TimeoutError:
                    print(f"✅ {uri} - Connected (no init message)")
        except Exception as e:
            print(f"❌ {uri} - {e}")

if __name__ == "__main__":
    import sys

    print("WebSocket Debug Test")
    print("=" * 60)

    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"

    # Test basic connection
    asyncio.run(test_websocket(host))

    print("\n\nTesting multiple hosts:")
    asyncio.run(test_multiple_hosts())
