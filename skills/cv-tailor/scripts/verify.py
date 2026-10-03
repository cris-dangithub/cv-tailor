#!/usr/bin/env python3
"""
Check a generated PDF against the measured design of its style (reference.json).

It doesn't give opinions: it measures. Metric checks are done on the rendered pixels,
because browsers embed web fonts in ways PDF text tools mis-measure (a real case: a text
tool said a line was 24% too small; in pixels it was x1.004).

Usage:
    verify.py CV.pdf [--yaml content.yml] [--style NAME] [--check-links] [--json]

Exit code 1 if any check fails. Warnings never fail the run.
Needs: pypdf, pdfplumber, pypdfium2.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

import logging

logging.getLogger("pdfminer").setLevel(logging.ERROR)  # noisy FontBBox warnings on browser PDFs
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import find_workspace, read_json, read_yaml, resolve_style  # noqa: E402

OK, FAIL, WARN = "  ok  ", " FAIL ", " warn "


class Report:
    def __init__(self):
        self.items = []

    def check(self, name, cond, detail=""):
        self.items.append({"check": name, "ok": bool(cond), "detail": detail, "warn": False})
        print(f"{OK if cond else FAIL}  {name}{('  - ' + detail) if detail else ''}")

    def warn(self, name, detail=""):
        self.items.append({"check": name, "ok": True, "detail": detail, "warn": True})
        print(f"{WARN}  {name}{('  - ' + detail) if detail else ''}")

    def info(self, name, detail=""):
        print(f"        {name}{('  - ' + detail) if detail else ''}")

    @property
    def failures(self):
        return sum(1 for i in self.items if not i["ok"])


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_to_hex(c) -> str | None:
    """pdfplumber colours: tuple of 1 (gray), 3 (rgb) or 4 (cmyk) floats in 0..1."""
    if c is None:
        return None
    if isinstance(c, (int, float)):
        c = (c,)
    c = tuple(float(x) for x in c if isinstance(x, (int, float)))
    if len(c) == 1:
        c = (c[0],) * 3
    elif len(c) == 4:
        k = c[3]
        c = tuple((1 - x) * (1 - k) for x in c[:3])
    elif len(c) != 3:
        return None
    return "#" + "".join(f"{round(max(0, min(1, x)) * 255):02x}" for x in c)


def near(a: str, b: str, tol: int) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(hex_to_rgb(a), hex_to_rgb(b)))


# --------------------------------------------------------------------------- pixels
class Page:
    """One page rendered to RGB rows (bytes), plus pt-per-pixel factors."""

    def __init__(self, pdfium_page, dpi=130):
        bm = pdfium_page.render(scale=dpi / 72, rev_byteorder=True)
        self.w, self.h = bm.width, bm.height
        nch = bm.n_channels
        stride = bm.stride
        raw = bytes(bm.buffer)
        self.rows = []
        for y in range(self.h):
            line = raw[y * stride: y * stride + self.w * nch]
            if nch != 3:
                line = b"".join(line[i:i + 3] for i in range(0, len(line), nch))
            self.rows.append(line)
        pw, ph = pdfium_page.get_size()
        self.kx, self.ky = pw / self.w, ph / self.h

    def xs_with(self, y, rgb, tol):
        r = self.rows[y]
        R, G, B = rgb
        return [x for x in range(self.w)
                if abs(r[3 * x] - R) < tol and abs(r[3 * x + 1] - G) < tol and abs(r[3 * x + 2] - B) < tol]

    def ink_bbox(self, thresh=235):
        top = bottom = None
        left, right = self.w, -1
        for y, r in enumerate(self.rows):
            dark = [x for x in range(0, self.w) if min(r[3 * x], r[3 * x + 1], r[3 * x + 2]) < thresh]
            if dark:
                top = y if top is None else top
                bottom = y
                left, right = min(left, dark[0]), max(right, dark[-1])
        return None if top is None else (left, top, right, bottom)


def find_rules(pages, color, kind, content_width_pt):
    rgb = hex_to_rgb(color)
    tol = 60 if kind == "solid" else 16
    found = []
    for pi, pg in enumerate(pages):
        prev_y = -10
        for y in range(pg.h):
            xs = pg.xs_with(y, rgb, tol)
            if not xs:
                continue
            span_pt = (xs[-1] - xs[0]) * pg.kx
            coverage = len(xs) / max(1, xs[-1] - xs[0] + 1)
            if kind == "solid":
                hit = span_pt > content_width_pt * 0.8 and coverage > 0.85
            else:
                hit = span_pt > content_width_pt * 0.3 and 0.30 < coverage < 0.80
            if hit:
                if y - prev_y > 2:  # a new rule, not the next row of the same one
                    found.append({"page": pi + 1, "y_pt": round(y * pg.ky, 1),
                                  "x0": round(xs[0] * pg.kx, 1), "x1": round(xs[-1] * pg.kx, 1),
                                  "width_pt": round(span_pt, 1), "coverage": round(coverage, 2)})
                prev_y = y
    return found


# --------------------------------------------------------------------------- links
def pdf_links(pdf_path) -> list[str]:
    from pypdf import PdfReader  # noqa: PLC0415
    urls = []
    for page in PdfReader(str(pdf_path)).pages:
        for a in page.get("/Annots") or []:
            obj = a.get_object()
            act = obj.get("/A")
            if act and act.get_object().get("/URI"):
                urls.append(str(act.get_object()["/URI"]))
    return urls


def check_url(url: str) -> tuple[str, str]:
    """Returns (verdict, detail). verdict: ok | warn | broken."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (cv-tailor link check)", "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(200_000).decode("utf-8", "ignore").lower()
            code = r.status
            final = r.geturl()
    except urllib.error.HTTPError as e:
        if e.code == 999:
            return "warn", "999 (LinkedIn anti-bot; check by hand)"
        if e.code in (401, 403, 429):
            return "warn", f"{e.code} (blocked for bots or needs login; check by hand)"
        return "broken", f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return "broken", type(e).__name__ + ": " + str(e)[:80]
    if "drive.google.com" in final and ("request access" in body or "solicitar acceso" in body):
        return "broken", "Google Drive file is private (request access page)"
    return "ok", f"{code} {final[:70]}"


