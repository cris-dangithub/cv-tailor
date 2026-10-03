#!/usr/bin/env python3
"""
Incremental GitHub evidence cache for a `github` pool source: which repositories exist and
how much of the candidate's own work is in each, so a new offer doesn't rescan everything.

    pool_github.py sync   [--source N] [--full]
    pool_github.py status [--source N]

The pool source (in .cv-tailor/config.yaml) looks like:

    - type: github
      owners:                       # where to look
        - {name: octocat, kind: user, account: octocat}
        - {name: acme-inc, kind: org, account: octocat-work}
      identities: [octocat, octo-work]   # author logins/emails the candidate commits with
      since: 2023-01-01                  # ignore repos without pushes since (optional)

The cache lives in <workspace>/.cv-tailor/cache/ and is never versioned (it can contain
private repository names). It tells where to look, never what to claim: authorship of a
file or the use of a library is always checked against the API at the moment of writing.
Entries verified more than 120 days ago are hypotheses again.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import WS_MARKER, load_config, read_json, require_workspace, today, write_json  # noqa: E402

STALE_DAYS = 120
_tokens: dict[str, str] = {}


def gh(*args, account=None) -> str:
    """Read-only GitHub API call. Uses the account's token through GH_TOKEN instead of
    `gh auth switch`, so the user's active gh account is never changed."""
    exe = shutil.which("gh")
    if not exe:
        sys.exit("gh (GitHub CLI) is not installed: https://cli.github.com")
    env = dict(os.environ)
    if account:
        if account not in _tokens:
            r = subprocess.run([exe, "auth", "token", "--user", account], capture_output=True, text=True)
            _tokens[account] = r.stdout.strip() if r.returncode == 0 else ""
        if _tokens[account]:
            env["GH_TOKEN"] = _tokens[account]
    r = subprocess.run([exe, "api", *args], capture_output=True, text=True, env=env)
    return r.stdout if r.returncode == 0 else ""


def list_repos(owner: dict) -> list[dict]:
    path = f"orgs/{owner['name']}/repos" if owner.get("kind") == "org" else "user/repos?affiliation=owner,collaborator"
    sep = "&" if "?" in path else "?"
    out = gh("--paginate", f"{path}{sep}per_page=100",
             "--jq", ".[]|[.full_name,.pushed_at,.language,.private]|@tsv", account=owner.get("account"))
    repos = []
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        full, pushed, lang, priv = parts
        if owner.get("kind") != "org" and not full.lower().startswith(owner["name"].lower() + "/"):
            continue
        repos.append({"full_name": full, "pushed_at": pushed[:10], "language": lang or "",
                      "private": priv == "true"})
    return repos


def measure(full_name: str, identities: list[str], account: str | None) -> tuple[int, str]:
    total, last = 0, ""
    for ident in identities:
        out = gh(f"repos/{full_name}/commits?author={ident}&per_page=100",
                 "--jq", '[length, (.[0].commit.author.date // "")]|@tsv', account=account)
        if not out.strip():
            continue
        try:
            n, date = out.strip().split("\t")
        except ValueError:
            continue
        total += int(n)
        last = max(last, date[:10])
    return total, last  # per_page caps at 100: "100" means "a hundred or more"


def sources(ws, only=None):
    srcs = (load_config(ws).get("pool") or {}).get("sources", [])
    found = [(i, s) for i, s in enumerate(srcs) if s.get("type") == "github" and (only is None or i == only)]
    if not found:
        sys.exit("No github pool source in the config (add one with: workspace.py add-pool github:USER)")
    return found


def cache_path(ws, i) -> pathlib.Path:
    p = ws / WS_MARKER / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"github-{i}.json"


def sync(ws, i, src, full=False):
    cache = read_json(cache_path(ws, i), {}) or {}
    repos, empty = cache.get("repos", {}), cache.get("no_trace", {})
    since = str(src.get("since") or "1970-01-01")
    new, changed, skipped, no_trace = [], [], 0, 0
    for owner in src.get("owners", []):
        listed = list_repos(owner)
        active = [r for r in listed if r["pushed_at"] >= since]
        print(f"  {owner['name']}: {len(listed)} repos, {len(active)} pushed since {since}")
        for r in active:
            fn = r["full_name"]
            prev = repos.get(fn) or empty.get(fn)
            if prev and not full and r["pushed_at"] <= prev.get("verified_on", ""):
                skipped += 1
                continue
            n, last = measure(fn, src.get("identities", []), owner.get("account"))
            if n == 0:
                # remember empty repos too, or they are re-queried on every pass
                no_trace += 1
                repos.pop(fn, None)
                empty[fn] = {"pushed_at": r["pushed_at"], "verified_on": today()}
                continue
            empty.pop(fn, None)
            (new if prev is None else changed).append(fn)
            repos[fn] = {"owner": owner["name"], "language": r["language"], "private": r["private"],
                         "pushed_at": r["pushed_at"], "own_commits": n, "last_own_commit": last,
                         "verified_on": today()}
    write_json(cache_path(ws, i), {
        "generated": today(), "since": since,
        "note": "own_commits caps at 100 per page. Contains private repo names: never version or quote them.",
        "repos": dict(sorted(repos.items(), key=lambda kv: -kv[1]["own_commits"])),
        "no_trace": dict(sorted(empty.items()))})
    print(f"  new={len(new)} changed={len(changed)} unchanged(skipped)={skipped} no-trace={no_trace}")


def status(ws, i):
    c = read_json(cache_path(ws, i))
    if not c:
        sys.exit("no cache yet: run `pool_github.py sync`")
    repos = c["repos"]
    limit = (dt.date.today() - dt.timedelta(days=STALE_DAYS)).isoformat()
    year = (dt.date.today() - dt.timedelta(days=365)).isoformat()
    stale = [k for k, v in repos.items() if v["verified_on"] < limit]
    print(json.dumps({
        "cache_date": c["generated"], "repos_with_own_commits": len(repos),
        "stale_entries": len(stale),
        "active_last_12_months": sum(1 for v in repos.values() if v["last_own_commit"] >= year),
        "top": [{"repo": k, "own_commits": v["own_commits"], "last": v["last_own_commit"],
                 "language": v["language"], "private": v["private"]} for k, v in list(repos.items())[:20]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sync", "status"])
    ap.add_argument("--source", type=int, default=None, help="index of the github source in pool.sources")
    ap.add_argument("--full", action="store_true", help="ignore the cache and re-verify everything")
    ap.add_argument("--workspace", default=None)
    a = ap.parse_args()
    ws = require_workspace(a.workspace)
    for idx, s in sources(ws, a.source):
        print(f"source {idx}")
        sync(ws, idx, s, a.full) if a.cmd == "sync" else status(ws, idx)
