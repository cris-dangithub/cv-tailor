"""Per-workspace settings of the web app, kept in <ws>/.cv-tailor/web/settings.json."""
from __future__ import annotations

import pathlib
import secrets

from common import WS_MARKER, read_json, write_json

EFFORTS = ["low", "medium", "high", "xhigh", "max"]
DEFAULTS = {
    "model": "claude-opus-5-5",
    "effort": "high",
    "autocompact": "100k",  # small window: the CLI compacts early, so long chats stay cheap
    "concurrency": 2,
    "ui_language": None,    # None = the workspace's ui_language
    "always_allow": [],     # permission rules the user ticked "remember" on
}


def web_dir(ws: pathlib.Path) -> pathlib.Path:
    d = pathlib.Path(ws) / WS_MARKER / "web"
    if not d.is_dir():
        d.mkdir(parents=True)
        ignore = d.parent / ".gitignore"  # chats and the access token never belong in a repo
        if ignore.is_file() and "web/" not in ignore.read_text(encoding="utf-8").split():
            with open(ignore, "a", encoding="utf-8") as fh:
                fh.write("web/\n")
    return d


def load(ws) -> dict:
    return {**DEFAULTS, **(read_json(web_dir(ws) / "settings.json", {}) or {})}


def save(ws, changes: dict) -> dict:
    cur = load(ws)
    for k, v in changes.items():
        if k not in DEFAULTS:
            continue
        if k == "effort" and v not in EFFORTS:
            raise ValueError(f"effort must be one of {EFFORTS}")
        if k == "concurrency":
            v = max(1, min(int(v), 6))
        if k == "autocompact" and not (v == "auto" or str(v).rstrip("kKmM").isdigit()):
            raise ValueError("autocompact must be 'auto' or a size such as 100k")
        cur[k] = v
    write_json(web_dir(ws) / "settings.json", cur)
    return cur


def token(ws) -> str:
    """The LAN access token, created once and kept so the phone's link keeps working."""
    p = web_dir(ws) / "token"
    if not p.is_file():
        p.write_text(secrets.token_urlsafe(24), encoding="utf-8")
    return p.read_text(encoding="utf-8").strip()
