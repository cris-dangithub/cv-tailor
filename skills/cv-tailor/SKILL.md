---
name: cv-tailor
description: >
  Generates a tailored CV (PDF, in every configured language) for each job offer, from the
  user's own knowledge pool (files, folders, links, GitHub) and in the user's own writing
  voice. Use it whenever the user pastes or links one or more job offers or job descriptions,
  even without asking for a CV; when they ask which CV they sent to a company, or say a
  recruiter replied and they don't remember what they applied with; when they give feedback
  on a generated application; when they update an application's status; when they want a new
  CV style from a sample CV or want to switch styles; and to set the skill up the first time.
  Never invents facts: everything comes from the pool or from the user's answers.
version: 0.1.0
---

# cv-tailor

Two required inputs: a **knowledge pool** about the candidate (configured once) and a **job
offer** (text, file or link). Output per offer: one numbered application folder with one CV per
configured language, each as editable YAML, HTML and PDF, plus the reasoning behind it.

`SKILL_DIR` below is the folder that contains this file. Every command is run through the
launcher, which uses the skill's own Python environment:

```
python "<SKILL_DIR>/cvt.py" <command> [args]        # `python3` on macOS/Linux if `python` is missing
```

Written below as `cvt <command>`.

---

## Step 0 — every time the skill starts

1. `cvt workspace find`
   - `NO_WORKSPACE` → this folder is not set up yet. Run the **setup** in
     `references/setup.md` in the current folder before anything else, even if the user pasted an
     offer (keep the offer and process it right after the setup).
   - a path → that is the workspace. Read `<ws>/.cv-tailor/config.yaml`.
2. **Speak the configured `ui_language`** for the whole session, whatever language the offer or
   the user's message is in. CVs are written in `cv_languages`, not in the UI language.
3. If any `cvt` command prints `ENV_MISSING` (exit 3): run `cvt setup-env`, then retry.
   `cvt doctor` explains anything else that is missing.

## Step 1 — what does the user want?

| The user... | Do | Read |
|---|---|---|
| pastes or links one or more job offers, with or without asking | generate the CVs (n offers × z languages) | `references/generate.md` |
| asks what they sent somewhere, or says a company replied | search past applications, show what was sent, offer to update the status | `references/applications.md` |
| comments on a generated application ("on 000012 I didn't like...") | record feedback, learn a rule, offer a v2 | `references/feedback.md` |
| reports progress (sent, interview, rejected, offer) | update the status | `references/applications.md` |
| shares a CV to copy its look, asks for another style, or to switch style | build or switch style (validated with the user) | `references/styles.md` |
| wants to change languages, pool or other settings | update the config | `references/setup.md` ("Changing the configuration") |
| wants to edit the content of an existing application | edit its YAML and rebuild | `references/pdf.md` ("Editing an existing version") |

When unsure whether a long pasted text is an offer, it is one if it describes a role to fill
(responsibilities, requirements, company). Don't ask "do you want a CV?": generate it.

---

## Rules that are never broken

1. **Nothing is invented.** No technology, number, client, title, date or responsibility that is
   not in the pool, in `learnings/facts.md`, or confirmed by the user in this session. A gap is
   declared, never filled. Unconfirmed items become `[PENDING: ...]` in the review file and are
   asked before the PDF is considered final.
2. **The pool is read-only.** Never create, edit, move or delete anything in a pool source. The
   skill writes only inside the workspace.
3. **Authorship is checked before attributing.** Being in a repository or a team document does
   not make it the candidate's work (`references/evidence-github.md` for code).
4. **Questions go in one batch**, short and concrete, with an example answer each. Answers that
   are facts are saved to `learnings/facts.md` so they are never asked again.
5. **The offer leads, learned preferences adjust.** `learnings/preferences.md` shapes choices
   and wording, but never removes what the offer asks for and never adds what the pool can't prove.
6. **Every PDF goes through `cvt build` with the active style** and is checked with `cvt verify`.
   No parallel renderer, no per-application CSS, never a smaller font or tighter leading to fit:
   cut by value and say what was cut.
7. **The YAML is the source of truth** of each CV. The HTML next to the PDF can be hand-edited
   and re-printed, but a rebuild from YAML replaces it.
8. **Previous outputs are never overwritten.** A new version of an application is `v2`, `v3` in
   the same folder; a new offer is a new folder.
9. **Links are verified before they go in**, with anchor text that says where they lead
   ("Link to the app"), and never private repository names or internal identifiers in a CV.
10. **Never say what the AI did** in the CV ("unlike AI", "irreplaceable"); the material speaks.

## Three questions, kept apart

| Question | Reference | Output in the application folder |
|---|---|---|
| **What** goes in, and why that material | `references/positioning.md` | `positioning.md` |
| **How it sounds**: the candidate's voice, no AI tells, ATS-safe | `references/voice.md` | `cv.<lang>.yml` + `CV-…-<LANG>-review.md` |
| **How it looks**: the PDF | `references/pdf.md` | `CV-…-<LANG>.html` + `.pdf` |

Choosing the wrong material is not fixed by good wording; good wording is not fixed by layout.

## Workspace map

```
<workspace>/
  .cv-tailor/config.yaml     ui_language, cv_languages, pool sources, active style, numbering
  CLAUDE.md, AGENTS.md       "an offer pasted here = generate" (written by the setup)
  profile/voice.md           the candidate's measured voice (+ voice.<lang>.json, samples/)
  learnings/facts.md         facts confirmed by the candidate (part of the pool from then on)
  learnings/preferences.md   rules learned from feedback
  styles/<name>/             styles created for this user (built-ins live in SKILL_DIR/styles)
  applications/index.jsonl   searchable index (rebuildable from each meta.json)
  applications/000001-company-role/
      offer.md  meta.json  positioning.md
      cv.en.yml  CV-Name-Company-EN.html  CV-Name-Company-EN.pdf  CV-Name-Company-EN-review.md
      feedback.md
```

## Agents

- **Claude Code**: delegate heavy reading to subagents (the pool reader in
  `references/pool-sources.md`; one positioning per offer when there are several) and keep only
  their conclusions. Pool skills, when present, are used by that subagent.
- **Codex and agents without subagents**: do the same steps in sequence; follow the pool's own
  `SKILL.md` files directly when the pool has them.
- Any agent without automatic skill discovery: the workspace `AGENTS.md` points to this file.
