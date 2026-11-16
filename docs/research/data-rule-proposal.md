# The data rule: reasons and record

Status: **accepted by the maintainer on 2026-11-13 and carried out by the stand-in pull request
(#29, merged 2026-11-14); condensed on 2026-11-16.** The rule's text in
[`AGENTS.md`](../../AGENTS.md) ("Rules that must not be broken") is canonical. This page keeps why
it reads as it does and what changed with it. The full proposal, drafted on 2026-10-05 after the
decision of 2026-10-04, is in the Git history.

## The rule

Two bullets replaced the earlier "Synthetic data only" rule:

- **Every case is synthetic.** Customers, assessment cases, transactions, finances and identity
  documents are generated, and none may be a real person or company, carry a real one's name or
  be linked to one.
- **Official reference data only as published.** Entries from official sanctions and country
  lists, and public legal-entity records, may be added unmodified and attributed, once the
  source's reuse terms and personal-data basis are recorded in
  [`docs/DATA-SOURCES.md`](../DATA-SOURCES.md).

## Why two bullets

The first keeps the earlier protection for everything ARGUS assesses. It is also what forced
the stand-ins: three of the original demo profiles gave real companies generated registry
fields, scores and transactions.

The second is a narrow opening with three limits: entries are unmodified and attributed; each
source is checked and recorded before anything is imported; and the first version takes legal
entities only, so list entries for natural persons, PEP data and company officers each need
their own reviewed decision. Raw downloads stay out of the repository, and ARGUS's results about
a real company are published only in aggregate.

## What changed with it (#29)

- The three real-company demo profiles became synthetic stand-ins: Synthetic Payments AG,
  Synthetic Nordic Bank A/S and Synthetic Pacific Banking Corporation. Their facts are invented
  and their tiers are what the live rules give.
- The public adverse-media file, its generator and the demo-only 12-point adverse-media boost
  were removed, and `data/` now holds synthetic generators only.
- `docs/DATA-SOURCES.md` was added as an empty register, on the maintainer's choice.
- `CONTRIBUTING.md`, the README disclaimer and the web UI's footer say the same as the rule. The
  pull request template, the issue template, `SECURITY.md` and the diagrams were left as they
  were, because what they say ("synthetic data only", "never include real personal data") is
  about what contributors paste, and remains true until a source is added.

## Stand-in names

Each name follows the pattern of the existing scenarios (Synthetic Holdings B.V., Cayman Synth
Capital), so the name itself says it is fictional. On 2026-11-13 each was searched in GLEIF, with
the API's exact legal-name filter and its fuzzy completion, with and without the legal form: no
record matches any of the three. The same queries do find a known bank's record, so they work.

## Out of scope, still open

"Explanations keep the facts" stayed as it was. Scoping it to a reviewer record plus a filtered
customer draft is a separate change, to be made before any customer-facing explanation path is
built ("Paper 1" in [`study-data-design.md`](study-data-design.md)).
