---
name: pool-keeper
description: >
  Reads and maintains Alex Rivera's knowledge base (FICTIONAL example). Use it to answer
  questions about Alex's career, and to add or correct facts in the knowledge base when another
  agent or skill brings new confirmed information.
---

# pool-keeper (example of a pool managed by a skill)

The knowledge base lives in `knowledge/`. Everything here is fictional.

| File | Contents |
|---|---|
| `knowledge/profile.md` | identity, contact, languages, certifications |
| `knowledge/experience.md` | roles and achievements, one fact per bullet |
| `knowledge/projects.md` | projects |
| `knowledge/not-done.md` | **Asked but not done**: things recruiters or tools asked about that Alex has not done |

## Reading
Answer only from these files. Say which file each fact comes from.

## Updating — allowed
Other agents may bring facts confirmed by Alex. Apply them like this:

1. Read the target file first. If the fact is already there (same meaning, even in other words),
   do nothing.
2. **New fact**: add one bullet in the right file and section, followed by
   `(confirmed YYYY-MM-DD, source: <who brought it>)`.
3. **Correction**: replace the old bullet with the new one and keep the old value as
   `(previously: <old>, corrected YYYY-MM-DD)`.
4. **Not done**: only in `knowledge/not-done.md`, one bullet per item, with the date.
5. Keep the existing style of each file. Don't reorganise, don't rewrite other bullets.
6. Never commit; Alex reviews the changes.
7. Return the list of files you changed and what you added or replaced.
