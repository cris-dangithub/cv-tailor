"""End-to-end render. Skipped when no Chromium-family browser is installed."""
import shutil

import pytest

import build
import verify
from conftest import EXAMPLES

pytestmark = pytest.mark.skipif(build.find_browser() is None, reason="no Chrome/Edge/Chromium installed")


def test_build_and_verify_sample(ws):
    d = ws / "applications" / "000001-acme"
    d.mkdir(parents=True)
    yml = d / "cv.en.yml"
    shutil.copy(EXAMPLES / "sample-cv.en.yml", yml)
    pdf = d / "CV-AlexRivera-Acme-EN.pdf"
    pages = build.build(yml, pdf)
    assert pdf.exists() and pdf.with_suffix(".html").exists() and pages == 1
    # assets are staged inside the workspace, so the HTML survives a skill update
    assert ".cv-tailor/style-cache/default-" in pdf.with_suffix(".html").read_text(encoding="utf-8")
    rep = verify.verify(pdf, content=yml)
    assert rep.failures == 0, [i for i in rep.items if not i["ok"]]


def test_from_html_reprint(ws, tmp_path):
    yml = ws / "cv.en.yml"
    shutil.copy(EXAMPLES / "sample-cv.en.yml", yml)
    pdf = ws / "out.pdf"
    build.build(yml, pdf)
    html = pdf.with_suffix(".html")
    html.write_text(html.read_text(encoding="utf-8").replace("Analytics Engineer", "Analytics Eng."), encoding="utf-8")
    out = ws / "edited.pdf"
    assert build.build_from_html(html, out) == 1
