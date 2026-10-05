# Setup (first use in a folder)

The skill can't be used until the folder where it was called is a workspace. The setup turns
the **current folder** into one. It asks four things, in this order, and nothing else.

## 0. Environment

Run `cvt doctor`. If the skill environment is missing, run `cvt setup-env` (it creates
`SKILL_DIR/.venv` with pipenv from `requirements.txt`; a few minutes the first time). If no
browser is found, tell the user to install Chrome, Edge or Chromium; nothing else is required.

## 1. Interface language — ask in English, wait for the answer

The very first question is always in English, alone, and you wait for the reply before asking
anything else:

> Which language do you want me to use when I talk to you in this workspace? (for example:
> English, Español, Bahasa Indonesia)

From the answer on, **everything** is in that language, including the rest of the setup and
every future session in this workspace.

## 2. CV languages

> In which languages should I generate each CV? For example: English, Spanish, Indonesian.

Store ISO 639-1 codes (`en, es, id`). Several languages mean each offer produces one CV per
language. Tell the user they can still ask for a single language for one offer ("this one
only in English") without changing the setting.

## 3. Knowledge pool (default)

> Where is the information about you? It can be a folder (with subfolders), a single file, a
> link (portfolio, LinkedIn export, online CV) or your GitHub user. You can give several.

- Paths: check they exist; store absolute paths. Links: store as given. GitHub: `github:<user>`;
  then ask for the work organisations and every identity they commit with (logins/emails) and
  from which date to look, and write them into the source (see `references/evidence-github.md`).
- Run `cvt workspace scan-pool --save`. It lists the skills, instruction files, document types,
  likely writing samples and style guides found in each path source.
- **Pool skills.** If the pool has skills (`SKILL.md`), they are the preferred way to read it:
  tell the user which ones were found and that generation will use them through a reader agent
  (`references/pool-sources.md`).
- **Managing skill.** When `scan-pool` reports `manager_probe: needed`, run the manager probe
  (`references/pool-writeback.md` step 1) and store it with `cvt workspace set-manager`. If a skill
  allows updates, tell the user, in plain words, that what they answer before each CV will also
  be saved in their knowledge base through that skill, automatically, and that any change can be
  undone; they can turn it off (`cvt workspace set pool.writeback=off`). If several sources can be
  updated, ask which one (`pool.writeback_source`).
- The pool is **never** created, hosted or reorganised by this skill, and never edited by it
  directly. If it is thin, say so; the missing facts will be asked per offer and stored in
  `learnings/facts.md`.
- Confirm the candidate's name as it must appear on CVs (from the pool; ask only if ambiguous).

## 4. Style (optional)

> Do you have a CV whose look you want me to copy? If not, I'll use the default style.

- No → `default`. Offer to show it: build `SKILL_DIR/../../examples/sample-cv.en.yml` if the
  examples folder exists, otherwise build the first real CV and show that.
- Yes → follow `references/styles.md` (measure, build, validate with the user). The approved
  style becomes the active one.

## 5. Write the workspace

```
cvt workspace init --root . --ui-language <code> --cv-languages <codes> \
    --pool "<source 1>" --pool "<source 2>" --candidate "<Full Name>"
cvt workspace scan-pool --save
```

`init` creates `.cv-tailor/config.yaml`, `applications/`, `learnings/`, `profile/`, `styles/`,
and writes a marked block into `CLAUDE.md` and `AGENTS.md` (existing content is preserved), so
that in future sessions pasting an offer in this folder is enough.

## 6. Voice profile

Build `profile/voice.md` now, following "Building the voice profile" in `references/voice.md`.
Sources in priority order: a style guide or writing-style skill in the pool → texts the
candidate wrote in the pool → 1–3 pasted samples (ask; save them to `profile/samples/`) →
none (say so; CVs will be factual and neutral).

## 7. Close

Summarise in the UI language: languages, pool sources (and pool skills found), style, voice
status, and how to use it: "paste an offer (or several, or links) here".

---

## Changing the configuration

| Change | Command |
|---|---|
| UI language | `cvt workspace set ui_language=<code>` (rewrites CLAUDE.md / AGENTS.md block) |
| CV languages | `cvt workspace set cv_languages=en,es,id` |
| add / remove a pool source | `cvt workspace add-pool <spec>` / `cvt workspace remove-pool <index>` then `scan-pool --save` |
| active style | see `references/styles.md` |
| candidate name | `cvt workspace set candidate.name="Full Name"` |

| knowledge-base updates on / off | `cvt workspace set pool.writeback=auto` / `=off` |

After a pool change, run `cvt workspace scan-pool --save` (it says whether the manager probe must be
redone) and offer to re-measure the voice profile.
