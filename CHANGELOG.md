# Changelog

## 0.3.0 — 2026-10-26

- **Web app** (`cvt web`). A local browser app over the workspace, as an alternative to the
  chat window.
  - Paste offers: each one gets its own agent session, and several run in parallel.
  - Follow the agent as it streams, answer its questions in place, and approve or deny
    actions outside its allow-list.
  - Keep each application's status on an index or a board.
  - Read an application's route, CVs per language and version, report and offer, and send it
    feedback.
  - Preview, download or ZIP any PDF.
  - Switch styles or build one from a sample CV.
  - The UI is in English, Spanish and Indonesian, light or dark, and works on a phone.
- The app runs Claude Code itself, with the user's own login and no API key. One message is
  one turn:
  - it resumes the session, so idle chats cost nothing;
  - the model is configurable and defaults to `claude-opus-5-5`;
  - effort is high or medium per message;
  - a small auto-compaction window (100k by default) keeps long chats cheap.
- **Sign-in and accounts.**
  - Every visitor signs in, on this computer too, and the session lasts until they sign out.
  - The superuser comes from `CVT_ADMIN_USER` / `CVT_ADMIN_PASSWORD` (environment or
    `.cv-tailor/web/.env`) and approves, disables, resets or deletes accounts.
  - Anyone can create an account: the first is active at once, later ones wait for approval.
  - Passwords are hashed with scrypt, only hashes of session tokens are stored, and repeated
    wrong passwords are slowed down.
- `cvt web --lan` opens the app to the local network. `cvt web --public` accepts any host name,
  for a tunnel such as ngrok.
  - Both refuse to start while the superuser still has the default password.
  - The Origin header is checked on every change.
  - Requests that come through a proxy never count as "this computer".
- Optional dependencies (`requirements-web.txt`) install with `cvt setup-env --web`. The UI ships
  prebuilt in `web/ui/dist`. `cvt doctor` reports the web app and whether the Claude Code CLI
  is present.
- **Parallel sessions no longer collide.** Index writes and id allocation take a workspace
  lock (`.cv-tailor/index.lock`), so two agents creating applications at once get different
  ids.
- New workspaces ignore `.cv-tailor/web/`.

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
