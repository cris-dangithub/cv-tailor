# Changelog

## 0.1.0 — 2026-10-03

First public version.

- Setup per folder (workspace): UI language (asked first, in English), CV languages, knowledge
  pool sources (paths, links, GitHub), optional style from a sample CV.
- Generation: n offers × z languages, one numbered application folder per offer
  (`000001-company-role`, auto-widened past 999999), positioning, voice audit, YAML → HTML → PDF.
- Cross-platform PDF engine: any installed Chrome / Edge / Chromium / Brave, Playwright fallback.
- Verifier without system tools (pypdf, pdfplumber, pypdfium2): pages, margins, fonts, sizes,
  palette, rules, page fill, extractable text, links.
- Searchable application index with status tracking.
- Feedback loop: confirmed facts and learned preferences per workspace.
- Voice measurement and comparison per language.
- Style measurement, scaffolding and side-by-side comparison for new styles.
- Own environment with pipenv from `requirements.txt` (`cvt.py setup-env`).
