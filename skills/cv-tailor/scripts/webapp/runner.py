"""Runs Claude Code sessions for the web app's threads, through the Claude Agent SDK.

Each message is one turn: the CLI starts with `--resume <session>` in the workspace, answers,
and exits, so idle threads cost nothing and every turn can use another effort. The CLI keeps
the transcript and compacts it on its own (`--autocompact`, a small window by default).

A semaphore caps how many turns run at once (settings.concurrency): pasting five offers queues
five threads. Tool calls outside the allow-list (permissions.py) wait for the browser.
"""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import time
import uuid

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient,
                              PermissionResultAllow, PermissionResultDeny, ResultMessage,
                              StreamEvent, SystemMessage, TextBlock, ToolResultBlock, ToolUseBlock,
                              UserMessage)

from common import read_json
from webapp import permissions, prompts, settings
from webapp.events import Bus
from webapp.threads import Store

NEW_APP_RE = re.compile(r'\{"id": "(\d+)", "dir": "([^"]+)"\}')
ASKS_RE = re.compile(r"\?\s*(\*\*)?\s*$|\?\s*\n", re.M)
PERMISSION_WAIT = 60 * 60  # an unanswered approval card is refused after an hour
AUTH_RE = re.compile(r"authenticat|not logged in|/login|oauth", re.I)


def tool_result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


