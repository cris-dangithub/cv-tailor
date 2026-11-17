"""What the web app says to Claude. Kept neutral and in English: the skill itself answers in the
workspace's ui_language, as its instructions say."""
from __future__ import annotations

import pathlib
import re
import urllib.parse

SYSTEM = """\
You are running inside the cv-tailor web app. The user reads this conversation in a browser
and answers in it; there is no terminal they can see.
- Work with the cv-tailor skill as its instructions say, in the workspace's ui_language.
- When the skill needs facts from the user, ask all of them in one message and stop: the user
  answers here. Never wait on something the user cannot see.
- Refer to files by application id and file name (the app shows them); do not paste long paths.
- Create or change files with the Write and Edit tools, not shell redirections or heredocs: those
  are approved automatically inside the workspace, while shell writes wait for the user.
- Keep the final message of each turn short: what was produced, what is pending, and what the
  user can do next."""


DELIVERABLE_LINES = {
    "cv": "The user chose to produce: a CV only (do not write a proposal).",
    "proposal": ("The user chose to produce: an implementation proposal only (PDF + short message "
                 "to paste), no CV. Follow references/proposal.md."),
    "both": ("The user chose to produce: both a CV and an implementation proposal (PDF + short "
             "message to paste). Follow references/generate.md and references/proposal.md."),
}


def offer(text: str, url: str, deliverable: str | None = None) -> str:
    """The first message of an offer thread. `deliverable` comes from the selector on the desk
    (cv | proposal | both); without it the skill decides from the post, as in the chat."""
    choice = DELIVERABLE_LINES.get((deliverable or "").lower())
    note = f"\n{choice} Pass it to `cvt index new --deliverables`." if choice else ""
    what = "post" if deliverable in ("proposal", "both") else "job offer"
    if url and not text:
        return f"Use the cv-tailor skill to generate the application for the {what} at this link:\n{url}{note}"
    head = f"Link: {url}\n\n" if url else ""
    return (f"Use the cv-tailor skill to generate the application for this {what}.{note}\n\n"
            f"{head}<offer>\n{text}\n</offer>")


def offer_title(text: str, url: str) -> str:
    for line in (text or "").splitlines():
        line = re.sub(r"[#*_>`]+", "", line).strip()
        if len(line) > 3:
            return line[:90]
    if url:
        u = urllib.parse.urlparse(url)
        return (u.netloc + u.path)[:90]
    return "Job offer"


def chat_title(text: str) -> str:
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else "Chat"
    return line[:80]


def feedback(meta: dict, text: str) -> str:
    return (f"Feedback from the user on application {meta['id']} ({meta.get('company', '')} - "
            f"{meta.get('role', '')}). Follow the cv-tailor skill's feedback flow for it:\n\n{text}")


def style(sample: pathlib.Path, name: str) -> str:
    named = f' and call it "{name}"' if name else ""
    return (f"Use the cv-tailor skill to create a new CV style from this sample CV{named}:\n{sample}\n"
            "Show me the preview before activating it.")
