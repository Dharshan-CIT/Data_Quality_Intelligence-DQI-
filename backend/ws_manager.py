"""WebSocket connection registry, keyed by session_id.

One browser tab holds one WebSocket to /ws/{session_id}, used for three
kinds of live push:
  - pipeline_progress / pipeline_done   (while a dataset is being processed)
  - stream_tick                          (while the streaming-simulation tab is open)
  - dataset_updated                      (pushed after remediation commits so the
                                           dashboard can refresh without polling)
"""
from __future__ import annotations

import asyncio
from typing import Dict, List

from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(session_id, []).append(ws)

    async def disconnect(self, session_id: str, ws: WebSocket):
        async with self._lock:
            conns = self._connections.get(session_id, [])
            if ws in conns:
                conns.remove(ws)
            if not conns and session_id in self._connections:
                del self._connections[session_id]

    async def send(self, ws: WebSocket, message: dict):
        try:
            await ws.send_json(message)
        except Exception:
            pass

    async def broadcast(self, session_id: str, message: dict):
        for ws in list(self._connections.get(session_id, [])):
            await self.send(ws, message)


manager = WSManager()
