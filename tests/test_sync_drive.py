import json
import time

import pytest

import index
import sync_drive as sd
from common import load_config, read_json, save_config
from conftest import EXAMPLES


@pytest.fixture
def drive(ws, tmp_path, monkeypatch):
    """A workspace with Google Drive sync pointing at a fake 'Mi unidad' folder."""
    root = tmp_path / "G" / "Mi unidad"
    root.mkdir(parents=True)
    sd.setup(ws, str(root), "cv-tailor", ["pdf", "report", "offer"], "desktop")
    monkeypatch.setenv("CV_TAILOR_SYNC", "off")  # index hooks must not spawn workers in tests
    index.main(["--workspace", str(ws), "new", "--company", "Acme", "--role", "Engineer",
                "--offer-file", str(EXAMPLES / "offers" / "acme-analytics-engineer.md")])
    d = index.find_app(ws, "1")
    (d / "CV-AlexRivera-Acme-EN.pdf").write_bytes(b"%PDF-1.4 fake")
    (d / "cv.en.yml").write_text("meta: {}\n", encoding="utf-8")
    return ws, root, d


def test_detect_finds_my_drive(tmp_path):
    (tmp_path / "Mi unidad").mkdir()
    found = sd.detect(win_letters=[str(tmp_path)], home=tmp_path / "nohome")
    assert found and found[0]["root"].endswith("Mi unidad") and found[0]["method"] == "desktop"


def test_setup_stores_config(drive):
    ws, root, _ = drive
    gd = load_config(ws)["sync"]["google_drive"]
    assert gd["enabled"] and gd["root"] == str(root) and gd["include"] == ["pdf", "report", "offer"]


def test_run_copies_same_structure_and_filters(drive):
    ws, root, d = drive
    log = sd.run(ws, None)
    base = root / "cv-tailor" / "applications" / d.name
    assert sorted(p.name for p in base.iterdir()) == ["CV-AlexRivera-Acme-EN.pdf", "offer.md", "report.md"]
    assert not log["errors"] and len(log["copied"]) == 3
    # nothing changed -> nothing copied
    assert sd.run(ws, None)["copied"] == []
    # only the changed file is copied again
    (d / "report.md").write_text("# changed\n", encoding="utf-8")
    assert sd.run(ws, [1])["copied"] == [f"applications/{d.name}/report.md"]
    s = sd.status(ws, 1)
    assert s["apps"]["1"]["files_ok"] == 3 and s["apps"]["1"]["status"] == "ok"
    assert list((ws / ".cv-tailor" / "sync" / "runs").iterdir())


def test_renumber_moves_folder_in_drive(drive, monkeypatch):
    ws, root, d = drive
    sd.run(ws, None)
    index.renumber(ws, 7)
    log = sd.run(ws, None)
    apps = root / "cv-tailor" / "applications"
    assert [p.name for p in apps.iterdir()] == ["0000001-acme-engineer"]
    assert log["moved"] == ["000001-acme-engineer -> 0000001-acme-engineer"] and log["copied"] == []


def test_local_delete_never_deletes_in_drive_until_clean(drive):
    ws, root, d = drive
    sd.run(ws, None)
    (d / "offer.md").unlink()
    sd.run(ws, None)
    target = root / "cv-tailor" / "applications" / d.name / "offer.md"
    assert target.exists()
    assert sd.clean(ws, yes=False) == [f"applications/{d.name}/offer.md"] and target.exists()
    sd.clean(ws, yes=True)
    assert not target.exists()


def test_unavailable_drive_marks_pending(drive):
    ws, root, d = drive
    cfg = load_config(ws)
    cfg["sync"]["google_drive"]["root"] = str(root.parent / "missing")
    save_config(ws, cfg)
    log = sd.run(ws, [1])
    assert log["errors"] and "not available" in log["errors"][0]
    assert sd.status(ws, 1)["apps"]["1"]["status"] == "pending"
    assert read_json(ws / ".cv-tailor" / "sync" / "pending.json") == [1]


def test_trigger_queues_and_single_worker(drive, monkeypatch):
    ws, root, d = drive
    monkeypatch.setenv("CV_TAILOR_SYNC", "on")
    spawned = []
    monkeypatch.setattr(sd, "spawn_worker", lambda w: spawned.append(w))
    assert sd.trigger(ws, 1)
    assert sd.acquire_lock(ws)            # a worker is now "running"
    sd.trigger(ws, 1)
    assert len(spawned) == 1              # no second worker while the lock is held
    sd.release_lock(ws)
    sd.drain(ws)                           # the worker empties the queue
    assert (root / "cv-tailor" / "applications" / d.name / "report.md").exists()
    assert read_json(ws / ".cv-tailor" / "sync" / "pending.json") == []


def test_trigger_is_noop_when_disabled(drive, monkeypatch):
    ws, _, _ = drive
    monkeypatch.setattr(sd, "spawn_worker", lambda w: pytest.fail("must not spawn"))
    assert sd.trigger(ws, 1) is False     # CV_TAILOR_SYNC=off from the fixture
