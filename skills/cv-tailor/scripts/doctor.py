#!/usr/bin/env python3
"""
Check that everything the skill needs is in place. Standard library only.

    doctor.py [--json]

Essential: Python 3.9+, the skill venv (setup-env), a Chromium-family browser (or Playwright).
Optional: gh (GitHub pool sources), LibreOffice (DOCX reference CVs for new styles).
Exit 0 when the essentials are ready.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build import find_browser  # noqa: E402  (stdlib-only at import time)
from common import SKILL_DIR, find_workspace, load_config  # noqa: E402
from setup_env import ready  # noqa: E402


def soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        w = shutil.which(name)
        if w:
            return w
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if pathlib.Path(p).exists():
            return p
    return None


def main():
    rows = []

    def row(name, ok, detail, essential):
        rows.append({"check": name, "ok": ok, "detail": detail, "essential": essential})

    row("python >= 3.9", sys.version_info >= (3, 9), sys.version.split()[0], True)
    ok, why = ready()
    row("skill environment (.venv)", ok, why if ok else f"{why} -> run: python \"{SKILL_DIR / 'cvt.py'}\" setup-env", True)
    b = find_browser()
    pw = False
    if not b:
        try:
            import playwright  # noqa: F401,PLC0415
            pw = True
        except ImportError:
            pass
    row("PDF engine (Chrome/Edge/Chromium/Brave)", bool(b) or pw,
        b or ("playwright" if pw else "none: install Chrome, Edge or Chromium"), True)

    gh = shutil.which("gh")
    detail = "not installed (only needed for github: pool sources)"
    if gh:
        r = subprocess.run([gh, "auth", "status"], capture_output=True, text=True)
        detail = "authenticated" if r.returncode == 0 else "installed, not logged in (gh auth login)"
    row("gh (GitHub CLI)", bool(gh), detail, False)
    so = soffice()
    row("LibreOffice", bool(so), so or "not installed (only to read DOCX reference CVs for new styles)", False)
    from sync_drive import detect, installed_but_not_running  # noqa: PLC0415
    drives = detect()
    row("Google Drive", bool(drives),
        ", ".join(d["root"] for d in drives) if drives else
        ("installed but not running: open Google Drive" if installed_but_not_running()
         else "not found (only needed to sync results: https://www.google.com/drive/download/)"), False)

    ws = find_workspace()
    if ws:
        try:
            cfg = load_config(ws)
            row("workspace", True, f"{ws} (ui={cfg.get('ui_language')}, cv={cfg.get('cv_languages')}, "
                f"style={(cfg.get('style') or {}).get('active')})", False)
        except SystemExit:  # doctor runs on the system Python, which may not have PyYAML
            row("workspace", True, str(ws), False)
    else:
        row("workspace", False, "none here: the setup creates one in the current folder", False)

    essential_ok = all(r["ok"] for r in rows if r["essential"])
    if "--json" in sys.argv:
        print(json.dumps({"ready": essential_ok, "checks": rows}, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            tag = "ok  " if r["ok"] else ("MISS" if r["essential"] else "opt ")
            print(f"[{tag}] {r['check']:<42} {r['detail']}")
        print("\nREADY" if essential_ok else "\nNOT_READY: fix the MISS lines above")
    sys.exit(0 if essential_ok else 1)


if __name__ == "__main__":
    main()
