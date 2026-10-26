import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import index  # noqa: E402
from conftest import EXAMPLES  # noqa: E402
from webapp import permissions, settings  # noqa: E402
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

    async def send(self, tid, text, effort=None, shown=None):
        self.sent.append((tid, text, effort))

    async def stop(self, tid):
        pass

    def pending_for(self, tid):
        return []

    def answer(self, req, allow, remember):
        self.answers.append((req, allow, remember))
        return req == "known"


def new(ws, company, role):
    index.main(["--workspace", str(ws), "new", "--company", company, "--role", role])
    return index.app_dirs(ws)[-1]


@pytest.fixture
def client(ws):
    runner = FakeRunner()
    with TestClient(create_app(ws, runner=runner)) as c:
        c.runner = runner
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
    assert client.post("/api/permissions/gone", json={"allow": False}).status_code == 404


def test_foreign_hosts_and_origins_are_refused(ws, client):
    assert client.get("/api/workspace", headers={"host": "evil.example"}).status_code == 421
    r = client.patch("/api/applications/1/status", json={"status": "sent"},
                     headers={"origin": "https://evil.example"})
    assert r.status_code == 403


def test_lan_clients_need_the_token(ws):
    app = create_app(ws, lan=True, lan_hosts=["192.168.1.20"], runner=FakeRunner())
    with TestClient(app, client=("192.168.1.50", 5000)) as c:
        headers = {"host": "192.168.1.20:8765"}
        assert c.get("/api/workspace", headers=headers).status_code == 401
        r = c.get(f"/?t={settings.token(ws)}", headers=headers, follow_redirects=False)
        assert r.status_code == 303 and "cvt_token" in r.headers["set-cookie"]
        c.cookies.set("cvt_token", settings.token(ws))
        assert c.get("/api/workspace", headers=headers).status_code == 200
    app = create_app(ws, lan=False, runner=FakeRunner())
    with TestClient(app, client=("192.168.1.50", 5000)) as c:
        assert c.get("/api/workspace").status_code == 403


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