class Runner:
    def __init__(self, ws, store: Store, bus: Bus):
        self.ws, self.store, self.bus = ws, store, bus
        self.sem = asyncio.Semaphore(settings.load(ws)["concurrency"])
        self.thread_locks: dict[str, asyncio.Lock] = {}
        self.tasks: dict[str, set[asyncio.Task]] = {}
        self.clients: dict[str, ClaudeSDKClient] = {}
        self.pending: dict[str, dict] = {}  # request id -> {thread, future, card}
        self._health: tuple[float, dict] | None = None
        self.creates_app: set[str] = set()  # tool calls that ran `cvt index new`
        self.stopping: set[str] = set()  # threads the user stopped; their turn must not go on

    # ----------------------------------------------------------------------- lifecycle
    async def start(self) -> None:
        for t in self.store.all():  # turns cut short by a restart
            if t["status"] in ("queued", "running"):
                self.store.update(t["id"], status="stopped")
                self.store.append(t["id"], {"role": "event", "kind": "interrupted"})

    async def shutdown(self) -> None:
        for tid in list(self.tasks):
            await self.stop(tid)

    def reconfigure(self) -> None:
        self.sem = asyncio.Semaphore(settings.load(self.ws)["concurrency"])

    async def health(self) -> dict:
        """Is Claude Code installed and signed in? The desktop app has its own login, so a
        computer can have a working desktop app and a signed-out CLI. Cached for a while."""
        if self._health and time.monotonic() - self._health[0] < 30:
            return self._health[1]
        cli = shutil.which("claude")
        out = {"cli": cli, "logged_in": None}
        if cli:
            try:
                p = await asyncio.create_subprocess_exec(cli, "auth", "status", stdout=asyncio.subprocess.PIPE,
                                                         stderr=asyncio.subprocess.DEVNULL)
                so, _ = await asyncio.wait_for(p.communicate(), 20)
                out["logged_in"] = bool(json.loads(so.decode("utf-8", "replace") or "{}").get("loggedIn"))
            except (OSError, ValueError, asyncio.TimeoutError):
                pass
        self._health = (time.monotonic(), out)
        return out

    def _auth_failed(self, tid: str, text: str) -> bool:
        if not AUTH_RE.search(text or ""):
            return False
        self._health = None
        self._add(tid, {"role": "event", "kind": "auth"})
        self.bus.emit("health")
        return True

    # ----------------------------------------------------------------------- api
    async def send(self, tid: str, text: str, effort: str | None = None, shown: str | None = None,
                   author: str = ""):
        t = self.store.get(tid)
        effort = effort or t.get("effort") or settings.load(self.ws)["effort"]
        if effort not in settings.EFFORTS:
            raise ValueError(f"effort must be one of {settings.EFFORTS}")
        msg = self.store.append(tid, {"role": "user", "text": shown if shown is not None else text,
                                      "effort": effort, "author": author})
        self.bus.emit("message", thread=tid, message=msg)
        self.stopping.discard(tid)
        self._set(tid, status="queued", effort=effort, error=None)
        task = asyncio.create_task(self._turn(tid, text, effort))
        self.tasks.setdefault(tid, set()).add(task)
        task.add_done_callback(lambda tk: self.tasks.get(tid, set()).discard(tk))

    async def stop(self, tid: str) -> None:
        self.stopping.add(tid)
        for req, p in list(self.pending.items()):
            if p["thread"] == tid and not p["future"].done():
                p["future"].set_result(False)
        client = self.clients.get(tid)
        if client:
            try:
                await client.interrupt()
            except Exception:  # noqa: BLE001  (already finished)
                pass
        # an interrupt can arrive while a tool is running and be ignored: ending the task closes
        # the session (and its CLI process) for sure
        for task in list(self.tasks.get(tid, ())):
            task.cancel()
        try:
            if self.store.get(tid)["status"] in ("queued", "running", "waiting"):
                self._set(tid, status="stopped")
        except KeyError:
            pass

    def pending_for(self, tid: str) -> list[dict]:
        return [p["card"] for p in self.pending.values() if p["thread"] == tid and not p["future"].done()]

    def answer(self, req_id: str, allow: bool, remember: bool, by: str = "") -> bool:
        p = self.pending.get(req_id)
        if not p or p["future"].done():
            return False
        if allow and remember:
            cur = settings.load(self.ws)
            key = p["card"]["rule"]
            if key not in cur["always_allow"]:
                settings.save(self.ws, {"always_allow": [*cur["always_allow"], key]})
        p["by"] = by
        p["future"].set_result(allow)
        return True

    # ----------------------------------------------------------------------- internals
    def _set(self, tid: str, **changes) -> dict:
        t = self.store.update(tid, **changes)
        self.bus.emit("thread", thread=t)
        return t

    def _add(self, tid: str, msg: dict) -> dict:
        m = self.store.append(tid, msg)
        self.bus.emit("message", thread=tid, message=m)
        return m

    def _options(self, t: dict, effort: str) -> ClaudeAgentOptions:
        s = settings.load(self.ws)
        tid = t["id"]

        async def can_use_tool(tool, tool_input, ctx):
            if permissions.decide(self.ws, tool, tool_input, settings.load(self.ws)["always_allow"]) == "allow":
                return PermissionResultAllow()
            return await self._ask(tid, tool, tool_input, ctx)

        return ClaudeAgentOptions(
            cwd=str(self.ws), model=s["model"], effort=effort, resume=t.get("session_id"),
            permission_mode="default", can_use_tool=can_use_tool, include_partial_messages=True,
            system_prompt={"type": "preset", "preset": "claude_code", "append": prompts.SYSTEM},
            extra_args={"autocompact": str(s["autocompact"])},
            env={"CV_TAILOR_WORKSPACE": str(self.ws)},
            # the user's own install first: same login, same version as their desktop app
            cli_path=shutil.which("claude") or None,
        )

    async def _ask(self, tid, tool, tool_input, ctx):
        if tid in self.stopping:
            return PermissionResultDeny(message="The user stopped this conversation.", interrupt=True)
        req = uuid.uuid4().hex[:12]
        card = {"request_id": req, "tool": tool, "summary": permissions.summary(tool, tool_input, None),
                "title": getattr(ctx, "title", None) or "", "rule": permissions.rule_key(tool, tool_input)}
        fut = asyncio.get_running_loop().create_future()
        self.pending[req] = {"thread": tid, "future": fut, "card": card}
        self._add(tid, {"role": "permission", **card})
        self._set(tid, status="waiting", unread=True)
        self.bus.emit("permission", thread=tid, card=card)
        try:
            allow = await asyncio.wait_for(fut, PERMISSION_WAIT)
        except asyncio.TimeoutError:
            allow = False
        finally:
            entry = self.pending.pop(req, None) or {}
        self._add(tid, {"role": "decision", "request_id": req, "allow": allow, "by": entry.get("by", "")})
        if tid in self.stopping:
            return PermissionResultDeny(message="The user stopped this conversation.", interrupt=True)
        self._set(tid, status="running")
        if allow:
            return PermissionResultAllow()
        return PermissionResultDeny(message="The user declined this action in the web app.")

    async def _turn(self, tid: str, text: str, effort: str) -> None:
        lock = self.thread_locks.setdefault(tid, asyncio.Lock())
        async with lock, self.sem:
            try:
                t = self.store.get(tid)
            except KeyError:
                return
            if t["status"] == "stopped":
                return
            self._set(tid, status="running")
            last_text = ""
            try:
                async with ClaudeSDKClient(options=self._options(t, effort)) as client:
                    self.clients[tid] = client
                    await client.query(text)
                    async for m in client.receive_response():
                        last_text = self._handle(tid, m) or last_text
                t = self.store.get(tid)
                if tid in self.stopping:
                    self._set(tid, status="stopped")
                elif t["status"] in ("running", "waiting"):
                    asks = bool(ASKS_RE.search(last_text[-400:]))
                    self._set(tid, status="waiting" if asks else "idle", unread=True,
                              preview=last_text.strip()[:240])
            except asyncio.CancelledError:
                self._set(tid, status="stopped")
                raise
            except Exception as e:  # noqa: BLE001  (shown in the thread; the server keeps running)
                if not self._auth_failed(tid, str(e)):
                    self._add(tid, {"role": "event", "kind": "error", "text": str(e)[:2000]})
                self._set(tid, status="error", error=str(e)[:300], unread=True)
            finally:
                self.clients.pop(tid, None)
                self._name_after_app(tid)

    def _handle(self, tid: str, m) -> str | None:
        """Turn one SDK message into chat entries. Returns the assistant text, if any."""
        if isinstance(m, StreamEvent):
            ev = m.event or {}
            if m.parent_tool_use_id is None and ev.get("type") == "content_block_delta":
                d = ev.get("delta") or {}
                if d.get("type") == "text_delta":
                    self.bus.emit("delta", thread=tid, text=d.get("text", ""))
            return None
        if isinstance(m, SystemMessage):
            if m.subtype == "init" and m.data.get("session_id"):
                self.store.update(tid, session_id=m.data["session_id"])
            elif m.subtype == "compact_boundary":
                self._add(tid, {"role": "event", "kind": "compacted"})
            return None
        if isinstance(m, AssistantMessage):
            if m.parent_tool_use_id:  # a subagent's inner work: the tool note covers it
                return None
            out = None
            if m.error:  # an API/auth failure dressed as a reply: the result message reports it
                return None
            for b in m.content:
                if isinstance(b, TextBlock) and b.text.strip():
                    self._add(tid, {"role": "assistant", "text": b.text})
                    out = b.text
                elif isinstance(b, ToolUseBlock):
                    cmd = str((b.input or {}).get("command", ""))
                    if "cvt" in cmd and re.search(r"\bindex\s+(--workspace\s+\S+\s+)?new\b", cmd):
                        self.creates_app.add(b.id)
                    self._add(tid, {"role": "tool", "tool_use_id": b.id, "name": b.name,
                                    "summary": permissions.summary(b.name, b.input or {})})
            return out
        if isinstance(m, UserMessage) and isinstance(m.content, list) and not m.parent_tool_use_id:
            for b in m.content:
                if isinstance(b, ToolResultBlock):
                    txt = tool_result_text(b.content)
                    self._add(tid, {"role": "tool_result", "tool_use_id": b.tool_use_id,
                                    "is_error": bool(b.is_error), "text": txt[:1500]})
                    # only the real `cvt index new` output: the skill's docs contain examples of it
                    hit = NEW_APP_RE.search(txt) if b.tool_use_id in self.creates_app else None
                    if hit and not self.store.get(tid).get("app_id"):
                        self._set(tid, app_id=hit.group(1))
                        self.bus.emit("apps")
            return None
        if isinstance(m, ResultMessage):
            t = self.store.get(tid)
            u = t.get("usage") or {}
            usage = m.usage or {}
            u = {"input_tokens": u.get("input_tokens", 0) + int(usage.get("input_tokens") or 0),
                 "output_tokens": u.get("output_tokens", 0) + int(usage.get("output_tokens") or 0),
                 "cost_usd": round(u.get("cost_usd", 0.0) + float(m.total_cost_usd or 0.0), 4)}
            self.store.update(tid, session_id=m.session_id or t.get("session_id"), usage=u)
            if m.is_error and m.terminal_reason not in ("aborted_streaming", "aborted_tools"):
                err = "; ".join(m.errors or []) or (m.result or m.subtype)
                if not self._auth_failed(tid, str(err)):
                    self._add(tid, {"role": "event", "kind": "error", "text": str(err)[:2000]})
                self._set(tid, status="error", error=str(err)[:300])
            return None
        return None

    def _name_after_app(self, tid: str) -> None:
        """An offer thread is titled by its pasted text until the skill has registered the
        application; from then on it carries the company and role."""
        try:
            t = self.store.get(tid)
        except KeyError:
            return
        if not t.get("app_id") or t["kind"] != "offer":
            return
        import index  # noqa: PLC0415
        try:
            meta = read_json(index.find_app(self.ws, t["app_id"]) / "meta.json", {})
        except SystemExit:
            return
        title = " · ".join(x for x in (meta.get("company"), meta.get("role")) if x)
        if title and title != t["title"]:
            self._set(tid, title=title)

