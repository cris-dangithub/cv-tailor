"""In-process event bus feeding the browser's Server-Sent Events stream."""
from __future__ import annotations

import asyncio
import json


class Bus:
    def __init__(self):
        self._subs: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def emit(self, kind: str, **data) -> None:
        msg = json.dumps({"type": kind, **data}, ensure_ascii=False, default=str)
        for q in list(self._subs):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:  # a stalled tab; it reloads everything on reconnect
                self._subs.discard(q)
