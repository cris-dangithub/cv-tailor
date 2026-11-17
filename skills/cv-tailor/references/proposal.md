# Implementation proposal (freelance projects, RFPs, gigs)

Some posts are not a job to fill but **a piece of work to deliver**: a freelance project on
Upwork/Workana/Fiverr/Malt, a client brief, an RFP, "we need someone to build/set up/migrate X".
For those the candidate needs an **implementation proposal**: how they would do the work, in
what phases, what the client gets, why they are credible — plus a short message to paste into
the platform. A proposal can also go **with** a CV when the client asks for both.

Same rules as a CV: **nothing invented** (every claim of experience comes from the pool or
`learnings/facts.md`), the candidate's voice (`references/voice.md`), the active style, `cvt
build` + `cvt verify`, never overwrite a previous version.

## 0. What to produce: CV, proposal or both

Decided once per post, **before** `cvt index new`, and stored with `--deliverables`:

1. **An explicit choice wins**: the web app's selector (the first message says "The user chose
   to produce: …"), or the user's words in chat ("solo la propuesta", "CV and proposal", "both").
2. Otherwise **infer it from the post**:
   - a role to fill (employer, position, requirements, salary, "we are hiring") → `cv`;
   - work to deliver (scope, deliverables, budget or hourly range, deadline, "project",
     "freelance", "contract to build…", platform job post, RFP) → `proposal`;
   - a freelance/contract post that also asks for a CV or résumé → `both`.
3. **Say it in one line** in the UI language before starting ("Lo trato como proyecto freelance:
   genero una propuesta. Si también quieres el CV, dímelo.") and go on. Ask only if the post is
   genuinely ambiguous and the choice changes the work; ask it in the same batch as the other
   questions (`references/generate.md` §5).

`cvt index new … --deliverables cv|proposal|both`. To change it later:
`cvt index update <id> --set deliverables=both`.

## 1. Read the post as a brief

From the post (the client's words, verbatim where it matters), write down:

- **The problem and the outcome** the client wants (not the tasks they listed).
- **Scope**: what is in, what is explicitly out, what is unclear.
- **Constraints**: deadline, budget/rate range, tools or stack imposed, time zone, language,
  access the freelancer will need.
- **How they will choose**: questions they ask applicants, screening questions, "start your
  proposal with…", required attachments.

Put this at the top of `positioning.md` (section "Brief"), then the usual evidence crossing
(`references/positioning.md` steps 2–4): which past work, results and skills prove the
candidate can deliver **this**.

## 2. Design the implementation

The plan is the candidate's professional judgement, built from the brief and from how they have
done similar work before (pool evidence). It is not a fact about the past, so it may propose,
but it must stay honest:

- **Phases** (3–6): each with its goal, the main activities, its deliverable, and an **estimated
  duration** (days or weeks). Durations are estimates: write them as such, derived from the
  scope and from similar past work when the pool has it ("a similar SOP set took ~2 weeks
  [pool: …]"). If the client gave a deadline, check the plan fits it and say how.
- **Deliverables**: concrete, checkable things the client receives (documents, configured
  system, trained team, report, code, handover session).
- **What the candidate needs from the client** (access, data, contacts, approvals, feedback
  turnaround) and **assumptions** (what the estimate depends on). Unclear scope → an assumption
  or a question, never a silent guess.
- **Risks** worth naming (1–3) and how the plan handles them — only real ones for this brief.
- **Price**: only when there is a rate — `proposal.rate` in the config (e.g. `{amount: 25,
  currency: USD, unit: hour}`) or a number the user gives for this post. Then compute the total
  from the estimate and show it as an estimate (range if the duration is a range). **No rate →
  no price**: the "Investment" section says the price will be agreed (or is left out), and the
  review file lists it under pending. Never use the client's budget as the candidate's price
  without the candidate saying so.
- Tools the candidate would use must be tools the pool shows they used; a tool the client
  imposes and the candidate never used is a **gap to declare** (or to ask about), not a claim.

## 3. The proposal YAML → PDF

Same schema as the CV (`references/pdf.md`), so every style renders it; only the sections
change. One YAML per language: `proposal.<lang>.yml`.

```yaml
meta:
  lang: en
  doc: proposal
  name: Full Name
  role: "Implementation proposal — <project name in the client's words>"
  role_plain: Implementation proposal
  target_pages: 3            # proposals may be longer than the CV's page target
