#!/usr/bin/env python3
"""
Download a job offer from a link and save it as text, so the application keeps a copy even
after the posting disappears (search depends on that copy).

    fetch_offer.py URL [--out offer.md]

Strategy, in order: known ATS JSON endpoints (Greenhouse, Lever, BambooHR, LinkedIn guest
view), then schema.org JobPosting JSON-LD embedded in the page, then the page text.
Exit code 2 when nothing usable came back (login wall, JavaScript-only page): then ask the
user to paste the offer text.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import today  # noqa: E402
from extract_text import html_text  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")


def get(url: str, accept="text/html,application/json,*/*") -> tuple[int, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept,
                                               "Accept-Language": "en,es;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(3_000_000).decode("utf-8", "ignore"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except Exception as e:  # noqa: BLE001
        return 0, str(e), url


def from_jsonld(html: str) -> dict | None:
    for m in re.finditer(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html):
        try:
            data = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if isinstance(it, dict) and "JobPosting" in str(it.get("@type")):
                org = it.get("hiringOrganization") or {}
                loc = it.get("jobLocation") or {}
                if isinstance(loc, list):
                    loc = loc[0] if loc else {}
                addr = (loc.get("address") or {}) if isinstance(loc, dict) else {}
                place = ", ".join(x for x in [addr.get("addressLocality"), addr.get("addressRegion"),
                                              addr.get("addressCountry") if isinstance(addr.get("addressCountry"), str)
                                              else (addr.get("addressCountry") or {}).get("name")] if x)
                if it.get("jobLocationType") == "TELECOMMUTE":
                    place = (place + " (remote)").strip()
                return {"title": it.get("title", ""), "company": org.get("name", "") if isinstance(org, dict) else str(org),
                        "location": place, "date_posted": it.get("datePosted", ""),
                        "employment_type": str(it.get("employmentType", "")),
                        "description": html_text(it.get("description", ""))}
    return None


def known_ats(url: str) -> dict | None:
    m = re.search(r"(?:boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if m:
        code, body, _ = get(f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}", "application/json")
        if code == 200:
            j = json.loads(body)
            import html as h  # noqa: PLC0415
            return {"title": j.get("title", ""), "company": m.group(1), "location": (j.get("location") or {}).get("name", ""),
                    "date_posted": j.get("updated_at", "")[:10], "employment_type": "",
                    "description": html_text(h.unescape(j.get("content", "")))}
    m = re.search(r"jobs\.lever\.co/([^/]+)/([0-9a-f-]{36})", url)
    if m:
        code, body, _ = get(f"https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}", "application/json")
        if code == 200:
            j = json.loads(body)
            lists = "\n".join(f"\n## {x.get('text', '')}\n" + html_text(x.get("content", "")) for x in j.get("lists", []))
            return {"title": j.get("text", ""), "company": m.group(1),
                    "location": (j.get("categories") or {}).get("location", ""), "date_posted": "",
                    "employment_type": (j.get("categories") or {}).get("commitment", ""),
                    "description": (j.get("descriptionPlain") or "") + "\n" + lists + "\n" + (j.get("additionalPlain") or "")}
    m = re.search(r"https?://([^/]+\.bamboohr\.com)/careers/(\d+)", url)
    if m:
        code, body, _ = get(f"https://{m.group(1)}/careers/{m.group(2)}/detail", "application/json")
        if code == 200:
            j = (json.loads(body).get("result") or {}).get("jobOpening") or {}
            loc = j.get("location") or {}
            return {"title": j.get("jobOpeningName", ""), "company": m.group(1).split(".")[0],
                    "location": ", ".join(x for x in [loc.get("city"), loc.get("state")] if x),
                    "date_posted": j.get("datePosted", ""), "employment_type": j.get("employmentStatusLabel", ""),
                    "description": html_text(j.get("description", ""))}
    m = re.search(r"linkedin\.com/jobs/(?:view|collections)/?(?:[^/?]*-)?(\d{6,})", url) or \
        re.search(r"currentJobId=(\d{6,})", url)
    if m:
        code, body, _ = get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{m.group(1)}")
        if code == 200 and body:
            title = re.search(r'(?is)<h2[^>]*top-card-layout__title[^>]*>(.*?)</h2>', body)
            comp = re.search(r'(?is)topcard__org-name-link[^>]*>(.*?)</a>', body)
            loc = re.search(r'(?is)topcard__flavor--bullet[^>]*>(.*?)</span>', body)
            desc = re.search(r'(?is)<div[^>]*show-more-less-html__markup[^>]*>(.*?)</div>', body)
            clean = lambda x: html_text(x.group(1)).strip() if x else ""  # noqa: E731
            if desc:
                return {"title": clean(title), "company": clean(comp), "location": clean(loc),
                        "date_posted": "", "employment_type": "", "description": clean(desc)}
    return None


def to_markdown(url: str, d: dict, method: str) -> str:
    head = [f"# {d.get('title') or 'Job offer'}", "",
            f"- Company: {d.get('company', '')}", f"- Location: {d.get('location', '')}",
            f"- Employment type: {d.get('employment_type', '')}",
            f"- Posted: {d.get('date_posted', '')}", f"- Source: {url}",
            f"- Retrieved: {today()} ({method})", "", "---", ""]
    return "\n".join(head) + d.get("description", "").strip() + "\n"


def fetch(url: str) -> tuple[str | None, str]:
    d = known_ats(url)
    if d and len(d.get("description", "")) > 200:
        return to_markdown(url, d, "ATS API"), "ok"
    code, body, final = get(url)
    if code != 200 or not body:
        return None, f"HTTP {code}"
    d = from_jsonld(body)
    if d and len(d.get("description", "")) > 200:
        return to_markdown(final, d, "JSON-LD"), "ok"
    text = html_text(body)
    if len(text) < 400 or re.search(r"sign in|log in|iniciar sesi[oó]n|enable javascript", text[:1500], re.I) and len(text) < 2500:
        return None, "page needs login or JavaScript"
    t = re.search(r"(?is)<title>(.*?)</title>", body)
    return to_markdown(final, {"title": html_text(t.group(1)) if t else "", "description": text}, "page text"), "ok"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Download a job offer as Markdown.")
    ap.add_argument("url")
    ap.add_argument("--out", type=pathlib.Path)
    a = ap.parse_args()
    md, why = fetch(a.url)
    if md is None:
        print(f"FETCH_FAILED: {why}. Ask the user to paste the offer text.")
        sys.exit(2)
    if a.out:
        a.out.write_text(md, encoding="utf-8")
        print(f"saved {a.out} ({len(md)} chars)")
    else:
        print(md)
