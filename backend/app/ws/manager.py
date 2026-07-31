import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[session_id].add(websocket)

    async def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms[session_id].discard(websocket)
            if not self._rooms[session_id]:
                del self._rooms[session_id]

    async def broadcast(self, session_id: UUID, message: dict) -> None:
        async with self._lock:
            connections = list(self._rooms.get(session_id, set()))
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(session_id, ws)


manager = ConnectionManager()
