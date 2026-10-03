# Voice: how the CV sounds

A CV written 100% by AI is discarded in seconds: cloned language, unproven claims, skills the
candidate can't defend, and layout the ATS can't read. This reference makes the CV sound like
**this** candidate, and keeps it honest.

**Principle: the candidate is the architect, the AI is the builder.** You structure and detect
problems; the candidate supplies the raw material. Never write a fact they did not give.

---

## Building the voice profile (setup, or when the pool changes)

The voice is **measured**, never guessed from how the user chats and never invented.

Sources, in priority order — use the first that exists, and combine 2 and 3 if both exist:

1. **An explicit style guide in the pool**: a document about how they write, or a writing-style
   skill (e.g. one produced by a "my writing style" setup). Read it; its rules win.
2. **Texts the candidate wrote, in the pool**: CVs, cover letters, LinkedIn "about", posts.
   `cvt workspace scan-pool` lists likely samples (`writing_samples`).
3. **Samples pasted by the candidate** (ask for 1–3 if 1 and 2 don't exist), saved to
   `profile/samples/<name>.md`.
4. **None**: CVs will be factual and neutral, and every review says the voice could not be measured.

Measure each language separately (a CV in English tells nothing about Spanish register):

```
cvt voice measure <sample files...> --lang en --save profile/voice.en.json
cvt extract <sample.pdf> --links          # hyperlinks of a sample CV: they must survive into new CVs
```

Then write `profile/voice.md` (in the UI language) with, per language: sources used; unit
(bullets or sentences); person (0 first person = no "I"); typical openers (past-tense verb,
noun, gerund); median and max length; whether the stack is named explicitly; punctuation
(final periods, colons, dashes); bold usage; anything from a style guide. Note the languages
with no sample.

## Step 0 — Inventory, every application

Before asking anything, list what is already known (offer, pool facts, `facts.md`, numbers,
roles, links, voice). Only what is missing **and** blocks goes to the question batch.

## Step 1 — Six filters

Apply them to every line you are about to write (details: `references/red-flags.md` for 1–4,
`references/ats.md` for 5, `references/interview-defense.md` for 6). Log each finding as
`section | original | problem | filter | change` for the audit report.

1. **Clichés and empty adjectives** → action verb + measurable fact.
2. **Unproven claims** → every line must be evaluable.
3. **Skill hallucination** → technologies added by pattern; each one must be in the pool.
4. **Fake voice** → both the corporate mould and the **literary** mould (colon introducing a
   generalisation, rhythmic triads, reflective asides). Test: *would THIS person write it like
   this?*, against their sample in the language you are writing.
5. **ATS-hostile format**.
6. **Interview defence** → every line must survive five minutes of questions.

## Step 2 — Confirm facts

Doubtful skills (production / own project / course / never), numbers (real / estimated /
unknown) and responsibilities (theirs / the team's) go to the question batch. Before dropping a
technology for "no evidence", do the import check (`references/red-flags.md`, "dependency ≠
experience"): deleting something real costs as much as inventing something false.

## Step 3 — Write, inside the measured register

- Summary in the measured register: if their CV has no first person, the summary has none.
  Data density, not narrative; 3–4 lines max; no personality statements.
- Each bullet: **verb + what + with what + result or scope**. **One bullet, one action**: a
  conjunction that fuses two or three actions doubles the length; split it.
- **Every bullet has a finite verb.** Compressing means removing the explanation, not the verb.
- **Keep every fact** when adapting to the voice: following the pattern is not losing information.
- Bold: 1–2 anchors per bullet (`references/cv-writing.md`).
- Apply `learnings/preferences.md` (wording rules).

**Numeric targets** — check with `cvt voice compare` and show the table in the review:

| Metric | Target |
|---|---|
| median bullet length | within ±25% of theirs |
| max length | not above their max |
| colons opening an enumeration | 0 |
| em-dash asides | 0 |
| causal clauses (because, so, while / porque, así que / karena) | 0 |
| bullets without a finite verb | 0 |
| volume metrics (lines, commits, files) | 0 |
| bold spans per bullet | 1 or 2, never 0 or 3+ |

If they don't match, you wrote your CV, not theirs. Show the numbers, not your opinion.

### Per-language conventions

The zero of first person is measured **per language**. English drops the subject by convention
(`Developed…` is `[I] developed…`); transplanting that zero to other languages breaks them.

| Language | Bullet convention |
|---|---|
| English | past tense, no subject: *Built…, Migrated…*; present for the current role is fine |
| Spanish | first person past: *Desarrollé, Diseñé*; or present perfect *He construido*; or nominal *Desarrollo de…* — never a bare participle (*Construidos servicios…*) |
| Portuguese | *Desenvolvi, Implementei*; or nominal |
| French | nominal or past participle with an implicit subject is common: *Conception de…*, *Développé…* |
| German | nominal style is common: *Aufbau von…*, *Entwicklung…* |
| Indonesian | active meN- verbs without *saya*: *Membangun, Mengembangkan, Mengelola* |
| other | follow that language's CV convention, keeping a serious register |

Measure on a sample in the target language when there is one; otherwise apply its convention
and say in the review that the register was not measured for it.

## Step 4 — ATS and render tests

`cvt verify` checks extraction, name, section titles, links. Also read the plain text once
(`cvt extract CV.pdf`): it must read clean and in order. For a two-column block, the left column
must come out whole before the right one (`references/ats.md`).

## Step 5 — One version per offer

Extract the offer's key requirements; for each, the real achievement that fits. What doesn't
fit is cut; what doesn't exist is **not invented** — it is a gap to state honestly.

## Step 6 — The review file

`CV-…-<LANG>-review.md`: the CV part is written by `cvt sync-md` from the YAML. Below the
`<!-- END OF CV` marker, write in the UI language:

1. **Audit report** — findings table (filter, original → change, reason) and the voice
   comparison table.
2. **Pending verification** — every `[PENDING: ...]`.
3. **Interview defence** — 3–5 likely questions with the CV line that triggers each.

## Limits

- Never invent experience, numbers, companies, dates or degrees.
- Never fill a gap with the statistically probable: mark it pending.
- Never promise the CV "passes the filter": a CV only gets the interview.
