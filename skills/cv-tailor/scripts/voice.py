#!/usr/bin/env python3
"""
Measure how a person writes (their register), and compare a draft against it.

The voice is measured on texts the candidate wrote, never guessed from chat or invented.

    voice.py measure FILE [FILE...] [--lang es] [--json] [--save profile/voice.es.json]
    voice.py measure --yaml applications/000001-x/cv.en.yml        # measure a draft
    voice.py compare --profile profile/voice.en.json --yaml cv.en.yml

Units: bullets when the text has at least 5 of them (a CV); otherwise sentences (a cover
letter, a post). Metrics: first person, opening words, median/max length, colons that open
an enumeration, em-dash asides, causal clauses, volume metrics, bold per bullet.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics as st
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import read_json, read_yaml, write_json  # noqa: E402
from extract_text import extract  # noqa: E402

FIRST_PERSON = {
    "en": r"\b(I|I'm|I've|I'd|my|me|mine|myself)\b",
    "es": r"\b(yo|mi|mis|me|conmigo|m[ií]o|m[ií]a)\b",
    "id": r"\b(saya|aku|ku|milikku)\b",
    "pt": r"\b(eu|meu|minha|meus|minhas|comigo)\b",
    "fr": r"\b(je|j'|mon|ma|mes|moi)\b",
    "de": r"\b(ich|mein|meine|meinen|mich|mir)\b",
    "it": r"\b(io|mio|mia|miei|mie)\b",
}
CAUSAL = {
    "en": r"\b(because|so that|so|while|since|as a result)\b",
    "es": r"\b(porque|as[ií] que|ya que|mientras|puesto que|por lo que)\b",
    "id": r"\b(karena|sehingga|sementara|oleh karena itu)\b",
    "pt": r"\b(porque|j[aá] que|enquanto|de modo que)\b",
    "fr": r"\b(parce que|puisque|tandis que|afin que)\b",
    "de": r"\b(weil|da|w[aä]hrend|sodass)\b",
}
STOPWORDS = {
    "en": "the and of to in for with on at is was by from that this",
    "es": "de la el los las y en con para por que del un una se",
    "id": "dan yang di ke dari untuk dengan ini itu pada dalam sebagai",
    "pt": "de da do os as e em com para por que um uma não",
    "fr": "de la le les et en avec pour par que des un une du",
    "de": "der die das und in mit für von zu den ein eine auf",
}
VOLUME = r"\b\d[\d.,]*\s*(k\s*)?(lines? of code|lines|loc|commits?|files|repositor(y|ies)|l[ií]neas|archivos|repositorios|baris|berkas)\b"
BULLET_CHARS = ("-", "*", "•", "●", "○", "▪", "–", "➢", "■")


def detect_lang(text: str) -> str:
    words = re.findall(r"[a-záéíóúñüçãõàèäöß']+", text.lower())
    c = Counter(words)
    scores = {lang: sum(c[w] for w in sw.split()) for lang, sw in STOPWORDS.items()}
    return max(scores, key=scores.get) if any(scores.values()) else "en"


def units_from_text(raw: str) -> tuple[str, list[str]]:
    bullets, cur = [], None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith(BULLET_CHARS) and len(s) > 2:
            if cur:
                bullets.append(cur)
            cur = s.lstrip("".join(BULLET_CHARS) + " ").strip()
        elif cur is not None and s and not s.startswith("#"):
            cur += " " + s
        elif cur:
            bullets.append(cur)
            cur = None
    if cur:
        bullets.append(cur)
    clean = [re.sub(r"\s+", " ", b.replace("​", "")).strip() for b in bullets]
    clean = [b for b in clean if len(b) > 30]
    if len(clean) >= 5:
        return "bullets", clean
    flat = re.sub(r"\s+", " ", raw)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", flat) if len(s.strip()) > 30]
    return "sentences", sents


def units_from_yaml(path: pathlib.Path) -> tuple[str, list[str], str]:
    d = read_yaml(path)
    out = []

    def txt(v):
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return "".join(p if isinstance(p, str) else p.get("text", "") for p in v)
        if isinstance(v, dict):
            return txt(v.get("text", ""))
        return ""

    def walk_bullets(items):
        for it in items or []:
            out.append(txt(it))
            if isinstance(it, dict) and it.get("sub"):
                walk_bullets(it["sub"])

    for s in d.get("sections", []):
        if s.get("type") == "entries":
            for e in s.get("entries", []):
                walk_bullets(e.get("bullets"))
                for g in e.get("groups") or []:
                    walk_bullets(g.get("bullets"))
    out = [re.sub(r"\s+", " ", b).strip() for b in out if b and len(b) > 20]
    return "bullets", out, (d.get("meta") or {}).get("lang", "")


def measure_units(unit: str, items: list[str], lang: str) -> dict:
    plain = [re.sub(r"</?strong>|\*\*", "", b) for b in items]
    lengths = [len(b.split()) for b in plain]
    fp = re.compile(FIRST_PERSON.get(lang, FIRST_PERSON["en"]), re.I if lang != "en" else 0)
    causal = re.compile(CAUSAL.get(lang, CAUSAL["en"]), re.I)
    bold = [len(re.findall(r"<strong>|\*\*[^*]+\*\*", b)) for b in items]
    return {
        "unit": unit, "lang": lang, "count": len(items),
        "first_person": sum(1 for b in plain if fp.search(b)),
        "median_words": st.median(lengths) if lengths else 0,
        "max_words": max(lengths) if lengths else 0,
        "min_words": min(lengths) if lengths else 0,
        "openers": Counter(b.split()[0].strip(",.;:") for b in plain if b.split()).most_common(12),
        "colon_enumerations": sum(1 for b in plain if re.search(r":\s+\S+(,|;)\s", b)),
        "em_dash_asides": sum(1 for b in plain if re.search(r"\s[—–]\s|—", b)),
        "causal_clauses": sum(1 for b in plain if causal.search(b)),
        "volume_metrics": sum(1 for b in plain if re.search(VOLUME, b, re.I)),
        "bold_per_bullet": dict(Counter(bold)) if any(bold) else {},
        "ends_with_period": sum(1 for b in plain if b.rstrip().endswith(".")),
        "examples": plain[:3],
    }


def compare(profile: dict, draft: dict) -> list[dict]:
    rows = []

    def row(metric, value, target, ok):
        rows.append({"metric": metric, "draft": value, "target": target, "ok": bool(ok)})

    pm = profile.get("median_words") or 0
    row("median words", draft["median_words"], f"{pm} ±25%",
        not pm or abs(draft["median_words"] - pm) <= 0.25 * pm)
    row("max words", draft["max_words"], f"<= {profile.get('max_words')}",
        draft["max_words"] <= (profile.get("max_words") or 999))
    row("first person", draft["first_person"], profile.get("first_person", 0),
        (draft["first_person"] == 0) == (profile.get("first_person", 0) == 0))
    row("colons opening an enumeration", draft["colon_enumerations"], 0, draft["colon_enumerations"] == 0)
    row("em-dash asides", draft["em_dash_asides"], 0, draft["em_dash_asides"] == 0)
    row("causal clauses", draft["causal_clauses"], 0, draft["causal_clauses"] == 0)
    row("volume metrics (lines, commits, files)", draft["volume_metrics"], 0, draft["volume_metrics"] == 0)
    bad_bold = sum(v for k, v in draft.get("bold_per_bullet", {}).items() if int(k) == 0 or int(k) >= 3)
    if draft.get("bold_per_bullet"):
        row("bullets with 0 or 3+ bold spans", bad_bold, 0, bad_bold == 0)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure")
    p.add_argument("files", nargs="*", type=pathlib.Path)
    p.add_argument("--yaml", type=pathlib.Path)
    p.add_argument("--lang", default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--save", type=pathlib.Path)
    p = sub.add_parser("compare")
    p.add_argument("--profile", type=pathlib.Path, required=True)
    p.add_argument("--yaml", type=pathlib.Path, required=True)
    a = ap.parse_args(argv)

    if a.cmd == "measure":
        if a.yaml:
            unit, items, ylang = units_from_yaml(a.yaml)
            lang = a.lang or ylang or detect_lang(" ".join(items))
        else:
            if not a.files:
                ap.error("give files or --yaml")
            raw = "\n\n".join(extract(f) for f in a.files)
            unit, items = units_from_text(raw)
            lang = a.lang or detect_lang(raw)
        m = measure_units(unit, items, lang)
        m["sources"] = [str(f) for f in a.files] or [str(a.yaml)]
        if a.save:
            a.save.parent.mkdir(parents=True, exist_ok=True)
            write_json(a.save, m)
        if a.json or a.save:
            print(json.dumps(m, ensure_ascii=False, indent=2))
        else:
            for k, v in m.items():
                print(f"{k:>20}: {v}")
        return

    profile = read_json(a.profile)
    unit, items, ylang = units_from_yaml(a.yaml)
    draft = measure_units(unit, items, profile.get("lang") or ylang)
    rows = compare(profile, draft)
    print(f"{'metric':<42} {'draft':>8}  {'target':<12} ok")
    for r in rows:
        print(f"{r['metric']:<42} {str(r['draft']):>8}  {str(r['target']):<12} {'yes' if r['ok'] else 'NO'}")
    sys.exit(0 if all(r["ok"] for r in rows) else 1)


if __name__ == "__main__":
    main()
