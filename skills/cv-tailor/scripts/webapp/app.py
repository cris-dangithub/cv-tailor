"""HTTP layer of the web app: JSON API under /api, the built React UI everywhere else.

Security model: by default the server listens on 127.0.0.1 only. With --lan it also accepts
other devices of the local network, which must present the access token once (the link or QR
printed at start); the token then lives in an HttpOnly cookie. Host and Origin are checked on
every request so a web page elsewhere cannot drive the agent (DNS rebinding, CSRF).
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import io
import ipaddress
import os
import pathlib
import re
import subprocess
import sys
import time
import zipfile

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

import workspace as workspace_cli
from common import SKILL_DIR, now
from webapp import library, prompts, settings
from webapp.events import Bus
from webapp.threads import Store

UI_DIST = SKILL_DIR / "web" / "ui" / "dist"
COOKIE = "cvt_token"
SAMPLE_TYPES = (".pdf", ".docx", ".doc", ".odt", ".html", ".png", ".jpg", ".jpeg")


# --------------------------------------------------------------------------- request bodies
class StatusBody(BaseModel):
    status: str
    note: str = ""


class OfferItem(BaseModel):
    text: str = ""
    url: str = ""


class OffersBody(BaseModel):
    items: list[OfferItem]
    effort: str | None = None


class MessageBody(BaseModel):
    text: str
    effort: str | None = None


class ThreadBody(BaseModel):
    text: str
    title: str = ""
    app_id: str | None = None
    effort: str | None = None


class PermissionBody(BaseModel):
    allow: bool
    remember: bool = False


class FeedbackBody(BaseModel):
    text: str
    effort: str | None = None


class StyleBody(BaseModel):
    name: str


class ZipBody(BaseModel):
    files: list[dict]


# --------------------------------------------------------------------------- helpers
def is_local(request: Request) -> bool:
    host = request.client.host if request.client else ""
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host in ("testclient", "localhost")


def allowed_hosts(lan_hosts: list[str]) -> set[str]:
    return {"localhost", "127.0.0.1", "[::1]", "::1", "testserver", *(h.lower() for h in lan_hosts)}


def open_folder(path: pathlib.Path) -> None:
    if os.name == "nt":
        os.startfile(str(path))  # noqa: S606  (the local user's own folder)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def create_app(ws: pathlib.Path, lan: bool = False, lan_hosts: list[str] | None = None,
               port: int = 8765, runner=None) -> FastAPI:
    ws = pathlib.Path(ws).resolve()
    store = Store(ws)
    bus = Bus()
    if runner is None:
        from webapp.runner import Runner  # noqa: PLC0415  (needs claude-agent-sdk)
        runner = Runner(ws, store, bus)
    hosts = allowed_hosts(lan_hosts or [])
    token = settings.token(ws)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        await runner.start()
        watch = asyncio.create_task(watch_index())
        try:
            yield
        finally:
            watch.cancel()
            await runner.shutdown()

    app = FastAPI(title="cv-tailor", docs_url=None, redoc_url=None, openapi_url=None,
                  lifespan=lifespan)
    app.state.ws, app.state.store, app.state.bus, app.state.runner = ws, store, bus, runner

    async def watch_index():
        """Agents in the desktop app or a terminal change the workspace too: tell the browser."""
        idx = ws / "applications" / "index.jsonl"
        last = None
        while True:
            try:
                cur = idx.stat().st_mtime_ns if idx.exists() else 0
                if last is not None and cur != last:
                    bus.emit("apps")
                last = cur
            except OSError:
                pass
            await asyncio.sleep(1.5)

    # ----------------------------------------------------------------------- guard
    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = (request.headers.get("host") or "").lower()
        host = host[: host.rindex(":")] if re.search(r":\d+$", host) else host
        if host and host not in hosts:
            return Response("unknown host", status_code=421)
        origin = request.headers.get("origin")
        if origin and request.method not in ("GET", "HEAD"):
            o = re.sub(r"^https?://", "", origin).lower()
            o = o[: o.rindex(":")] if re.search(r":\d+$", o) else o
            if o not in hosts:
                return Response("cross-origin request refused", status_code=403)
        if not is_local(request):
            if not lan:
                return Response("local only", status_code=403)
            given = request.query_params.get("t")
            if given and hmac.compare_digest(given, token):
                resp = Response(status_code=303, headers={"location": request.url.path})
                resp.set_cookie(COOKIE, token, httponly=True, samesite="strict",
                                max_age=3600 * 24 * 365)
                return resp
            if not hmac.compare_digest(request.cookies.get(COOKIE, ""), token):
                return Response("Open the link printed by `cvt web --lan` first.", status_code=401)
        return await call_next(request)

    @app.exception_handler(library.NotFound)
    async def not_found(_, exc):
        return JSONResponse({"error": str(exc) or "not found"}, status_code=404)

    @app.exception_handler(ValueError)
    async def bad_value(_, exc):
        return JSONResponse({"error": str(exc)}, status_code=400)

    @app.exception_handler(KeyError)
    async def no_thread(_, exc):
        return JSONResponse({"error": f"not found: {exc}"}, status_code=404)

    # ----------------------------------------------------------------------- workspace
    @app.get("/api/workspace")
    def get_workspace(request: Request):
        info = library.workspace_info(ws)
        info["local"] = is_local(request)
        info["lan"] = {"enabled": lan,
                       "urls": [f"http://{h}:{port}/?t={token}" for h in (lan_hosts or [])]
                       } if is_local(request) else None
        return info

    @app.get("/api/health")
    async def health():
        return await runner.health()

    @app.get("/api/lan/qr.svg")
    def lan_qr(request: Request):
        if not (lan and lan_hosts and is_local(request)):
            raise HTTPException(404)
        import qrcode  # noqa: PLC0415
        import qrcode.image.svg  # noqa: PLC0415
        img = qrcode.make(f"http://{lan_hosts[0]}:{port}/?t={token}",
                          image_factory=qrcode.image.svg.SvgPathImage, border=1)
        return Response(img.to_string(), media_type="image/svg+xml")

    @app.get("/api/settings")
    def get_settings():
        return settings.load(ws)

    @app.put("/api/settings")
    def put_settings(body: dict):
        out = settings.save(ws, body)
        runner.reconfigure()
        return out

    # ----------------------------------------------------------------------- applications
    @app.get("/api/applications")
    def list_apps(q: str = "", status: str | None = None):
        return library.applications(ws, q, status)

    @app.get("/api/applications/{app_id}")
    def get_app(app_id: str):
        out = library.application(ws, app_id)
        out["threads"] = store.for_app(app_id)
        return out

    @app.patch("/api/applications/{app_id}/status")
    def patch_status(app_id: str, body: StatusBody):
        out = library.set_status(ws, app_id, body.status, body.note)
        bus.emit("apps")
        return out

    @app.get("/api/applications/{app_id}/files/{name}")
    def get_file(app_id: str, name: str, download: bool = False):
        p = library.app_file(ws, app_id, name)
        return FileResponse(p, media_type=library.VIEWABLE[p.suffix.lower()], filename=p.name,
                            content_disposition_type="attachment" if download else "inline")

    @app.post("/api/applications/{app_id}/open-folder")
    def post_open_folder(app_id: str, request: Request):
        if not is_local(request):
            raise HTTPException(403, "only on this computer")
        open_folder(library.app_dir(ws, app_id))
        return {"ok": True}

    @app.post("/api/applications/{app_id}/feedback")
    async def post_feedback(app_id: str, body: FeedbackBody):
        meta = library.application(ws, app_id)
        threads = store.for_app(app_id)
        t = threads[0] if threads else store.create(
            "feedback", f"{meta.get('company', '')} · {meta.get('role', '')}", app_id=meta["id"],
            effort=body.effort or settings.load(ws)["effort"])
        await runner.send(t["id"], prompts.feedback(meta, body.text), effort=body.effort,
                          shown=body.text)
        return store.get(t["id"])

    # ----------------------------------------------------------------------- pdfs
    @app.get("/api/pdfs")
    def list_pdfs():
        return library.all_pdfs(ws)

    @app.post("/api/pdfs/zip")
    def zip_pdfs(body: ZipBody):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in body.files[:500]:
                p = library.app_file(ws, str(f.get("app_id", "")), str(f.get("name", "")))
                z.write(p, arcname=f"{p.parent.name}/{p.name}")
        name = f"cv-tailor-{time.strftime('%Y%m%d-%H%M')}.zip"
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"content-disposition": f'attachment; filename="{name}"'})

    # ----------------------------------------------------------------------- offers & threads
    @app.post("/api/offers")
    async def post_offers(body: OffersBody):
        created = []
        for item in body.items:
            text, url = item.text.strip(), item.url.strip()
            if not text and not url:
                continue
            t = store.create("offer", prompts.offer_title(text, url),
                             effort=body.effort or settings.load(ws)["effort"])
            await runner.send(t["id"], prompts.offer(text, url), effort=body.effort,
                              shown=url or text)
            created.append(store.get(t["id"]))
        if not created:
            raise ValueError("paste an offer or a link")
        return created

    @app.get("/api/threads")
    def list_threads():
        return store.all()

    @app.post("/api/threads")
    async def new_thread(body: ThreadBody):
        t = store.create("chat", body.title or prompts.chat_title(body.text), app_id=body.app_id,
                         effort=body.effort or settings.load(ws)["effort"])
        await runner.send(t["id"], body.text, effort=body.effort)
        return store.get(t["id"])

    @app.get("/api/threads/{tid}")
    def get_thread(tid: str):
        t = store.get(tid)
        if t.get("unread"):
            t = store.update(tid, unread=False)
        return {**t, "messages": store.messages(tid), "pending": runner.pending_for(tid)}

    @app.post("/api/threads/{tid}/messages")
    async def post_message(tid: str, body: MessageBody):
        store.get(tid)
        await runner.send(tid, body.text, effort=body.effort)
        return store.get(tid)

    @app.post("/api/threads/{tid}/stop")
    async def stop_thread(tid: str):
        await runner.stop(tid)
        return store.get(tid)

    @app.delete("/api/threads/{tid}")
    async def delete_thread(tid: str):
        await runner.stop(tid)
        store.delete(tid)
        bus.emit("threads")
        return {"ok": True}

    @app.post("/api/permissions/{req_id}")
    def answer_permission(req_id: str, body: PermissionBody):
        if not runner.answer(req_id, body.allow, body.remember):
            raise HTTPException(404, "that request is no longer waiting")
        return {"ok": True}

    # ----------------------------------------------------------------------- styles
    @app.get("/api/styles")
    def get_styles():
        return library.styles(ws)

    @app.put("/api/styles/active")
    def put_style(body: StyleBody):
        if body.name not in {s["name"] for s in library.styles(ws)["styles"]}:
            raise ValueError(f"unknown style {body.name!r}")
        library.quiet(workspace_cli.main, ["--workspace", str(ws), "set", f"style.active={body.name}"])
        bus.emit("workspace")
        return library.styles(ws)

    @app.post("/api/styles/sample")
    async def post_style_sample(file: UploadFile = File(...), name: str = Form(""),
                                effort: str | None = Form(None)):
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", pathlib.Path(file.filename or "sample").name)[-80:]
        if pathlib.Path(safe).suffix.lower() not in SAMPLE_TYPES:
            raise ValueError("send the sample CV as PDF, DOCX, HTML or an image")
        dest = settings.web_dir(ws) / "uploads" / f"{time.strftime('%Y%m%d-%H%M%S')}-{safe}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(await file.read())
        t = store.create("style", name or safe, effort=effort or settings.load(ws)["effort"])
        await runner.send(t["id"], prompts.style(dest, name), effort=effort, shown=safe)
        return store.get(t["id"])

    # ----------------------------------------------------------------------- live updates
    @app.get("/api/events")
    async def events(request: Request):
        q = bus.subscribe()

        async def stream():
            try:
                yield f"event: hello\ndata: {now()}\n\n"
                while not await request.is_disconnected():
                    try:
                        msg = await asyncio.wait_for(q.get(), timeout=15)
                        yield f"data: {msg}\n\n"
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
            finally:
                bus.unsubscribe(q)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"cache-control": "no-cache", "x-accel-buffering": "no"})

    # ----------------------------------------------------------------------- the UI
    @app.get("/{path:path}")
    def ui(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        dist = UI_DIST.resolve()
        f = (dist / path).resolve()
        if path and f.is_file() and dist in f.parents:
            immutable = "/assets/" in f.as_posix()
            return FileResponse(f, headers={"cache-control": "public, max-age=31536000, immutable"}
                                if immutable else {"cache-control": "no-cache"})
        page = dist / "index.html"
        if not page.is_file():
            return Response("The web UI is not built: npm --prefix web/ui ci && npm --prefix web/ui run build",
                            status_code=500)
        return FileResponse(page, headers={"cache-control": "no-cache"})

    return app
