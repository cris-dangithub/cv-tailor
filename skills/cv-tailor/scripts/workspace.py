#!/usr/bin/env python3
"""
Workspace management: create, inspect and change a cv-tailor workspace.

A workspace is the folder where the user set the skill up. It holds everything the user
produces; the skill folder holds only the engine.

    workspace.py find                                   # prints the workspace path or NO_WORKSPACE
    workspace.py init --root . --ui-language es --cv-languages en,es \
                      --pool "C:/me/cv-notes" --pool https://me.dev --pool github:octocat
    workspace.py show
    workspace.py set style.active=modern  cv_languages=en,es,id  ui_language=en
    workspace.py add-pool PATH|URL|github:USER   /   remove-pool INDEX
    workspace.py scan-pool [--save]                     # skills, documents, writing samples in the pool
    workspace.py styles                                 # built-in + workspace styles
    workspace.py refresh-instructions                   # rewrite the CLAUDE.md / AGENTS.md block
    workspace.py set-manager --json '{"source":0,"skill":"kb","can_update":true,"has_not_done_section":false}'
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (CONFIG_NAME, SKILL_DIR, TEMPLATES_DIR, WS_MARKER, find_workspace,  # noqa: E402
                    list_styles, load_config, require_workspace, save_config, today)

BLOCK_START, BLOCK_END = "<!-- cv-tailor:start -->", "<!-- cv-tailor:end -->"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next",
             ".cache", "target", ".idea", ".vscode", WS_MARKER}
DOC_EXT = {".pdf", ".docx", ".doc", ".odt", ".md", ".txt", ".rtf", ".html", ".htm", ".json",
           ".yaml", ".yml", ".csv", ".tex"}
SAMPLE_RE = re.compile(r"cv|resume|r[eé]sum[eé]|curriculum|hoja.?de.?vida|cover|carta|linkedin|"
                       r"about|bio|perfil|profile|post|blog|article|articulo|email|correo", re.I)
GUIDE_RE = re.compile(r"style|voice|voz|tono|tone|escritura|writing|redacci", re.I)


def pool_entry(spec: str) -> dict:
    s = spec.strip()
    if s.lower().startswith("github:"):
        user = s.split(":", 1)[1].strip()
        return {"type": "github", "owners": [{"name": user, "kind": "user", "account": user}],
                "identities": [user], "since": None}
    if re.match(r"^https?://", s, re.I):
        return {"type": "url", "url": s}
    p = pathlib.Path(s).expanduser()
    if not p.exists():
        sys.exit(f"Pool path does not exist: {s}")
    return {"type": "path", "path": str(p.resolve()), "kind": "dir" if p.is_dir() else "file"}


# --------------------------------------------------------------------------- instructions
def render_template(name: str, cfg: dict) -> str:
    t = (TEMPLATES_DIR / "workspace" / name).read_text(encoding="utf-8")
    return (t.replace("{{ui_language}}", str(cfg.get("ui_language", "en")))
             .replace("{{cv_languages}}", ", ".join(cfg.get("cv_languages", [])))
             .replace("{{skill_dir}}", str(SKILL_DIR)))


def write_block(path: pathlib.Path, block: str) -> str:
    block = f"{BLOCK_START}\n{block.strip()}\n{BLOCK_END}\n"
    if path.is_file():
        cur = path.read_text(encoding="utf-8")
        if BLOCK_START in cur and BLOCK_END in cur:
            # a function as replacement: Windows paths in the block contain backslashes
            new = re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END) + r"\n?",
                         lambda _m: block, cur, flags=re.S)
            path.write_text(new, encoding="utf-8")
            return "updated"
        path.write_text(cur.rstrip() + "\n\n" + block, encoding="utf-8")
        return "appended"
    path.write_text(block, encoding="utf-8")
    return "created"


def refresh_instructions(ws: pathlib.Path) -> None:
    cfg = load_config(ws)
    for name in ("CLAUDE.md", "AGENTS.md"):
        print(f"{name}: {write_block(ws / name, render_template(name, cfg))}")


# --------------------------------------------------------------------------- commands
def cmd_init(a):
    root = pathlib.Path(a.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / WS_MARKER / CONFIG_NAME).exists() and not a.force:
        sys.exit(f"ALREADY_CONFIGURED: {root} is already a workspace (use --force to overwrite the config)")
    cfg = {
        "version": 1,
        "created": today(),
        "ui_language": a.ui_language,
        "cv_languages": [x.strip() for x in a.cv_languages.split(",") if x.strip()],
        "candidate": {"name": a.candidate or ""},
        "pool": {"sources": [pool_entry(p) for p in a.pool or []], "skills": [], "inventory": {},
                 "writeback": "auto", "manager": None},
        "style": {"active": "default", "history": [{"style": "default", "date": today()}]},
        "numbering": {"width": 6},
        "skill_dir": str(SKILL_DIR),
    }
    (root / WS_MARKER).mkdir(exist_ok=True)
    save_config(root, cfg)
    (root / WS_MARKER / ".gitignore").write_text("style-cache/\ncache/\n", encoding="utf-8")
    for d in ("applications", "learnings", "profile/samples", "styles"):
        (root / d).mkdir(parents=True, exist_ok=True)
    seeds = {
        "learnings/facts.md": (TEMPLATES_DIR / "workspace" / "facts.md"),
        "learnings/preferences.md": (TEMPLATES_DIR / "workspace" / "preferences.md"),
        "profile/voice.md": (TEMPLATES_DIR / "workspace" / "voice.md"),
    }
    for rel, src in seeds.items():
        if not (root / rel).exists():
            (root / rel).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    refresh_instructions(root)
    print(json.dumps({"workspace": str(root), "config": cfg}, ensure_ascii=False, indent=2))


def set_dotted(cfg: dict, key: str, value: str):
    parts = key.split(".")
    cur = cfg
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    if parts[-1] in ("cv_languages",) or key.endswith(".identities"):
        value = [x.strip() for x in value.split(",") if x.strip()]
    elif value.isdigit():
        value = int(value)
    cur[parts[-1]] = value


def cmd_set(a):
    ws = require_workspace(a.workspace)
    cfg = load_config(ws)
    for kv in a.pairs:
        k, _, v = kv.partition("=")
        set_dotted(cfg, k.strip(), v.strip())
        if k.strip() == "style.active":
            cfg["style"].setdefault("history", []).append({"style": v.strip(), "date": today()})
    save_config(ws, cfg)
    if any(kv.split("=")[0] in ("ui_language", "cv_languages") for kv in a.pairs):
        refresh_instructions(ws)
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


def cmd_show(a):
    ws = require_workspace(a.workspace)
    cfg = load_config(ws)
    apps = ws / "applications"
    n = len([d for d in apps.iterdir() if d.is_dir()]) if apps.is_dir() else 0
    print(json.dumps({"workspace": str(ws), "applications": n, "config": cfg}, ensure_ascii=False, indent=2))


def frontmatter(md: pathlib.Path) -> dict:
    t = md.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\s*\n(.*?)\n---", t, re.S)
    out = {}
    if m:
        cur = None
        for line in m.group(1).splitlines():
            mm = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
            if mm:
                cur = mm.group(1)
                out[cur] = mm.group(2).strip().strip(">|").strip()
            elif cur and line.startswith(" "):
                out[cur] = (out[cur] + " " + line.strip()).strip()
    return out


def scan_path(root: pathlib.Path, max_depth=6, max_files=4000) -> dict:
    skills, instructions, samples, guides, counts = [], [], [], [], {}
    seen = 0
    if root.is_file():
        files = [root]
    else:
        files = []
        stack = [(root, 0)]
        while stack and seen < max_files:
            d, depth = stack.pop()
            try:
                entries = sorted(d.iterdir())
            except OSError:
                continue
            for e in entries:
                if e.is_dir():
                    if e.name not in SKIP_DIRS and depth < max_depth:
                        stack.append((e, depth + 1))
                elif e.is_file():
                    files.append(e)
                    seen += 1
    for f in files:
        ext = f.suffix.lower()
        if f.name == "SKILL.md":
            fm = frontmatter(f)
            skills.append({"name": fm.get("name", f.parent.name), "path": str(f.parent),
                           "description": fm.get("description", "")[:300]})
            continue
        if f.name in ("AGENTS.md", "CLAUDE.md"):
            instructions.append(str(f))
        if ext in DOC_EXT:
            counts[ext] = counts.get(ext, 0) + 1
            if GUIDE_RE.search(f.stem):
                guides.append(str(f))
            elif SAMPLE_RE.search(f.stem):
                samples.append(str(f))
    return {"skills": skills, "instructions": instructions, "writing_samples": samples[:50],
            "style_guides": guides[:20], "documents_by_type": counts, "files_scanned": len(files)}


def cmd_scan_pool(a):
    ws = require_workspace(a.workspace)
    cfg = load_config(ws)
    report = []
    all_skills = []
    for i, src in enumerate(cfg.get("pool", {}).get("sources", [])):
        entry = {"index": i, "source": src}
        if src["type"] == "path":
            r = scan_path(pathlib.Path(src["path"]))
            for s in r["skills"]:
                s["source"] = i
            entry.update(r)
            all_skills += r["skills"]
        report.append(entry)
    h = skills_hash(all_skills)
    mgr = cfg.get("pool", {}).get("manager") or {}
    status = {"skills_hash": h,
              "manager_probe": ("needed" if all_skills and not mgr else
                                "outdated: the pool skills changed, probe again" if mgr and mgr.get("skills_hash") != h
                                else "up to date" if mgr else "not applicable: no skills in the pool")}
    if a.save:
        cfg.setdefault("pool", {})["skills"] = all_skills
        cfg["pool"]["skills_hash"] = h
        cfg["pool"]["inventory"] = {"scanned": today(), "sources": [
            {k: v for k, v in e.items() if k in ("index", "documents_by_type", "writing_samples",
                                                  "style_guides", "instructions")} for e in report]}
        save_config(ws, cfg)
    print(json.dumps({"sources": report, "status": status}, ensure_ascii=False, indent=2))


def skills_hash(skills: list[dict]) -> str:
    """Fingerprint of the pool's SKILL.md files: when it changes, the manager probe is stale."""
    h = hashlib.sha256()
    for s in sorted(skills, key=lambda x: x["path"]):
        f = pathlib.Path(s["path"]) / "SKILL.md"
        h.update(s["path"].encode())
        if f.is_file():
            h.update(f.read_bytes())
    return h.hexdigest()[:16] if skills else ""


