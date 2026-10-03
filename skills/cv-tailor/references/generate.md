# Generate: offers → applications → CVs

Triggered by any pasted or linked job offer. The user does not need to say "generate".

## 1. Split the input into offers

- Different links = different offers. Different companies or roles in the text = different
  offers. One offer pasted with its link = one offer.
- If the split is genuinely ambiguous (two roles at the same company in one post), ask once.
- Languages: `cv_languages` from the config, unless the user restricted this request
  ("only English"). The offer's own language does not change the set, but if the offer is in a
  language that is **not** configured, mention it and offer to add it for this offer.
- Result: n offers × z languages CVs.

## 2. Get the offer text, open the application

For each offer:

1. Link → `cvt fetch-offer <url> --out <tmp>/offer.md`. Exit 2 (`FETCH_FAILED`: login wall,
   JavaScript-only page, LinkedIn without the guest view) → ask the user to paste the text.
   Text → save it as is. Never generate from a title alone.
2. Read the offer and get company, role and location.
3. `cvt index new --company "<Company>" --role "<Role>" --location "<Location>" --url "<url>" \
   --offer-file <offer.md> [--languages en]` → prints `{"id": "000012", "dir": "..."}`.
   The folder `applications/000012-company-role/` now has `offer.md` and `meta.json`.

## 3. Read the pool (once per run, shared by all offers)

Follow `references/pool-sources.md`. Inputs, in this order of authority:

1. `learnings/facts.md` — facts the candidate confirmed (they win over older pool text).
2. The pool sources in the config (through the pool's skills when it has them).
3. `profile/voice.md` — how the candidate writes (not facts).
4. `learnings/preferences.md` — how the candidate likes CVs (not facts).

With several offers on Claude Code, one reader subagent produces an evidence digest that all
offers share; don't re-read the pool per offer.

## 4. Position each offer → `positioning.md`

Follow `references/positioning.md`. With several offers on Claude Code, run one subagent per
offer with the digest, the offer and the positioning reference; each returns its decision and
its open questions. On other agents, do them one after another.

## 5. One batch of questions for all offers

Merge the open questions of every offer, remove duplicates and anything already answered in
`facts.md`, and ask **once**: max ~7 questions, concrete, each with an example answer and the
application id(s) it affects. Typical: a level of a language, a date, whether a freelance job
was paid, whether a technology was used in production, which personal projects to include.

- Save each factual answer to `learnings/facts.md` (format in that file).
- If the user does not answer something, continue with what is verified and keep it as
  `[PENDING: ...]` in the review file. Don't block all offers on one missing detail.

## 6. Write each CV, per language

Follow `references/voice.md` (voice, filters, numeric targets) and `references/cv-writing.md`.

- One YAML per language: `applications/<id>-…/cv.<lang>.yml`, schema in `references/pdf.md`.
  Same facts and structure in every language; section titles and conventions translated
  (per-language rules in `references/voice.md`).
- Check the draft against the voice: `cvt voice compare --profile profile/voice.<lang>.json
  --yaml cv.<lang>.yml` when a profile exists for that language. Fix until it passes or say why not.
- File names: `CV-<NameNoSpaces>-<CompanyNoSpaces>-<LANG>.pdf` (e.g. `CV-AlexRivera-AcmeMobility-EN.pdf`).

## 7. Build, verify, review file

For each `cv.<lang>.yml`:

```
cvt build   cv.<lang>.yml -o CV-…-<LANG>.pdf
cvt verify  CV-…-<LANG>.pdf --yaml cv.<lang>.yml --check-links
cvt sync-md cv.<lang>.yml CV-…-<LANG>-review.md
```

- Over the page target → `references/pdf.md` "Fitting the pages" (fix pagination first, then
  cut by value, never shrink type) and rebuild.
- Then write the review part of `CV-…-<LANG>-review.md` below the marker, in the UI language:
  audit report, pending verification, interview defence (`references/voice.md` step 6).
- Register the files and a short summary for search:

```
cvt index add-file <id> --lang en --kind yaml --path cv.en.yml
cvt index add-file <id> --lang en --kind pdf  --path CV-…-EN.pdf
cvt index update <id> --summary "<2 lines: angle taken, main evidence>" --keywords "<8-15 terms from the offer and the CV>"
```

## 8. Deliver

In the UI language, short, per application:

- id, company, role, and the PDF path of each language (links the user can click);
- strong matches, partial ones, gaps (with the honest argument), what was left out and why;
- what weighed for being recent and what entered despite being old;
- anything still `[PENDING]` and links that need a manual check;
- verification result (pages, checks).

Don't paste the CV in the chat; it is in the files. Remind once that feedback is welcome
("tell me what you didn't like about 000012") and that the status can be updated when they send it.
