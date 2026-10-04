#!/usr/bin/env python3
"""
The application report: applications/<id>-.../report.md, written for the candidate.

It says what was done and why, never how: no commands, internal paths or check counts.
Two kinds of blocks, kept apart by markers:
  - automatic blocks (status, CVs, knowledge-base updates, history): rewritten here from
    meta.json, the *.verify.json files and the pool write-back runs, every time they change;
  - the agent block (decisions, questions and answers, pending items): written by the agent
    in the UI language and never touched by this script.

    report.py 12            # create or refresh the report of application 12
    report.py --all         # refresh every report
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import load_config, read_json, require_workspace  # noqa: E402

AUTO = "cv-tailor:auto:{}"
NOTES_START, NOTES_END = "<!-- cv-tailor:notes:start -->", "<!-- cv-tailor:notes:end -->"

L = {
    "en": {
        "status": "Status", "updated": "Updated", "offer": "Offer", "applied_on": "Created on",
        "history": "History", "cvs": "Your CVs", "kb": "Your knowledge base", "feedback": "Your feedback",
        "versions": "Versions",
        "st": {"generated": "CV ready, not sent yet", "sent": "Sent", "replied": "They replied",
               "interview": "Interviewing", "rejected": "Not selected", "offer": "Offer received",
               "withdrawn": "Withdrawn"},
        "fits": "fits in {n} pages", "fits1": "fits on one page", "over": "is {n} pages, longer than the {t} planned",
        "links_ok": "all links work", "links_unchecked": "links not checked yet",
        "links_broken": "these links don't respond: {x}", "links_manual": "open these by hand to be sure: {x}",
        "pending_in_pdf": "it still has items waiting for your confirmation",
        "not_built": "not generated yet",
        "kb_none": "Your knowledge base is not changed: it has no skill that manages it.",
        "kb_off": "Updating your knowledge base is turned off for this workspace.",
        "kb_nothing": "Nothing new to save in your knowledge base.",
        "kb_undo": "If something is wrong, tell me «undo the knowledge base changes of {id}» or «correct ...».",
        "kb_rolled_all": "undone on {d}", "kb_rolled_part": "partly undone on {d}",
        "notes_hint": "_(filled in when the CV is generated)_",
        "notes_head": ["## What I decided and why", "## Questions I asked you", "## Before you send it"],
    },
    "es": {
        "status": "Estado", "updated": "Actualizado", "offer": "Oferta", "applied_on": "Creada el",
        "history": "Historial", "cvs": "Tus CVs", "kb": "Tu base de conocimiento", "feedback": "Tus comentarios",
        "versions": "Versiones",
        "st": {"generated": "CV listo, todavía no enviado", "sent": "Enviada", "replied": "Te respondieron",
               "interview": "En entrevistas", "rejected": "No seleccionada", "offer": "Oferta recibida",
               "withdrawn": "Retirada"},
        "fits": "cabe en {n} páginas", "fits1": "cabe en una página", "over": "ocupa {n} páginas, más de las {t} previstas",
        "links_ok": "todos los enlaces funcionan", "links_unchecked": "los enlaces aún no se revisaron",
        "links_broken": "estos enlaces no responden: {x}", "links_manual": "abre estos a mano para confirmarlos: {x}",
        "pending_in_pdf": "todavía tiene datos esperando tu confirmación",
        "not_built": "aún no generado",
        "kb_none": "Tu base de conocimiento no se modifica: no tiene una skill que la gestione.",
        "kb_off": "La actualización de tu base de conocimiento está desactivada en este espacio.",
        "kb_nothing": "No hubo nada nuevo que guardar en tu base de conocimiento.",
        "kb_undo": "Si algo no está bien, dime «deshaz los cambios en mi base de la {id}» o «corrige ...».",
        "kb_rolled_all": "deshecho el {d}", "kb_rolled_part": "deshecho en parte el {d}",
        "notes_hint": "_(se completa al generar el CV)_",
        "notes_head": ["## Qué decidí y por qué", "## Lo que te pregunté", "## Antes de enviarlo"],
    },
}
LANG_NAMES = {
    "en": {"en": "English", "es": "Spanish", "id": "Indonesian", "pt": "Portuguese", "fr": "French",
           "de": "German", "it": "Italian"},
    "es": {"en": "Inglés", "es": "Español", "id": "Indonesio", "pt": "Portugués", "fr": "Francés",
           "de": "Alemán", "it": "Italiano"},
}


def labels(ui: str) -> tuple[dict, dict]:
    code = (ui or "en").lower()[:2]
    return L.get(code, L["en"]), LANG_NAMES.get(code, LANG_NAMES["en"])


def block(name: str, body: str) -> str:
    return f"<!-- {AUTO.format(name)}:start -->\n{body.rstrip()}\n<!-- {AUTO.format(name)}:end -->"


def domains(urls: list[str]) -> str:
    return ", ".join(dict.fromkeys((urlparse(u).netloc or u).removeprefix("www.") for u in urls))


def cv_line(d: pathlib.Path, lang: str, files: dict, t: dict, names: dict) -> str:
    pdf = files.get("pdf")
    name = names.get(lang, lang.upper())
    if not pdf:
        return f"- **{name}**: {t['not_built']}"
    v = read_json(d / (pathlib.Path(pdf).name + ".verify.json"))
    bits = []
    if v:
        if v.get("pages"):
            fits = v.get("fits")
            if fits in (True, None):
                bits.append(t["fits1"] if v["pages"] == 1 else t["fits"].format(n=v["pages"]))
            else:
                bits.append(t["over"].format(n=v["pages"], t=v.get("target_pages")))
        if v.get("broken_links"):
            bits.append(t["links_broken"].format(x=domains(v["broken_links"])))
        elif v.get("links_checked"):
            bits.append(t["links_ok"])
        elif v.get("links"):
            bits.append(t["links_unchecked"])
        if v.get("links_to_check_by_hand"):
            bits.append(t["links_manual"].format(x=domains(v["links_to_check_by_hand"])))
        if v.get("pending_markers"):
            bits.append(t["pending_in_pdf"])
    link = f"[{pathlib.Path(pdf).name}]({pathlib.Path(pdf).as_posix()})"
    return f"- **{name}**: {link}" + (f" — {'; '.join(bits)}." if bits else "")


def kb_lines(cfg: dict, meta: dict, t: dict) -> list[str]:
    pool = cfg.get("pool") or {}
    runs = meta.get("pool_writeback") or []
    if not runs:
        if pool.get("writeback", "auto") == "off":
            return [t["kb_off"]]
        if not (pool.get("manager") or {}).get("can_update"):
            return [t["kb_none"]]
        return [t["kb_nothing"]]
    out = []
    for r in runs:
        text = r.get("summary") or t["kb_nothing"]
        if r.get("not_sent"):
            text += f" {r['not_sent']}"
        if r.get("rolled_back") == "all":
            text += f" ({t['kb_rolled_all'].format(d=r.get('rolled_back_on', ''))})"
        elif r.get("rolled_back") == "partial":
            text += f" ({t['kb_rolled_part'].format(d=r.get('rolled_back_on', ''))})"
        out.append(f"- {r.get('date', '')}: {text}")
    out.append("")
    out.append(t["kb_undo"].format(id=meta.get("id", "")))
    return out


def render_auto(ws, d: pathlib.Path, meta: dict) -> dict:
    cfg = load_config(ws)
    t, names = labels(cfg.get("ui_language"))
    st = meta.get("status", "generated")
    hist = meta.get("status_history") or []
    top = [f"**{t['status']}:** {t['st'].get(st, st)}  ",
           f"**{t['applied_on']}:** {meta.get('date', '')}  "]
    if meta.get("url"):
        top.append(f"**{t['offer']}:** [{domains([meta['url']])}]({meta['url']})  ")
    top.append(f"**{t['updated']}:** {(meta.get('updated') or '')[:10]}")
    top += ["", f"## {t['cvs']}", ""]
    files = meta.get("files") or {}
    for lang in meta.get("languages") or files.keys():
        top.append(cv_line(d, lang, files.get(lang, {}), t, names))

    bottom = [f"## {t['kb']}", "", *kb_lines(cfg, meta, t), ""]
    versions = meta.get("versions") or []
    if len(versions) > 1:
        bottom += [f"## {t['versions']}", ""]
        bottom += [f"- v{v.get('v')} ({v.get('date', '')}): {v.get('note', '')}" for v in versions] + [""]
    fb = d / "feedback.md"
    if fb.exists():
        dates = re.findall(r"^## (\d{4}-\d{2}-\d{2})", fb.read_text(encoding="utf-8"), re.M)
        if dates:
            bottom += [f"## {t['feedback']}", "", ", ".join(dict.fromkeys(dates)), ""]
    if len(hist) > 1:
        bottom += [f"## {t['history']}", ""]
        bottom += [f"- {h.get('date', '')}: {t['st'].get(h.get('status'), h.get('status'))}"
                   + (f" — {h['note']}" if h.get("note") else "") for h in hist]
    return {"top": "\n".join(top), "bottom": "\n".join(bottom)}


def replace_block(text: str, name: str, body: str) -> str:
    start, end = f"<!-- {AUTO.format(name)}:start -->", f"<!-- {AUTO.format(name)}:end -->"
    pat = re.escape(start) + r".*?" + re.escape(end)
    return re.sub(pat, lambda _m: block(name, body), text, flags=re.S)


def update(ws, d: pathlib.Path) -> pathlib.Path:
    meta = read_json(d / "meta.json") or {}
    auto = render_auto(ws, d, meta)
    path = d / "report.md"
    title = f"# {meta.get('company', '')} — {meta.get('role', '')} ({meta.get('id', '')})"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"\A# .*", lambda _m: title, text, count=1)
        for name in ("top", "bottom"):
            if f"{AUTO.format(name)}:start" in text:
                text = replace_block(text, name, auto[name])
            else:
                text = text.rstrip() + "\n\n" + block(name, auto[name]) + "\n"
    else:
        t, _ = labels(load_config(ws).get("ui_language"))
        notes = "\n\n".join(f"{h}\n\n{t['notes_hint']}" for h in t["notes_head"])
        text = "\n\n".join([title, block("top", auto["top"]),
                            f"{NOTES_START}\n{notes}\n{NOTES_END}", block("bottom", auto["bottom"])]) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--workspace", default=None)
    a = ap.parse_args(argv)
    ws = require_workspace(a.workspace)
    import index  # noqa: PLC0415
    targets = index.app_dirs(ws) if a.all else [index.find_app(ws, a.id)] if a.id else []
    if not targets:
        ap.error("give an application id or --all")
    for d in targets:
        print(update(ws, d))


if __name__ == "__main__":
    main()
