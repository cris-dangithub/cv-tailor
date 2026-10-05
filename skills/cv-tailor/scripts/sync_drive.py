#!/usr/bin/env python3
"""
One-way sync of a workspace's applications to Google Drive (workspace -> Drive), in the
background, keeping the same structure:  <Drive>/<folder>/applications/<id>-<slug>/<file>

How it reaches Drive:
  desktop  Google Drive for desktop (Windows, macOS) mounts "My Drive" as a local folder;
           copying a file there is uploading it. No API, no credentials in the skill.
  rclone   Linux (no official client): an rclone remote of type "drive" the user configured.

    sync_drive.py detect                         # where Google Drive is on this computer
    sync_drive.py setup --root "G:/My Drive" --folder cv-tailor --include pdf,report,offer [--method desktop|rclone]
    sync_drive.py disable
    sync_drive.py trigger --app 12 | --all       # queue + start a detached worker, returns at once
    sync_drive.py run [--app 12 | --all | --drain]   # do the work now (the worker uses --drain)
    sync_drive.py status [--app 12] [--json]     # from local state only, never reads Drive
    sync_drive.py clean [--yes]                  # files this sync put in Drive whose source is gone

Never deletes in Drive except with `clean --yes`, and only what it uploaded itself.
CV_TAILOR_SYNC=off disables every trigger (tests use it).
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import pathlib
import platform
import shutil
import string
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (WS_MARKER, load_config, now, read_json, require_workspace,  # noqa: E402
                    save_config, write_json)

INCLUDE = {
    "pdf": lambda n: n.lower().endswith(".pdf"),
    "report": lambda n: n == "report.md",
    "offer": lambda n: n == "offer.md",
    "yaml": lambda n: n.startswith("cv.") and n.endswith((".yml", ".yaml")),
    "review": lambda n: n.endswith("-review.md"),
    "positioning": lambda n: n == "positioning.md",
}
DEFAULT_INCLUDE = ["pdf", "report", "offer"]
MY_DRIVE_NAMES = ["My Drive", "Mi unidad", "Meine Ablage", "Mon Drive", "Il mio Drive", "Meu Drive",
                  "Mijn Drive", "Drive Saya", "Mój dysk", "Min disk", "マイドライブ", "내 드라이브"]
LOCK_STALE_SECONDS = 600


# --------------------------------------------------------------------------- paths
def sync_dir(ws) -> pathlib.Path:
    d = ws / WS_MARKER / "sync"
    (d / "runs").mkdir(parents=True, exist_ok=True)
    return d


def drive_cfg(ws) -> dict:
    return ((load_config(ws).get("sync") or {}).get("google_drive")) or {}


def enabled(ws) -> bool:
    return os.environ.get("CV_TAILOR_SYNC", "").lower() != "off" and bool(drive_cfg(ws).get("enabled"))


# --------------------------------------------------------------------------- detect
def detect(win_letters: str | None = None, home: pathlib.Path | None = None) -> list[dict]:
    """Candidate "My Drive" roots. Parameters exist so tests can point at a fake tree."""
    found = []
    home = home or pathlib.Path.home()
    sysname = platform.system()
    if sysname == "Windows" or win_letters is not None:
        for letter in (win_letters if win_letters is not None else string.ascii_uppercase):
            base = pathlib.Path(f"{letter}:/") if len(letter) == 1 else pathlib.Path(letter)
            for name in MY_DRIVE_NAMES:
                p = base / name
                try:
                    if p.is_dir():
                        found.append({"method": "desktop", "root": str(p), "how": "Google Drive for desktop (drive letter)"})
                except OSError:
                    continue
        for name in MY_DRIVE_NAMES:
            p = home / name
            if p.is_dir():
                found.append({"method": "desktop", "root": str(p), "how": "Google Drive for desktop (mirror folder)"})
    if sysname == "Darwin" or (home / "Library" / "CloudStorage").is_dir():
        for acc in glob.glob(str(home / "Library" / "CloudStorage" / "GoogleDrive-*")):
            for name in MY_DRIVE_NAMES:
                p = pathlib.Path(acc) / name
                if p.is_dir():
                    found.append({"method": "desktop", "root": str(p), "how": f"Google Drive for desktop ({pathlib.Path(acc).name})"})
    rc = shutil.which("rclone")
    if rc:
        r = subprocess.run([rc, "listremotes", "--long"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "drive":
                found.append({"method": "rclone", "root": parts[0], "how": "rclone remote of type drive"})
    return found


def installed_but_not_running() -> bool:
    return platform.system() == "Windows" and any(
        pathlib.Path(os.environ.get(v, ""), "Google", "Drive File Stream").exists()
        for v in ("PROGRAMFILES", "PROGRAMFILES(X86)"))


# --------------------------------------------------------------------------- targets
class Target:
    def __init__(self, cfg: dict):
        self.method = cfg.get("method", "desktop")
        self.root = cfg["root"]
        self.folder = cfg.get("folder", "cv-tailor").strip("/\\")

    def path(self, rel: str) -> str:
        if self.method == "rclone":
            return f"{self.root.rstrip('/')}" + ("" if self.root.endswith(":") else "/") + f"{self.folder}/{rel}"
        return str(pathlib.Path(self.root) / self.folder / rel)

    def check(self) -> None:
        if self.method == "rclone":
            r = subprocess.run(["rclone", "mkdir", self.path("applications")], capture_output=True, text=True)
            if r.returncode:
                raise OSError(r.stderr.strip() or "rclone mkdir failed")
            return
        root = pathlib.Path(self.root)
        if not root.is_dir():
            raise OSError(f"Google Drive folder not available: {root} (is Google Drive running?)")
        probe = pathlib.Path(self.path(".cv-tailor-write-test"))
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()

    def copy(self, src: pathlib.Path, rel: str) -> None:
        if self.method == "rclone":
            r = subprocess.run(["rclone", "copyto", str(src), self.path(rel)], capture_output=True, text=True)
            if r.returncode:
                raise OSError(r.stderr.strip())
            return
        dest = pathlib.Path(self.path(rel))
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f".{dest.name}.cvtpart")
        shutil.copy2(src, tmp)
        os.replace(tmp, dest)  # never leave a half-written file in Drive

    def move(self, old_rel: str, new_rel: str) -> bool:
        if self.method == "rclone":
            r = subprocess.run(["rclone", "moveto", self.path(old_rel), self.path(new_rel)], capture_output=True, text=True)
            return r.returncode == 0
        old, new = pathlib.Path(self.path(old_rel)), pathlib.Path(self.path(new_rel))
        if old.exists() and not new.exists():
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), str(new))
            return True
        return False

    def delete(self, rel: str) -> None:
        if self.method == "rclone":
            subprocess.run(["rclone", "deletefile", self.path(rel)], capture_output=True)
        else:
            p = pathlib.Path(self.path(rel))
            if p.is_file():
                p.unlink()


# --------------------------------------------------------------------------- state
def load_state(ws) -> dict:
    return read_json(sync_dir(ws) / "state.json", {}) or {"apps": {}}


def save_state(ws, st: dict) -> None:
    write_json(sync_dir(ws) / "state.json", st)


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def app_folders(ws) -> dict[int, pathlib.Path]:
    root = ws / "applications"
    out = {}
    if root.is_dir():
        for d in root.iterdir():
            head = d.name.split("-", 1)[0]
            if d.is_dir() and head.isdigit():
                out[int(head)] = d
    return out


# --------------------------------------------------------------------------- run
def sync_app(ws, target: Target, include: list[str], app: int, d: pathlib.Path, st: dict, log: dict) -> None:
    key = str(app)
    entry = st["apps"].setdefault(key, {"folder": d.name, "files": {}})
    # a renumbering renamed the local folder: move it in Drive instead of uploading it again
    if entry.get("folder") and entry["folder"] != d.name:
        if target.move(f"applications/{entry['folder']}", f"applications/{d.name}"):
            log["moved"].append(f"{entry['folder']} -> {d.name}")
        for name, f in entry["files"].items():
            f["target"] = f"applications/{d.name}/{name}"
        entry["folder"] = d.name
    wanted = [p for p in sorted(d.iterdir()) if p.is_file() and any(INCLUDE[k](p.name) for k in include if k in INCLUDE)]
    for p in wanted:
        h = sha(p)
        rel = f"applications/{d.name}/{p.name}"
        f = entry["files"].get(p.name, {})
        if f.get("hash") == h and f.get("status") == "ok" and f.get("target") == rel:
            continue
        try:
            target.copy(p, rel)
            entry["files"][p.name] = {"hash": h, "target": rel, "synced_at": now(), "status": "ok"}
            log["copied"].append(rel)
        except OSError as e:
            entry["files"][p.name] = {**f, "status": "error", "error": str(e)[:200], "tried_at": now()}
            log["errors"].append(f"{rel}: {e}")
    entry["last_sync"] = now()
    entry["status"] = "error" if any(x.get("status") == "error" for x in entry["files"].values()) else "ok"


def run(ws, apps: list[int] | None) -> dict:
    cfg = drive_cfg(ws)
    t0 = time.time()
    log = {"started": now(), "apps": [], "copied": [], "moved": [], "errors": []}
    st = load_state(ws)
    folders = app_folders(ws)
    targets = sorted(folders) if apps is None else [a for a in apps if a in folders]
    try:
        target = Target(cfg)
        target.check()
    except (OSError, KeyError) as e:
        log["errors"].append(f"Drive not available: {e}")
        for a in targets:
            st["apps"].setdefault(str(a), {"folder": folders[a].name, "files": {}})["status"] = "pending"
        queue_add(ws, targets)
    else:
        include = cfg.get("include") or DEFAULT_INCLUDE
        for a in targets:
            log["apps"].append(a)
            sync_app(ws, target, include, a, folders[a], st, log)
    log["seconds"] = round(time.time() - t0, 2)
    st["last_run"] = {k: (len(v) if isinstance(v, list) else v) for k, v in log.items()}
    save_state(ws, st)
    write_json(sync_dir(ws) / "runs" / f"{dt.datetime.now():%Y%m%d-%H%M%S-%f}.json", log)
    return log


# --------------------------------------------------------------------------- queue + worker
def queue_add(ws, apps: list[int] | None) -> None:
    q = sync_dir(ws) / "pending.json"
    cur = read_json(q, []) or []
    if apps is None:
        cur = ["all"]
    elif "all" not in cur:
        cur = sorted(set(cur) | set(apps))
    write_json(q, cur)


def queue_take(ws) -> list | None:
    q = sync_dir(ws) / "pending.json"
    cur = read_json(q, []) or []
    if not cur:
        return None
    write_json(q, [])
    return cur


def acquire_lock(ws) -> bool:
    lock = sync_dir(ws) / "lock"
    if lock.exists() and time.time() - lock.stat().st_mtime > LOCK_STALE_SECONDS:
        lock.unlink(missing_ok=True)  # a crashed worker left it behind
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.write(fd, f"{os.getpid()} {now()}".encode())
    os.close(fd)
    return True


def release_lock(ws) -> None:
    (sync_dir(ws) / "lock").unlink(missing_ok=True)


def drain(ws) -> None:
    if not acquire_lock(ws):
        return  # another worker is running; it will pick up the queue
    try:
        while True:
            batch = queue_take(ws)
            if batch is None:
                break
            run(ws, None if "all" in batch else [int(x) for x in batch])
            # a failure re-queues; don't spin on it within the same worker
            if (read_json(sync_dir(ws) / "state.json", {}) or {}).get("last_run", {}).get("errors"):
                break
    finally:
        release_lock(ws)


def spawn_worker(ws) -> None:
    logf = open(sync_dir(ws) / "worker.log", "a", encoding="utf-8")  # noqa: SIM115
    cmd = [sys.executable, str(pathlib.Path(__file__).resolve()), "--workspace", str(ws), "run", "--drain"]
    kw = {"stdin": subprocess.DEVNULL, "stdout": logf, "stderr": logf, "cwd": str(ws)}
    if platform.system() == "Windows":
        kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED | NEW_GROUP | NO_WINDOW
    else:
        kw["start_new_session"] = True
    subprocess.Popen(cmd, **kw)


def trigger(ws, app: int | None = None, everything: bool = False) -> bool:
    """Queue an application (or all) and make sure a background worker runs. Never blocks."""
    if not enabled(ws):
        return False
    queue_add(ws, None if everything else [int(app)])
    lock = sync_dir(ws) / "lock"
    if not lock.exists() or time.time() - lock.stat().st_mtime > LOCK_STALE_SECONDS:
        spawn_worker(ws)
    return True


# --------------------------------------------------------------------------- status / clean
def ago(iso: str | None) -> str:
    if not iso:
        return "never"
    s = (dt.datetime.now() - dt.datetime.fromisoformat(iso)).total_seconds()
    return f"{int(s)}s ago" if s < 90 else f"{int(s // 60)} min ago" if s < 5400 else f"{int(s // 3600)} h ago" \
        if s < 129600 else iso[:10]


def status(ws, app: int | None) -> dict:
    st = load_state(ws)
    cfg = drive_cfg(ws)
    pend = read_json(sync_dir(ws) / "pending.json", []) or []
    apps = {}
    for k, e in st.get("apps", {}).items():
        if app is not None and int(k) != int(app):
            continue
        files = e.get("files", {})
        apps[k] = {"folder": e.get("folder"), "status": e.get("status"),
                   "files_ok": sum(1 for f in files.values() if f.get("status") == "ok"),
                   "files_error": [n for n, f in files.items() if f.get("status") == "error"],
                   "last_sync": e.get("last_sync"), "last_sync_ago": ago(e.get("last_sync"))}
    return {"enabled": bool(cfg.get("enabled")), "destination": Target(cfg).path("applications") if cfg.get("root") else None,
            "running": (sync_dir(ws) / "lock").exists(), "pending": pend,
            "last_run": st.get("last_run"), "apps": apps}


def clean(ws, yes: bool) -> list[str]:
    st = load_state(ws)
    folders = app_folders(ws)
    orphans = []
    for k, e in st.get("apps", {}).items():
        d = folders.get(int(k))
        for name, f in list(e.get("files", {}).items()):
            if d is None or not (d / name).exists():
                orphans.append(f["target"])
                if yes:
                    Target(drive_cfg(ws)).delete(f["target"])
                    del e["files"][name]
    if yes:
        save_state(ws, st)
    return orphans


# --------------------------------------------------------------------------- setup
def setup(ws, root: str, folder: str, include: list[str], method: str) -> dict:
    bad = [i for i in include if i not in INCLUDE]
    if bad:
        sys.exit(f"unknown include values {bad}; choose from {sorted(INCLUDE)}")
    if method == "desktop":
        root = str(pathlib.Path(root).expanduser().resolve())
    gd = {"enabled": True, "method": method, "root": root, "folder": folder, "include": include}
    try:
        Target(gd).check()
    except OSError as e:
        print(f"DRIVE_NOT_WRITABLE: {e}")
        sys.exit(4)
    cfg = load_config(ws)
    cfg.setdefault("sync", {})["google_drive"] = gd
    save_config(ws, cfg)
    return gd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect")
    p = sub.add_parser("setup")
    p.add_argument("--root", required=True)
    p.add_argument("--folder", default="cv-tailor")
    p.add_argument("--include", default=",".join(DEFAULT_INCLUDE))
    p.add_argument("--method", choices=["desktop", "rclone"], default="desktop")
    sub.add_parser("disable")
    for name in ("trigger", "run"):
        p = sub.add_parser(name)
        p.add_argument("--app", type=int, default=None)
        p.add_argument("--all", action="store_true")
        if name == "run":
            p.add_argument("--drain", action="store_true", help="process the queue (background worker)")
    p = sub.add_parser("status")
    p.add_argument("--app", type=int, default=None)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("clean")
    p.add_argument("--yes", action="store_true", help="delete them (ask the user first)")
    a = ap.parse_args(argv)

    if a.cmd == "detect":
        found = detect()
        print(json.dumps({"found": found, "installed_but_not_running": not found and installed_but_not_running(),
                          "install_url": "https://www.google.com/drive/download/"}, ensure_ascii=False, indent=2))
        return
    ws = require_workspace(a.workspace)
    if a.cmd == "setup":
        print(json.dumps(setup(ws, a.root, a.folder, [x.strip() for x in a.include.split(",") if x.strip()], a.method),
                         ensure_ascii=False, indent=2))
    elif a.cmd == "disable":
        cfg = load_config(ws)
        cfg.setdefault("sync", {}).setdefault("google_drive", {})["enabled"] = False
        save_config(ws, cfg)
        print("Google Drive sync disabled")
    elif a.cmd == "trigger":
        print("queued" if trigger(ws, a.app, a.all or a.app is None) else "sync disabled")
    elif a.cmd == "run":
        if a.drain:
            drain(ws)
        else:
            print(json.dumps(run(ws, None if a.all or a.app is None else [a.app]), ensure_ascii=False, indent=2))
    elif a.cmd == "status":
        s = status(ws, a.app)
        if a.json:
            print(json.dumps(s, ensure_ascii=False, indent=2))
        else:
            print(f"Google Drive sync: {'on' if s['enabled'] else 'off'}  ->  {s['destination']}")
            print(f"running: {s['running']}   pending: {s['pending'] or 'none'}")
            for k, e in sorted(s["apps"].items(), key=lambda kv: int(kv[0])):
                err = f"  errors: {e['files_error']}" if e["files_error"] else ""
                print(f"  {int(k):06d}  {e['status']:<8} {e['files_ok']} file(s) up to date, last {e['last_sync_ago']}{err}")
    else:
        orphans = clean(ws, a.yes)
        print(json.dumps({"deleted" if a.yes else "would_delete": orphans}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
