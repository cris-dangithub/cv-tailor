# Positioning: what the CV tells, and why that material

Output: `applications/<id>-…/positioning.md`, written in the UI language. It is the part of the
work the candidate can't rebuild alone, so it is always saved.

## The axis: the decision over the artefact

Producing work got cheap. A CV that only lists what the candidate **produced** is measured
against something that produces fast and cheap. A CV that shows what the candidate **decided,
sustained and answered for** has no such comparison. This holds for any field:

| Weak: the artefact | Strong: the decision and its consequence |
|---|---|
| built a service | migrated it **without a maintenance window**, and how |
| prepared reports | replaced a manual report that **40 managers** now use weekly |
| served customers | handled the **VIP desk alone on night shifts** |
| used Docker | **answers for the server**: secrets, networks, certificates |
| wrote tests | wrote the **CI that blocks the merge** when they fail |
| uses AI to work | works **from specs** and **reviews** what is generated before it ships |

Same fact behind each row; what changes is what is in the foreground: the **constraint**, the
**decision** and what the candidate **answers for**.

**Never say it explicitly.** No "unlike an AI", "irreplaceable" or variants: it ages badly and
sounds defensive. **And still invent nothing**: this axis chooses and frames verified facts.

## Step 1 — Read the offer as a contract

Extract: title and seniority, **years required**, tools/skills (mandatory vs nice to have), what
kind of person they really want (the body lies less than the title), non-skill requirements
(language, time zone, on-site, work permit, shifts), the domain and its constraints.

Rank each requirement **must / important / nice**. That ranking decides the CV order, not intuition.

## Step 2 — Gather evidence, not memories

Evidence is whatever the pool proves: documents, certificates, portfolios, repositories,
previous CVs, `learnings/facts.md`. For code, follow `references/evidence-github.md`. For other
fields, the same discipline: each claim must point to a pool item.

Two biases seen in real use:

- **Anchoring on the old CV.** Reading the previous CV first makes you refill its skeleton. Gather
  evidence **before** opening any previous CV; open it last, only to see what is missing. Sign
  it happened: the new CV features exactly the old CV's projects although the evidence found
  newer and stronger work.
- **Convenience sampling.** Scanning 200 items and opening 15 is a sample, not a review. Say how
  many you opened. What you didn't look at, you don't claim.

## Step 3 — Cross offer against evidence

For each must/important requirement: **strong / partial / none**.

- **Strong** → goes high, with the decision in the foreground.
- **Partial** → goes in if genuinely adjacent, without stretching.
- **None** → **does not go in**. It is reported as a gap, with the honest argument for the
  interview (e.g. no Django, but Flask + ORM + PostgreSQL + React is the same shape: a framework
  jump, not an architecture jump). A declared gap is stronger than a hidden one.

## Step 4 — Choose what goes in

Space is finite. In order:

1. Must-have requirement with strong evidence.
2. Recent professional work where a decision shows, not just a delivery (see Recency).
3. Work under a **real constraint**: production, regulated data, real customers, no downtime.
4. Own projects that are **deployed and operated**. Half-finished ones stay out: they don't
   survive an interview.
5. Education last, unless the offer requires it.

Leave out, even if it hurts: old entries irrelevant to the role, undeployed projects, scaffolding,
anything the candidate can't defend for five minutes. Paid freelance work is professional
experience, not a personal project. When personal projects are many, list them and let the
candidate choose (in the question batch).

**Title.** Chosen from the evidence and the offer, not inherited from the old CV. No seniority
title (Senior, Lead, Staff, Head) without evidence of that scope.

### Recency weighs, but doesn't rule

Recent work proves the candidate is current. But recency is a multiplier, not a filter: what
decides is **how much it adds to this offer**.

| Age | Weight |
|---|---|
| last 12 months | maximum; in unless unrelated to the offer |
| 1–2 years | high |
| 2–4 years | medium; in if it covers a requirement recent work doesn't |
| 4+ years | low; only if it is the only evidence of something essential |

> **Older work that fits the offer better beats recent work that fits it worse.**

Old work goes first when it is the only evidence of a must, has scale or constraints recent work
lacks, or is in the offer's domain. Recent work goes in even if small when the requirement is
being current (fast-moving tools, a daily practice). In the CV it shows without saying it:
recent work takes more lines and goes higher; old work is compressed to a line but **not
deleted** while it still adds.

### Metrics: which ones count

A number counts if it helps the employer **decide**; not if it only describes the size of the
artefact.

| No | Yes |
|---|---|
| 54,000 lines, 300 commits, 40 files | 4,000 → 24,000 quotations/day |
| "large volume of code" | a 1,000-item batch from 5h30 to under 1h |
| "20+ repositories" | 500+ advisers using it |

Every number needs a source in the pool. If its origin is unknown, soften or drop it.

### Learned preferences

Apply `learnings/preferences.md` here (e.g. "always include the open-source contributions",
"never lead with the analyst years") **after** the must-haves are covered. If a preference
conflicts with the offer, the offer wins and the conflict is mentioned in the delivery.

## Step 5 — Write positioning.md

Sections, short, in the UI language:

1. **Offer read**: requirements ranked must / important / nice.
2. **Strong matches** with the evidence behind each (pool file or fact).
3. **Partial matches** and how far they go.
4. **Gaps**, unadorned, each with the honest interview argument.
5. **Left out, and why** — what is most appreciated and almost nobody gives.
6. **Recency calls**: what weighed for being recent, what entered despite being old.
7. **Open questions** for the batch (with the example answer).
8. **To verify before sending**: links, deployments, things only the candidate knows.

No fit scores ("85% match"): they mean nothing and fake precision.

## Limits

- Don't invent experience, numbers, clients or responsibilities.
- Don't attribute to the candidate what merely **is** in a repository or a team document.
- Don't turn "contributed" into "led" without evidence of leading.
- Don't hide a gap: declare it and prepare the answer.
