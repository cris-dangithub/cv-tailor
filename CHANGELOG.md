# Changelog

## 0.2.0 — 2026-10-04

- **The knowledge pool learns from your answers.** When the pool is managed by a skill whose
  rules allow updates, the facts you confirm before a CV (and fact corrections given as
  feedback) are handed to that skill automatically: new facts and corrections always, things
  you haven't done only if the pool has a place for them. cv-tailor never writes into the pool
  itself.
- Every pool update is photographed before and after, and can be undone (all or per file);
  files edited again later are never overwritten. `pool.writeback: off` disables it.
- Manager probe stored in the config (`workspace set-manager`), re-requested when the pool's
  skills change.
- **Application report** (`report.md`) in every application, written for the person applying:
  status, CVs, what was decided and why, questions and answers, knowledge-base updates, history.
  Refreshed automatically on every change.
- `verify` writes a small summary next to each PDF, used by the report.
- New example: a fictional pool managed by a skill (`examples/sample-managed-pool`).

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