header:                       # same contact rows as the CV (+ the client and date, if useful)
  - {left: "City, Country", center: "+00 000", right: [{text: Portfolio, url: "https://..."}]}
  - {left: "Prepared for: <Client>", center: "", right: "<Month YYYY>"}
sections:
  - {title: YOUR GOAL, type: prose, body: "<the outcome, in the client's terms, 2–4 sentences>"}
  - title: PROPOSED APPROACH
    type: entries
    entries:
      - entity: "Phase 1 — Discovery"
        entity_note: "Week 1 (estimate)"   # right of the phase title
        bullets: ["<activity>", "<activity>", "Deliverable: <thing>"]
      - entity: "Phase 2 — ..."
        entity_note: "Weeks 2–3 (estimate)"
        bullets: ["..."]
  - {title: DELIVERABLES, type: list, bullets: ["...", "..."]}
  - title: WHY ME
    type: entries
    entries:
      - entity: "<Past organisation / project>"
        role: "<role>"
        dates: "<dates>"
        bullets: ["<result from the pool that proves this brief can be done>"]
  - {title: WHAT I NEED FROM YOU, type: list, bullets: ["..."]}
  - {title: ASSUMPTIONS AND RISKS, type: list, bullets: ["..."]}
  - {title: TIMELINE AND INVESTMENT, type: prose, body: "<total estimate; price only with a rate>"}
  - {title: NEXT STEP, type: prose, body: "<one concrete step: a call, a sample, a start date>"}
```

Section titles are translated per language and may be renamed to the client's vocabulary; keep
the order goal → approach → deliverables → proof → needs/assumptions → timeline/price → next step.
Use only section types the active style supports (`prose`, `entries`, `list` exist in all).

File names: `Proposal-<NameNoSpaces>-<ClientNoSpaces>-<LANG>.pdf` (the `Proposal-` prefix is the
same in every language: the app and the report use it to tell proposals from CVs).

```
cvt build   proposal.<lang>.yml -o Proposal-…-<LANG>.pdf
cvt verify  Proposal-…-<LANG>.pdf --yaml proposal.<lang>.yml --check-links
cvt sync-md proposal.<lang>.yml Proposal-…-<LANG>-review.md
cvt index add-file <id> --lang <lang> --kind proposal-yaml --path proposal.<lang>.yml
cvt index add-file <id> --lang <lang> --kind proposal-pdf  --path Proposal-…-<LANG>.pdf
```

The review file (below the marker, UI language): what was estimated and on what basis, the
assumptions, the price status, the gaps, and the questions the client is likely to ask.

## 4. The message to paste

`Proposal-…-<LANG>-message.md`: the text the candidate pastes in the platform's proposal box or
an e-mail, in the candidate's voice:

- **≤ 1,200 characters** unless the post or platform asks for more; plain text, no Markdown
  formatting that platforms show raw (no `**`, no headings).
- Opens with the client's problem in one sentence (not "Dear Sir/Madam", not "I am excited").
- 2–3 lines of proof (the strongest matching results from the pool, with numbers).
- The plan in one or two sentences (phases + total estimate), price only if there is one.
- Answers every screening question the post asked, in order, labelled as the post labels them.
- Ends with one concrete next step. Mentions the attached PDF if there is one.

`cvt index add-file <id> --lang <lang> --kind proposal-message --path Proposal-…-<LANG>-message.md`

## 5. Report and delivery

The application's `report.md` lists the proposal (and its message) next to the CVs
automatically. In the notes block, "What I decided and why" also says how the plan and the
estimate were built; "Before you send it" lists the price if it is pending and any assumption the
candidate should confirm. In the chat: the PDF, the message file, the one thing to check.

## Limits

- A proposal promises future work; it never upgrades past work. "I will set up X" is fine;
  "I have set up X many times" needs the pool to prove it.
- No fake social proof (no invented client counts, ratings or testimonials).
- No hidden price: if a rate exists and the post asks for a quote, show it.