def cmd_set_manager(a):
    """Store the result of the manager probe (done by an agent reading the pool's skills)."""
    ws = require_workspace(a.workspace)
    cfg = load_config(ws)
    data = json.loads(pathlib.Path(a.json_file).read_text(encoding="utf-8")) if a.json_file else json.loads(a.json)
    required = {"source", "skill", "can_update", "has_not_done_section"}
    missing = required - set(data)
    if missing:
        sys.exit(f"missing keys in the probe result: {sorted(missing)}")
    pool = cfg.setdefault("pool", {})
    data["checked_on"] = today()
    data["skills_hash"] = pool.get("skills_hash") or skills_hash(pool.get("skills", []))
    pool["manager"] = data
    if data.get("can_update") and pool.get("writeback_source") is None:
        pool["writeback_source"] = data["source"]
    save_config(ws, cfg)
    print(json.dumps(pool["manager"], ensure_ascii=False, indent=2))


def cmd_add_pool(a):
    ws = require_workspace(a.workspace)
    cfg = load_config(ws)
    cfg.setdefault("pool", {}).setdefault("sources", []).append(pool_entry(a.spec))
    save_config(ws, cfg)
    print(json.dumps(cfg["pool"]["sources"], ensure_ascii=False, indent=2))


def cmd_remove_pool(a):
    ws = require_workspace(a.workspace)
    cfg = load_config(ws)
    src = cfg.get("pool", {}).get("sources", [])
    if not 0 <= a.index < len(src):
        sys.exit("no pool source with that index")
    removed = src.pop(a.index)
    save_config(ws, cfg)
    print("removed:", json.dumps(removed, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("find")
    p = sub.add_parser("init")
    p.add_argument("--root", default=".")
    p.add_argument("--ui-language", required=True, help="language the skill speaks, e.g. es, en")
    p.add_argument("--cv-languages", required=True, help="comma separated ISO codes, e.g. en,es,id")
    p.add_argument("--pool", action="append", help="path, URL or github:USER (repeatable)")
    p.add_argument("--candidate", default="", help="candidate full name, as it should appear on the CV")
    p.add_argument("--force", action="store_true")
    sub.add_parser("show")
    p = sub.add_parser("set")
    p.add_argument("pairs", nargs="+", help="key=value, dotted keys allowed")
    p = sub.add_parser("add-pool")
    p.add_argument("spec")
    p = sub.add_parser("remove-pool")
    p.add_argument("index", type=int)
    p = sub.add_parser("scan-pool")
    p.add_argument("--save", action="store_true")
    sub.add_parser("styles")
    sub.add_parser("refresh-instructions")
    p = sub.add_parser("set-manager", help="store the pool manager probe result")
    p.add_argument("--json", default=None, help="probe result as a JSON string")
    p.add_argument("--json-file", default=None, help="probe result in a JSON file")
    a = ap.parse_args(argv)

    if a.cmd == "find":
        ws = find_workspace(a.workspace)
        print(ws if ws else "NO_WORKSPACE")
        return
    if a.cmd == "styles":
        ws = find_workspace(a.workspace)
        active = (load_config(ws).get("style") or {}).get("active") if ws else None
        for s in list_styles(ws):
            mark = "*" if s["name"] == (active or "default") else " "
            print(f"{mark} {s['name']:<20} {s['origin']:<10} {s['description'][:90]}")
        return
    if a.cmd == "refresh-instructions":
        refresh_instructions(require_workspace(a.workspace))
        return
    {"init": cmd_init, "show": cmd_show, "set": cmd_set, "scan-pool": cmd_scan_pool,
     "add-pool": cmd_add_pool, "remove-pool": cmd_remove_pool, "set-manager": cmd_set_manager}[a.cmd](a)


if __name__ == "__main__":
    main()
