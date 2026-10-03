import pytest

import sync_md
import voice
import workspace
from common import find_workspace, load_config, resolve_style
from conftest import EXAMPLES, SKILL


def test_init_writes_config_and_instructions(ws):
    cfg = load_config(ws)
    assert cfg["ui_language"] == "es" and cfg["cv_languages"] == ["en", "es"]
    assert cfg["pool"]["sources"][0]["type"] == "path"
    assert cfg["style"]["active"] == "default"
    for name in ("CLAUDE.md", "AGENTS.md"):
        text = (ws / name).read_text(encoding="utf-8")
        assert "cv-tailor:start" in text and "**es**" in text and "en, es" in text
    for d in ("applications", "learnings", "profile/samples", "styles"):
        assert (ws / d).is_dir()


def test_find_from_subfolder(ws):
    sub = ws / "applications" / "x"
    sub.mkdir(parents=True)
    assert find_workspace(sub) == ws


def test_init_refuses_twice(ws):
    with pytest.raises(SystemExit):
        workspace.main(["init", "--root", str(ws), "--ui-language", "en", "--cv-languages", "en"])


def test_instructions_block_keeps_user_content(ws):
    p = ws / "CLAUDE.md"
    p.write_text("# My notes\nkeep me\n\n" + p.read_text(encoding="utf-8"), encoding="utf-8")
    workspace.main(["--workspace", str(ws), "set", "ui_language=en"])
    t = p.read_text(encoding="utf-8")
    assert "keep me" in t and "**en**" in t and t.count("cv-tailor:start") == 1


def test_scan_pool_finds_samples(ws, capsys):
    workspace.main(["--workspace", str(ws), "scan-pool", "--save"])
    inv = load_config(ws)["pool"]["inventory"]["sources"][0]
    assert any("old-cv-2024" in s for s in inv["writing_samples"])


def test_style_resolution(ws):
    assert resolve_style(None, ws) == (SKILL / "styles" / "default").resolve()
    workspace.main(["--workspace", str(ws), "set", "style.active=default"])
    assert load_config(ws)["style"]["history"][-1]["style"] == "default"


def test_voice_measure_and_compare(tmp_path):
    unit, items = voice.units_from_text((EXAMPLES / "sample-pool" / "old-cv-2024.md").read_text(encoding="utf-8"))
    prof = voice.measure_units(unit, items, "en")
    assert unit == "bullets" and prof["count"] == 10 and prof["first_person"] == 0
    _, yitems, lang = voice.units_from_yaml(EXAMPLES / "sample-cv.en.yml")
    draft = voice.measure_units("bullets", yitems, lang)
    rows = {r["metric"]: r for r in voice.compare(prof, draft)}
    assert rows["first person"]["ok"] and rows["volume metrics (lines, commits, files)"]["ok"]


def test_language_detection():
    assert voice.detect_lang("Diseñé el pipeline de datos para la empresa y los informes") == "es"
    assert voice.detect_lang("Built the data pipeline for the company and the reports") == "en"


def test_sync_md_creates_and_preserves_review(tmp_path):
    md = tmp_path / "review.md"
    assert sync_md.sync(EXAMPLES / "sample-cv.en.yml", md)
    text = md.read_text(encoding="utf-8")
    assert text.startswith("# Alex Rivera") and sync_md.MARKER in text
    md.write_text(text.replace("## Audit report", "## Audit report\nhuman notes"), encoding="utf-8")
    sync_md.sync(EXAMPLES / "sample-cv.en.yml", md)
    assert "human notes" in md.read_text(encoding="utf-8")
