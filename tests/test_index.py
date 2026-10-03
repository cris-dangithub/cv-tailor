import json
import shutil

import index
from common import load_config, read_json, save_config, write_json
from conftest import EXAMPLES


def new(ws, company, role, offer=None, **kw):
    args = ["--workspace", str(ws), "new", "--company", company, "--role", role]
    if offer:
        args += ["--offer-file", str(offer)]
    for k, v in kw.items():
        args += [f"--{k}", v]
    index.main(args)
    return index.app_dirs(ws)[-1]


def test_numbering_and_folder_names(ws):
    d1 = new(ws, "Acme Mobility", "Analytics Engineer")
    d2 = new(ws, "Globex Seguros", "Ingeniero/a de Datos Sr.")
    assert d1.name == "000001-acme-mobility-analytics-engineer"
    assert d2.name == "000002-globex-seguros-ingeniero-a-de-datos-sr"
    meta = read_json(d2 / "meta.json")
    assert meta["id"] == "000002" and meta["status"] == "generated"
    assert meta["languages"] == ["en", "es"]
    lines = (ws / "applications" / "index.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["id"] for x in lines] == ["000001", "000002"]


def test_overflow_renumbers_everything(ws):
    first = new(ws, "Acme", "Engineer")
    last = ws / "applications" / "999999-initech-analyst"
    last.mkdir()
    write_json(last / "meta.json", {"id": "999999", "company": "Initech", "role": "Analyst"})
    created = new(ws, "Hooli", "Data Engineer")
    names = sorted(p.name for p in (ws / "applications").iterdir() if p.is_dir())
    assert names == ["0000001-acme-engineer", "0999999-initech-analyst", "1000000-hooli-data-engineer"]
    assert read_json(ws / "applications" / "0999999-initech-analyst" / "meta.json")["id"] == "0999999"
    assert load_config(ws)["numbering"]["width"] == 7
    assert created.name.startswith("1000000-")
    assert not first.exists()


def test_small_width_rollover(ws):
    cfg = load_config(ws)
    cfg["numbering"]["width"] = 1
    save_config(ws, cfg)
    for i in range(10):
        new(ws, f"Company {i}", "Role")
    names = [d.name for d in index.app_dirs(ws)]
    assert names[0].startswith("01-") and names[-1].startswith("10-")


def test_status_and_history(ws):
    new(ws, "Acme", "Engineer")
    index.main(["--workspace", str(ws), "status", "1", "sent", "--note", "via portal"])
    index.main(["--workspace", str(ws), "status", "1", "interview"])
    meta = read_json(index.find_app(ws, "1") / "meta.json")
    assert meta["status"] == "interview"
    assert [h["status"] for h in meta["status_history"]] == ["generated", "sent", "interview"]


def test_search_finds_company_inside_an_email(ws):
    new(ws, "Acme Mobility", "Analytics Engineer", EXAMPLES / "offers" / "acme-analytics-engineer.md")
    new(ws, "Globex Seguros", "Ingeniero de Plataforma de Datos",
        EXAMPLES / "offers" / "globex-data-platform.md", keywords="airflow,terraform")
    email = ("Hola Alex, gracias por tu interés en la posición de plataforma de datos en GLOBEX. "
             "¿Tienes disponibilidad para una llamada?")
    res = index.search(ws, email)
    assert res and res[0]["company"] == "Globex Seguros"
    res = index.search(ws, "Re: Acme Mobilty - next steps")  # misspelt
    assert res and res[0]["company"] == "Acme Mobility"
    res = index.search(ws, "dbt tests BigQuery remote EU")
    assert res[0]["company"] == "Acme Mobility"


def test_rebuild_from_meta(ws):
    new(ws, "Acme", "Engineer")
    (ws / "applications" / "index.jsonl").unlink()
    assert index.rebuild_index(ws) == 1


def test_add_file_relative(ws):
    d = new(ws, "Acme", "Engineer")
    shutil.copy(EXAMPLES / "sample-cv.en.yml", d / "cv.en.yml")
    index.main(["--workspace", str(ws), "add-file", "1", "--lang", "en", "--kind", "yaml", "--path", "cv.en.yml"])
    assert read_json(d / "meta.json")["files"]["en"]["yaml"] == "cv.en.yml"
