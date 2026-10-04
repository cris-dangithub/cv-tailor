# Pool write-back: the pool learns from the candidate's answers

The answers to the questions asked before a CV, and the fact corrections given as feedback, are
often knowledge the pool did not have. When the pool is **managed by a skill whose rules allow
updates**, cv-tailor hands those facts to that skill, which decides how to store them without
duplicating anything.

**cv-tailor never writes into the pool itself.** It only: classifies, sends, photographs the pool
before and after, reports, and can undo. Pools without a managing skill, `url` and `github`
sources stay read-only.

Automatic: no confirmation is asked. The candidate sees what was saved in the application
report and can ask to undo it or correct it. `pool.writeback: off` in the config disables it.

## 1. The manager probe (once, and when the pool's skills change)

Needed when `cvt workspace scan-pool --save` reports `manager_probe: needed` or `outdated`. Read
the pool's skills (`pool.skills` in the config) and its `AGENTS.md`/`CLAUDE.md` (on Claude Code,
in a subagent) with this brief:

> Read these skills and instruction files of a knowledge pool: <paths>. Do not change anything.
> Answer in JSON only: `{"source": <pool source index>, "skill": "<name of the skill that manages
> the knowledge>", "can_update": true|false, "how": "<one paragraph: where facts go, format,
> how corrections are made, files involved>", "has_not_done_section": true|false,
> "not_done_location": "<file/section or null>", "commits": true|false, "reason": "<why>"}`.
> `can_update` is true only if the rules allow other agents or tools to add or correct facts.
> `has_not_done_section` is true only if there is an explicit place for things the person was
> asked about and has not done (gaps, "not done", "asked but not done").

Store it: `cvt workspace set-manager --json '<the JSON>'`. If several sources can be updated, ask
the candidate once which one receives updates: `cvt workspace set pool.writeback_source=<index>`.

## 2. Classify each answer

| Kind | Example | Sent to the pool? |
|---|---|---|
| **positive**: a new fact about the candidate | "I gave a talk at PyData 2025", "the batch went from 5h to 40 min" | **yes** |
| **correction**: contradicts the pool | pool says English B2, the answer is C1 | **yes**, marked as a correction |
| **negative**: something not done | "I've never used Kafka in production" | **only if** `manager.has_not_done_section` |
| application decision | "apply anyway", "don't mention X to this company" | never |
| CV preference | "no first person", "skills before projects" | never (→ `learnings/preferences.md`) |
| unanswered / pending / trivial | "skip", "yes go ahead" | never |

All of them are still written to `learnings/facts.md` (decisions and preferences where they
belong), each with its pool status line (format in that file).

## 3. The packet

Write it to the run folder as `packet.md` (step 4 gives the folder):

```
Facts confirmed by <candidate name> on <date>, while preparing application <id> (<company> — <role>).
Source: cv-tailor (answers to clarifying questions | feedback correction).

NEW
- <fact, in plain words, with any number and its origin>

CORRECTIONS
- <topic>: before "<what the pool says>", now "<confirmed value>"

NOT DONE            (only when the pool has a place for it)
- <thing asked about and not done>
```

## 4. Run it

1. `cvt pool-writeback snapshot --app <id>` → `{"run": "...", "dir": "...", "pool": "..."}`.
   Exit 4 (`WRITEBACK_UNAVAILABLE`) → don't write; note the reason in `facts.md`.
2. Launch the writer (Claude Code: a **background subagent**, in parallel with the CV build;
   Codex: inline, following the pool skill's `SKILL.md`):

   > You maintain a knowledge pool with its own skill `<skill>` at `<path>`; follow its rules.
   > Apply this packet: <packet.md>. For each item: read where it would go; if the pool already
   > says it (even in other words) do nothing; otherwise add it, or for a correction replace the
   > old value as the skill's rules say. Not-done items go only to <not_done_location>. Keep the
   > existing style, don't reorganise or rewrite anything else, don't delete files. Don't commit
   > or push unless the skill's rules require a commit (never push). Return: per item, written /
   > already known / rejected (with the reason), and the files you changed.

3. `cvt pool-writeback finish <run> --summary "<plain words>" --not-sent "<plain words>"`.
   Both texts go to the candidate's report, in the UI language, about **what** and **why**, never
   how: *"Your English level is now C1 and I added your PyData 2025 talk."* /
   *"What you haven't done wasn't saved: your knowledge base has no place for it."*
4. Update each entry of `facts.md`: `pool: written <run>` / `already known` /
   `not sent (negative, no section)` / `rejected by manager (<reason>)`.

## 5. Undo or correct

The candidate says "undo the knowledge base changes of 000012" or "that's wrong, it was …":

- `cvt pool-writeback list --app <id>` → the runs. `cvt pool-writeback diff <run>` → what changed
  (for you; summarise it in plain words for the candidate).
- Undo all: `cvt pool-writeback rollback <run>`. Some files: `--files <rel> ...`.
  Files changed again after the write-back are refused, so later edits are never lost; only with
  the candidate's explicit OK use `--force`. Binary files have no backup copy and are reported.
- Correct: a new run (steps 3–4) whose packet holds the correction.
- Mark the affected `facts.md` entries `pool: rolled back <run>`. The application report
  refreshes itself.

## Limits

- Never send private repository names, internal identifiers or anything the candidate asked to
  keep out.
- If the pool has more than 100 MB of text files, there is no write-back (the safety copy would be
  too big): say so once.
