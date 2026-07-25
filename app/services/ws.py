"""In-Memory WebSocket-Broadcast pro Chat-Thread.

Gilt für Single-Process-Betrieb (uvicorn ohne --workers). Für Multi-Worker/Prod
später ein Redis-PubSub-Broker davorsetzen.
"""
import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, thread_id: int, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms[thread_id].add(ws)

    async def disconnect(self, thread_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[thread_id].discard(ws)

    async def broadcast(self, thread_id: int, payload: dict) -> None:
        """Sendet an alle offenen Verbindungen des Threads; tote Sockets werden entfernt."""
        tot: list[WebSocket] = []
        for ws in list(self._rooms.get(thread_id, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                tot.append(ws)
        if tot:
            async with self._lock:
                for ws in tot:
                    self._rooms[thread_id].discard(ws)


manager = ConnectionManager()
