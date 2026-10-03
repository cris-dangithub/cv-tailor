#!/usr/bin/env python3
"""
Measure a reference CV so a new style can be built from numbers, not from eyeballing.

    extract_style.py measure REF.pdf|REF.docx --out DIR
        -> DIR/measurements.json   page size, margins, text catalogue (font, size, colour),
                                   horizontal rules (colour, width, dashed/solid), x alignments
        -> DIR/pages/page-N.png    renders at 130 dpi, to look at with your own eyes
    extract_style.py scaffold NAME [--from default]
        -> <workspace>/styles/NAME/  a copy of a style to adapt (template, CSS, tokens, fonts)
    extract_style.py compare REF.pdf GENERATED.pdf --out DIR
        -> DIR/compare-page-N.png  reference (left) and generated (right) side by side

DOCX references are converted to PDF with LibreOffice when it is installed; otherwise ask the
user to export the DOCX to PDF.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from collections import Counter

import logging

logging.getLogger("pdfminer").setLevel(logging.ERROR)  # noisy FontBBox warnings on browser PDFs
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import BUILTIN_STYLES, find_workspace, require_workspace, write_json  # noqa: E402
from verify import Page, color_to_hex  # noqa: E402

DPI = 130


def write_png(path: pathlib.Path, w: int, h: int, rows: list[bytes]) -> None:
    raw = b"".join(b"\x00" + r for r in rows)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def to_pdf(src: pathlib.Path, tmp: pathlib.Path) -> pathlib.Path:
    if src.suffix.lower() == ".pdf":
        return src
    from doctor import soffice  # noqa: PLC0415
    exe = soffice()
    if not exe:
        sys.exit("DOCX_NEEDS_PDF: LibreOffice is not installed. Ask the user to export the document to PDF.")
    subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(src)],
                   capture_output=True, timeout=180)
    out = tmp / (src.stem + ".pdf")
    if not out.exists():
        sys.exit("DOCX conversion failed. Ask the user to export the document to PDF.")
    return out


def rules_on(pg: Page, page_no: int) -> list[dict]:
    """Rows where one non-white colour spans > 25% of the page width."""
    found, last = [], {}
    for y in range(pg.h):
        r = pg.rows[y]
        counts = Counter(r[3 * x:3 * x + 3] for x in range(0, pg.w, 2)
                         if min(r[3 * x], r[3 * x + 1], r[3 * x + 2]) < 245)
        if not counts:
            continue
        col, n = counts.most_common(1)[0]
        if n * 2 < pg.w * 0.25:
            continue
        xs = [x for x in range(pg.w) if r[3 * x:3 * x + 3] == col]
        span = xs[-1] - xs[0] + 1
        cov = len(xs) / span
        if span < pg.w * 0.25:
            continue
        key = col
        if key in last and y - last[key]["_y"] <= 1:
            last[key]["thickness_pt"] = round((y - last[key]["_y0"] + 1) * pg.ky, 2)
            last[key]["_y"] = y
            continue
        item = {"page": page_no, "y_pt": round(y * pg.ky, 1), "x0_pt": round(xs[0] * pg.kx, 1),
                "x1_pt": round(xs[-1] * pg.kx, 1), "width_pt": round(span * pg.kx, 1),
                "color": "#%02x%02x%02x" % tuple(col), "coverage": round(cov, 2),
                "kind": "solid" if cov > 0.85 else ("dashed" if cov > 0.25 else "dotted"),
                "thickness_pt": round(pg.ky, 2), "_y": y, "_y0": y}
        if item["kind"] != "solid":
            runs, gaps, cur, prev = [], [], 1, xs[0]
            for x in xs[1:]:
                if x == prev + 1:
                    cur += 1
                else:
                    runs.append(cur)
                    gaps.append(x - prev - 1)
                    cur = 1
                prev = x
            runs.append(cur)
            if gaps:
                item["dash_pt"] = round(sorted(runs)[len(runs) // 2] * pg.kx, 2)
                item["gap_pt"] = round(sorted(gaps)[len(gaps) // 2] * pg.kx, 2)
        last[key] = item
        found.append(item)
    for f in found:
        f.pop("_y", None)
        f.pop("_y0", None)
    return found


def measure(src: pathlib.Path, out: pathlib.Path) -> dict:
    import pdfplumber  # noqa: PLC0415
    import pypdfium2 as pdfium  # noqa: PLC0415
    out.mkdir(parents=True, exist_ok=True)
    (out / "pages").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = to_pdf(src, pathlib.Path(tmp))
        if pdf != src:
            shutil.copy2(pdf, out / "reference.pdf")
        doc = pdfium.PdfDocument(str(pdf))
        pages = [Page(doc[i], DPI) for i in range(len(doc))]
        for i, pg in enumerate(pages, 1):
            write_png(out / "pages" / f"page-{i}.png", pg.w, pg.h, pg.rows)
        cat, lefts, rights = {}, Counter(), Counter()
        first_texts = []
        with pdfplumber.open(str(pdf)) as pl:
            pw, ph = float(pl.pages[0].width), float(pl.pages[0].height)
            producer = (pl.metadata or {}).get("Producer", "")
            for pi, p in enumerate(pl.pages, 1):
                for w in p.extract_words(extra_attrs=["fontname", "size", "non_stroking_color"]):
                    key = (w["fontname"].split("+")[-1], round(w["size"], 1),
                           color_to_hex(w.get("non_stroking_color")) or "?")
                    c = cat.setdefault(key, {"font": key[0], "size_pt": key[1], "color": key[2],
                                             "words": 0, "example": "", "first": (pi, round(w["top"], 1))})
                    c["words"] += 1
                    if len(c["example"]) < 60:
                        c["example"] = (c["example"] + " " + w["text"]).strip()
                    lefts[round(w["x0"])] += 1
                    rights[round(w["x1"])] += 1
                    if pi == 1 and len(first_texts) < 40:
                        first_texts.append({"y": round(w["top"], 1), "x0": round(w["x0"], 1),
                                            "x1": round(w["x1"], 1), "size": round(w["size"], 1),
                                            "font": key[0], "text": w["text"]})
    bbox = pages[0].ink_bbox()
    p1 = pages[0]
    m = {
        "source": str(src), "producer": producer, "pages": len(pages),
        "page_size_pt": [round(pw, 1), round(ph, 1)],
        "margins_pt_from_pixels": None if not bbox else {
            "left": round(bbox[0] * p1.kx, 1), "top": round(bbox[1] * p1.ky, 1),
            "right": round(pw - (bbox[2] + 1) * p1.kx, 1),
            "bottom_of_ink_page1": round(ph - (bbox[3] + 1) * p1.ky, 1)},
        "text_catalogue": sorted(cat.values(), key=lambda c: (-c["size_pt"], -c["words"])),
        "fonts": sorted({c["font"] for c in cat.values()}),
        "sizes_pt": sorted({c["size_pt"] for c in cat.values()}, reverse=True),
        "text_colors": sum((Counter({c["color"]: c["words"]}) for c in cat.values()), Counter()).most_common(),
        "rules": [r for i, pg in enumerate(pages, 1) for r in rules_on(pg, i)],
        "frequent_left_edges_pt": lefts.most_common(8),
        "frequent_right_edges_pt": rights.most_common(8),
        "page1_reading_order": sorted(first_texts, key=lambda t: (t["y"], t["x0"])),
        "notes": [
            "Sizes and fonts come from the PDF content stream; confirm the headline size on the "
            "render (pages/page-1.png): text tools mis-measure some embedded fonts.",
            "Look at the renders: solid vs dashed rules, title case vs uppercase, columns, icons.",
            "Inconsistencies of the original are the user's decision: replicate or normalise.",
        ],
    }
    for c in m["text_catalogue"]:
        c["first"] = {"page": c["first"][0], "y_pt": c["first"][1]}
    write_json(out / "measurements.json", m)
    return m


def scaffold(name: str, base: str):
    ws = require_workspace()
    src = BUILTIN_STYLES / base
    if not src.is_dir():
        src = ws / "styles" / base
    if not (src / "reference.json").is_file():
        sys.exit(f"base style not found: {base}")
    dest = ws / "styles" / name
    if dest.exists():
        sys.exit(f"style already exists: {dest}")
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
    print(dest)


def compare(ref: pathlib.Path, gen: pathlib.Path, out: pathlib.Path):
    import pypdfium2 as pdfium  # noqa: PLC0415
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        refpdf = to_pdf(ref, pathlib.Path(tmp))
        a, b = pdfium.PdfDocument(str(refpdf)), pdfium.PdfDocument(str(gen))
        for i in range(max(len(a), len(b))):
            pa = Page(a[i], DPI) if i < len(a) else None
            pb = Page(b[i], DPI) if i < len(b) else None
            h = max(p.h for p in (pa, pb) if p)
            wa, wb = (pa.w if pa else pb.w), (pb.w if pb else pa.w)
            sep = b"\x80\x80\x80" * 8
            rows = []
            for y in range(h):
                ra = pa.rows[y] if pa and y < pa.h else b"\xff" * (3 * wa)
                rb = pb.rows[y] if pb and y < pb.h else b"\xff" * (3 * wb)
                rows.append(ra + sep + rb)
            write_png(out / f"compare-page-{i + 1}.png", wa + 8 + wb, h, rows)
            print(out / f"compare-page-{i + 1}.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure")
    p.add_argument("ref", type=pathlib.Path)
    p.add_argument("--out", type=pathlib.Path, required=True)
    p = sub.add_parser("scaffold")
    p.add_argument("name")
    p.add_argument("--from", dest="base", default="default")
    p = sub.add_parser("compare")
    p.add_argument("ref", type=pathlib.Path)
    p.add_argument("generated", type=pathlib.Path)
    p.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.cmd == "measure":
        r = measure(a.ref, a.out)
        print(json.dumps({k: r[k] for k in ("pages", "page_size_pt", "margins_pt_from_pixels", "fonts",
                                             "sizes_pt", "text_colors")}, ensure_ascii=False, indent=2))
        print(f"rules: {len(r['rules'])}  ->  {a.out / 'measurements.json'}")
    elif a.cmd == "scaffold":
        scaffold(a.name, a.base)
    else:
        compare(a.ref, a.generated, a.out)
