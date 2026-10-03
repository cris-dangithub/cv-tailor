#!/usr/bin/env python3
"""
Write the CV part of a review Markdown from the YAML, which is the single source of truth.

Everything below the `<!-- END OF CV` marker (audit report, pending items, interview
defence) is human work and is never touched. If the Markdown does not exist yet, it is
created with the marker and empty review headings.

    sync_md.py cv.en.yml CV-Name-Company-EN-review.md
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import read_yaml  # noqa: E402

MARKER = "<!-- END OF CV"
LEGACY_MARKERS = ("<!-- FIN DEL CV",)
HB = "  "  # Markdown hard break: two trailing spaces
SKELETON = f"""{MARKER} - nothing below this line is sent -->

## Audit report

## Pending verification

## Interview defence
"""


def text(v) -> str:
    """A YAML value (string or list of chunks) as Markdown."""
    if v is None:
        return ""
    if isinstance(v, str):
        out = v
    else:
        parts = []
        for p in v:
            parts.append(f"[{p['text']}]({p['url']})" if isinstance(p, dict) else str(p))
        out = "".join(parts)
    out = re.sub(r"\s*\n\s*", " ", out)
    return out.replace("<strong>", "**").replace("</strong>", "**")


def bullets(items, level=0):
    lines, pad = [], "  " * level
    for it in items or []:
        if isinstance(it, dict):
            lines.append(f"{pad}- {text(it['text'])}")
            if it.get("sub"):
                lines += bullets(it["sub"], level + 1)
        else:
            lines.append(f"{pad}- {text(it)}")
    return lines


def to_markdown(d: dict) -> str:
    L = [f"# {d['meta']['name']}", ""]
    head = [text(d["meta"]["role"])]
    for row in d.get("header", []):
        bits = [text(row.get(k)) for k in ("left", "center", "right")]
        bits = [b for b in bits if b]
        if bits:
            head.append(" · ".join(bits))
    for i, line in enumerate(head):
        L.append(line + (HB if i < len(head) - 1 else ""))

    for s in d.get("sections", []):
        L += ["", "---", "", f"## {str(s['title']).title()}", ""]
        kind = s.get("type")
        if kind == "prose":
            L.append(text(s["body"]))
        elif kind == "entries":
            for e in s["entries"]:
                head = text(e["entity"])
                if e.get("role"):
                    head += f" — {text(e['role'])}"
                L.append(f"### {head}")
                foot = [text(e.get(k)) for k in ("dates", "entity_note")]
                foot = [f for f in foot if f]
                if foot:
                    L.append(" · ".join(foot))
                for ln in e.get("lines") or []:
                    parts = [text(ln.get("left")), text(ln.get("right"))]
                    L += ["", " · ".join(p for p in parts if p)]
                if e.get("meta"):
                    L += ["", text(e["meta"])]
                if e.get("summary"):
                    L += ["", text(e["summary"])]
                for g in e.get("groups") or []:
                    L += ["", f"**{g['title']}**", ""] + bullets(g["bullets"])
                if e.get("bullets"):
                    L += [""] + bullets(e["bullets"])
                L.append("")
            L.pop()
        elif kind == "columns":
            for col in (s.get("left") or []) + (s.get("right") or []):
                L += [f"**{col['title']}**", ""] + bullets(col["bullets"]) + [""]
            L.pop()
        elif kind == "list":
            L += bullets(s["bullets"])
    L += ["", "---", ""]
    return "\n".join(L)


def lint(md: str) -> tuple[int, int]:
    """Lines Markdown would merge by accident, and '---' that would turn the line above into H2."""
    ls = md.splitlines()
    merged = sum(1 for a, b in zip(ls, ls[1:])
                 if a.strip() and b.strip() and not a.endswith(HB)
                 and not re.match(r"^[-*#|>]", a.strip()) and not re.match(r"^[-*#|>]", b.strip())
                 and not a.strip().startswith("<!--"))
    setext = sum(1 for a, b in zip(ls, ls[1:]) if a.strip() and b.strip() == "---")
    return merged, setext


def sync(yaml_path: pathlib.Path, md_path: pathlib.Path) -> bool:
    md = to_markdown(read_yaml(yaml_path))
    if md_path.exists():
        cur = md_path.read_text(encoding="utf-8")
        idx = next((cur.index(m) for m in (MARKER, *LEGACY_MARKERS) if m in cur), None)
        if idx is None:
            sys.exit(f"{md_path} has no {MARKER!r} marker; nothing was changed.")
        tail = cur[idx:]
    else:
        tail = SKELETON
    md_path.write_text(md + tail, encoding="utf-8")
    merged, setext = lint(md_path.read_text(encoding="utf-8").split(MARKER)[0])
    print(f"  {md_path.name}: CV part written from {yaml_path.name}  merges={merged}  setext-risk={setext}")
    return merged == 0 and setext == 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(0 if sync(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])) else 1)
