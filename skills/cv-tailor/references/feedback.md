# Feedback and learning

The user can comment on any generated application: "on 000012 the summary sounds fake", "I
liked how you grouped the skills", "never put my analyst job first". The skill learns from it
so the next CVs are better, without drifting from what each offer asks for.

## 1. Record it in the application

Append to `applications/<id>-…/feedback.md` (create it if missing):

```
## YYYY-MM-DD
- Liked: ...
- Disliked: ...
- Asked to change: ...
(the user's words, short)
```

## 2. Separate facts from preferences

- **A fact correction** ("I was never team lead there", "my English is C1, not B2") → append to
  `learnings/facts.md`. It overrides older pool text from now on. If the pool has a managing skill
  that allows updates, send it there too, with the same filter as the pre-CV answers (corrections
  and new facts always, "not done" only if the pool has a place for it):
  `references/pool-writeback.md`.
- **A preference** (style, emphasis, order, wording) → turn it into a rule in
  `learnings/preferences.md`, in the format of that file:
  - generalise it so it applies to any offer ("summary: no first person, max 3 lines"), but don't
    over-generalise a one-off remark: mark it `soft` unless they said always/never (`firm`);
  - keep the user's words in **Why**;
  - scope it (all, a language, a kind of role).
- If a new rule contradicts an old one, the newer firm one wins; mention it to the user.
- Positive feedback is a rule too ("keep doing X"): it protects what works.

## 3. Apply it

- **Future CVs**: `references/generate.md` reads `preferences.md` before positioning and writing.
  Preferences adjust choices and wording; **the offer's requirements always weigh more**, and a
  preference never introduces a fact the pool doesn't prove. When a preference had to yield to an
  offer, say so in the delivery.
- **This application**: offer to regenerate it as a new version (`v2`), never overwriting the one
  that may already have been sent: `cv.<lang>.v2.yml` → `CV-…-<LANG>-v2.pdf`, then
  `cvt index update <id> --version-note "v2: <what changed>"` and `cvt index add-file`.

## 4. Update the report and tell the user

Update the application's `report.md` (its notes part: what changed in the v2 and why, in plain
words), then run `cvt report <id>`. In the chat, one or two lines: the rule as stored, its scope
and strength, whether a v2 was produced, and what was saved into the knowledge base.
