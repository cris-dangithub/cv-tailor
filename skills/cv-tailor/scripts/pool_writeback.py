#!/usr/bin/env python3
"""
Safety net for pool write-back: snapshot the pool before its managing skill writes to it,
record what changed, and undo it (all or per file).

cv-tailor never writes into the pool itself. When the pool is managed by a skill that allows
updates, a sub-agent using THAT skill writes; this script only photographs, diffs and restores.

    pool_writeback.py snapshot --app 12 [--source N]      -> prints {"run": ..., "dir": ..., "pool": ...}
    pool_writeback.py finish RUN --summary "plain words: what was learned and saved"
    pool_writeback.py diff RUN                             # technical diff (for the agent)
    pool_writeback.py rollback RUN [--files REL ...] [--force]
    pool_writeback.py list [--app 12]

Exit codes: 4 = write-back not possible (off, no managing skill, not a local folder, too big).
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import pathlib
import shutil
import sys
import datetime as dt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (WS_MARKER, load_config, now, read_json, require_workspace,  # noqa: E402
                    write_json)
from workspace import SKIP_DIRS  # noqa: E402

TEXT_EXT = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".csv", ".tsv", ".toml",
            ".html", ".htm", ".rst", ".tex", ".xml", ".ini", ".cfg", ".org", ".adoc"}
MAX_TEXT_FILE = 2 * 1024 * 1024        # copied for rollback up to this size
MAX_TEXT_TOTAL = 100 * 1024 * 1024     # beyond this, no write-back
HASH_LIMIT = 50 * 1024 * 1024          # bigger files: size + mtime instead of a hash


def runs_dir(ws) -> pathlib.Path:
    return ws / WS_MARKER / "pool-writeback"


def fail(msg: str):
    print(f"WRITEBACK_UNAVAILABLE: {msg}")
    sys.exit(4)


def writable_source(ws, index: int | None) -> tuple[int, pathlib.Path]:
    cfg = load_config(ws)
    pool = cfg.get("pool") or {}
    if pool.get("writeback", "auto") == "off":
        fail("pool.writeback is off in the config")
    srcs = pool.get("sources", [])
    mgr = pool.get("manager") or {}
    i = index if index is not None else pool.get("writeback_source", mgr.get("source"))
    if i is None:
        fail("no managing skill recorded for the pool (run the manager probe first)")
    if not 0 <= int(i) < len(srcs):
        fail(f"pool source {i} does not exist")
    src = srcs[int(i)]
    if src.get("type") != "path":
        fail("only local folders or files can be updated")
    if not mgr.get("can_update"):
        fail("the pool's managing skill does not allow updates")
    return int(i), pathlib.Path(src["path"])


def walk(root: pathlib.Path):
    if root.is_file():
        yield root.parent, root
        return
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            yield root, pathlib.Path(d) / f


def signature(p: pathlib.Path) -> dict:
    st = p.stat()
    if st.st_size > HASH_LIMIT:
        return {"size": st.st_size, "sig": f"size:{st.st_size}:mtime:{int(st.st_mtime)}"}
    return {"size": st.st_size, "sig": hashlib.sha256(p.read_bytes()).hexdigest()}


def manifest(root: pathlib.Path) -> dict:
    out = {}
    for base, f in walk(root):
        try:
            out[f.relative_to(base).as_posix()] = signature(f)
        except OSError:
            continue
    return out


def base_of(root: pathlib.Path) -> pathlib.Path:
    return root.parent if root.is_file() else root


def is_text(rel: str, size: int) -> bool:
    return pathlib.Path(rel).suffix.lower() in TEXT_EXT and size <= MAX_TEXT_FILE


# --------------------------------------------------------------------------- commands
def snapshot(ws, app: str, source: int | None) -> dict:
    i, root = writable_source(ws, source)
    if not root.exists():
        fail(f"pool path not found: {root}")
    man = manifest(root)
    total = sum(v["size"] for k, v in man.items() if is_text(k, v["size"]))
    if total > MAX_TEXT_TOTAL:
        fail(f"the pool has {total // 2**20} MB of text files; the rollback copy limit is "
             f"{MAX_TEXT_TOTAL // 2**20} MB")
    run = f"{dt.datetime.now():%Y%m%d-%H%M%S}-{str(app).zfill(6) if str(app).isdigit() else app}"
    d = runs_dir(ws) / run
    (d / "files").mkdir(parents=True)
    base = base_of(root)
    for rel, v in man.items():
        if is_text(rel, v["size"]):
            target = d / "files" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(base / rel, target)
    write_json(d / "before.json", {"date": now(), "app": str(app), "source": i, "pool": str(root),
                                   "files": man})
    out = {"run": run, "dir": str(d), "pool": str(root)}
    print(json.dumps(out, ensure_ascii=False))
    return out


def changes(before: dict, after: dict) -> dict:
    b, a = before["files"], after["files"]
    return {"created": sorted(set(a) - set(b)), "deleted": sorted(set(b) - set(a)),
            "modified": sorted(k for k in set(a) & set(b) if a[k]["sig"] != b[k]["sig"])}


def text_diff(d: pathlib.Path, base: pathlib.Path, ch: dict) -> str:
    parts = []
    for rel in ch["modified"] + ch["created"] + ch["deleted"]:
        old_p, new_p = d / "files" / rel, base / rel
        old = old_p.read_text(encoding="utf-8", errors="replace").splitlines() if old_p.exists() else []
        new = new_p.read_text(encoding="utf-8", errors="replace").splitlines() \
            if new_p.exists() and pathlib.Path(rel).suffix.lower() in TEXT_EXT else []
        if not old and not new and rel not in ch["deleted"]:
            parts.append(f"### {rel}\n(binary or too large: no diff, no rollback copy)\n")
            continue
        diff = "\n".join(difflib.unified_diff(old, new, f"before/{rel}", f"after/{rel}", lineterm=""))
        parts.append(f"### {rel}\n```diff\n{diff}\n```\n")
    return "\n".join(parts) or "(no changes)\n"


def app_dir(ws, app: str) -> pathlib.Path | None:
    root = ws / "applications"
    if not str(app).isdigit() or not root.is_dir():
        return None
    for d in root.iterdir():
        head = d.name.split("-", 1)[0]
        if d.is_dir() and head.isdigit() and int(head) == int(app):
            return d
    return None


def record(ws, app: str, entry: dict) -> None:
    """Append/update the run in the application's meta.json (and refresh its report)."""
    d = app_dir(ws, app)
    if not d or not (d / "meta.json").exists():
        return
    meta = read_json(d / "meta.json")
    runs = [r for r in meta.get("pool_writeback", []) if r.get("run") != entry["run"]]
    runs.append(entry)
    meta["pool_writeback"] = runs
    meta["updated"] = now()
    write_json(d / "meta.json", meta)
    try:
        import report  # noqa: PLC0415
        report.update(ws, d)
    except Exception as e:  # noqa: BLE001  (a report problem must never break the write-back)
        print(f"(report not refreshed: {e})")


