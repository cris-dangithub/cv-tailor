"""Shared helpers for the cv-tailor scripts: paths, workspace discovery, config, slugs.

The skill directory is the engine (read-only at runtime). Everything a user produces lives
in a *workspace*: a folder that contains `.cv-tailor/config.yaml`.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import pathlib
import re
import sys
import threading
import time
import unicodedata

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
BUILTIN_STYLES = SKILL_DIR / "styles"
TEMPLATES_DIR = SKILL_DIR / "templates"

WS_MARKER = ".cv-tailor"
CONFIG_NAME = "config.yaml"
APPS_DIR = "applications"
INDEX_NAME = "index.jsonl"

STATUSES = ["generated", "sent", "replied", "interview", "rejected", "offer", "withdrawn"]

# Windows consoles default to a legacy code page; CV text is full of non-ASCII.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def today() -> str:
    return dt.date.today().isoformat()


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def slugify(text: str, max_len: int = 48) -> str:
    """ASCII, lowercase, dash-separated. 'Ingeniero/a de Datos Sr.' -> 'ingeniero-a-de-datos-sr'."""
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    if len(t) > max_len:
        t = t[:max_len].rsplit("-", 1)[0] or t[:max_len]
    return t or "untitled"


# --------------------------------------------------------------------------- yaml
def _yaml():
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        sys.exit("PyYAML is missing. Run: python -m pip install -r <skill>/requirements.txt")
    return yaml


def read_yaml(path: pathlib.Path):
    return _yaml().safe_load(pathlib.Path(path).read_text(encoding="utf-8"))


def write_yaml(path: pathlib.Path, data) -> None:
    text = _yaml().safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    pathlib.Path(path).write_text(text, encoding="utf-8")


def read_json(path: pathlib.Path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, data) -> None:
    pathlib.Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")


# --------------------------------------------------------------------------- workspace
def find_workspace(start: str | os.PathLike | None = None) -> pathlib.Path | None:
    """Walk up from `start` (default: cwd) looking for `.cv-tailor/config.yaml`.

    `CV_TAILOR_WORKSPACE` overrides the search.
    """
    env = os.environ.get("CV_TAILOR_WORKSPACE")
    if env:
        p = pathlib.Path(env).expanduser().resolve()
        return p if (p / WS_MARKER / CONFIG_NAME).is_file() else None
    cur = pathlib.Path(start or os.getcwd()).resolve()
    for d in [cur, *cur.parents]:
        if (d / WS_MARKER / CONFIG_NAME).is_file():
            return d
    return None


def require_workspace(start=None) -> pathlib.Path:
    ws = find_workspace(start)
    if ws is None:
        sys.exit("NO_WORKSPACE: no .cv-tailor/config.yaml here or in any parent folder. "
                 "Run the setup first (workspace.py init).")
    return ws


def load_config(ws: pathlib.Path) -> dict:
    return read_yaml(ws / WS_MARKER / CONFIG_NAME) or {}


def save_config(ws: pathlib.Path, cfg: dict) -> None:
    write_yaml(ws / WS_MARKER / CONFIG_NAME, cfg)


def apps_dir(ws: pathlib.Path) -> pathlib.Path:
    return ws / APPS_DIR


# --------------------------------------------------------------------------- locking
_lock_guard = threading.RLock()
_lock_depth: dict[str, int] = {}


@contextlib.contextmanager
def workspace_lock(ws: pathlib.Path, timeout: float = 60.0):
    """Serialise application writes across processes: several agent sessions and the web app
    can work on one workspace at once, and two of them must never take the same id.

    Re-entrant within a process (save_meta runs inside cmd_new's lock).
    """
    key = str(pathlib.Path(ws).resolve())
    with _lock_guard:
        if _lock_depth.get(key):
            _lock_depth[key] += 1
            try:
                yield
            finally:
                _lock_depth[key] -= 1
            return
        path = pathlib.Path(ws) / WS_MARKER / "index.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a+b") as fh:
            _lock_file(fh, timeout)
            _lock_depth[key] = 1
            try:
                yield
            finally:
                _lock_depth.pop(key, None)
                _unlock_file(fh)


def _lock_file(fh, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if os.name == "nt":
                import msvcrt  # noqa: PLC0415
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl  # noqa: PLC0415
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError:
            if time.monotonic() > deadline:
                sys.exit("LOCKED: another cv-tailor process kept the workspace locked too long.")
            time.sleep(0.05)


def _unlock_file(fh) -> None:
    if os.name == "nt":
        import msvcrt  # noqa: PLC0415
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl  # noqa: PLC0415
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


# --------------------------------------------------------------------------- styles
def resolve_style(name_or_path: str | None, ws: pathlib.Path | None) -> pathlib.Path:
    """A style is a folder with reference.json + cv.css + cv.html.j2.

    Lookup order: explicit path -> workspace styles/<name> -> built-in styles/<name>.
    With no name, the workspace's active style (or 'default').
    """
    if not name_or_path:
        name_or_path = ((load_config(ws).get("style") or {}).get("active") if ws else None) or "default"
    p = pathlib.Path(name_or_path).expanduser()
    candidates = [p] if p.is_absolute() or p.exists() else []
    if ws:
        candidates.append(ws / "styles" / name_or_path)
    candidates.append(BUILTIN_STYLES / name_or_path)
    for c in candidates:
        if (c / "reference.json").is_file() and (c / "cv.html.j2").is_file():
            return c.resolve()
    sys.exit(f"Style not found: {name_or_path!r} (looked in {[str(c) for c in candidates]})")


def list_styles(ws: pathlib.Path | None) -> list[dict]:
    out = []
    roots = [("built-in", BUILTIN_STYLES)] + ([("workspace", ws / "styles")] if ws else [])
    for origin, root in roots:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if (d / "reference.json").is_file():
                ref = read_json(d / "reference.json", {})
                out.append({"name": d.name, "origin": origin, "path": str(d),
                            "description": ref.get("_description", "")})
    return out


def python_cmd() -> str:
    return pathlib.Path(sys.executable).name if sys.executable else "python3"
