#!/usr/bin/env python3
"""
Create the skill's own Python environment: <skill>/.venv, managed by pipenv.

Standard library only: this runs before any dependency exists.

    setup_env.py            # install (or repair) the environment
    setup_env.py --dev      # also install the test tools
    setup_env.py --check    # only report: exit 0 if ready, 3 if not

Dependencies come from requirements.txt (and requirements-dev.txt with --dev); this is the
same as running, inside the skill folder:

    pipenv install -r requirements.txt
    pipenv install --dev -r requirements-dev.txt

The Pipfile / Pipfile.lock that pipenv generates are local and ignored by git.
The venv lives inside the skill folder (PIPENV_VENV_IN_PROJECT=1, also set in <skill>/.env)
and is ignored by git. Reinstalling the skill (for example a plugin update) removes it; the
next run detects that and rebuilds it.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
VENV = SKILL_DIR / ".venv"
REQUIRED = ["yaml", "jinja2", "pypdf", "pdfplumber", "pypdfium2"]


def venv_python() -> pathlib.Path:
    win = VENV / "Scripts" / "python.exe"
    return win if win.exists() or os.name == "nt" else VENV / "bin" / "python"


def ready() -> tuple[bool, str]:
    py = venv_python()
    if not py.exists():
        return False, f"no venv at {VENV}"
    code = "import importlib.util,sys;m=[x for x in %r if not importlib.util.find_spec(x)];print(','.join(m));sys.exit(1 if m else 0)" % REQUIRED
    r = subprocess.run([str(py), "-c", code], capture_output=True, text=True)
    return (r.returncode == 0, "ok" if r.returncode == 0 else f"missing: {r.stdout.strip()}")


def run(cmd, env=None):
    print("$", " ".join(cmd))
    r = subprocess.run(cmd, cwd=SKILL_DIR, env=env)
    if r.returncode != 0:
        sys.exit(f"command failed ({r.returncode}): {' '.join(cmd)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    ok, why = ready()
    if a.check:
        print(("ENV_READY " if ok else "ENV_MISSING ") + why)
        sys.exit(0 if ok else 3)
    if sys.version_info < (3, 9):
        sys.exit("Python 3.9+ is required")

    py = sys.executable
    if subprocess.run([py, "-m", "pipenv", "--version"], capture_output=True).returncode != 0:
        run([py, "-m", "pip", "install", "--user", "pipenv"])

    # pipenv runs with cwd = skill folder and creates the Pipfile there (no parent lookup)
    env = {k: v for k, v in os.environ.items() if k not in ("PIPENV_PIPFILE", "VIRTUAL_ENV")}
    env.update(PIPENV_VENV_IN_PROJECT="1", PIPENV_YES="1", PIPENV_NOSPIN="1", PIPENV_MAX_DEPTH="1")
    run([py, "-m", "pipenv", "install", "--python", py, "-r", "requirements.txt"], env)
    if a.dev:
        run([py, "-m", "pipenv", "install", "--dev", "-r", "requirements-dev.txt"], env)
    ok, why = ready()
    print(("ENV_READY " if ok else "ENV_MISSING ") + why + f"  ({venv_python()})")
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
