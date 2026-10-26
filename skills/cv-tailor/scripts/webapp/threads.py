"""Chat threads of the web app. One thread = one Claude Code session in the workspace.

<ws>/.cv-tailor/web/threads/<id>.json    thread state (title, session id, application, status)
<ws>/.cv-tailor/web/threads/<id>.jsonl   what the browser shows, one message per line

Claude Code keeps the real transcript (and compacts it); this copy only renders the chat.
"""
from __future__ import annotations

import json
import pathlib
import threading
import uuid

from common import now, read_json, write_json
from webapp.settings import web_dir

# queued -> running -> (waiting: needs the user) -> idle | error | stopped
STATES = ["queued", "running", "waiting", "idle", "error", "stopped"]


class Store:
    def __init__(self, ws: pathlib.Path):
        self.root = web_dir(ws) / "threads"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _meta_path(self, tid: str) -> pathlib.Path:
        if not tid.isalnum():
            raise KeyError(tid)
        return self.root / f"{tid}.json"

    def create(self, kind: str, title: str, app_id: str | None = None, effort: str = "high") -> dict:
        t = {"id": uuid.uuid4().hex[:12], "kind": kind, "title": title.strip()[:120] or kind,
             "app_id": app_id, "session_id": None, "status": "idle", "effort": effort,
             "created": now(), "updated": now(), "unread": False, "preview": "", "error": None,
             "usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}}
        self.save(t)
        return t

    def get(self, tid: str) -> dict:
        t = read_json(self._meta_path(tid))
        if not t:
            raise KeyError(tid)
        return t

    def save(self, t: dict) -> dict:
        t["updated"] = now()
        with self._lock:
            write_json(self._meta_path(t["id"]), t)
        return t

    def update(self, tid: str, **changes) -> dict:
        with self._lock:
            t = self.get(tid)
            t.update(changes)
            t["updated"] = now()
            write_json(self._meta_path(tid), t)
        return t

    def all(self) -> list[dict]:
        out = [read_json(p) for p in self.root.glob("*.json")]
        return sorted((t for t in out if t), key=lambda t: t["updated"], reverse=True)

    def for_app(self, app_id: str) -> list[dict]:
        return [t for t in self.all() if t.get("app_id") and int(t["app_id"]) == int(app_id)]

    def append(self, tid: str, msg: dict) -> dict:
        msg = {"id": uuid.uuid4().hex[:10], "ts": now(), **msg}
        with self._lock, open(self.root / f"{tid}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(msg, ensure_ascii=False, default=str) + "\n")
        return msg

    def messages(self, tid: str) -> list[dict]:
        self._meta_path(tid)
        p = self.root / f"{tid}.jsonl"
        if not p.is_file():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def delete(self, tid: str) -> None:
        for p in (self._meta_path(tid), self.root / f"{tid}.jsonl"):
            p.unlink(missing_ok=True)