def finish(ws, run: str, summary: str, not_sent: str) -> dict:
    d = runs_dir(ws) / run
    before = read_json(d / "before.json")
    if not before:
        sys.exit(f"unknown run {run}")
    root = pathlib.Path(before["pool"])
    after = {"date": now(), "files": manifest(root)}
    write_json(d / "after.json", after)
    ch = changes(before, after)
    write_json(d / "changes.json", ch)
    (d / "diff.md").write_text(text_diff(d, base_of(root), ch), encoding="utf-8")
    n = sum(len(v) for v in ch.values())
    entry = {"run": run, "date": after["date"][:10], "status": "written" if n else "nothing-new",
             "summary": summary, "not_sent": not_sent, "files_changed": n, "rolled_back": None}
    record(ws, before["app"], entry)
    print(json.dumps({"run": run, **ch}, ensure_ascii=False, indent=2))
    return ch


def rollback(ws, run: str, files: list[str] | None, force: bool) -> dict:
    d = runs_dir(ws) / run
    before, after = read_json(d / "before.json"), read_json(d / "after.json")
    if not before or not after:
        sys.exit(f"run {run} is not finished; nothing to roll back")
    root = pathlib.Path(before["pool"])
    base = base_of(root)
    ch = read_json(d / "changes.json")
    todo = {k: v for k, v in ch.items()}
    if files:
        todo = {k: [f for f in v if f in files] for k, v in ch.items()}
    done, refused, lost, already = [], [], [], []
    for kind, rels in todo.items():
        for rel in rels:
            cur = base / rel
            expected, original = after["files"].get(rel), before["files"].get(rel)
            now_sig = signature(cur)["sig"] if cur.exists() else None
            if now_sig == (original["sig"] if original else None):
                already.append(rel)  # restored by an earlier (partial) rollback
                continue
            if not force and now_sig != (expected["sig"] if expected else None):
                refused.append(rel)  # changed again after the write-back: don't clobber it
                continue
            if kind == "created":
                if cur.exists():
                    cur.unlink()
                done.append(rel)
            else:
                copy = d / "files" / rel
                if not copy.exists():
                    lost.append(rel)
                    continue
                cur.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(copy, cur)
                done.append(rel)
    total = sum(len(v) for v in ch.values())
    log = read_json(d / "rollback.json", []) or []
    log.append({"date": now(), "files": done, "already": already, "refused": refused, "no_copy": lost})
    write_json(d / "rollback.json", log)
    prev = {}
    app = app_dir(ws, before["app"])
    if app:
        prev = next((r for r in read_json(app / "meta.json", {}).get("pool_writeback", [])
                     if r.get("run") == run), {})
    if done or already:
        restored = set(prev.get("restored_files", [])) | set(done) | set(already)
        record(ws, before["app"], {**prev, "run": run,
                                   "rolled_back": "all" if len(restored) == total else "partial",
                                   "rolled_back_on": now()[:10], "restored_files": sorted(restored)})
    out = {"restored": done, "already_restored": already, "refused_changed_since": refused,
           "no_backup_copy": lost}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def list_runs(ws, app: str | None):
    root = runs_dir(ws)
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        b = read_json(d / "before.json", {})
        if app and str(int(b.get("app", "0") or 0)) != str(int(app)):
            continue
        ch = read_json(d / "changes.json")
        state = "unfinished" if ch is None else f"{sum(len(v) for v in ch.values())} file(s) changed"
        rb = " rolled back" if (d / "rollback.json").exists() else ""
        print(f"{d.name}  app {b.get('app')}  {state}{rb}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("snapshot")
    p.add_argument("--app", required=True, help="application id the facts came from")
    p.add_argument("--source", type=int, default=None)
    p = sub.add_parser("finish")
    p.add_argument("run")
    p.add_argument("--summary", default="", help="plain-language sentence for the report: what was saved")
    p.add_argument("--not-sent", default="", help="plain-language note: what was not saved and why")
    p = sub.add_parser("diff")
    p.add_argument("run")
    p = sub.add_parser("rollback")
    p.add_argument("run")
    p.add_argument("--files", nargs="*", default=None, help="relative paths; default: everything")
    p.add_argument("--force", action="store_true", help="restore even files changed after the write-back")
    p = sub.add_parser("list")
    p.add_argument("--app", default=None)
    a = ap.parse_args(argv)
    ws = require_workspace(a.workspace)
    if a.cmd == "snapshot":
        snapshot(ws, a.app, a.source)
    elif a.cmd == "finish":
        finish(ws, a.run, a.summary, a.not_sent)
    elif a.cmd == "diff":
        print((runs_dir(ws) / a.run / "diff.md").read_text(encoding="utf-8"))
    elif a.cmd == "rollback":
        rollback(ws, a.run, a.files, a.force)
    else:
        list_runs(ws, a.app)


if __name__ == "__main__":
    main()
