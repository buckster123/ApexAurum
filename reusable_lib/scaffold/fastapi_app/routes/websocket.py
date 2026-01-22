"""
WebSocket Routes for Village GUI

Handles real-time communication between backend and village frontend.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.event_service import get_event_broadcaster

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/village")
async def village_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for Village GUI.

    Connect: ws://localhost:8765/ws/village

    Receives events:
    - tool_start: Agent started executing a tool
    - tool_complete: Tool finished executing
    - tool_error: Tool execution failed
    - connection: Initial connection confirmed
    """
    print(f"🔌 WebSocket connection request from {websocket.client}")
    await websocket.accept()
    print(f"✅ WebSocket ACCEPTED - client connected!")

    broadcaster = get_event_broadcaster()
    await broadcaster.connect(websocket)
    print(f"📡 Broadcaster now has {len(broadcaster.connections)} connection(s)")

    try:
        while True:
            # Keep connection alive, receive messages from frontend
            data = await websocket.receive_text()
            print(f"📨 Received from village GUI: {data}")

    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
        print(f"🔌 WebSocket disconnected. Remaining: {len(broadcaster.connections)}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        broadcaster.disconnect(websocket)
