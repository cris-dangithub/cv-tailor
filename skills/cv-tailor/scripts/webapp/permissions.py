"""What a headless session may do without asking. Anything else becomes an approval card in the
chat, answered from the browser.

The allow-list covers the skill's normal work: reading anywhere (the pool may live outside the
workspace), writing inside the workspace, running cvt.py, reading the web, and subagents.
"""
from __future__ import annotations

import pathlib
import re

from common import SKILL_DIR, load_config

READ_ONLY_TOOLS = {"Read", "Glob", "Grep", "LS", "NotebookRead", "WebFetch", "WebSearch", "Task",
                   "Agent", "Skill", "TodoWrite", "ToolSearch", "TaskOutput", "BashOutput"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
# commands that only look: the agent explores the workspace and the pool, and pipes cvt output
READ_COMMANDS = {"cat", "head", "tail", "ls", "dir", "echo", "type", "wc", "grep", "findstr", "stat",
                 "basename", "dirname", "realpath", "which", "where", "jq", "get-content", "select-object", "select-string", "get-childitem",
                 "test-path", "measure-object", "format-list", "format-table", "convertfrom-json",
                 "out-string", "write-output", "write-host", "get-item", "resolve-path", "cd",
                 "set-location", "pwd", "get-location", "true"}
SEPARATORS = re.compile(r"\s*(?:&&|\|\||;|\||\r?\n)\s*")
# redirections that only silence or merge output
QUIET = re.compile(r"\s\d?>\s*(?:/dev/null|\$null|nul)\b|\s2>&1\b|\|\s*Out-Null\b", re.I)
CVT = re.compile(r"""^["']?(?:[^\s"']*[\\/])?(?:python3?|py|pythonw)(?:\.exe)?["']?\s+["']?[^\s"']*cvt\.py["']?(?:\s|$)""",
                 re.I)
ASSIGN = re.compile(r"""^([A-Za-z_]\w*)=("[^"$`]*"|'[^']*'|[^\s"'$`;&|]+)$""")
ASSIGN_SEG = re.compile(r"""(?:^|(?<=&&)|(?<=;)|(?<=\n))\s*[A-Za-z_]\w*=("[^"$`]*"|'[^']*'|[^\s"'$`;&|]+)\s*(?=$|&&|;|\n)""")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
REDIRECT = re.compile(r"(?<![<\d&])(\d?>>?)\s*(\"[^\"]+\"|'[^']+'|[^\s;&|<>]+)")
CD = re.compile(r"(?:^|&&|;|\n)\s*(?:cd|Set-Location)\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)", re.I)


def _inside(path: str, root: pathlib.Path) -> bool:
    try:
        pathlib.Path(path).expanduser().resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def pool_roots(ws) -> list[pathlib.Path]:
    cfg = load_config(ws)
    srcs = (cfg.get("pool") or {}).get("sources") or []
    return [pathlib.Path(s["path"]) for s in srcs if s.get("type") == "path" and s.get("path")]


def pool_writable(ws) -> bool:
    """The pool's own managing skill accepts cv-tailor's write-back (detected at setup)."""
    pool = load_config(ws).get("pool") or {}
    return bool((pool.get("manager") or {}).get("can_update")) and pool.get("writeback") != "off"


def _segment_ok(seg: str, writable) -> bool:
    seg = seg.strip().lstrip("&").strip()
    if not seg:
        return True
    words = seg.split()
    if "cvt.py" in seg:  # the launcher itself, never `python -c ... cvt.py`
        return bool(CVT.match(seg))
    if words[0].lower() == "mkdir":
        return all(writable(w) for w in words[1:] if not w.startswith("-"))
    return words[0].lower() in READ_COMMANDS


def shell_allowed(command: str, ws=None) -> bool:
    """cvt.py and read-only commands, chained or piped. With a workspace, also writes (`>`, `>>`,
    `mkdir`) whose every target is inside it, which is how the skill often saves its files.
    Anything else asks."""
    # a heredoc body is data, whatever it contains; the rest of its first line is still command
    command = HEREDOC.sub(lambda m: " " + m.group(3), command)
    command = QUIET.sub(" ", command)
    # plain assignments (C="<skill>/cvt.py") are expanded where they are used, then dropped
    names = {}
    for seg in SEPARATORS.split(command):
        a = ASSIGN.match(seg.strip())
        if a:
            names[a.group(1)] = a.group(2).strip("\"'")
    command = ASSIGN_SEG.sub(" ", command)
    command = re.sub(r"\$\{?(\w+)\}?", lambda m: names.get(m.group(1), m.group(0)), command)
    root = pathlib.Path(ws).resolve() if ws else None
    cds = CD.findall(command)
    cwd = pathlib.Path(cds[0].strip("\"'")) if len(cds) == 1 and CD.match(command) else None

    def writable(target: str) -> bool:
        if "$" in target or "%" in target:  # a variable we could not resolve
            return False
        p = pathlib.Path(target.strip("\"'")).expanduser()
        if not p.is_absolute():
            if cwd is None:
                return False
            p = cwd / p
        return root is not None and _inside(str(p), root) and not _inside(str(p), SKILL_DIR)

    if not all(writable(r.group(2)) for r in REDIRECT.finditer(command)):
        return False
    command = REDIRECT.sub(" ", command)
    # other redirections, substitutions and background jobs always ask
    if re.search(r"[<>`]|\$\(|\bInvoke-Expression\b|\biex\b|\bStart-Process\b|\brm\b|Remove-Item",
                 command, re.I):
        return False
    return all(_segment_ok(s, writable) for s in SEPARATORS.split(command))


def rule_key(tool: str, tool_input: dict) -> str:
    """What "remember" stores: the tool, plus the first word of a shell command."""
    if tool in SHELL_TOOLS:
        first = (str(tool_input.get("command", "")).split() or [""])[0]
        return f"{tool}:{pathlib.Path(first.strip(chr(34) + chr(39))).name.lower()}"
    return tool


def decide(ws, tool: str, tool_input: dict, always_allow: list[str]) -> str:
    """'allow' or 'ask'."""
    if rule_key(tool, tool_input) in always_allow or tool in always_allow:
        return "allow"
    if tool in READ_ONLY_TOOLS:
        return "allow"
    if tool in WRITE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if _inside(path, pathlib.Path(ws)) and not _inside(path, SKILL_DIR):
            return "allow"
        if pool_writable(ws) and any(_inside(path, r) for r in pool_roots(ws)):
            return "allow"
        return "ask"
    if tool in SHELL_TOOLS:
        return "allow" if shell_allowed(str(tool_input.get("command", "")), ws) else "ask"
    return "ask"


def summary(tool: str, tool_input: dict, limit: int | None = 300) -> str:
    """One line for the tool notes; the approval card passes limit=None, because what the
    user approves must be shown whole."""
    for k in ("command", "file_path", "notebook_path", "url", "pattern", "query", "description",
              "skill", "prompt"):
        v = tool_input.get(k)
        if v:
            if limit is None:
                return str(v)[:20000]
            v = str(v).replace("\n", " ")
            return v if len(v) <= limit else v[:limit - 3] + "..."
    return ""
