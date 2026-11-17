"""CV, proposal or both: what an application produces, how it is recorded, reported, served and
rendered. Fictional data only."""
import json
import shutil

import pytest

import build
import index
import report
import verify
from common import read_json
from conftest import EXAMPLES


def new(ws, *extra):
    index.main(["--workspace", str(ws), "new", "--company", "Brightside Foods",
                "--role", "Nightly sales pipeline", *extra])
    return index.app_dirs(ws)[-1]


def test_deliverables_default_and_choices(ws):
    assert read_json(new(ws) / "meta.json")["deliverables"] == ["cv"]
    assert read_json(new(ws, "--deliverables", "proposal") / "meta.json")["deliverables"] == ["proposal"]
    d = new(ws, "--deliverables", "both")
    assert read_json(d / "meta.json")["deliverables"] == ["cv", "proposal"]
    with pytest.raises(SystemExit):
        new(ws, "--deliverables", "letter")
    index.main(["--workspace", str(ws), "update", "1", "--set", "deliverables=proposal,cv"])
    assert read_json(index.app_dirs(ws)[0] / "meta.json")["deliverables"] == ["cv", "proposal"]
    line = json.loads((ws / "applications" / "index.jsonl").read_text(encoding="utf-8").splitlines()[1])
    assert line["deliverables"] == ["proposal"]


def test_proposal_files_are_registered_and_reported(ws):
    d = new(ws, "--deliverables", "both")
    for kind, name in (("pdf", "CV-AlexRivera-BrightsideFoods-EN.pdf"),
                       ("proposal-pdf", "Proposal-AlexRivera-BrightsideFoods-EN.pdf"),
                       ("proposal-message", "Proposal-AlexRivera-BrightsideFoods-EN-message.md")):
        (d / name).write_bytes(b"%PDF-1.4" if name.endswith(".pdf") else b"Hi")
        index.main(["--workspace", str(ws), "add-file", "1", "--lang", "en", "--kind", kind, "--path", name])
    meta = read_json(d / "meta.json")
    assert meta["files"]["en"]["proposal-pdf"] == "Proposal-AlexRivera-BrightsideFoods-EN.pdf"
    auto = report.render_auto(ws, d, meta)["top"]  # workspace ui_language = es
    assert "## Tus documentos" in auto
    assert "**CV — Inglés**: [CV-AlexRivera-BrightsideFoods-EN.pdf]" in auto
    assert "**Propuesta — Inglés**: [Proposal-AlexRivera-BrightsideFoods-EN.pdf]" in auto
    assert "[mensaje para pegar](Proposal-AlexRivera-BrightsideFoods-EN-message.md)" in auto
    # a CV-only application keeps the old wording
    d2 = new(ws)
    assert "## Tus CVs" in report.render_auto(ws, d2, read_json(d2 / "meta.json"))["top"]


def test_library_tells_proposals_from_cvs(ws):
    pytest.importorskip("fastapi")
    from webapp import library  # noqa: PLC0415
    d = new(ws, "--deliverables", "both")
    for name in ("CV-AlexRivera-BrightsideFoods-EN.pdf", "Proposal-AlexRivera-BrightsideFoods-EN.pdf"):
        (d / name).write_bytes(b"%PDF-1.4")
    index.main(["--workspace", str(ws), "add-file", "1", "--lang", "en", "--kind", "proposal-pdf",
                "--path", "Proposal-AlexRivera-BrightsideFoods-EN.pdf"])
    pdfs = {p["name"]: p for p in library.pdfs_of(d, read_json(d / "meta.json"))}
    assert pdfs["Proposal-AlexRivera-BrightsideFoods-EN.pdf"]["kind"] == "proposal"
    assert pdfs["Proposal-AlexRivera-BrightsideFoods-EN.pdf"]["current"] is True
    assert pdfs["CV-AlexRivera-BrightsideFoods-EN.pdf"]["kind"] == "cv"
    assert library.applications(ws)[0]["deliverables"] == ["cv", "proposal"]


def test_prompt_carries_the_choice():
    from webapp import prompts  # noqa: PLC0415
    plain = prompts.offer("Data Engineer at Acme", "")
    assert "job offer" in plain and "chose to produce" not in plain
    p = prompts.offer("Build a pipeline for us", "", "proposal")
    assert "implementation proposal only" in p and "--deliverables" in p and "<offer>" in p
    assert "both a CV and an implementation proposal" in prompts.offer("", "https://x.example/1", "both")
    assert "a CV only" in prompts.offer("Data Engineer", "", "cv")


@pytest.mark.skipif(build.find_browser() is None, reason="no Chrome/Edge/Chromium installed")
def test_sample_proposal_builds_with_its_own_page_target(ws):
    d = ws / "applications" / "000001-brightside"
    d.mkdir(parents=True)
    yml = d / "proposal.en.yml"
    shutil.copy(EXAMPLES / "sample-proposal.en.yml", yml)
    pdf = d / "Proposal-AlexRivera-BrightsideFoods-EN.pdf"
    pages = build.build(yml, pdf)
    assert 1 <= pages <= 3
    assert 'name="cv-tailor-target-pages" content="3"' in pdf.with_suffix(".html").read_text(encoding="utf-8")
    rep = verify.verify(pdf, content=yml)
    assert rep.failures == 0, [i for i in rep.items if not i["ok"]]
