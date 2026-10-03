# Writing the CV content

## Sections and sizes

Section titles in the CV language and standard (Summary, Experience, Projects, Skills,
Education, Languages). Order follows the positioning, usually:

| Section | Guidance |
|---|---|
| Summary | 2–4 lines in the measured register: what they do, since when, with what, on which systems. No narrative, no adjectives, no personality statements |
| Experience | current role 5–8 bullets, older roles 2–4, very old ones 1 line or merged; most defensible first |
| Projects | 2–4 bullets each; only deployed/operated or verifiable ones; a fact line (stack · link) |
| Skills | grouped by category and by real level (production / own projects / learning); never a giant keyword list |
| Education | short; credentials linked next to what they prove |
| Languages | real, verifiable levels (in the header if space is tight) |

Length: 1 page with under ~5 years of experience, 2 max, unless the active style or the user
says otherwise (`page.target_pages`).

## Bold inside bullets

A recruiter doesn't read the CV: they scan it. Bold is what lets them jump from bullet to bullet.

**One or two per bullet. Never three.** If everything is bold, nothing stands out.

What deserves bold, in order:

1. **The technology or skill the offer asks for.**
2. **The constraint or the result**: `no maintenance window`, `atomic and fail-closed`,
   `24,000 automated quotations`. That separates a delivery from a decision.
3. **The responsibility**, when the bullet is about it: `answers for the deployment and the server`.

Not: lone verbs, connectors, company names, whole sentences, the whole bullet. If the bold piece
is longer than half a line, it isn't emphasis.

```
❌  Built the audit service on DynamoDB with idempotent writes...          (no anchor)
❌  <strong>Built the audit service on DynamoDB with idempotent writes</strong>  (all bold)
✅  Built the platform's <strong>audit service</strong> on DynamoDB with idempotent writes,
    covered by <strong>pytest on every pull request</strong>.
```

Check: **read only the bold, top to bottom.** If that already tells the career, it's right. If it
is a list of loose technologies with no verb or result, you highlighted the artefact, not the decision.

## Writing rules
- Action verbs (in the language's CV convention, see `references/voice.md`).
- No self-praise adjectives, no unconfirmed skills, no unconfirmed numbers.
- No essay register: colon + generalisation, rhythmic triads, reflective dash asides, likes and preferences.
- Every unconfirmed item is `[PENDING: confirm X]` in the review, never invented; the PDF sent
  to a company must not contain it (`cvt verify` warns).
- Dates in one consistent format per CV.
- Paid freelance work is professional experience.
- Private repository names, internal ticket ids, client names under NDA: never.
