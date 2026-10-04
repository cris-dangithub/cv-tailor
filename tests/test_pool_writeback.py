import json
import re
import shutil

import pytest

import index
import pool_writeback as pw
import report
import workspace
from common import load_config, read_json, save_config
from conftest import EXAMPLES


@pytest.fixture
def managed(tmp_path, monkeypatch):
    """Workspace whose pool (a copy of the managed example) has a skill that allows updates."""
    monkeypatch.delenv("CV_TAILOR_WORKSPACE", raising=False)
    pool = tmp_path / "pool"
    shutil.copytree(EXAMPLES / "sample-managed-pool", pool)
    ws = tmp_path / "ws"
    workspace.main(["init", "--root", str(ws), "--ui-language", "es", "--cv-languages", "en",
                    "--pool", str(pool), "--candidate", "Alex Rivera"])
    workspace.main(["--workspace", str(ws), "scan-pool", "--save"])
    workspace.main(["--workspace", str(ws), "set-manager", "--json", json.dumps(
        {"source": 0, "skill": "pool-keeper", "can_update": True, "has_not_done_section": True,
         "not_done_location": "knowledge/not-done.md", "commits": False})])
    index.main(["--workspace", str(ws), "new", "--company", "Acme Mobility", "--role", "Analytics Engineer"])
    monkeypatch.chdir(ws)
    return ws, pool


def manager_writes(pool):
    """Stand-in for the pool's own agent: one correction, one new fact, one new file, one deletion."""
    prof = pool / "knowledge" / "profile.md"
    prof.write_text(prof.read_text(encoding="utf-8").replace(
        "- English: B2 (self-assessed)",
        "- English: C1, IELTS 7.5 (previously: B2 self-assessed, corrected 2026-10-04)"), encoding="utf-8")
    nd = pool / "knowledge" / "not-done.md"
    nd.write_text(nd.read_text(encoding="utf-8") + "- Spark in production (asked 2026-10-04)\n", encoding="utf-8")
    (pool / "knowledge" / "talks.md").write_text("# Talks\n- PyData Valencia 2025\n", encoding="utf-8")
    (pool / "knowledge" / "projects.md").unlink()


def test_manager_probe_is_stored(managed):
    ws, _ = managed
    pool = load_config(ws)["pool"]
    assert pool["manager"]["can_update"] and pool["writeback_source"] == 0
    assert pool["manager"]["skills_hash"] == pool["skills_hash"] != ""
    assert pool["skills"][0]["name"] == "pool-keeper"


def test_snapshot_finish_and_full_rollback(managed):
    ws, pool = managed
    original = pw.manifest(pool)
    run = pw.snapshot(ws, "1", None)["run"]
    manager_writes(pool)
    ch = pw.finish(ws, run, "Tu inglés pasó a C1 y agregué tu charla en PyData.", "")
    assert ch == {"created": ["knowledge/talks.md"], "deleted": ["knowledge/projects.md"],
                  "modified": ["knowledge/not-done.md", "knowledge/profile.md"]}
    meta = read_json(index.find_app(ws, "1") / "meta.json")
    assert meta["pool_writeback"][0]["status"] == "written"
    rep = (index.find_app(ws, "1") / "report.md").read_text(encoding="utf-8")
    assert "C1" in rep and "deshaz los cambios" in rep
    out = pw.rollback(ws, run, None, False)
    assert len(out["restored"]) == 4 and not out["refused_changed_since"]
    assert pw.manifest(pool) == original
    rep = (index.find_app(ws, "1") / "report.md").read_text(encoding="utf-8")
    assert "deshecho el" in rep


