"""Who may use the web app: a superuser from the environment, and accounts people create.

- The superuser is `CVT_ADMIN_USER` / `CVT_ADMIN_PASSWORD` (real environment variables first,
  then <ws>/.cv-tailor/web/.env). Without them it is admin / admin, which `web.py` refuses to
  expose beyond this computer. It is never stored, so it cannot be locked out from the app.
- Anyone can create an account. The first one is active at once; every later one waits until
  the superuser approves it.
- A login gives a random token in a cookie. It never expires: it ends when the user signs out
  or the superuser disables, deletes or resets them. Only its SHA-256 is kept on disk.

<ws>/.cv-tailor/web/users.json      accounts (scrypt password hashes)
<ws>/.cv-tailor/web/sessions.json   sha256(token) -> user, created, last seen
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import time

from common import now, read_json, write_json
from webapp.settings import web_dir

ENV_USER, ENV_PASSWORD = "CVT_ADMIN_USER", "CVT_ADMIN_PASSWORD"
DEFAULT_ADMIN = ("admin", "admin")
USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,32}$")
MIN_PASSWORD = 8
MAX_FAILURES = 5  # per address and user name, then an increasing wait
SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}


class AuthError(Exception):
    """`code` is what the browser shows: bad_credentials, pending_approval, disabled,
    too_many_attempts, username_taken, invalid_username, weak_password, not_found, forbidden."""

    def __init__(self, code: str, status: int = 400, retry_after: int = 0):
        super().__init__(code)
        self.code, self.status, self.retry_after = code, status, retry_after


# --------------------------------------------------------------------------- superuser
def load_env(ws) -> None:
    """Read <ws>/.cv-tailor/web/.env (KEY=VALUE lines) into os.environ without overriding it."""
    p = web_dir(ws) / ".env"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def admin_credentials() -> tuple[str, str, bool]:
    user = (os.environ.get(ENV_USER) or DEFAULT_ADMIN[0]).strip().lower()
    password = os.environ.get(ENV_PASSWORD) or DEFAULT_ADMIN[1]
    return user, password, password == DEFAULT_ADMIN[1]


# --------------------------------------------------------------------------- hashing
def _hash(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, **SCRYPT).hex()


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class Auth:
    def __init__(self, ws):
        self.users_path = web_dir(ws) / "users.json"
        self.sessions_path = web_dir(ws) / "sessions.json"
        self._lock = threading.Lock()
        self._failures: dict[tuple[str, str], tuple[int, float]] = {}

    # ----------------------------------------------------------------------- storage
    def _users(self) -> dict:
        return read_json(self.users_path, {}) or {}

    def _sessions(self) -> dict:
        return read_json(self.sessions_path, {}) or {}

    # ----------------------------------------------------------------------- brute force
    def _check_throttle(self, key: tuple[str, str]) -> None:
        count, until = self._failures.get(key, (0, 0.0))
        if count >= MAX_FAILURES and time.monotonic() < until:
            raise AuthError("too_many_attempts", 429, int(until - time.monotonic()) + 1)

    def _failed(self, key: tuple[str, str]) -> None:
        count, _ = self._failures.get(key, (0, 0.0))
        count += 1
        wait = 0 if count < MAX_FAILURES else min(2 ** (count - MAX_FAILURES) * 30, 3600)
        self._failures[key] = (count, time.monotonic() + wait)

    # ----------------------------------------------------------------------- accounts
    def register(self, username: str, password: str) -> str:
        """Returns the new account's status: 'active' for the first account, else 'pending'."""
        username = (username or "").strip().lower()
        if not USERNAME_RE.match(username):
            raise AuthError("invalid_username")
        if len(password or "") < MIN_PASSWORD:
            raise AuthError("weak_password")
        with self._lock:
            users = self._users()
            if username in users or username == admin_credentials()[0]:
                raise AuthError("username_taken", 409)
            salt = secrets.token_bytes(16)
            status = "pending" if users else "active"
            users[username] = {"pw_hash": _hash(password, salt), "salt": salt.hex(), "status": status,
                               "created": now(), "approved_by": None,
                               "approved_at": None if users else now()}
            write_json(self.users_path, users)
        return status

    def login(self, username: str, password: str, address: str = "", agent: str = "") -> str:
        username = (username or "").strip().lower()
        key = (address, username)
        self._check_throttle(key)
        admin, admin_pw, _ = admin_credentials()
        if username == admin:
            ok = hmac.compare_digest(password.encode("utf-8"), admin_pw.encode("utf-8"))
        else:
            u = self._users().get(username)
            # hash something even for an unknown name, so timing does not reveal accounts
            salt = bytes.fromhex(u["salt"]) if u else b"\0" * 16
            ok = hmac.compare_digest(_hash(password or "", salt), u["pw_hash"] if u else "")
            if ok and u["status"] == "pending":
                raise AuthError("pending_approval", 403)
            if ok and u["status"] == "disabled":
                raise AuthError("disabled", 403)
        if not ok:
            self._failed(key)
            raise AuthError("bad_credentials", 401)
        self._failures.pop(key, None)
        return self._new_session(username, agent)

    def _new_session(self, username: str, agent: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            sessions = self._sessions()
            sessions[_digest(token)] = {"user": username, "created": now(), "last_seen": now(),
                                        "agent": (agent or "")[:160]}
            write_json(self.sessions_path, sessions)
        return token

    def user_for(self, token: str | None) -> dict | None:
        """{'user', 'is_admin'} for a valid session token, else None."""
        if not token:
            return None
        d = _digest(token)
        s = self._sessions().get(d)
        if not s:
            return None
        admin = admin_credentials()[0]
        if s["user"] != admin:
            u = self._users().get(s["user"])
            if not u or u["status"] != "active":
                return None
        if s.get("last_seen", "")[:16] != now()[:16]:  # at most one write per minute and session
            with self._lock:
                sessions = self._sessions()
                if d in sessions:
                    sessions[d]["last_seen"] = now()
                    write_json(self.sessions_path, sessions)
        return {"user": s["user"], "is_admin": s["user"] == admin}

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            sessions = self._sessions()
            if sessions.pop(_digest(token), None) is not None:
                write_json(self.sessions_path, sessions)

    def revoke_user(self, username: str) -> int:
        with self._lock:
            sessions = self._sessions()
            keep = {k: v for k, v in sessions.items() if v["user"] != username}
            write_json(self.sessions_path, keep)
        return len(sessions) - len(keep)

    # ----------------------------------------------------------------------- superuser actions
    def list(self) -> list[dict]:
        users, sessions = self._users(), self._sessions()
        out = []
        for name, u in users.items():
            mine = [s for s in sessions.values() if s["user"] == name]
            out.append({"username": name, "status": u["status"], "created": u["created"],
                        "approved_by": u.get("approved_by"), "approved_at": u.get("approved_at"),
                        "sessions": len(mine),
                        "last_seen": max((s["last_seen"] for s in mine), default=None)})
        order = {"pending": 0, "active": 1, "disabled": 2}
        return sorted(out, key=lambda u: (order.get(u["status"], 3), u["created"]))

    def pending_count(self) -> int:
        return sum(1 for u in self._users().values() if u["status"] == "pending")

    def _change(self, username: str, fn) -> None:
        with self._lock:
            users = self._users()
            if username not in users:
                raise AuthError("not_found", 404)
            if fn(users, username) is not False:
                write_json(self.users_path, users)

    def approve(self, username: str, by: str) -> None:
        def go(users, name):
            users[name].update(status="active", approved_by=by, approved_at=now())
        self._change(username, go)

    def reject(self, username: str) -> None:
        """Refuse a pending account (it is deleted, so the name can be used again)."""
        def go(users, name):
            if users[name]["status"] != "pending":
                raise AuthError("not_pending", 409)
            del users[name]
        self._change(username, go)

    def set_status(self, username: str, status: str) -> None:
        if status not in ("active", "disabled"):
            raise AuthError("invalid_status")
        self._change(username, lambda users, name: users[name].update(status=status))
        if status == "disabled":
            self.revoke_user(username)

    def delete(self, username: str) -> None:
        self._change(username, lambda users, name: users.pop(name))
        self.revoke_user(username)

    def set_password(self, username: str, password: str) -> None:
        if len(password or "") < MIN_PASSWORD:
            raise AuthError("weak_password")
        salt = secrets.token_bytes(16)

        def go(users, name):
            users[name].update(pw_hash=_hash(password, salt), salt=salt.hex())
        self._change(username, go)
        self.revoke_user(username)
