#!/usr/bin/env python3
"""
Plain text (and hyperlinks) out of the documents a pool or an offer usually contains:
PDF, DOCX, ODT, HTML, Markdown, TXT, JSON, YAML. No system tools needed.

    extract_text.py FILE [--links] [--max-chars N]

--links lists every hyperlink with its anchor text and the text right before it: in a CV
the anchor is often just "(Certificate)", and only the preceding text says what it proves.
PDF text extraction drops link annotations, so without this a CV full of verifiable links
silently becomes a list of unproven titles.
"""
from __future__ import annotations

import argparse
import html as htmlmod
import pathlib
import re
import sys
import zipfile

import logging

logging.getLogger("pdfminer").setLevel(logging.ERROR)  # noisy FontBBox warnings on browser PDFs
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402,F401  (utf-8 console)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def pdf_text(p: pathlib.Path) -> str:
    from pypdf import PdfReader  # noqa: PLC0415
    out = []
    for i, page in enumerate(PdfReader(str(p)).pages, 1):
        try:
            t = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            t = page.extract_text() or ""
        out.append(f"--- page {i} ---\n{t}")
    return "\n".join(out)


def pdf_links(p: pathlib.Path) -> list[dict]:
    import pdfplumber  # noqa: PLC0415
    links = []
    with pdfplumber.open(str(p)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            for h in page.hyperlinks:
                x0, top, x1, bottom = h["x0"], h["top"], h["x1"], h["bottom"]
                try:
                    anchor = page.within_bbox((max(0, x0 - 1), max(0, top - 1),
                                               min(page.width, x1 + 1), min(page.height, bottom + 1))).extract_text() or ""
                    before = page.within_bbox((0, max(0, top - 1), max(1, x0), min(page.height, bottom + 1))).extract_text() or ""
                except ValueError:
                    anchor, before = "", ""
                links.append({"page": i, "url": h.get("uri"), "anchor": " ".join(anchor.split()),
                              "before": " ".join(before.split())[-90:]})
    return links


def docx_parts(p: pathlib.Path):
    import xml.etree.ElementTree as ET  # noqa: PLC0415
    z = zipfile.ZipFile(p)
    root = ET.fromstring(z.read("word/document.xml"))
    rels = {}
    if "word/_rels/document.xml.rels" in z.namelist():
        for r in ET.fromstring(z.read("word/_rels/document.xml.rels")):
            rels[r.get("Id")] = r.get("Target")
    return root, rels


def docx_text(p: pathlib.Path) -> str:
    root, _ = docx_parts(p)
    lines = []
    for para in root.iter(f"{W}p"):
        txt = "".join(t.text or "" for t in para.iter(f"{W}t"))
        if not txt.strip():
            lines.append("")
            continue
        is_list = para.find(f"{W}pPr/{W}numPr") is not None
        style = para.find(f"{W}pPr/{W}pStyle")
        if style is not None and "List" in (style.get(f"{W}val") or ""):
            is_list = True
        lines.append(("- " if is_list else "") + txt)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def docx_links(p: pathlib.Path) -> list[dict]:
    root, rels = docx_parts(p)
    out = []
    for para in root.iter(f"{W}p"):
        before = ""
        for el in para:
            if el.tag == f"{W}hyperlink":
                anchor = "".join(t.text or "" for t in el.iter(f"{W}t"))
                url = rels.get(el.get(f"{R}id"), el.get(f"{W}anchor") or "")
                out.append({"page": None, "url": url, "anchor": anchor, "before": before[-90:]})
                before += anchor
            else:
                before += "".join(t.text or "" for t in el.iter(f"{W}t"))
    return out


def odt_text(p: pathlib.Path) -> str:
    raw = zipfile.ZipFile(p).read("content.xml").decode("utf-8", "ignore")
    raw = re.sub(r"<text:list-item[^>]*>", "\n- ", raw)
    raw = re.sub(r"</text:(p|h)>", "\n", raw)
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", raw))


def html_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<li[^>]*>", "\n- ", raw)
    raw = re.sub(r"(?i)<(br|/p|/div|/h[1-6]|/tr|/li|/ul|/ol)[^>]*>", "\n", raw)
    raw = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", raw)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", "", raw))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def html_links(raw: str) -> list[dict]:
    out = []
    for m in re.finditer(r'(?is)<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', raw):
        anchor = htmlmod.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        ctx = htmlmod.unescape(re.sub(r"<[^>]+>", " ", raw[max(0, m.start() - 400):m.start()]))
        out.append({"page": None, "url": m.group(1), "anchor": anchor, "before": " ".join(ctx.split())[-90:]})
    return out


def extract(p: pathlib.Path) -> str:
    ext = p.suffix.lower()
    if ext == ".pdf":
        return pdf_text(p)
    if ext == ".docx":
        return docx_text(p)
    if ext == ".odt":
        return odt_text(p)
    raw = p.read_text(encoding="utf-8", errors="ignore")
    if ext in (".html", ".htm"):
        return html_text(raw)
    return raw


def links(p: pathlib.Path) -> list[dict]:
    ext = p.suffix.lower()
    if ext == ".pdf":
        return pdf_links(p)
    if ext == ".docx":
        return docx_links(p)
    raw = p.read_text(encoding="utf-8", errors="ignore")
    if ext in (".html", ".htm"):
        return html_links(raw)
    return [{"page": None, "url": u, "anchor": a, "before": ""}
            for a, u in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", raw)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Extract text and links from a document.")
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--links", action="store_true", help="list hyperlinks instead of text")
    ap.add_argument("--max-chars", type=int, default=0)
    a = ap.parse_args()
    if not a.file.is_file():
        sys.exit(f"not a file: {a.file}")
    if a.links:
        for ln in links(a.file):
            print(f"...{ln['before']}\n      [{ln['anchor']}] -> {ln['url']}" +
                  (f"  (p{ln['page']})" if ln["page"] else "") + "\n")
    else:
        t = extract(a.file)
        print(t[:a.max_chars] if a.max_chars else t)
