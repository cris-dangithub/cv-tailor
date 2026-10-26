import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import index  # noqa: E402
from conftest import EXAMPLES  # noqa: E402
from webapp import permissions  # noqa: E402
from webapp.app import create_app  # noqa: E402


class FakeRunner:
    """Stands in for Claude: records what would be sent, spends no tokens."""

    def __init__(self):
        self.sent, self.answers = [], []

    async def start(self):
        pass

    async def shutdown(self):
        pass

    def reconfigure(self):
        pass

    async def health(self):
        return {"cli": "claude", "logged_in": True}

    async def send(self, tid, text, effort=None, shown=None, author=""):
        self.sent.append((tid, text, effort, author))

    async def stop(self, tid):
        pass

    def pending_for(self, tid):
        return []

    def answer(self, req, allow, remember, by=""):
        self.answers.append((req, allow, remember, by))
        return req == "known"


def new(ws, company, role):
    index.main(["--workspace", str(ws), "new", "--company", company, "--role", role])
    return index.app_dirs(ws)[-1]


ADMIN = {"username": "boss", "password": "a long admin secret"}


@pytest.fixture(autouse=True)
def admin_env(monkeypatch):
    monkeypatch.setenv("CVT_ADMIN_USER", ADMIN["username"])
    monkeypatch.setenv("CVT_ADMIN_PASSWORD", ADMIN["password"])


def login(c, username, password):
    return c.post("/api/auth/login", json={"username": username, "password": password})


@pytest.fixture
def client(ws):
    runner = FakeRunner()
    with TestClient(create_app(ws, runner=runner)) as c:
        c.runner = runner
        assert login(c, **ADMIN).status_code == 200
        yield c


def test_applications_status_and_board_counts(ws, client):
    new(ws, "Acme Mobility", "Analytics Engineer")
    new(ws, "Globex", "Data Engineer")
    rows = client.get("/api/applications").json()
    assert [r["company"] for r in rows] == ["Globex", "Acme Mobility"]
    r = client.patch("/api/applications/1/status", json={"status": "interview", "note": "call"})
    assert r.status_code == 200 and r.json()["status"] == "interview"
    assert r.json()["status_history"][-1]["note"] == "call"
    info = client.get("/api/workspace").json()
    assert info["counts"]["interview"] == 1 and info["total"] == 2
    assert client.patch("/api/applications/1/status", json={"status": "hired"}).status_code == 400
    assert client.get("/api/applications/99").status_code == 404


def test_health_reports_the_cli(client):
    assert client.get("/api/health").json()["logged_in"] is True


def test_search_uses_the_index(ws, client):
    new(ws, "Acme Mobility", "Analytics Engineer")
    new(ws, "Globex", "Data Engineer")
    rows = client.get("/api/applications", params={"q": "thanks for applying at globex"}).json()
    assert rows[0]["company"] == "Globex"


