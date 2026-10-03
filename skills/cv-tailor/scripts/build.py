#!/usr/bin/env python3
"""
Render one CV version to PDF.

    style/reference.json  measured design tokens (single source of truth for the design)
    style/cv.css          the design; consumes the tokens through var(--...)
    style/cv.html.j2      the structure; no design values
    <content>.yml         the content of ONE version (one offer, one language)

Usage:
    build.py content.en.yml -o CV-Name-Company-EN.pdf [--style NAME|PATH]
    build.py --from-html CV-Name-Company-EN.html [-o CV-Name-Company-EN.pdf]

The first form always writes the HTML next to the PDF and prints that same file. The second
form re-prints a hand-edited HTML without regenerating it. A new version = a new YAML; the
style is never edited to make one version fit.

Engine: any installed Chromium-family browser (Chrome, Edge, Chromium, Brave), found
automatically on Windows, macOS and Linux; Playwright's Chromium as a fallback.
Set CV_TAILOR_BROWSER to force a browser executable.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import WS_MARKER, find_workspace, read_json, read_yaml, resolve_style  # noqa: E402


# --------------------------------------------------------------------------- tokens
def css_vars(style_dir: pathlib.Path, ref: dict) -> dict:
    """A style may ship tokens.py with css_vars(ref) -> {"--name": "value"}.
    Without it, every scalar of every non-underscore group becomes --group-key
    (numbers in pt, unless the group is listed in ref["_unitless_groups"])."""
    tk = style_dir / "tokens.py"
    if tk.is_file():
        spec = importlib.util.spec_from_file_location(f"tokens_{style_dir.name}", tk)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.css_vars(ref)
    unitless = set(ref.get("_unitless_groups", []))
    out = {}
    for group, vals in ref.items():
        if group.startswith("_") or not isinstance(vals, dict) or group == "verify":
            continue
        for k, v in vals.items():
            if k.startswith("_") or isinstance(v, (dict, list)):
                continue
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                v = f"{v}" if group in unitless else f"{v}pt"
            out[f"--{group}-{k}".replace("_", "-")] = v
    return out


def root_block(vars_: dict) -> str:
    body = "\n".join(f"  {k}: {v};" for k, v in vars_.items())
    return f":root {{\n{body}\n}}\n"


# --------------------------------------------------------------------------- assets
def static_files(style_dir: pathlib.Path) -> list[pathlib.Path]:
    files = [style_dir / "cv.css"]
    for sub in ("fonts", "assets"):
        d = style_dir / sub
        if d.is_dir():
            files += sorted(p for p in d.rglob("*") if p.is_file())
    return [f for f in files if f.is_file()]


def stage_assets(style_dir: pathlib.Path, ws: pathlib.Path | None) -> pathlib.Path:
    """Copy the style's CSS and fonts into the workspace, in a folder named by content hash.

    The skill folder can move or be replaced on update; the workspace can't. An HTML that
    points into the workspace keeps rendering exactly as it did when it was generated.
    """
    if ws is None:
        return style_dir
    files = static_files(style_dir)
    h = hashlib.sha256()
    for f in files:
        h.update(f.relative_to(style_dir).as_posix().encode())
        h.update(f.read_bytes())
    dest = ws / WS_MARKER / "style-cache" / f"{style_dir.name}-{h.hexdigest()[:10]}"
    if not (dest / "cv.css").is_file():
        for f in files:
            target = dest / f.relative_to(style_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
    return dest


def rel_or_uri(target: pathlib.Path, base_dir: pathlib.Path) -> str:
    try:
        return pathlib.Path(os.path.relpath(target, base_dir)).as_posix()
    except ValueError:  # different drives on Windows
        return target.resolve().as_uri()


# --------------------------------------------------------------------------- browser
def browser_candidates() -> list[str]:
    env = os.environ.get("CV_TAILOR_BROWSER")
    if env:
        return [env]
    sysname = platform.system()
    out = []
    if sysname == "Windows":
        roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        rels = [r"Google\Chrome\Application\chrome.exe",
                r"Microsoft\Edge\Application\msedge.exe",
                r"Chromium\Application\chrome.exe",
                r"BraveSoftware\Brave-Browser\Application\brave.exe"]
        out += [str(pathlib.Path(r) / rel) for rel in rels for r in roots if r]
    elif sysname == "Darwin":
        out += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "microsoft-edge", "microsoft-edge-stable", "brave-browser", "chrome", "msedge"):
        w = shutil.which(name)
        if w:
            out.append(w)
    return out


def find_browser() -> str | None:
    for c in browser_candidates():
        if pathlib.Path(c).is_file():
            return c
    return None


def render_with_browser(exe: str, html: pathlib.Path, pdf: pathlib.Path) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="cv-tailor-profile-") as profile:
        cmd = [exe, "--headless=new", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", "--disable-extensions",
               f"--user-data-dir={profile}",
               "--no-pdf-header-footer", "--print-to-pdf-no-header",
               "--run-all-compositor-stages-before-draw", "--virtual-time-budget=10000",
               f"--print-to-pdf={pdf}", html.resolve().as_uri()]
        if platform.system() == "Linux":
            cmd.insert(1, "--no-sandbox")
        if pdf.exists():
            pdf.unlink()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, str(e)
        ok = pdf.exists() and pdf.stat().st_size > 0
        return ok, "" if ok else (proc.stderr[-2000:] or f"exit {proc.returncode}")


def render_with_playwright(html: pathlib.Path, pdf: pathlib.Path) -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        return False, "playwright not installed"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            page.goto(html.resolve().as_uri(), wait_until="networkidle")
            page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
            b.close()
        return pdf.exists(), ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def render(html: pathlib.Path, pdf: pathlib.Path) -> str:
    errors = []
    exe = find_browser()
    if exe:
        ok, err = render_with_browser(exe, html, pdf)
        if ok:
            return pathlib.Path(exe).name
        errors.append(f"{exe}: {err}")
    ok, err = render_with_playwright(html, pdf)
    if ok:
        return "playwright-chromium"
    errors.append(f"playwright: {err}")
    sys.exit("PDF rendering failed. Install Chrome/Edge/Chromium or "
             "`pip install playwright && playwright install chromium`.\n" + "\n".join(errors))


def count_pages(pdf: pathlib.Path) -> int:
    try:
        from pypdf import PdfReader  # noqa: PLC0415
        return len(PdfReader(str(pdf)).pages)
    except Exception:  # noqa: BLE001
        return -1


def report(pdf: pathlib.Path, target: int | None, engine: str) -> int:
    n = count_pages(pdf)
    mark = ""
    if target and n > 0:
        mark = "OK" if n <= target else f"OVER TARGET (target {target})"
    print(f"pdf: {pdf}  -  {n} page(s)  {mark}  [{engine}]")
    return n


# --------------------------------------------------------------------------- build
def build(content: pathlib.Path, out: pathlib.Path, style: str | None = None,
          workspace: pathlib.Path | None = None) -> int:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined  # noqa: PLC0415

    ws = workspace or find_workspace(content.parent)
    style_dir = resolve_style(style, ws)
    ref = read_json(style_dir / "reference.json")
    data = read_yaml(content)
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    html_path = out.with_suffix(".html")

    assets = stage_assets(style_dir, ws)
    env = Environment(loader=FileSystemLoader(str(style_dir)), undefined=StrictUndefined,
                      trim_blocks=False, lstrip_blocks=False, autoescape=False)
    html = env.get_template("cv.html.j2").render(
        tokens_css=root_block(css_vars(style_dir, ref)),
        css_path=rel_or_uri(assets / "cv.css", html_path.parent),
        style_name=style_dir.name,
        target_pages=(ref.get("page") or {}).get("target_pages", 2),
        **data)
    html_path.write_text(html, encoding="utf-8")
    print(f"html: {html_path}")
    engine = render(html_path, out)
    return report(out, (ref.get("page") or {}).get("target_pages"), engine)


def build_from_html(html_path: pathlib.Path, out: pathlib.Path) -> int:
    html_path = html_path.resolve()
    if not html_path.is_file():
        sys.exit(f"HTML not found: {html_path}")
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    engine = render(html_path, out)
    import re  # noqa: PLC0415
    m = re.search(r'name="cv-tailor-target-pages" content="(\d+)"',
                  html_path.read_text(encoding="utf-8", errors="replace"))
    return report(out, int(m.group(1)) if m else None, engine)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Render one CV version (YAML) to HTML + PDF.")
    ap.add_argument("content", nargs="?", type=pathlib.Path, help="content YAML")
    ap.add_argument("-o", "--out", type=pathlib.Path, default=None, help="output PDF")
    ap.add_argument("--style", default=None, help="style name or folder (default: active style)")
    ap.add_argument("--workspace", type=pathlib.Path, default=None)
    ap.add_argument("--from-html", type=pathlib.Path, help="re-print an edited HTML")
    ap.add_argument("--which-browser", action="store_true", help="print the browser that would be used")
    a = ap.parse_args()
    if a.which_browser:
        print(find_browser() or "none (playwright fallback)")
        sys.exit(0)
    if a.from_html:
        if a.content:
            ap.error("use a YAML or --from-html, not both")
        build_from_html(a.from_html, a.out or a.from_html.with_suffix(".pdf"))
    else:
        if not a.content:
            ap.error("missing the content YAML (or --from-html)")
        build(a.content, a.out or a.content.with_suffix(".pdf"), a.style, a.workspace)
