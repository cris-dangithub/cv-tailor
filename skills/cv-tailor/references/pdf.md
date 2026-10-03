# The PDF: content YAML → style → HTML → PDF

**Principle: design is measured, not estimated**, and design is separate from content. A style
(`SKILL_DIR/styles/<name>` or `<ws>/styles/<name>`) holds:

```
reference.json   measured tokens: page, sizes, colours, rules, spacing, verify settings
tokens.py        optional: reference.json -> CSS variables (derived values precomputed here)
cv.css           the design, reads only var(--...)
cv.html.j2       the structure, no design values
fonts/           font files + licence
```

A new CV version = a new YAML. **If a version needs the CSS touched, the system is wrong.**

## Commands

```
cvt build   cv.en.yml -o CV-Name-Company-EN.pdf [--style NAME]    # writes the .html next to the .pdf
cvt verify  CV-Name-Company-EN.pdf --yaml cv.en.yml [--check-links]
cvt sync-md cv.en.yml CV-Name-Company-EN-review.md
cvt build --from-html CV-Name-Company-EN.html -o CV-Name-Company-EN.pdf   # re-print a hand-edited HTML
```

`build` uses the workspace's active style unless `--style` is given, copies the style's CSS and
fonts into `<ws>/.cv-tailor/style-cache/` (so old HTML keeps rendering after a skill update),
and prints with any installed Chrome/Edge/Chromium/Brave (Playwright as fallback).

## Content YAML schema (default style)

A value is plain text or a list of chunks: `{text, url}` is a link, `{text, url, cert: true}` a
small credential link. Bold is `<strong>…</strong>`. HTML in values is allowed and not escaped.

```yaml
meta: {lang: en, name: Full Name, role: Target Role, role_plain: Target Role}
header:                     # rows of the 3-column contact block (left / center / right)
  - {left: "City, Country", center: "+00 000", right: [{text: Portfolio, url: "https://..."}]}
sections:
  - {title: SUMMARY, type: prose, body: "..."}
  - title: EXPERIENCE
    type: entries
    entries:
      - entity: Company            # left, bold
        entity_note: "(Remote)"    # right of the entity
        role: Position             # second row, left (optional)
        dates: Jan 2024 – Present  # second row, right (optional)
        lines:                     # rows BELOW the dotted rule: [{left, right}]
          - {left: "...", right: "Level: B2"}
        meta: "Stack · links"      # small fact line
        summary: "..."             # a paragraph
        groups: [{title: "Sub-area", bullets: [...]}]
        bullets: ["...", {text: "...", sub: ["nested"]}]
  - {title: SKILLS, type: columns, left: [{title: ..., bullets: [...]}], right: [...]}
  - {title: LANGUAGES, type: list, bullets: [...]}
```

The template uses StrictUndefined: a misspelt key fails instead of rendering empty. The block
pattern is: title (+ optional subtitle) **above** the dotted rule, everything describing the
entry **below** it. Other styles document their own schema in their `reference.json`
(`_schema`) or reuse this one.

Never reuse an old YAML's facts: a previous YAML is a schema at most, emptied first.

## Fitting the pages

`verify` prints the page fill (`p1=86%, p2=85%`). Loop: render → measure → decide.

1. **Sum the fills. If the total is under 100 × target pages, nothing needs cutting: air is badly
   distributed.** Fix pagination first. The usual culprit is a chain of `break-after: avoid`
   making a whole section unbreakable, or a two-column block that can't split.
2. Still over: cut **by value**, never by squeezing:
   1. entries irrelevant to the offer;
   2. sections whose content fits elsewhere (languages into the header);
   3. fact lines and redundant prefixes (`Company:`, `Stack:`);
   4. long bullets to one line each, without losing a fact.
3. **Never** reduce font size or leading below the style. Tell the user what was cut.
4. A last page under ~25% (`verify` warns) is worse than a full one: fix it.

## What `verify` checks

Pages vs target, page size, extractable text (min from the style), name and every section title
in the extracted text, `[PENDING]` markers left in the PDF, the style font actually used (or no
system fallback), sizes in the style catalogue, text colours in the palette, the three margins
(measured on pixels), the name band visible and inside the page, the style's rules (solid/dashed,
count, width), page fill, links (alive with `--check-links`). Exit 1 on failure.

## Editing an existing version

- **Content** (the user wants a bullet changed): edit `cv.<lang>.yml`, rebuild, verify, sync-md.
  If it is a correction of a fact, also record it in `learnings/facts.md`.
- **One-off visual tweak** of a single PDF: edit the `.html`, `cvt build --from-html`. That HTML
  is then the source of that PDF only; a rebuild from YAML overwrites it (say so).
- **A new version after feedback**: never overwrite. Write `cv.<lang>.v2.yml` → `CV-…-<LANG>-v2.pdf`
  and record it with `cvt index update <id> --version-note "..."` and `cvt index add-file`.
