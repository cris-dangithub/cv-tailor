#!/usr/bin/env python3
"""
Applications registry of a workspace: numbering, index, search, status.

Each application lives in  applications/<ID>-<company>-<role>/  with a meta.json that is the
source of truth. applications/index.jsonl is a rebuildable cache of all meta.json files.
IDs are zero-padded to `numbering.width` digits (default 6: 000001). When the next ID no
longer fits, every folder and meta is renumbered to one more digit before creating it.

    index.py new --company "Acme" --role "Data Engineer" [--url URL] [--offer-file F] [--languages en,es]
    index.py list [--status sent] [--limit 20]
    index.py show 12
    index.py path 12
    index.py update 12 --summary "..." --keywords "spark,airflow" --set location=Remote
    index.py add-file 12 --lang en --kind pdf --path CV-...-EN.pdf
    index.py status 12 replied [--note "recruiter email 2026-10-20"]
    index.py search "Hi, thanks for applying to the Data Engineer role at Acme" [--top 5] [--json]
    index.py rebuild
    index.py renumber --width 7
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import pathlib
import re
import shutil
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (INDEX_NAME, STATUSES, apps_dir, load_config, now,  # noqa: E402
                    read_json, require_workspace, save_config, slugify, today, write_json)

ID_RE = re.compile(r"^(\d+)-")
DEFAULT_WIDTH = 6


# --------------------------------------------------------------------------- basics
def width_of(ws) -> int:
    return int((load_config(ws).get("numbering") or {}).get("width", DEFAULT_WIDTH))


def app_dirs(ws) -> list[pathlib.Path]:
    root = apps_dir(ws)
    if not root.is_dir():
        return []
    return sorted((d for d in root.iterdir() if d.is_dir() and ID_RE.match(d.name)),
                  key=lambda d: int(ID_RE.match(d.name).group(1)))


def all_meta(ws) -> list[dict]:
    out = []
    for d in app_dirs(ws):
        m = read_json(d / "meta.json")
        if m:
            m["_dir"] = str(d)
            out.append(m)
    return out


def find_app(ws, ref: str) -> pathlib.Path:
    ref = str(ref).strip()
    if not ref.isdigit():
        sys.exit(f"Application id must be a number, got {ref!r}")
    for d in app_dirs(ws):
        if int(ID_RE.match(d.name).group(1)) == int(ref):
            return d
    sys.exit(f"NOT_FOUND: no application with id {ref}")


INDEX_FIELDS = ["id", "company", "role", "location", "url", "date", "languages", "style",
                "status", "keywords", "summary", "folder"]


def rebuild_index(ws) -> int:
    lines = []
    for m in all_meta(ws):
        row = {k: m.get(k) for k in INDEX_FIELDS}
        row["folder"] = pathlib.Path(m["_dir"]).name
        lines.append(json.dumps(row, ensure_ascii=False))
    apps_dir(ws).mkdir(parents=True, exist_ok=True)
    (apps_dir(ws) / INDEX_NAME).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def save_meta(ws, d: pathlib.Path, meta: dict) -> None:
    meta = {k: v for k, v in meta.items() if not k.startswith("_")}
    meta["updated"] = now()
    write_json(d / "meta.json", meta)
    rebuild_index(ws)


# --------------------------------------------------------------------------- numbering
def renumber(ws, new_width: int) -> None:
    """Rename every application folder (and its meta id) to `new_width` digits."""
    dirs = app_dirs(ws)
    for d in dirs:
        num = int(ID_RE.match(d.name).group(1))
        if len(str(num)) > new_width:
            sys.exit(f"Cannot renumber to {new_width} digits: id {num} does not fit.")
    for d in dirs:
        num = int(ID_RE.match(d.name).group(1))
        new_id = f"{num:0{new_width}d}"
        rest = d.name[ID_RE.match(d.name).end():]
        target = d.parent / f"{new_id}-{rest}"
        meta = read_json(d / "meta.json", {})
        if meta:
            meta["id"] = new_id
            write_json(d / "meta.json", meta)
        if target != d:
            shutil.move(str(d), str(target))
    cfg = load_config(ws)
    cfg.setdefault("numbering", {})["width"] = new_width
    save_config(ws, cfg)
    rebuild_index(ws)
    print(f"renumbered {len(dirs)} application(s) to {new_width} digits")


def next_id(ws) -> str:
    width = width_of(ws)
    nums = [int(ID_RE.match(d.name).group(1)) for d in app_dirs(ws)]
    n = (max(nums) if nums else 0) + 1
    if n > 10 ** width - 1:
        renumber(ws, width + 1)
        width += 1
    return f"{n:0{width}d}"


# --------------------------------------------------------------------------- commands
def cmd_new(ws, a) -> dict:
    cfg = load_config(ws)
    new = next_id(ws)
    slug = slugify(f"{a.company}-{a.role}") if a.company or a.role else "offer"
    d = apps_dir(ws) / f"{new}-{slug}"
    d.mkdir(parents=True, exist_ok=False)
    langs = [x.strip() for x in a.languages.split(",")] if a.languages else cfg.get("cv_languages", [])
    meta = {
        "id": new, "slug": slug, "company": a.company or "", "role": a.role or "",
        "location": a.location or "", "url": a.url or "", "date": a.date or today(),
        "languages": langs,
        "style": (cfg.get("style") or {}).get("active", "default"),
        "status": "generated",
        "status_history": [{"status": "generated", "date": today(), "note": ""}],
        "keywords": [k.strip() for k in (a.keywords or "").split(",") if k.strip()],
        "summary": a.summary or "",
        "files": {}, "versions": [{"v": 1, "date": today(), "note": "first version"}],
        "created": now(),
    }
    if a.offer_file:
        shutil.copyfile(a.offer_file, d / "offer.md")
    save_meta(ws, d, meta)
    out = {"id": new, "dir": str(d)}
    print(json.dumps(out, ensure_ascii=False))
    return out


def cmd_update(ws, a):
    d = find_app(ws, a.id)
    meta = read_json(d / "meta.json")
    if a.summary is not None:
        meta["summary"] = a.summary
    if a.keywords is not None:
        kws = [k.strip() for k in a.keywords.split(",") if k.strip()]
        meta["keywords"] = sorted(set(meta.get("keywords", [])) | set(kws), key=str.lower)
    for kv in a.set or []:
        k, _, v = kv.partition("=")
        if k in ("id", "files", "status_history"):
            sys.exit(f"{k} cannot be set directly")
        meta[k] = [x.strip() for x in v.split(",")] if k == "languages" else v
    if a.version_note:
        vs = meta.setdefault("versions", [])
        vs.append({"v": len(vs) + 1, "date": today(), "note": a.version_note})
    save_meta(ws, d, meta)
    print(json.dumps({k: meta.get(k) for k in INDEX_FIELDS if k != "folder"}, ensure_ascii=False, indent=2))


def cmd_add_file(ws, a):
    d = find_app(ws, a.id)
    meta = read_json(d / "meta.json")
    p = pathlib.Path(a.path)
    if not p.is_absolute():  # relative paths are relative to the application folder
        p = d / p
    try:
        rel = p.resolve().relative_to(d.resolve()).as_posix()
    except ValueError:
        rel = str(p.resolve())
    meta.setdefault("files", {}).setdefault(a.lang, {})[a.kind] = rel
    save_meta(ws, d, meta)
    print(f"{meta['id']}: {a.lang}.{a.kind} = {rel}")


def cmd_status(ws, a):
    if a.status not in STATUSES:
        sys.exit(f"status must be one of {STATUSES}")
    d = find_app(ws, a.id)
    meta = read_json(d / "meta.json")
    meta["status"] = a.status
    meta.setdefault("status_history", []).append({"status": a.status, "date": a.date or today(),
                                                  "note": a.note or ""})
    save_meta(ws, d, meta)
    print(f"{meta['id']} {meta['company']} - {meta['role']}: {a.status}")


def cmd_list(ws, a):
    rows = all_meta(ws)
    if a.status:
        rows = [r for r in rows if r.get("status") == a.status]
    rows = rows[-a.limit:] if a.limit else rows
    for r in rows:
        print(f"{r['id']}  {r.get('date', ''):10}  {r.get('status', ''):10}  "
              f"{r.get('company', '')} - {r.get('role', '')}  [{','.join(r.get('languages', []))}]")
    print(f"({len(rows)} shown)")


def cmd_show(ws, a):
    d = find_app(ws, a.id)
    meta = read_json(d / "meta.json")
    meta["folder"] = str(d)
    meta["present_files"] = sorted(p.name for p in d.iterdir() if p.is_file())
    print(json.dumps(meta, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------- search
STOP = set("""a an the and or of to for in on at by with from is are was were be been this that
these those it its as your you our we i me my de la el los las y o u del al en con por para un una
unos unas su sus que se lo le les mi tu es son fue hola hi hello dear regards thanks thank gracias
saludos dan yang di ke dari untuk dengan ini itu""".split())


def tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return [w for w in re.split(r"[^a-z0-9+#]+", t) if len(w) > 1 and w not in STOP]


def offer_text(d: pathlib.Path, limit=20000) -> str:
    p = d / "offer.md"
    return p.read_text(encoding="utf-8", errors="ignore")[:limit] if p.is_file() else ""


def search(ws, query: str, top=5, status=None, since=None) -> list[dict]:
    metas = all_meta(ws)
    if status:
        metas = [m for m in metas if m.get("status") == status]
    if since:
        metas = [m for m in metas if (m.get("date") or "") >= since]
    if not metas:
        return []
    q = tokens(query)
    qset = set(q)
    qnorm = " ".join(tokens(query))
    weights = {"company": 6.0, "role": 4.0, "keywords": 3.0, "url": 3.0, "location": 2.0,
               "summary": 2.0, "offer": 1.0}
    docs = []
    for m in metas:
        d = pathlib.Path(m["_dir"])
        fields = {
            "company": set(tokens(m.get("company", ""))),
            "role": set(tokens(m.get("role", ""))),
            "keywords": set(tokens(" ".join(m.get("keywords", [])))),
            "url": set(tokens(m.get("url", ""))),
            "location": set(tokens(m.get("location", ""))),
            "summary": set(tokens(m.get("summary", ""))),
            "offer": set(tokens(offer_text(d))),
        }
        docs.append((m, fields))
    n = len(docs)
    df = {}
    for _, f in docs:
        for t in set().union(*f.values()):
            df[t] = df.get(t, 0) + 1
    results = []
    for m, f in docs:
        score, hits = 0.0, {}
        for t in qset:
            idf = math.log(1 + n / df.get(t, n + 1)) if t in df else 0
            for field, toks in f.items():
                if t in toks:
                    score += weights[field] * idf
                    hits.setdefault(field, []).append(t)
        # the company name written inside a free text (an email, a subject line) is the strongest clue
        comp = " ".join(tokens(m.get("company", "")))
        if comp and f" {comp} " in f" {qnorm} ":
            score += 12
            hits.setdefault("company_phrase", []).append(comp)
        role = " ".join(tokens(m.get("role", "")))
        if role and f" {role} " in f" {qnorm} ":
            score += 8
            hits.setdefault("role_phrase", []).append(role)
        # fuzzy: misspelt or partial company names ("Acme Corp" vs "ACME Corporation")
        if comp:
            best = max((difflib.SequenceMatcher(None, comp, w).ratio() for w in q), default=0)
            if best > 0.8 and "company" not in hits:
                score += 4 * best
                hits.setdefault("company_fuzzy", []).append(round(best, 2))
        if score > 0:
            results.append({"score": round(score, 2), "id": m["id"], "company": m.get("company"),
                            "role": m.get("role"), "date": m.get("date"), "status": m.get("status"),
                            "languages": m.get("languages"), "folder": m["_dir"],
                            "files": m.get("files", {}), "matched": hits})
    results.sort(key=lambda r: (r["score"], r["date"] or ""), reverse=True)
    return results[:top]


def cmd_search(ws, a):
    res = search(ws, a.query, a.top, a.status, a.since)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not res:
        print("NO_MATCH: nothing in the index matches. Try other words (company, role, city, a link).")
        return
    for r in res:
        print(f"[{r['score']:>6}] {r['id']}  {r['date']}  {r['status']:10}  {r['company']} - {r['role']}")
        print(f"          {r['folder']}")
        print(f"          matched: {json.dumps(r['matched'], ensure_ascii=False)}")


# --------------------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new")
    p.add_argument("--company", default="")
    p.add_argument("--role", default="")
    p.add_argument("--location", default="")
    p.add_argument("--url", default="")
    p.add_argument("--date", default=None)
    p.add_argument("--languages", default=None, help="comma separated; default: config cv_languages")
    p.add_argument("--keywords", default="")
    p.add_argument("--summary", default="")
    p.add_argument("--offer-file", default=None, help="file with the offer text, copied to offer.md")

    p = sub.add_parser("update")
    p.add_argument("id")
    p.add_argument("--summary", default=None)
    p.add_argument("--keywords", default=None, help="comma separated, merged with existing")
    p.add_argument("--set", action="append", help="key=value (company, role, location, url, languages, style...)")
    p.add_argument("--version-note", default=None, help="record a new version (v2, v3...) with this note")

    p = sub.add_parser("add-file")
    p.add_argument("id")
    p.add_argument("--lang", required=True)
    p.add_argument("--kind", required=True, choices=["yaml", "pdf", "html", "review"])
    p.add_argument("--path", required=True)

    p = sub.add_parser("status")
    p.add_argument("id")
    p.add_argument("status", choices=STATUSES)
    p.add_argument("--note", default="")
    p.add_argument("--date", default=None)

    p = sub.add_parser("list")
    p.add_argument("--status", default=None)
    p.add_argument("--limit", type=int, default=0)

    p = sub.add_parser("show")
    p.add_argument("id")
    p = sub.add_parser("path")
    p.add_argument("id")

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--status", default=None)
    p.add_argument("--since", default=None, help="YYYY-MM-DD")
    p.add_argument("--json", action="store_true")

    sub.add_parser("rebuild")
    p = sub.add_parser("renumber")
    p.add_argument("--width", type=int, required=True)

    a = ap.parse_args(argv)
    ws = require_workspace(a.workspace)
    {"new": cmd_new, "update": cmd_update, "add-file": cmd_add_file, "status": cmd_status,
     "list": cmd_list, "show": cmd_show, "search": cmd_search,
     "path": lambda w, x: print(find_app(w, x.id)),
     "rebuild": lambda w, x: print(f"index rebuilt: {rebuild_index(w)} application(s)"),
     "renumber": lambda w, x: renumber(w, x.width)}[a.cmd](ws, a)


if __name__ == "__main__":
    main()
