# Roadmap: a plain-language explanation for the person screened

**Status:** deferred, and the original design is withdrawn. Revised 2026-11-11.
**Goal:** a second version of the explanation that the person being screened, or a caseworker
helping them, can read.

## What exists today

- The analyst explanation is wired in: `explain_decision()` in
  `src/argus/agents/compliance/tools/explain_decision.py`.
- A customer-facing variant, `explain_decision_plain_language()`, is in the same file. It has
  tests, but nothing calls it: no API field, no UI toggle.

## Why the original design is withdrawn

The first version of this page proposed sending that variant's output to customers. Its prompt
and fallback do things ARGUS's own rules do not allow:

- It tells the model not to quote the findings and passes only the first two, so the text cannot
  be checked against what was found.
- It never says that a person still decides.
- Its fallback promises contact "within 5 business days", which nothing in ARGUS supports.
- It reassures the reader ("it doesn't mean we've found anything wrong") whatever the findings
  are.
- It takes no account of what may lawfully be said. Anti-money-laundering law limits what a
  customer may be told about an examination or a report.

## What has to come first

1. The matched explanation study in [`../ARGUS-V2-PLAN.md`](../ARGUS-V2-PLAN.md), which builds
   the measures for whether an explanation preserves findings, evidence, uncertainty and
   review status. Its follow-up question is whether wording can be made simpler without losing
   them.
2. A design for what may be disclosed, reviewed by a legal expert and a practitioner. The
   working draft is "Paper 1" in
   [`../research/study-data-design.md`](../research/study-data-design.md): code removes facts
   that must be withheld before any model call, each sentence cites the facts it rests on, and
   a person approves every letter. Nothing is sent automatically.

Translations, a UI toggle and readability targets depend on both, and are not scheduled.
