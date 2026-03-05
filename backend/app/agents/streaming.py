from fastapi import WebSocket
from typing import Dict
import json
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_event(self, session_id: str, event: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                self.disconnect(session_id)

    async def send_agent_start(self, session_id: str, agent: str, order: int):
        await self.send_event(session_id, {
            "type": "agent_start",
            "agent": agent,
            "order": order,
        })

    async def send_agent_chunk(self, session_id: str, agent: str, chunk: str):
        await self.send_event(session_id, {
            "type": "agent_chunk",
            "agent": agent,
            "chunk": chunk,
        })

    async def send_agent_done(self, session_id: str, agent: str, output: str):
        await self.send_event(session_id, {
            "type": "agent_done",
            "agent": agent,
            "output": output,
        })

    async def send_pipeline_complete(self, session_id: str):
        await self.send_event(session_id, {
            "type": "pipeline_complete",
        })

    async def send_error(self, session_id: str, error: str):
        await self.send_event(session_id, {
            "type": "error",
            "message": error,
        })


manager = ConnectionManager()
