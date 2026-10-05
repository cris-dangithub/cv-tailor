#!/usr/bin/env python3
"""
cv-tailor command launcher. Runs any script of the skill with the skill's own venv.

    python <skill>/cvt.py <command> [args...]

Commands:
    setup-env [--dev]   create/repair <skill>/.venv with pipenv (run this first)
    doctor              check environment, browser and optional tools
    workspace ...       init / show / set / scan-pool / styles ...      (scripts/workspace.py)
    index ...           new / list / show / update / status / search ... (scripts/index.py)
    build ...           YAML -> HTML + PDF                               (scripts/build.py)
    verify ...          measure a PDF against its style                  (scripts/verify.py)
    sync-md ...         write the CV part of the review Markdown         (scripts/sync_md.py)
    voice ...           measure / compare the writing register           (scripts/voice.py)
    extract ...         text and links from PDF/DOCX/HTML/...            (scripts/extract_text.py)
    fetch-offer ...     download a job offer to Markdown                 (scripts/fetch_offer.py)
    github ...          GitHub evidence cache for a github pool source   (scripts/pool_github.py)
    style ...           measure a reference CV / scaffold a new style    (scripts/extract_style.py)
    report ID|--all     refresh the candidate-facing report.md           (scripts/report.py)
    pool-writeback ...  snapshot / finish / diff / rollback pool updates (scripts/pool_writeback.py)
    sync ...            Google Drive: detect / setup / status / run / clean (scripts/sync_drive.py)

Standard library only, so it works before the venv exists. Exit code 3 = environment missing.
"""
import os
import pathlib
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent
SCRIPTS = SKILL_DIR / "scripts"
COMMANDS = {
    "workspace": "workspace.py", "index": "index.py", "build": "build.py", "verify": "verify.py",
    "sync-md": "sync_md.py", "voice": "voice.py", "extract": "extract_text.py",
    "fetch-offer": "fetch_offer.py", "github": "pool_github.py", "style": "extract_style.py",
    "doctor": "doctor.py", "setup-env": "setup_env.py", "report": "report.py",
    "pool-writeback": "pool_writeback.py", "sync": "sync_drive.py",
}
NO_VENV = {"setup-env", "doctor"}  # these must run with the system Python


def venv_python():
    for p in (SKILL_DIR / ".venv" / "Scripts" / "python.exe", SKILL_DIR / ".venv" / "bin" / "python"):
        if p.exists():
            return p
    return None


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd not in COMMANDS:
        print(f"unknown command {cmd!r}\n{__doc__}")
        return 2
    py = sys.executable if cmd in NO_VENV else venv_python()
    if py is None:
        print("ENV_MISSING: the skill environment is not installed. "
              f"Run: python \"{SKILL_DIR / 'cvt.py'}\" setup-env")
        return 3
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([str(py), str(SCRIPTS / COMMANDS[cmd]), *args], env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
