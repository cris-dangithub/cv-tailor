# The knowledge pool

The pool is everything the candidate pointed to during setup: folders (with subfolders), single
files, links, GitHub. **It is external and read-only**: the skill never creates, hosts, edits or
reorganises it. Only its location is stored, in `pool.sources` of the config.

Facts the pool lacks are asked to the candidate and stored in `learnings/facts.md`, which is
read as part of the pool from then on (and wins over older pool text).

## Source types

| Type | How to read it |
|---|---|
| `path` (folder) | the pool's own skills if any (below); otherwise its `AGENTS.md`/`CLAUDE.md` for orientation, then the documents: `cvt extract <file>` for PDF/DOCX/ODT/HTML, direct reading for text |
| `path` (file) | `cvt extract <file>`; `--links` to keep its hyperlinks |
| `url` | fetch it (WebFetch, or `cvt fetch-offer <url>` works for plain pages too); a page behind a login can't be read: ask for an export |
| `github` | `cvt github sync` / `status`, then live checks (`references/evidence-github.md`) |

## Pool skills come first

`cvt workspace scan-pool --save` records the skills found inside path sources (`pool.skills`:
name, path, description). When they exist, the pool is read **through them**, by an agent, not by
manual searching:

- **Claude Code**: launch one subagent (a general-purpose agent) with the brief below, telling it
  which pool skills exist and their paths, and to use them. It returns the digest; you never load
  the raw pool into your own context.
- **Codex / no subagents**: open each pool skill's `SKILL.md`, follow it to answer the brief, and
  write the digest yourself.

Re-scan when the user says the pool changed (`scan-pool --save`).

## The reader brief (the subagent's prompt, adapted)

> You read a candidate's knowledge pool and return evidence, not prose. The pool is READ-ONLY:
> never modify anything in it. Sources: <list>. Pool skills to use: <names + paths>. Also read
> `<ws>/learnings/facts.md` (confirmed facts, they win over older pool text).
> Offers (requirements only): <list of must/important requirements per offer, or "general">.
> Return, as a structured list:
> 1. Identity and contact as stated in the pool (name, location, email, phone, links, languages
>    with levels and their proof).
> 2. Every role: organisation, title, dates, location/mode, and each achievement or
>    responsibility as a separate item with its **source file** and any number with its origin.
> 3. Projects: what, the candidate's role, status (deployed/operated/unfinished), links.
> 4. Education and certificates, each credential link next to what it proves.
> 5. Skills with the **level the evidence supports** (production / own project / course).
> 6. For each offer requirement: strong / partial / none, with the items that support it.
> 7. Contradictions between sources, and things that look relevant but can't be verified.
> 8. Writing samples by the candidate (paths), if any.
> Mark anything inferred as inferred. Say how many files you opened out of how many exist.
> Do not quote private repository names or internal identifiers as CV material.

## Digest reuse

For several offers in one run, one digest serves all. Keep it in
`<ws>/.cv-tailor/cache/pool-digest.md` with its date; reuse it in the same day's runs unless the
pool changed, and always re-check the specific facts you put in a CV.
