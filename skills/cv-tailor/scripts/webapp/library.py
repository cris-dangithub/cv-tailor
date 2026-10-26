"""Read side of the workspace for the web app: applications, their files and the PDFs.

Everything goes through index.py so the web app and the agent sessions see the same data.
"""
from __future__ import annotations

import contextlib
import io
import pathlib
import re

import index
from common import STATUSES, list_styles, load_config, read_json

PDF_RE = re.compile(r"-(?P<lang>[A-Z]{2,3})(?:-v(?P<v>\d+))?\.pdf$")
VIEWABLE = {".pdf": "application/pdf", ".md": "text/markdown; charset=utf-8"}


class NotFound(Exception):
    pass


def quiet(fn, *args, **kw):
    """Call an index.py command: its prints are dropped and sys.exit becomes an exception."""
    with contextlib.redirect_stdout(io.StringIO()) as out:
        try:
            fn(*args, **kw)
        except SystemExit as e:
            raise NotFound(str(e.code)) from None
    return out.getvalue()


def app_dir(ws, app_id: str) -> pathlib.Path:
    try:
        return index.find_app(ws, app_id)
    except SystemExit as e:
        raise NotFound(str(e.code)) from None


def _row(m: dict) -> dict:
    d = pathlib.Path(m["_dir"])
    return {k: m.get(k) for k in ("id", "company", "role", "location", "url", "date", "languages",
                                  "style", "status", "keywords", "summary", "status_history",
                                  "versions", "updated")} | {"folder": d.name,
                                                             "pdfs": len(list(d.glob("*.pdf")))}


def applications(ws, q: str = "", status: str | None = None) -> list[dict]:
    if q.strip():
        hits = index.search(ws, q, top=200, status=status)
        by_id = {m["id"]: m for m in index.all_meta(ws)}
        return [_row(by_id[h["id"]]) for h in hits if h["id"] in by_id]
    rows = [_row(m) for m in index.all_meta(ws)]
    if status:
        rows = [r for r in rows if r["status"] == status]
    return list(reversed(rows))  # newest first


def pdfs_of(d: pathlib.Path, meta: dict) -> list[dict]:
    current = {(f or {}).get("pdf") for f in (meta.get("files") or {}).values()}
    out = []
    for p in sorted(d.glob("*.pdf")):
        m = PDF_RE.search(p.name)
        ver = read_json(p.with_name(p.name + ".verify.json"), {}) or {}
        st = p.stat()
        out.append({"name": p.name, "lang": (m.group("lang").lower() if m else None),
                    "version": int(m.group("v")) if m and m.group("v") else 1,
                    "current": p.name in current, "size": st.st_size, "modified": st.st_mtime,
                    "pages": ver.get("pages"), "fits": ver.get("fits"),
                    "broken_links": len(ver.get("broken_links") or []),
                    "pending": len(ver.get("pending_markers") or [])})
    return out


def application(ws, app_id: str) -> dict:
    d = app_dir(ws, app_id)
    meta = read_json(d / "meta.json", {})

    def text(name):
        p = d / name
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None

    return {**{k: v for k, v in meta.items() if not k.startswith("_")}, "folder": d.name,
            "pdfs": pdfs_of(d, meta), "report": text("report.md"), "feedback": text("feedback.md"),
            "offer": text("offer.md"), "positioning": text("positioning.md")}


def all_pdfs(ws) -> list[dict]:
    out = []
    for m in reversed(index.all_meta(ws)):
        d = pathlib.Path(m["_dir"])
        for p in pdfs_of(d, m):
            out.append({**p, "app_id": m["id"], "company": m.get("company"), "role": m.get("role"),
                        "status": m.get("status"), "date": m.get("date")})
    return out


def app_file(ws, app_id: str, name: str) -> pathlib.Path:
    """A file the browser may open: a direct child of the application folder, PDF or Markdown."""
    d = app_dir(ws, app_id).resolve()
    if "/" in name or "\\" in name or name.startswith("."):
        raise NotFound(name)
    p = (d / name).resolve()
    if p.parent != d or p.suffix.lower() not in VIEWABLE or not p.is_file():
        raise NotFound(name)
    return p


def set_status(ws, app_id: str, status: str, note: str = "") -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    quiet(index.main, ["--workspace", str(ws), "status", str(app_id), status, "--note", note or ""])
    return application(ws, app_id)


def workspace_info(ws) -> dict:
    cfg = load_config(ws)
    counts = {s: 0 for s in STATUSES}
    for m in index.all_meta(ws):
        counts[m.get("status", "generated")] = counts.get(m.get("status", "generated"), 0) + 1
    return {"path": str(ws), "name": pathlib.Path(ws).name,
            "candidate": (cfg.get("candidate") or {}).get("name", ""),
            "ui_language": cfg.get("ui_language") or "en", "cv_languages": cfg.get("cv_languages") or [],
            "style": (cfg.get("style") or {}).get("active", "default"), "statuses": STATUSES,
            "counts": counts, "total": sum(counts.values())}


def styles(ws) -> dict:
    cfg = load_config(ws)
    active = (cfg.get("style") or {}).get("active", "default")
    return {"active": active, "history": (cfg.get("style") or {}).get("history", []),
            "styles": [{**s, "active": s["name"] == active} for s in list_styles(ws)]}
