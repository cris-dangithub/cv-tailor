# Applications: numbering, index, search, status

## Numbering

Every offer gets the next number, zero-padded: `000001`, `000002`… in
`applications/<id>-<company>-<role>/`. `cvt index new` assigns it; never create folders by hand.
When the next number no longer fits (after `999999`), `index new` first renames **every** folder
and `meta.json` to one more digit (`0000001…`), then creates the new one. To force it:
`cvt index renumber --width 7`.

`meta.json` in each folder is the source of truth; `applications/index.jsonl` is a cache.
If they ever disagree: `cvt index rebuild`.

## Commands

```
cvt index list [--status sent] [--limit 20]
cvt index show <id>                       # meta + files present
cvt index path <id>
cvt index search "<free text>" [--top 5] [--status ...] [--since YYYY-MM-DD] [--json]
cvt index status <id> <generated|sent|replied|interview|rejected|offer|withdrawn> [--note "..."]
cvt index update <id> --summary "..." --keywords "a,b" --set location=Remote --version-note "v2: ..."
cvt index add-file <id> --lang en --kind pdf|yaml|html|review --path <file>
```

## Search: "they replied and I don't remember what I sent"

The user gives anything: a recruiter email, a company name, a role, a city, a date, a link, a
half-remembered detail.

1. Run `cvt index search "<their text>" --top 5 --json`. It scores company (also inside a
   sentence, and fuzzy for misspellings), role, keywords, URL, location, summary and the saved
   offer text, weighting rare words above common ones.
2. **Judge the candidates yourself**: read the top results' `offer.md` / `positioning.md` against
   the user's text (dates, recruiter name, city, salary, technologies mentioned). Rank them and
   say why. If the user's text names something not in any application, say so: maybe it was never
   generated here.
3. If nothing scores: try again with the distinctive words only (company, product, city), with
   `--since` around the date they remember, or list the recent ones with `cvt index list`.
4. Show the best match(es), per language: the PDF path (clickable), the date, the angle taken
   (from `summary` / `positioning.md`), the CV headline and 3–4 key bullets, the status history,
   and pending items it had. That is what they need before answering the recruiter.
5. Ask whether to update the status (e.g. `replied` or `interview`) and record it with a note
   ("recruiter email, 2026-10-20"). Offer to prepare for the interview with the review file's
   "Interview defence" section.

## Status

`generated` (default after creating) → `sent` → `replied` → `interview` → `offer` / `rejected`
(`withdrawn` if the candidate drops it). Statuses are free to jump; each change is appended to
`status_history` with date and note. When the user says "I sent it", mark `sent`.
