# Styles: default, new from a sample CV, switching

- Built-in: `SKILL_DIR/styles/default` (one column, centred name, 3-column contact header,
  Montserrat, A4, 2 pages max). Other built-ins may exist: `cvt workspace styles` lists all.
- User styles: `<ws>/styles/<name>/`, created from a sample CV and approved by the user.
- **The active style is the last one the user chose**: `style.active` in the config. It stays
  until they choose another. An application records the style it was built with (`meta.json`).

## Switching

"Use the X style" / "go back to the default":

```
cvt workspace styles
cvt workspace set style.active=<name>
```

Confirm, and offer to rebuild a recent application with it as a preview (new version, never
overwriting).

## New style from a sample CV

The user shares a CV (PDF preferred; DOCX works if LibreOffice is installed, otherwise ask them
to export it as PDF). Its **content is never used**: only its look. Do not copy text, names or
photos of a sample CV that isn't the candidate's.

### 1. Measure — numbers, not impressions

```
cvt style measure <sample.pdf> --out <ws>/.cv-tailor/cache/style-<name>
```

It writes `measurements.json` (page size, margins from pixels, text catalogue: font, size,
colour, count, example; horizontal rules: colour, width, solid/dashed with dash/gap; frequent
left/right edges; page 1 reading order) and `pages/page-N.png`.

**Look at the PNGs.** Things no tool reports: rules solid in one place and dotted in another,
title case vs uppercase, a sidebar, a two-column block, icons, a photo. Map each catalogue entry
to a role (name, role line, section title, entity, position, dates, body, meta, links).

Traps:
- Sizes from the content stream are usually right for Office/Docs PDFs, but confirm the
  headline on the render: some embedded fonts are mis-measured by text tools.
- Variable fonts don't have exactly the proportions of static cuts: 4–6% differences on the
  headline are normal; adjust the size and **write the adjustment** as a `_note_*`.
- Inconsistencies of the original (one title in title case, dates in two sizes) are the user's
  decision: replicate or normalise. Ask.
- A centred middle column needs equal side columns, derived from the widest content of each.

### 2. Fonts

Find the font family (`fonts` in measurements). If it is free (Google Fonts / OFL), it must be
added to the style's `fonts/` folder with its licence: **ask the user before downloading any
file**, saying the file names and the source. If it is proprietary (Calibri, Helvetica Neue),
propose the closest free equivalent and say so; never bundle a proprietary font.
Download notes: the google/fonts repository serves variable `.ttf` files under `ofl/<family>/`;
`fonts.google.com/download?family=X` returns HTML, not a zip.

### 3. Build the package

```
cvt style scaffold <name> --from default      # copy into <ws>/styles/<name>/
```

Then adapt, keeping the separation:
- `reference.json`: every value measured, with `_origin` and `_note_*` for adjusted ones;
  `_description` (one line, shown in the style list); `page.target_pages`; a `verify` block with
  the rules the style must show (colour, solid/dashed, min count, width), `min_chars`, tolerances.
- `tokens.py`: map tokens to CSS variables; precompute derived values (`calc()` can't divide
  lengths reliably).
- `cv.css`: only `var(--…)`. Exact dashed rules with `repeating-linear-gradient`, not
  `border: dashed`. Bullet glyphs missing in the font → a fallback font only for `::before`.
  Right-aligned dates: flex with `justify-content: space-between`. Keep `break-after: avoid`
  only where it really must not split.
- `cv.html.j2`: structure only. Prefer keeping the default content schema (so existing YAMLs work
  with every style); if the layout needs other fields, document them in `reference.json._schema`.
- ATS risk: a full two-column page or a sidebar is high risk (`references/ats.md`). If the
  sample has it, tell the user before building it, and propose the safer variant.

### 4. Validate with the user (mandatory)

1. Build a **real** CV with it: the most recent application's YAML, or a draft from the pool.
   `cvt build cv.en.yml -o <ws>/.cv-tailor/cache/style-<name>/preview.pdf --style <name>`
2. `cvt verify <preview.pdf> --style <name>` until it passes.
3. `cvt style compare <sample.pdf> <preview.pdf> --out <ws>/.cv-tailor/cache/style-<name>` and
   look at `compare-page-N.png` yourself; fix what differs.
4. Show the user the preview PDF and the comparison image. Ask: approve, or what to change.
5. Iterate. Only on approval: `cvt workspace set style.active=<name>`.

Never activate a style the user has not seen.