def test_partial_rollback_and_refusal(managed):
    ws, pool = managed
    run = pw.snapshot(ws, "1", None)["run"]
    manager_writes(pool)
    pw.finish(ws, run, "cambios", "")
    # the user edits profile.md after the write-back: rollback must not clobber it
    prof = pool / "knowledge" / "profile.md"
    prof.write_text(prof.read_text(encoding="utf-8") + "- note added by hand\n", encoding="utf-8")
    out = pw.rollback(ws, run, ["knowledge/profile.md", "knowledge/talks.md"], False)
    assert out["restored"] == ["knowledge/talks.md"]
    assert out["refused_changed_since"] == ["knowledge/profile.md"]
    assert not (pool / "knowledge" / "talks.md").exists()
    assert "Spark" in (pool / "knowledge" / "not-done.md").read_text(encoding="utf-8")  # untouched
    meta = read_json(index.find_app(ws, "1") / "meta.json")
    assert meta["pool_writeback"][0]["rolled_back"] == "partial"
    out = pw.rollback(ws, run, ["knowledge/profile.md"], True)
    assert out["restored"] == ["knowledge/profile.md"]
    assert "B2 (self-assessed)" in prof.read_text(encoding="utf-8")


def test_binary_files_are_reported_without_backup(managed):
    ws, pool = managed
    (pool / "photo.png").write_bytes(b"\x89PNG old")
    run = pw.snapshot(ws, "1", None)["run"]
    (pool / "photo.png").write_bytes(b"\x89PNG new")
    pw.finish(ws, run, "", "")
    out = pw.rollback(ws, run, None, False)
    assert out["no_backup_copy"] == ["photo.png"]
    assert "binary or too large" in (ws / ".cv-tailor" / "pool-writeback" / run / "diff.md").read_text(encoding="utf-8")


def test_unavailable_cases(managed, monkeypatch):
    ws, pool = managed
    monkeypatch.setattr(pw, "MAX_TEXT_TOTAL", 10)
    with pytest.raises(SystemExit) as e:
        pw.snapshot(ws, "1", None)
    assert e.value.code == 4
    monkeypatch.setattr(pw, "MAX_TEXT_TOTAL", 100 * 2**20)
    cfg = load_config(ws)
    cfg["pool"]["writeback"] = "off"
    save_config(ws, cfg)
    with pytest.raises(SystemExit):
        pw.snapshot(ws, "1", None)
    cfg["pool"]["writeback"] = "auto"
    cfg["pool"]["manager"]["can_update"] = False
    save_config(ws, cfg)
    with pytest.raises(SystemExit):
        pw.snapshot(ws, "1", None)


def test_report_is_for_people(managed):
    ws, _ = managed
    d = index.find_app(ws, "1")
    index.main(["--workspace", str(ws), "status", "1", "sent", "--note", "por el portal"])
    text = (d / "report.md").read_text(encoding="utf-8")
    assert text.startswith("# Acme Mobility")
    assert "Enviada" in text and "por el portal" in text
    # nothing technical in what the person reads (HTML comment markers are invisible)
    visible = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    for bad in ("cvt ", ".cv-tailor", ".py", "meta.json", "verify", "--"):
        assert bad not in visible, bad
    # the agent block survives a refresh
    text = text.replace("_(se completa al generar el CV)_", "Destaqué dbt porque la oferta lo pide.", 1)
    (d / "report.md").write_text(text, encoding="utf-8")
    index.main(["--workspace", str(ws), "status", "1", "interview"])
    text = (d / "report.md").read_text(encoding="utf-8")
    assert "Destaqué dbt" in text and "En entrevistas" in text


def test_report_without_manager_says_read_only(tmp_path, monkeypatch, ws):
    index.main(["--workspace", str(ws), "new", "--company", "Globex", "--role", "Data Engineer"])
    text = (index.find_app(ws, "1") / "report.md").read_text(encoding="utf-8")
    assert "no tiene una skill que la gestione" in text
    report.update(ws, index.find_app(ws, "1"))


def test_full_rollback_after_partial_counts_already_restored(managed):
    ws, pool = managed
    original = pw.manifest(pool)
    run = pw.snapshot(ws, "1", None)["run"]
    manager_writes(pool)
    pw.finish(ws, run, "cambios", "")
    pw.rollback(ws, run, ["knowledge/not-done.md"], False)
    out = pw.rollback(ws, run, None, False)
    assert out["already_restored"] == ["knowledge/not-done.md"] and not out["refused_changed_since"]
    assert pw.manifest(pool) == original
    meta = read_json(index.find_app(ws, "1") / "meta.json")
    assert meta["pool_writeback"][0]["rolled_back"] == "all"
