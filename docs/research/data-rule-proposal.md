# Proposal: the data rule and the stand-in migration

Status: **accepted by the maintainer on 2026-11-13, not yet in force.** Drafted 2026-10-05,
following the decision of 2026-10-04 to replace the real-company demo profiles with synthetic
stand-ins and to reword the data rule. On 2026-11-13 the maintainer accepted the two-bullet
wording as written, the empty `docs/DATA-SOURCES.md` register, and the three stand-in names
(section 5). The rule in [`AGENTS.md`](../../AGENTS.md) governs until the stand-in branch that
carries this text is merged. The text lands on its own branch together with the stand-in
migration; the inventory of files to change is in
[`study-data-design.md`](study-data-design.md) ("Demo migration is part of that rule-change
branch"). Section 5 lists the three questions still open.

Out of scope for this branch (said so on purpose): the "Explanations keep the facts" rule
stays as it is. Scoping it to a reviewer record plus a filtered customer draft is a separate,
later change, made before any customer-facing explanation path is built. No public data is
imported on this branch either; the rule only makes a later, source-checked import possible.

## 1. AGENTS.md, "Rules that must not be broken"

Replace the current first bullet:

> - **Synthetic data only.** Never add real people's or real companies' personal data. The public
>   demo cases (for example Wirecard AG) use published enforcement facts only.

with two bullets:

> - **Every case is synthetic.** Customers, assessment cases, transactions, finances and
>   identity documents are generated. Never turn a real person or company into one, give a
>   generated record a real one's name, or invent a link (ownership, payment, control) between a
>   generated record and a real person or company.
> - **Official reference data only as published.** Entries from official sanctions and country
>   lists, and public legal-entity records (for example GLEIF), may be added unmodified and
>   attributed to their source, once that source's reuse terms and personal-data basis are
>   recorded in `docs/DATA-SOURCES.md`. Legal entities only: list
>   entries for natural persons, PEP data and company officers each need their own reviewed
>   decision first. Raw downloads stay out of the repository, and ARGUS's results about a real
>   company are published only in aggregate.

Why two bullets: the first keeps today's protection for everything ARGUS assesses (and is
what forces the stand-ins: Wirecard, Danske Bank and Westpac are real companies given
generated registry fields, scores and transactions). The second is the narrow opening, with
the three limits the design asked for: unmodified + attributed, a recorded source check
before import, and no natural persons in v1.

## 2. AGENTS.md, repository map

`| data/ | Synthetic data generators and public-source demo data |`
becomes
`| data/ | Synthetic data generators |`
(`data/public/` is deleted with `adverse_media_public.jsonl` and its generator.)

## 3. New file `docs/DATA-SOURCES.md` (the register the rule points to)

Starts empty on purpose:

> **Data sources** (the file's title)
>
> ARGUS's cases are synthetic (see the data rules in `AGENTS.md`). This register
> lists every official public source ARGUS reads as reference data, and what was checked before
> it was added.
>
> | Source | Publisher | What ARGUS takes | Reuse terms | Personal data | History available | Added |
> | --- | --- | --- | --- | --- | --- | --- |
>
> No public source has been added yet.

Alternative if you'd rather not add a file now: drop the link from the rule and say "recorded
in the pull request that adds it". The register is better for the papers' source review.

## 4. Other places that state the rule

| File | Today | Proposed |
| --- | --- | --- |
| `CONTRIBUTING.md` (Ground rules) | **Synthetic data only.** Never add real people's or companies' personal data, in code, tests or issues. | **Cases are synthetic.** Never add a real person or company as a customer or case, in code, tests or issues. Official list entries and public company records follow the rules in `AGENTS.md`. |
| `web/src/app/layout.tsx` footer | Synthetic data and published enforcement facts only. ARGUS recommends; a human reviewer decides. | Synthetic data only. ARGUS recommends; a human reviewer decides. |
| `README.md` (disclaimer, line ~287) | Core test data is synthetic, with a small public-source adverse-media corpus for demo variety. | All test and demo data is synthetic. |
| `.github/PULL_REQUEST_TEMPLATE.md` | Synthetic data only. | Unchanged: true until a source is added; revisit then. |
| `.github/ISSUE_TEMPLATE/bug_report.yml`, `SECURITY.md` | "synthetic data only" / "never include real personal data" | Unchanged: these are about what reporters paste. |
| Diagrams ("synthetic data only") | | Unchanged: still true. |

## 5. Questions for the maintainer (answered 2026-11-13)

1. Accept the two-bullet wording as written, or edit? **Accepted as written.**
2. Add `docs/DATA-SOURCES.md` now (empty register), or leave the register for the first
   source import? **Now, empty, on the stand-in branch.**
3. Stand-in names: proposal follows the existing scenarios' pattern (Synthetic Holdings B.V.,
   Cayman Synth Capital), so the name itself says it is fictional: "Synthetic Payments AG"
   (Wirecard's role), "Synthetic Nordic Bank A/S" (Danske's), "Synthetic Pacific Banking
   Corporation" (Westpac's). Each name gets a GLEIF search before use so none matches a real
   registered company. **Accepted.** GLEIF search on 2026-11-13 (the API's exact legal-name
   filter and its fuzzy completion, with and without the legal form): no record matches any of
   the three. The same queries find "Danske Bank A/S", so they work.
