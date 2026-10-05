# cv-tailor

*[Leer en español](README.es.md)*

An agent skill (Claude Code and Codex) that turns **your knowledge pool** and **a job offer** into
a tailored CV in PDF, in every language you choose, written the way **you** write. It never
invents a fact.

```
you:   [paste one or more job offers, or links]
agent: 000014 Acme Mobility — Analytics Engineer  → CV-AlexRivera-AcmeMobility-EN.pdf, -ES.pdf
       strong matches · gaps and how to argue them · what was left out and why · pending checks
```

## What it does

- **Generates** one CV per offer and language (n offers × z languages), from your pool only:
  files, folders, links, GitHub. Missing facts are asked once and remembered.
- **Writes in your voice**, measured from texts you wrote, with numeric checks (sentence length,
  first person, AI tells) instead of opinions.
- **Numbers and keeps** every application (`applications/000001-company-role/`) with the offer,
  the reasoning, the editable YAML, the HTML and the PDF.
- **Finds what you sent**: paste the recruiter's email and it tells you which CV went to them.
- **Tracks status**: sent, replied, interview, rejected, offer.
- **Learns** from your feedback ("on 000012 I didn't like…") without drifting from what each
  offer asks.
- **Teaches your knowledge base**: if your pool is managed by its own skill and allows updates,
  the facts you confirm while preparing a CV are saved there through that skill, automatically,
  without duplicates, and can be undone.
- **Keeps a report per application** (`report.md`), written for you: status, your CVs, what was
  decided and why, the questions you were asked and your answers.
- **Styles**: a measured default style, or a new one copied from any CV you like (measured,
  previewed side by side, approved by you). The last chosen style stays active.

## Install

Requirements: Python 3.9+, and Chrome, Edge, Chromium or Brave (any one). Optional: `gh` (GitHub
as a pool source), LibreOffice (DOCX sample CVs for new styles).

**Claude Code, as a plugin**

```
/plugin marketplace add cris-dangithub/cv-tailor
/plugin install cv-tailor@cv-tailor
```

**Codex and/or Claude Code, from a clone**

```bash
git clone https://github.com/cris-dangithub/cv-tailor
cd cv-tailor
./install.sh            # Windows: .\install.ps1
```

It links `skills/cv-tailor` into `~/.codex/skills` and `~/.claude/skills` and creates the skill
environment. You can also copy `skills/cv-tailor` into a project's `.claude/skills/`.

**Dependencies** live in `skills/cv-tailor/requirements.txt` and are installed into the skill's
own venv (`skills/cv-tailor/.venv`, ignored by git) with pipenv. The skill does it on first use;
by hand it is:

```bash
cd skills/cv-tailor
PIPENV_VENV_IN_PROJECT=1 pipenv install -r requirements.txt     # same on Windows (the .env sets the variable)
```

or simply `python skills/cv-tailor/cvt.py setup-env`.

## First use

Open your agent in an empty folder: that folder becomes your **workspace**. Paste an offer (or
say "set up cv-tailor"). The setup asks, in this order:

1. the language the skill talks to you in (asked in English; everything after is in your language);
2. the languages of your CVs (e.g. English, Spanish, Indonesian);
3. where your knowledge pool is (folders, files, links, `github:<user>`), and it looks for
   skills inside the pool to read it with;
4. optionally, a CV whose look you want to copy.

From then on, in that folder, pasting an offer is enough.

## Your data

- **The pool is yours and stays where it is.** The skill only stores its location and never
  writes to it; only the pool's own managing skill can update it, when its rules allow it, and
  every update can be undone. Turn it off with `pool.writeback: off`.
- **Everything the skill produces lives in your workspace**, never in this repository: config,
  applications, learned facts and preferences, voice profile, your styles.
- One workspace = one person. Another person = another folder.

```
workspace/
  .cv-tailor/config.yaml
  CLAUDE.md, AGENTS.md          # written by the setup: "an offer pasted here = generate"
  profile/voice.md
  learnings/facts.md            # facts you confirmed
  learnings/preferences.md      # rules learned from your feedback
  styles/<name>/
  applications/index.jsonl
  applications/000001-acme-mobility-analytics-engineer/
      offer.md  meta.json  positioning.md  cv.en.yml
      CV-AlexRivera-AcmeMobility-EN.html  .pdf  -review.md
```

## Repository layout

```
.claude-plugin/          plugin + marketplace manifests
skills/cv-tailor/        the skill (this is what agents load)
  SKILL.md               entry point and rules
  references/            step-by-step guides loaded on demand
  scripts/               build, verify, index, workspace, voice, extract, styles, github...
  styles/default/        the default style (Montserrat, OFL)
  templates/workspace/   files the setup writes into a workspace
  cvt.py                 launcher: runs any script with the skill's venv
  requirements.txt
examples/                a fictional candidate, offers, a sample CV YAML and a pool managed by a skill
tests/                   pytest suite
```

## Development

```bash
python skills/cv-tailor/cvt.py setup-env --dev
skills/cv-tailor/.venv/Scripts/python -m pytest tests      # bin/python on macOS/Linux
python skills/cv-tailor/cvt.py build examples/sample-cv.en.yml -o tmp/sample.pdf
```

## License

MIT. The bundled Montserrat fonts are under the SIL Open Font License 1.1.
