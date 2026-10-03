# Red flags of an AI-written CV

## 1. Empty adjectives → verb + fact

Models trained on millions of CVs produce the most generic CV possible: the one that, trying
to please everyone, impresses no one.

| Typical AI cliché | Rewrite with proof |
|---|---|
| Proactive, results-oriented professional | (delete: nothing to evaluate) |
| Excellent communication and teamwork skills | Mentored 2 juniors for 6 months: onboarding and code review |
| Passionate about new challenges | (delete) |
| Proven track record of delivering on time and on budget | Led 4 projects (€120k) with 90% on-time delivery |
| Improved team efficiency | Automated the monthly reports: 10 h/month saved |
| Strong leadership | Coordinated 3 people in the migration from X to Y |
| Advanced command of multiple technologies | Node.js and React in production; Python at a basic level |

**Rule:** less spectacular but real wins. Every line must be something a recruiter can evaluate.

Words to hunt (any language): proactive, dynamic, passionate, results-oriented, synergy, proven
track record, highly motivated, excellent communicator, team player, rockstar, ninja, guru,
expert, revolutionised, versatile, committed, growth mindset, extensive experience, solid
knowledge / proactivo, dinámico, apasionado, orientado a resultados, sinergia, altamente
motivado, resolutivo, amplia experiencia, sólidos conocimientos.

Literary mould: what drives me, I discovered that, and I like it that way, I'm passionate about,
I learned that, the kind of work that / lo que me mueve, descubrí que, me apasiona.

## 2. Unproven claim

Quick test per line: a past-tense action verb? a concrete object (which system, process, team)?
a measurable result or at least a scope (%, hours, money, users, people)? Missing two of three →
rewrite or delete.

## 3. Skill hallucination

The model doesn't know the truth: it fills gaps with the statistically probable. You write
"frontend" and it adds Angular, Vue and NestJS because "a frontend usually has them". The
candidate only used React. In the interview they get asked about their hardest Angular project:
not only the job is lost, credibility is.

Auditor mindset: if they didn't do it, it's not in the CV. Each technology: production, own
project, course, or never. Each number: where does it come from. Each responsibility: theirs or
the team's. "Basic Python" that is true beats "Python expert" that is false.

### Special case: dependency ≠ experience

With repository access, the temptation is to copy `package.json` / `requirements.txt` into
Skills. Same hallucination with a source that *looks* like evidence: a declared library says
nothing about who used it.

But the right question is **not** "are there files named like the library that they touched?".
That shortcut gives false negatives: nobody names the file `kendo.jsx` where Kendo is imported.

> Does any file **they** modified **import** that library?

The three-step check (commits → files touched → **content** of those files) is in
`references/evidence-github.md`. Do it in **every** repository where the library is declared,
not the first one. Only if it gives 0 everywhere does the library leave the CV.

Infrastructure follows the same principle, but there the path **is** the artefact: a deployment
workflow the candidate never committed to is not theirs.

The check cuts both ways: a tool that looked like padding can turn out real (20 commits on the
test suite of another repo), and one "obviously" unused can be in their imports.

Safe format for skills, by declared level:
- **In production:** X, Y
- **Own projects:** Z
- **Learning:** W

## 4. Fake voice — and its twin trap, storytelling

A grammatically perfect, perfectly structured CV smells of AI from afar. The obvious fix — "give
it voice, tell a story" — produces **the other AI CV**: reflective, literary, with a colon
introducing a general idea and pretty triads.

| AI mould 1: corporate | AI mould 2: literary |
|---|---|
| Tech professional with 10+ years of experience, looking to contribute to the company's success. | After a decade building software, I discovered that what drives me isn't just code, but being part of how the product grows. |
| Empty, evaluates to zero. | Reads like an essay. No engineer writes their own CV like that. |

Signs of the literary mould: a colon introducing a generalisation instead of a concrete list;
rhythmic triads ("pipelines that can't X, logs that can't Y, migrations that Z"); dash asides
that add a reflection, not a fact; sentences about what the candidate *likes*, *is driven by* or
*prefers*; insistent first person when the rest of the document has none.

**"Voice" doesn't mean literary. It means THAT person's register**, measured from what they wrote.

A real example. A candidate whose CV had **0 first person in 61 bullets**, all opening with a
past-tense verb, median 15 words, got this rewritten summary:

> Most of my work is the unglamorous kind and I like it that way: batch pipelines that can't
> lose a record, audit logs that can't be rewritten, migrations that run with the old path
> still alive.

They rejected it on sight: "it looks VERY AI". In their real register the same information is:

> Built batch pipelines with no-record-loss guarantees, an immutable audit log and migrations
> with no maintenance window.

Same content. One is an essay, the other is their CV. The test is not "would you say it in a
conversation?" — a CV isn't one — but **"would THIS person write it LIKE THIS?"**.

## 4b. Grammar traps when compressing

Compressing **is not** removing function words. It is **removing the explanation and keeping the
fact**. A finite verb is never surplus; the colon, the aside and the "because" are.

- **Zero first person is measured per language** (see `references/voice.md`).
- **No fragment without a finite verb.** Spanish *Construidos servicios en Python* is a broken
  sentence; *He construido servicios en Python* is not.
- **One bullet, one action.** Three facts stitched with "and" double the length: split them.
  It costs one bullet and usually pays off.
- **Active voice.** *Build and operate…* rather than *Hired to build…*: the participle makes the
  candidate the object.

## 4c. Vanity metrics

A number that measures **volume produced** says nothing about who produced it: lines of code,
commits, files, hours. Generating volume is cheap today; the number invites exactly the wrong
comparison. Replace it with **what the system does and under which constraint**. Numbers do count
when they measure an outcome: throughput, time saved, users served, errors avoided.

## 5. Similarity between candidates

When five candidates for the same role use the same sentence, that sentence is worth zero. The
only thing that can't be cloned is the concrete story: what problem there was, what they did,
what came out of it.