def test_pdfs_are_listed_served_and_zipped(ws, client):
    d = new(ws, "Acme", "Engineer")
    (d / "CV-AlexRivera-Acme-EN.pdf").write_bytes(b"%PDF-1.4 en")
    (d / "CV-AlexRivera-Acme-ES-v2.pdf").write_bytes(b"%PDF-1.4 es")
    (d / "CV-AlexRivera-Acme-EN.pdf.verify.json").write_text('{"pages": 1, "fits": true}', encoding="utf-8")
    pdfs = client.get("/api/pdfs").json()
    by_lang = {p["lang"]: p for p in pdfs}
    assert by_lang["en"]["pages"] == 1 and by_lang["en"]["fits"] is True
    assert by_lang["es"]["version"] == 2
    r = client.get("/api/applications/1/files/CV-AlexRivera-Acme-EN.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    z = client.post("/api/pdfs/zip", json={"files": [{"app_id": "1", "name": p["name"]} for p in pdfs]})
    assert z.status_code == 200 and z.content[:2] == b"PK"


def test_files_outside_the_application_are_refused(ws, client):
    d = new(ws, "Acme", "Engineer")
    (ws / "secret.pdf").write_bytes(b"%PDF")
    (d / "meta.json").exists()
    for name in ("..%2Fsecret.pdf", "meta.json", ".hidden.pdf", "..\\secret.pdf"):
        assert client.get(f"/api/applications/1/files/{name}").status_code == 404


def test_offers_open_one_thread_each(client):
    r = client.post("/api/offers", json={"items": [{"text": "Data Engineer at Acme\nSpark, Airflow"},
                                                  {"url": "https://jobs.example.com/42"}],
                                        "effort": "medium"})
    assert r.status_code == 200
    threads = r.json()
    assert [t["title"] for t in threads] == ["Data Engineer at Acme", "jobs.example.com/42"]
    assert [s[2] for s in client.runner.sent] == ["medium", "medium"]
    assert client.runner.sent[0][3] == "boss"
    assert "<offer>" in client.runner.sent[0][1] and "jobs.example.com/42" in client.runner.sent[1][1]
    assert client.post("/api/offers", json={"items": [{"text": "  "}]}).status_code == 400


def test_feedback_reuses_the_application_thread(ws, client):
    new(ws, "Acme", "Engineer")
    first = client.post("/api/applications/1/feedback", json={"text": "too long"}).json()
    again = client.post("/api/applications/1/feedback", json={"text": "and less formal"}).json()
    assert first["id"] == again["id"] and first["app_id"] == "000001"
    assert "application 000001" in client.runner.sent[0][1]


def test_style_switch_records_history(ws, client):
    assert client.get("/api/styles").json()["active"] == "default"
    assert client.put("/api/styles/active", json={"name": "nope"}).status_code == 400
    r = client.put("/api/styles/active", json={"name": "default"}).json()
    assert r["history"][-1]["style"] == "default"


def test_settings_are_validated(client):
    assert client.put("/api/settings", json={"effort": "medium", "concurrency": 99}).json()["concurrency"] == 6
    assert client.put("/api/settings", json={"effort": "extreme"}).status_code == 400
    assert client.get("/api/settings").json()["effort"] == "medium"


def test_permission_answers_reach_the_runner(client):
    assert client.post("/api/permissions/known", json={"allow": True, "remember": True}).status_code == 200
    assert client.runner.answers[-1] == ("known", True, True, "boss")
    assert client.post("/api/permissions/gone", json={"allow": False}).status_code == 404


def test_foreign_hosts_and_origins_are_refused(ws, client):
    assert client.get("/api/workspace", headers={"host": "evil.example"}).status_code == 421
    r = client.patch("/api/applications/1/status", json={"status": "sent"},
                     headers={"origin": "https://evil.example"})
    assert r.status_code == 403


def test_everything_needs_a_session(ws):
    with TestClient(create_app(ws, runner=FakeRunner())) as c:
        for path in ("/api/applications", "/api/workspace", "/api/events", "/api/auth/me", "/api/pdfs"):
            assert c.get(path).status_code == 401, path
        assert c.get("/api/health").status_code == 200
        assert login(c, "boss", "wrong").status_code == 401
        r = login(c, **ADMIN)
        assert r.status_code == 200 and r.json()["is_admin"] is True
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "max-age=315360000" in cookie
        assert c.get("/api/applications").status_code == 200
        assert c.post("/api/auth/logout").status_code == 200
        assert c.get("/api/applications").status_code == 401


def test_first_account_is_free_later_ones_wait_for_approval(ws):
    app = create_app(ws, runner=FakeRunner())
    with TestClient(app) as first, TestClient(app) as second, TestClient(app) as boss:
        r = first.post("/api/auth/register", json={"username": "Ana", "password": "password-ana"})
        assert r.status_code == 200 and r.json()["user"] == "ana"
        assert first.get("/api/applications").status_code == 200
        assert first.get("/api/users").status_code == 403

        r = second.post("/api/auth/register", json={"username": "bruno", "password": "password-bruno"})
        assert r.json() == {"status": "pending"}
        assert login(second, "bruno", "password-bruno").json()["error"] == "pending_approval"
        assert second.post("/api/auth/register", json={"username": "boss", "password": "whatever-1"}).status_code == 409
        assert second.post("/api/auth/register", json={"username": "x", "password": "password-x"}).status_code == 400
        assert second.post("/api/auth/register", json={"username": "carla", "password": "short"}).status_code == 400
        assert second.post("/api/auth/register", json={"username": "Ana Lopez", "password": "password-x"}).json()["error"] == "invalid_username"
        r = second.post("/api/auth/register", json={"username": "Widi@Example.com", "password": "fictional-pass-1"})
        assert r.json() == {"status": "pending"}  # an email is a fine user name

        login(boss, **ADMIN)
        assert boss.get("/api/auth/me").json()["pending_users"] == 2
        users = boss.get("/api/users").json()
        assert [(u["username"], u["status"]) for u in users] == [
            ("bruno", "pending"), ("widi@example.com", "pending"), ("ana", "active")]
        boss.post("/api/users/bruno/approve")
        assert login(second, "bruno", "password-bruno").status_code == 200
        assert next(u for u in boss.get("/api/users").json() if u["username"] == "bruno")["approved_by"] == "boss"

        # disabling or a new password signs the user out everywhere
        boss.post("/api/users/ana/disable")
        assert first.get("/api/applications").status_code == 401
        assert login(first, "ana", "password-ana").json()["error"] == "disabled"
        boss.post("/api/users/ana/enable")
        boss.post("/api/users/bruno/password", json={"password": "a-new-password"})
        assert second.get("/api/applications").status_code == 401
        assert login(second, "bruno", "a-new-password").status_code == 200
        assert boss.delete("/api/users/boss").status_code == 404  # the superuser lives in the environment


def test_repeated_failures_are_slowed_down(ws):
    with TestClient(create_app(ws, runner=FakeRunner())) as c:
        codes = [login(c, "boss", f"guess-{i}").status_code for i in range(6)]
        assert codes[:5] == [401] * 5 and codes[5] == 429
        assert login(c, **ADMIN).status_code == 429  # still waiting, even with the right password


def test_public_mode_accepts_any_host_but_still_needs_a_session(ws):
    with TestClient(create_app(ws, runner=FakeRunner())) as c:
        assert c.get("/api/workspace", headers={"host": "abc.ngrok-free.app"}).status_code == 421
    with TestClient(create_app(ws, runner=FakeRunner(), public=True), base_url="https://testserver") as c:
        tunnel = {"host": "abc.ngrok-free.app", "x-forwarded-for": "203.0.113.9", "x-forwarded-proto": "https"}
        assert c.get("/api/workspace", headers=tunnel).status_code == 401
        assert c.get("/", headers=tunnel).status_code in (200, 500)  # the sign-in page itself is open
        r = c.post("/api/auth/login", json=ADMIN, headers={**tunnel, "origin": "https://abc.ngrok-free.app"})
        assert r.status_code == 200 and "secure" in r.headers["set-cookie"].lower()
        info = c.get("/api/workspace", headers=tunnel).json()
        assert info["local"] is False and info["lan"] is None
        new(ws, "Acme", "Engineer")
        assert c.post("/api/applications/1/open-folder", headers=tunnel).status_code == 403
        r = c.patch("/api/applications/1/status", json={"status": "sent"},
                    headers={**tunnel, "origin": "https://evil.example"})
        assert r.status_code == 403


def test_web_refuses_to_expose_the_default_admin_password(ws, monkeypatch):
    import web  # noqa: PLC0415
    monkeypatch.delenv("CVT_ADMIN_PASSWORD")
    with pytest.raises(SystemExit) as e:
        web.main(["--workspace", str(ws), "--public", "--no-open"])
    assert "DEFAULT_ADMIN" in str(e.value)


def test_admin_password_can_come_from_the_workspace_env_file(ws, monkeypatch):
    from webapp import auth  # noqa: PLC0415
    monkeypatch.delenv("CVT_ADMIN_USER")
    monkeypatch.delenv("CVT_ADMIN_PASSWORD")
    assert auth.admin_credentials() == ("admin", "admin", True)
    (ws / ".cv-tailor" / "web").mkdir(parents=True, exist_ok=True)
    (ws / ".cv-tailor" / "web" / ".env").write_text("CVT_ADMIN_USER=Admin\nCVT_ADMIN_PASSWORD='from file'\n",
                                                   encoding="utf-8")
    auth.load_env(ws)
    assert auth.admin_credentials() == ("admin", "from file", False)


def test_allow_list(ws):
    skill_cmd = f'python "{EXAMPLES.parent / "skills" / "cv-tailor" / "cvt.py"}" index new --company Acme'
    assert permissions.decide(ws, "Bash", {"command": skill_cmd}, []) == "allow"
    assert permissions.decide(ws, "Bash", {"command": skill_cmd + " | head -5"}, []) == "allow"
    assert permissions.decide(ws, "Bash", {"command": skill_cmd + " && rm -rf ~"}, []) == "ask"
    assert permissions.decide(ws, "Bash", {"command": skill_cmd + " > out.txt"}, []) == "ask"
    assert permissions.decide(ws, "Bash", {"command": "curl https://x.example"}, []) == "ask"
    look = 'cd "/w" && ls -R learnings 2>&1 | head -50; cat learnings/*.md 2>/dev/null'
    assert permissions.decide(ws, "Bash", {"command": look}, []) == "allow"
    assert permissions.decide(ws, "Bash", {"command": "cat a.md > b.md"}, []) == "ask"
    assert permissions.decide(ws, "Bash", {"command": "ls; python other.py"}, []) == "ask"
    app = ws / "applications" / "000001-acme"
    save = f'cd "{app}" && mkdir -p notes && cat > positioning.md <<\'EOF\'\n# rm -rf / > x is just text\nEOF'
    assert permissions.decide(ws, "Bash", {"command": save}, []) == "allow"
    escape = f'cd "{app}" && cat > ../../../outside.md <<\'EOF\'\nx\nEOF'
    assert permissions.decide(ws, "Bash", {"command": escape}, []) == "ask"
    tail = f'cd "{app}" && cat > a.md <<\'EOF\' && curl https://x.example\nx\nEOF'
    assert permissions.decide(ws, "Bash", {"command": tail}, []) == "ask"
    assert permissions.decide(ws, "Bash", {"command": "cat > a.md <<'EOF'\nx\nEOF"}, []) == "ask"
    assert permissions.decide(ws, "Bash", {"command": f'cd "{app}"\nrm -rf notes'}, []) == "ask"
    assert permissions.decide(ws, "Bash", {"command": 'python -c "import os" cvt.py'}, []) == "ask"
    var = f'cd "{app}"\nC="/s/cvt.py"\npython "$C" build cv.en.yml'
    assert permissions.decide(ws, "Bash", {"command": var}, []) == "allow"
    assert permissions.decide(ws, "Bash", {"command": f'cd "{app}" && echo x > "$OUT"'}, []) == "ask"
    assert permissions.decide(ws, "Bash", {"command": 'C="rm -rf /"; $C'}, []) == "ask"
    assert permissions.decide(ws, "PowerShell", {"command": '& "C:\\Py\\python.exe" "C:\\s\\cvt.py" doctor'}, []) == "allow"
    assert permissions.decide(ws, "Bash", {"command": f'cd "{app}"\npython "/s/cvt.py" extract a.pdf'}, []) == "allow"
    assert permissions.decide(ws, "Write", {"file_path": str(ws / "applications" / "x.md")}, []) == "allow"
    assert permissions.decide(ws, "Write", {"file_path": str(EXAMPLES / "sample-pool" / "x.md")}, []) == "ask"
    assert permissions.decide(ws, "Read", {"file_path": "C:/anything"}, []) == "allow"
    assert permissions.decide(ws, "mcp__mail__send", {}, []) == "ask"
    assert permissions.decide(ws, "mcp__mail__send", {}, ["mcp__mail__send"]) == "allow"


def test_runner_links_the_thread_only_to_a_real_new_application(ws):
    sdk = pytest.importorskip("claude_agent_sdk")
    from webapp.events import Bus  # noqa: PLC0415
    from webapp.runner import Runner  # noqa: PLC0415
    from webapp.threads import Store  # noqa: PLC0415
    store = Store(ws)
    runner = Runner(ws, store, Bus())
    t = store.create("offer", "Data Engineer at Acme")
    example = 'cvt index new ... prints {"id": "000012", "dir": "..."}'

    def call(tool_id, name, tool_input, output):
        runner._handle(t["id"], sdk.AssistantMessage(content=[sdk.ToolUseBlock(tool_id, name, tool_input)], model="m"))
        runner._handle(t["id"], sdk.UserMessage(content=[sdk.ToolResultBlock(tool_id, output)]))

    call("a", "Read", {"file_path": "references/generate.md"}, example)
    assert store.get(t["id"])["app_id"] is None
    call("b", "Bash", {"command": 'python "/s/cvt.py" index new --company Acme'}, '{"id": "000003", "dir": "/w/x"}')
    assert store.get(t["id"])["app_id"] == "000003"
