#!/usr/bin/env python3
"""
The cv-tailor web app: send offers, follow the agent, manage applications and PDFs from a
browser instead of a chat window. It runs Claude Code itself (your own login, no API key).

    web.py                       # http://127.0.0.1:8765, this computer only
    web.py --lan                 # also your phone on the same network (link + QR with a token)
    web.py --port 9000 --no-open
    web.py --workspace PATH      # default: the workspace around the current folder

Needs the optional dependencies: `cvt setup-env --web`.
"""
from __future__ import annotations

import argparse
import pathlib
import socket
import sys
import webbrowser

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import require_workspace  # noqa: E402


def lan_addresses() -> list[str]:
    out = set()
    try:
        out.update(i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError:
        pass
    try:  # the address used to reach the network, even when the hostname lookup gives none
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))
            out.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(a for a in out if not a.startswith("127."))


def print_qr(url: str) -> None:
    try:
        import qrcode  # noqa: PLC0415
    except ImportError:
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.print_ascii(invert=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=None)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--lan", action="store_true", help="accept devices of the local network (token)")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    a = ap.parse_args(argv)
    ws = require_workspace(a.workspace)
    try:
        import uvicorn  # noqa: PLC0415

        from webapp.app import create_app  # noqa: PLC0415
    except ImportError as e:
        sys.exit(f"WEB_ENV_MISSING: {e}. Run: python \"{pathlib.Path(__file__).parent.parent / 'cvt.py'}\" setup-env --web")

    hosts = [*lan_addresses(), socket.gethostname().lower()] if a.lan else []
    app = create_app(ws, lan=a.lan, lan_hosts=hosts, port=a.port)
    local = f"http://127.0.0.1:{a.port}/"
    print(f"cv-tailor web  ·  workspace {ws}")
    print(f"  this computer:  {local}")
    if a.lan:
        from webapp import settings  # noqa: PLC0415
        tok = settings.token(ws)
        for h in lan_addresses():
            url = f"http://{h}:{a.port}/?t={tok}"
            print(f"  other devices:  {url}")
        if lan_addresses():
            print_qr(f"http://{lan_addresses()[0]}:{a.port}/?t={tok}")
        print("  Anyone with that link on your network can use the app: share it with nobody.")
    if not a.no_open:
        webbrowser.open(local)
    uvicorn.run(app, host="0.0.0.0" if a.lan else "127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