# --------------------------------------------------------------------------- main
def verify(pdf: pathlib.Path, style: str | None = None, content: pathlib.Path | None = None,
           check_links: bool = False) -> Report:
    import pdfplumber  # noqa: PLC0415
    import pypdfium2 as pdfium  # noqa: PLC0415
    from pypdf import PdfReader  # noqa: PLC0415

    pdf = pdf.resolve()
    html = pdf.with_suffix(".html")
    if not style and html.is_file():
        m = re.search(r'name="cv-tailor-style" content="([^"]+)"', html.read_text(encoding="utf-8", errors="replace"))
        style = m.group(1) if m else None
    ws = find_workspace(pdf.parent)
    style_dir = resolve_style(style, ws)
    ref = read_json(style_dir / "reference.json")
    page_ref, vref = ref.get("page", {}), ref.get("verify", {})
    data = read_yaml(content) if content else None

    rep = Report()
    print(f"\nverifying {pdf}\nstyle: {style_dir}\n" + "-" * 78)

    # ---- pages and size
    reader = PdfReader(str(pdf))
    n = len(reader.pages)
    target = page_ref.get("target_pages")
    if target:
        rep.check(f"pages ({n})", n <= target, f"target <= {target}")
    box = reader.pages[0].mediabox
    w_pt, h_pt = float(box.width), float(box.height)
    if page_ref.get("width"):
        rep.check("page size", abs(w_pt - page_ref["width"]) < 2 and abs(h_pt - page_ref["height"]) < 2,
                  f"{w_pt:.0f} x {h_pt:.0f} pt")

    # ---- text (what an ATS reads)
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    min_chars = vref.get("min_chars", 800)
    rep.check("extractable text", len(text) >= min_chars, f"{len(text)} chars (min {min_chars})")
    norm = lambda s: re.sub(r"\s+", " ", s).casefold()  # noqa: E731
    ntext = norm(text)
    if data:
        name = data.get("meta", {}).get("name", "")
        rep.check("candidate name in extracted text", norm(name) in ntext, name)
        missing = [s["title"] for s in data.get("sections", []) if norm(str(s.get("title", ""))) not in ntext]
        rep.check("every section title in extracted text", not missing,
                  f"missing: {missing}" if missing else f"{len(data.get('sections', []))} sections")
        pend = re.findall(r"\[(?:PENDING|PENDIENTE)[^\]]*\]", text, re.I)
        if pend:
            rep.warn("unresolved [PENDING] markers in the PDF", f"{len(pend)}: {pend[:3]}")

    # ---- fonts, sizes, colours (from the content stream)
    family = (ref.get("fonts") or {}).get("family", "")
    sizes, colors, fonts = {}, {}, {}
    with pdfplumber.open(str(pdf)) as pl:
        for p in pl.pages:
            for ch in p.chars:
                if not ch["text"].strip():
                    continue
                sizes[round(ch["size"], 1)] = sizes.get(round(ch["size"], 1), 0) + 1
                hx = color_to_hex(ch.get("non_stroking_color"))
                if hx:
                    colors[hx] = colors.get(hx, 0) + 1
                fonts[ch["fontname"]] = fonts.get(ch["fontname"], 0) + 1
    total = sum(fonts.values()) or 1
    fam_key = family.replace(" ", "").lower()
    named = sum(v for k, v in fonts.items() if fam_key and fam_key in k.replace(" ", "").lower())
    system = sum(v for k, v in fonts.items()
                 if re.search(r"arial|times|helvetica|dejavu|liberation|segoe|calibri|courier", k, re.I))
    if named:
        rep.check("style font is used", named / total > 0.8, f"{family}: {named}/{total} glyphs")
    else:
        # Browsers may embed web fonts anonymously (Type 3). Then the name proves nothing;
        # what matters is that body text is not set in a system fallback font.
        rep.check("no system fallback font for body text", system / total < 0.1,
                  f"system-font glyphs {system}/{total}; fonts: {sorted(fonts)[:4]}")

    expected = [v for k, v in (ref.get("sizes") or {}).items()
                if not k.startswith("_") and isinstance(v, (int, float))]
    if expected:
        tol = vref.get("size_tolerance", 0.8)
        off = sorted(s for s, cnt in sizes.items() if cnt > 2 and not any(abs(s - e) <= tol for e in expected))
        if off:
            rep.warn("font sizes outside the style catalogue", f"{off} (tolerance {tol}pt; "
                     "text tools can misread browser-embedded fonts: confirm on the render)")
        else:
            rep.check("font sizes in the style catalogue", True, f"{sorted(sizes)}")

    allowed = [v for v in (ref.get("colors") or {}).values() if isinstance(v, str) and v.startswith("#")]
    if allowed:
        tol = vref.get("color_tolerance", 4)
        extra = sorted(c for c, cnt in colors.items() if cnt > 2 and not any(near(c, a, tol) for a in allowed))
        rep.check("text colours in the style palette", not extra,
                  f"unexpected: {extra}" if extra else f"{len(allowed)} inks, +-{tol}/255")

    # ---- pixels
    doc = pdfium.PdfDocument(str(pdf))
    pages = [Page(doc[i]) for i in range(len(doc))]
    p1 = pages[0]
    bbox = p1.ink_bbox()
    if bbox and page_ref.get("margin_left") is not None:
        l, t, r, _b = bbox
        mt = vref.get("margin_tolerance", {})
        left, right, top = l * p1.kx, page_ref["width"] - (r + 1) * p1.kx, t * p1.ky
        rep.check("left margin", abs(left - page_ref["margin_left"]) < mt.get("left", 3),
                  f"{left:.1f} vs {page_ref['margin_left']}")
        rep.check("right margin", abs(right - page_ref["margin_right"]) < mt.get("right", 3.5),
                  f"{right:.1f} vs {page_ref['margin_right']}")
        rep.check("top margin", abs(top - page_ref["margin_top"]) < mt.get("top", 3.5),
                  f"{top:.1f} vs {page_ref['margin_top']}")

    # name band: first band of dark pixels at the top must be visible and inside the margins
    ys = [y for y in range(int(p1.h * 0.02), int(p1.h * 0.15))
          if sum(1 for x in range(p1.w) if p1.rows[y][3 * x] < 160) > 2]
    if ys:
        band = [ys[0]]
        for y in ys[1:]:
            if y - band[-1] <= 2:
                band.append(y)
            else:
                break
        xs = [x for y in band for x in range(p1.w) if p1.rows[y][3 * x] < 160]
        wd, ht = (max(xs) - min(xs) + 1) * p1.kx, (band[-1] - band[0] + 1) * p1.ky
        nref = vref.get("name_reference")
        if nref and data and norm(data["meta"]["name"]) == norm(nref["text"]):
            rep.check("name metric (pixels)", abs(wd - nref["width"]) < nref["width"] * 0.05
                      and abs(ht - nref["height"]) < 1.5,
                      f"{wd:.1f} x {ht:.1f} pt vs {nref['width']} x {nref['height']}")
        else:
            inside = min(xs) * p1.kx >= page_ref.get("margin_left", 0) - 1 and \
                max(xs) * p1.kx <= page_ref.get("width", 9e9) - page_ref.get("margin_right", 0) + 1
            rep.check("top line (name) visible and inside the page", 6 < ht < 40 and inside,
                      f"{wd:.1f} x {ht:.1f} pt")

    cw = page_ref.get("content_width") or (w_pt - page_ref.get("margin_left", 40) - page_ref.get("margin_right", 40))
    for rule in vref.get("rules", []):
        found = find_rules(pages, rule["color"], rule["kind"], cw)
        rep.check(rule.get("name", f"{rule['kind']} rules {rule['color']}"),
                  len(found) >= rule.get("min_count", 1), f"{len(found)} found")
        if found and rule.get("width"):
            wdt = found[0]["width_pt"]
            rep.check(f"  width of {rule.get('name', 'rule')}", abs(wdt - rule["width"]) < 6,
                      f"{wdt} vs {rule['width']}")

    # page fill: helps decide between fixing pagination and cutting content
    fills = []
    for i, pg in enumerate(pages):
        bb = pg.ink_bbox()
        fills.append(0 if not bb else round(bb[3] * pg.ky / h_pt * 100))
    rep.info("page fill (% of height)", ", ".join(f"p{i + 1}={f}%" for i, f in enumerate(fills)))
    if len(fills) > 1 and fills[-1] < 25:
        rep.warn("last page is almost empty", f"{fills[-1]}%: fix pagination or cut by value")

    # ---- links
    urls = pdf_links(pdf)
    rep.info("links in the PDF", str(len(urls)))
    if check_links:
        for u in dict.fromkeys(urls):
            verdict, detail = check_url(u)
            if verdict == "ok":
                rep.check(f"link {u[:60]}", True, detail)
            elif verdict == "warn":
                rep.warn(f"link {u[:60]}", detail)
            else:
                rep.check(f"link {u[:60]}", False, detail)

    print("-" * 78)
    total_checks = sum(1 for i in rep.items if not i["warn"])
    print(f"{total_checks - rep.failures}/{total_checks} checks passed, "
          f"{sum(1 for i in rep.items if i['warn'])} warning(s)\n")
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Verify a generated CV PDF against its style.")
    ap.add_argument("pdf", type=pathlib.Path)
    ap.add_argument("--yaml", type=pathlib.Path, default=None, help="content YAML used to build it")
    ap.add_argument("--style", default=None)
    ap.add_argument("--check-links", action="store_true", help="request every link (network)")
    ap.add_argument("--json", action="store_true", help="also print the result as JSON")
    a = ap.parse_args()
    r = verify(a.pdf, a.style, a.yaml, a.check_links)
    if a.json:
        print(json.dumps(r.items, ensure_ascii=False, indent=2))
    sys.exit(1 if r.failures else 0)
