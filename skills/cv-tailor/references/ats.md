# ATS checklist (Applicant Tracking Systems)

Companies filter with software before a human reads the CV. Templates AI tools suggest
(columns, tables, icons, star bars) are invisible to that software and absurd to the human.

## Forbidden
- Icons, emojis, decorative symbols
- Progress bars / skill-level stars
- Charts, timelines, images with text inside
- Contact data in the page header/footer area (many parsers skip it)
- Floating text boxes
- Invented section titles ("My journey", "What drives me")

## Columns and layout tables: a risk, not a ban

"Never use columns or tables" is too absolute and clashes with a common real case: **replicating
a reference CV** made in Google Docs or Word, which uses invisible tables to right-align dates and
sometimes a two-column block.

| Pattern | Risk |
|---|---|
| 2–3 column table only in the contact header | low |
| row with text on the left and date on the right | low |
| one two-column block (e.g. skills) | **medium: verify it** |
| a whole page in two columns | high, always avoid |
| bordered tables presenting data | high, always avoid |

The feared failure is **interleaving**: the parser reads a line from the left column, one from
the right, and returns a salad. It doesn't always happen and **it can be checked**:

```
cvt extract CV.pdf
```

Left column whole and **then** the right → fine. Alternating lines → interleaved: redesign that
section to one column. A stray bullet character between blocks is cosmetic noise.

If the style requires columns, keep them, verify extraction, and **tell the user** a residual
risk remains with weak parsers. Their informed decision. Replicating and staying silent is not OK.

Bold, colour, dividers and link anchors don't affect the ATS.

## Required
- Linear reading order
- Standard section titles (Experience, Education, Skills, Projects, Languages — in the CV language)
- Simple bulleted lists
- Contact in the body, at the top (name, email, phone, city, links as text)
- Consistent date format
- The offer's keywords written as the offer writes them (no keyword stuffing)
- PDF with selectable text (`cvt verify` checks extraction), or .docx if the offer asks for it

## Link text must say where it leads

A link in a CV is read **out of context**: the eye jumps to the blue first.

| Bad | Good |
|---|---|
| `app.example.com` | `Link to the app` |
| `github.com/user/project` | `Link to the repository` |
| `here`, `link`, `more info` | `Link to the demo`, `Link to the article` |

Vary the last word with what is on the other side. A raw URL wastes width and says nothing the
title didn't.

**Certificate links: each one next to what it certifies.** Grouping titles and leaving links in a
row at the end makes them indistinguishable:

```
❌  Programming basics, Java, Spring Boot (9 certificates) (6 certificates) (7 certificates)
✅  Programming basics (9 certificates); Java (6 certificates); Spring Boot (7 certificates)
```

Check by listing anchors alone: `cvt extract CV.pdf --links`. Two different anchors with the same
text leading to different places is wrong.

**YAML eats trailing spaces** in folded blocks (`>-`): a link after a folded block sticks to the
previous text. Put the separator as its own chunk (`- " · "`).

## Links must be alive

`cvt verify CV.pdf --check-links` requests each one. `999` from LinkedIn is its anti-bot, not a
failure (check by hand). Google Drive may answer 200 and still be private ("request access"):
the verifier detects that. A persistent 403/404/500 → out. Links that fail are reported to the
user; never invent a replacement or drop one silently. Every live link of the candidate's
reference CV must still be in the new CV.

## Markdown review file traps

The review file is Markdown; `cvt sync-md` writes its CV part correctly. If you write Markdown by
hand: lines meant to stand alone need a hard break (two trailing spaces); one block = one
physical line (never wrap at 80/90 columns); always a blank line before `---` (otherwise the
line above becomes an H2). `sync-md` reports `merges=0 setext-risk=0` when it is clean.

## Before delivering
- [ ] `cvt verify` passes, with `--check-links`
- [ ] Plain-text read is clean and in order; two-column blocks don't interleave
- [ ] Every anchor says where it leads; no two different anchors share a text
- [ ] Every certificate link sits next to what it certifies
- [ ] No hyperlink of the candidate's reference CV was lost
- [ ] The CV still makes sense with the links removed
