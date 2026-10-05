import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "cv-tailor"
sys.path.insert(0, str(SKILL / "scripts"))
EXAMPLES = ROOT / "examples"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """A fresh workspace pointing at the fictional sample pool."""
    monkeypatch.delenv("CV_TAILOR_WORKSPACE", raising=False)
    monkeypatch.setenv("CV_TAILOR_SYNC", "off")  # never spawn background sync workers in tests
    import workspace  # noqa: PLC0415
    workspace.main(["init", "--root", str(tmp_path), "--ui-language", "es",
                    "--cv-languages", "en,es", "--pool", str(EXAMPLES / "sample-pool"),
                    "--candidate", "Alex Rivera"])
    monkeypatch.chdir(tmp_path)
    return tmp_path
