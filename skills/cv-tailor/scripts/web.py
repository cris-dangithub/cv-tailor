#!/usr/bin/env python3
"""
The cv-tailor web app: send offers, follow the agent, manage applications and PDFs from a
browser instead of a chat window. It runs Claude Code itself (your own login, no API key).

    web.py                       # http://127.0.0.1:8765, this computer only
    web.py --lan                 # also your phone on the same network (link + QR)
    web.py --public              # behind a tunnel such as `ngrok http 8765`: any host name
    web.py --port 9000 --no-open
    web.py --workspace PATH      # default: the workspace around the current folder

Everyone signs in. The superuser is CVT_ADMIN_USER / CVT_ADMIN_PASSWORD (environment, or
<ws>/.cv-tailor/web/.env); without them it is admin / admin, accepted on this computer only.
People create their own accounts: the first is active at once, later ones wait for approval.

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
    ap.add_argument("--lan", action="store_true", help="accept devices of the local network")
    ap.add_argument("--public", action="store_true",
                    help="accept any host name, for a tunnel (ngrok, cloudflared) to this port")
    ap.add_argument("--allow-default-admin", action="store_true",
                    help="allow --lan/--public with the default admin password (not recommended)")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    a = ap.parse_args(argv)
    ws = require_workspace(a.workspace)
    try:
        import uvicorn  # noqa: PLC0415

        from webapp.app import create_app  # noqa: PLC0415
        from webapp.auth import ENV_PASSWORD, admin_credentials, load_env  # noqa: PLC0415
        from webapp.settings import web_dir  # noqa: PLC0415
    except ImportError as e:
        sys.exit(f"WEB_ENV_MISSING: {e}. Run: python \"{pathlib.Path(__file__).parent.parent / 'cvt.py'}\" setup-env --web")

    load_env(ws)
    admin, _, default_password = admin_credentials()
    if default_password and (a.lan or a.public) and not a.allow_default_admin:
        sys.exit(f"DEFAULT_ADMIN: the superuser still has the default password, and --lan/--public "
                 f"would let other people try it.\nSet {ENV_PASSWORD} in the environment or in "
                 f"{web_dir(ws) / '.env'}:\n    CVT_ADMIN_USER={admin}\n    {ENV_PASSWORD}=<a long password>\n"
                 "(or pass --allow-default-admin, at your own risk).")

    hosts = [*lan_addresses(), socket.gethostname().lower()] if a.lan else []
    app = create_app(ws, lan=a.lan, lan_hosts=hosts, port=a.port, public=a.public)
    local = f"http://127.0.0.1:{a.port}/"
    print(f"cv-tailor web  ·  workspace {ws}")
    print(f"  this computer:  {local}")
    print(f"  superuser:      {admin}" + ("  (default password: set CVT_ADMIN_PASSWORD)" if default_password else ""))
    if a.lan:
        for h in lan_addresses():
            print(f"  other devices:  http://{h}:{a.port}/")
        if lan_addresses():
            print_qr(f"http://{lan_addresses()[0]}:{a.port}/")
    if a.public:
        print(f"  public:         any host name is accepted; point your tunnel at port {a.port},")
        print(f"                  e.g.  ngrok http {a.port}   (everyone still has to sign in)")
    if not a.no_open:
        webbrowser.open(local)
    # a tunnel connects from this computer, so --public alone does not need to listen on the network
    uvicorn.run(app, host="0.0.0.0" if a.lan else "127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
