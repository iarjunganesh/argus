# Study data design: working draft

Status: **working draft, last revised 2026-10-04; partly deferred on 2026-11-11;
typed-record implementation merged on 2026-11-16 (#31); finished work condensed on
2026-11-16.** It was revised after three review passes (not published). This is a research
design, not an implementation specification or a claim of legal or screening effectiveness.
Legal readings here are the author's and have not been reviewed by a lawyer.

What is in use now, for the study in [`../ARGUS-V2-PLAN.md`](../ARGUS-V2-PLAN.md): the
typed-findings design in "Shared rule and decision record". The first section records the data
rule and the stand-in migration, both done. The two papers below ("Paper 1" and "Paper 2"), the
public legal-entity cohort and the source-feasibility steps are deferred until that study is
written up.

Both papers use Sweden as the primary setting. The [Swedish AML Act](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-2017630-om-atgarder-mot-penningtvatt-och_sfs-2017-630/)
and [FI rules](https://www.fi.se/en/bank/money-laundering/rules-to-prevent-money-laundering-and-the-financing-of-terrorism/)
anchor present-day scenarios; the EU AMLR and current AMLA consultation draft are labelled
prospective until their applicable/final versions are checked. UK law is a labelled comparison.

## First decision: source-data rule and study boundary

**Done.** The data rule in `AGENTS.md` keeps every case synthetic and admits unmodified,
attributed official list entries and public legal-entity records as reference data once each
source is recorded in `docs/DATA-SOURCES.md` (accepted 2026-11-13, merged in #29; reasons in
[`data-rule-proposal.md`](data-rule-proposal.md)). Do not turn a real person or company into a
generated record, fabricate a relationship with a synthetic customer, or publish raw personal
data.

**The stand-in migration is done (#29).** The three real-company demo profiles became clearly
fictional corporate stand-ins whose registry matches, scores and transaction histories are
invented and whose tiers follow the live rules, with no aliases to the old names. The public
adverse-media file left local retrieval and both Azure upload paths, and the demo-only
adverse-media boost was removed. Historical enforcement facts about real companies may appear
only as separately sourced background, never as generated assessment cases.

**The hosted demo is bounded (decided and implemented on 2026-10-04 with the deployment work).**
A visitor notice alone cannot enforce the synthetic-data rule, so a public deployment accepts
only the synthetic demo cases at the API boundary (`ARGUS_DEMO_ONLY`, on in Bicep;
`NEXT_PUBLIC_ARGUS_DEMO_ONLY` for the site). Reports and their events expire after 24 hours
(Cosmos default time to live 86400 on `kyc_reports`, and the same expiry in the memory store),
and no names are logged.

One replay may combine synthetic customer cases with public reference events, but every
field and event records its origin. Allowed synthetic exposure kinds are **closed**:

1. A synthetic customer's or synthetic counterparty's country is affected by a dated
   country-list update.
2. An event's category and dates are transplanted into a generated subject; the public
   subject and any real relationship facts are removed, and the scenario is labelled
   `synthetic_event_derived_from_public`.
3. A generated namesake is compared with a synthetic list entry as a matching negative
   or ambiguous test, without asserting that a real listed person is the customer. A
   real natural-person list entry requires a separate privacy and lawful-basis decision
   and is outside the first version.

A synthetic customer paying or being owned by a real listed subject is forbidden even
if marked simulated. Labelled true-match fixtures are allowed only where they do not
make a real person a synthetic customer; otherwise true matches belong in the public
legal-entity cohort. Plaid Sandbox remains a candidate delivery path for generated
transactions and Plaid-native users as negative controls **only after its developer
terms and publication rights enter the source register**. The **Tide transaction generator** (MIT;
arXiv 2603.01863) is a candidate generator, distinct from the UK bank with that name.

**Maintainer decision (2026-10-04): yes, in the first version of the two papers; deferred with them on 2026-11-11.** Include a narrow public legal-entity cohort in the first version for observed event
frequencies in a declared GLEIF sampling frame and real matching difficulty. These
frequencies are **not** base rates for a bank's customer population. GLEIF records form
the company spine, `SOLE_PROPRIETOR` entries are excluded, and direct matches use
official entity records. EU sanctions designations come
first for Sweden; an OFAC feed is explicitly third-country context, not a Swedish binding
designation. Restrict the cohort to public corporate status/parent changes, entity
designations, country-list changes and dated official notices. Do not claim PEP,
transaction, document or finance coverage in this cohort. Publish methods, source IDs,
scripts and hashes only after source review; report ARGUS alerts in aggregate, never as
per-company accusations. Report synthetic and public-cohort results separately.

The company-matching answer key is a prerequisite, not an assumed property of the
feed. For EU designations, link an official registration number to a GLEIF
registration-authority entity ID in the same jurisdiction, and double-annotate a sample
of name-only candidates. Record disagreements and unresolved cases. The OFAC comparison
can use its LEI-bearing entity entries as an exact-ID check, but that does not make
OFAC designations binding in Sweden. EU delistings require archived snapshots or the
Official Journal; a current-only list cannot reconstruct removals.

For each source, record the rights to access, reuse and redistribute, attribution,
historical availability, permitted fields, GDPR/personal-data basis where relevant,
retention and publication decision. A free copyright licence is not a personal-data
basis. The [UK Open Government Licence v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
excludes personal data; the [UN website terms](https://www.un.org/en/about-us/terms-of-use)
are limited to personal non-commercial use. Do not ingest the UN site as a general
commercially reusable source; inspect applicable EU transpositions instead. Keep raw
snapshots with personal data out of the public repository. Public PEP and officer fields
need their own purpose, lawful basis and minimisation review before any import.

## Shared rule and decision record

Before the typed-findings prerequisite, `key_findings` omitted identity discrepancies,
transaction layering/typologies and ownership depth that affected the score. The policy
caps dimensions, counts PEP in multiple dimensions and lets a sanctions match override
the tier; the adverse-media boost was removed with the stand-ins. **Implemented on
2026-11-15 and merged on 2026-11-16 (#31):** typed findings are the only case inputs to scoring and obligations,
with stable IDs, retained source evidence and citations, uncertainty, source/observation
times, policy version and pending human review. A separate machine decision record stores
the evaluation and input IDs; human reviewer, decision time and rationale remain null.
The string list is a compatibility projection, and the analyst prompt template is unchanged.
The [runtime documentation](../ARCHITECTURE.md#typed-findings-and-decision-record) describes
the implementation. No minimised input, exact-set benchmark or study model run is implemented
by this prerequisite; the subset-analysis requirements below remain planned.

Never claim additive contributions. Declare and version an empty-finding reference
case with fixed structural metadata; missing evidence stays unknown, not verified or
clear. Record the exact score, tier and obligations the policy gives that reference.
Evaluate every subset against that same reference and policy. Report all
**inclusion-minimal** sufficient sets for each outcome, obligation and tier that differs
from the reference, not just the set with the fewest members; two redundant findings
can each be sufficient even though removing either alone changes nothing. Record
risk-lowering findings separately as mitigators/defeaters with their evaluation context;
do not treat their absence as positive evidence or assume the rules are monotone.
Cap exhaustive enumeration at 16 findings per case (65,536 subsets, including empty),
counting mitigators too. Cases above the cap are excluded from the exact-set benchmark
and reported separately, never silently truncated or presented as exactly attributed.
Record leave-one-out score/tier/outcome changes as a separate diagnostic with effect types
(`score_change`, `override`, `obligation`, or `none`). Build counterfactual pairs by
toggling a finding in a valid minimal context where that toggle changes the result.
The current hand-set weights are illustrative: Paper 1 can assess faithfulness
to ARGUS's rules, not whether those rules are substantively correct. The analyst record
retains every finding, evidence reference, uncertainty and review status. A customer
draft is a separate, filtered artefact, never the canonical report. This distinction
also needs an explicit update to `AGENTS.md` and the committed v2 plan before the
customer-facing path is implemented.

## Paper 1: customer explanation benchmark

One item is a synthetic case plus a **human decision** to request information, delay,
refuse or close; the letter explains that outcome, not an internal risk tier. A legal
expert and practitioner review scenario-level disclosure labels (`allow`, `withhold`,
`needs_review`) with jurisdiction, outcome, policy version and reason. Labels must cover
combinations of facts: two individually allowed facts plus an outcome can disclose a
protected examination. A potential match is never described as confirmed. PEP or
confirmed sanctions status is not blanket-secret; the legal basis and context decide.

In Sweden, [4 kap. 9 § of the AML Act](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-2017630-om-atgarder-mot-penningtvatt-och_sfs-2017-630/)
restricts revealing that the examination under 4 kap. 2 § is, was or will be carried
out, as well as reporting. A transaction-anomaly finding linked to that examination
therefore defaults to `withhold` pending expert review. The Swedish duty to give reasons
appears narrower, chiefly around basic payment accounts; the legal expert must confirm
its scope. The question is what a faithful and lawful customer draft can say, not a
claim that every KYC outcome must be explained. [EU AMLR Article 73](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1624)
is a prospective EU anchor. [CJEU C-81/24 Jenec](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A62024CJ0081)
supports a basic-account scenario where a third-country listing alone does not justify
automatic refusal without individual risk assessment. The UK termination rule is a
separate comparison with its AML/CDD exceptions, not the Swedish default.

Candidate Swedish scenarios for expert selection: basic-account refusal for a non-AML
reason; third-country-only listing and basic-account refusal; request for documents
after a PEP finding; delay while a transaction examination is under way; a potential
EU sanctions match held for human disposition. Do not produce customer letters until
the scenario labels and ethics route are settled.

Code removes `withhold` and `needs_review` facts **before** any model call. A reviewer
sees all facts and the legal basis for omissions, and records the final disclosure
decision. Each generated sentence cites allowed fact IDs; deterministic checks cover
cited-ID validity, allowed-fact coverage, direction, review status and match certainty.
Human annotation measures unsupported or reversed free-text claims, inferential leaks,
and false completeness (for example, saying an allowed reason is the *only* reason when
others were withheld), with inter-rater agreement. Compare a fixed template and at
least two pinned models (including one open-weights model) under cached, reproducible
settings. Use Swedish letters in the primary study, with Swedish LIX as a descriptive
readability measure and lay-reader comprehension as the meaningful outcome; the
current English Flesch-Kincaid target does not transfer. An open-weights model needs
compute, and a paid API needs the maintainer's resource approval before use. Keep
today's prompt-only raw-findings method as an offline ablation; it is
not a customer-delivery path. Lay readers answer comprehension questions; practitioners
assess accuracy and lawful disclosure. No automated sending.

## Paper 2: dated event replay

An append-only event records source, source ID, category, listing authority,
`effective_at` if known, `published_at`, `observed_at`, snapshot/hash, subject ID,
licence/privacy decision, optional `derived_from`, and `supersedes` link for revisions.
A transplanted synthetic event gets its own synthetic source and subject ID; its
`derived_from` points to the public source ID/hash, and it cannot inherit the real
listing authority as though that authority listed the generated subject. Matching decisions and
human dispositions are separate records. Historical `observed_at` is simulated from a
predeclared polling schedule after publication; prospective collection can capture it
directly. The replay sees nothing before `observed_at`.

The [3 June 2026 AMLA consultation draft](https://www.amla.europa.eu/policy/public-consultations/consultation-draft-guidelines-ongoing-monitoring-business-relationship_en)
is a draft; pin that version and recheck the final guidelines before preregistration.
Its categories and adjacent controls are:

| Category | Candidate source or generator | Coverage boundary |
| --- | --- | --- |
| Identity, directors, signatories, ownership and legal status changes | GLEIF Level 1/2 and checked registers; generated personal changes | Public cohort covers legal entities only; Level 2 is accounting parents, not complete UBOs |
| Behavioural and transaction anomalies | Generated ledgers; independent SynthAML (CC0) test | Continuous monitoring in both policy arms; no real customer transactions |
| PEP, adverse media, legal proceedings, regulatory notices and authority warnings | Source-checked public records and dated official notices; generated PEP/customer cases | Public cohort covers company notices, not personal PEP customers; source history may be incomplete |
| Financial situation, products, source of funds, higher-risk jurisdictions or counterparties | Generated finances/behaviour; dated FATF/EU list updates | Distinguish customer behaviour from a regulatory list update |
| Targeted sanctions screening (adjacent, outside AMLA draft scope) | EU entity designations first; OFAC third-country comparator | Rescreen on every list update in both policy arms; human match disposition |
| Document expiry or renewal | Generated documents | Expiry alone is not automatically a trigger under AMLA's preferred risk-based option |

Baseline = scheduled CDD review **plus** sanctions rescreening on every list update
**plus** continuous transaction monitoring. Treatment retains all three and adds
event-driven review for the other categories. The [AMLR Article 26](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1624)
one-/five-year maxima inform the scheduled clock but do not imply a bank waits to
rescreen sanctions or monitor transactions. Run both policies for whether an early
review resets the next periodic date; the AMLA draft says it can. Predeclare replay
window, cohort sizes, polling cadence, review capacity and queue order (risk priority,
then observation time as a tie-breaker). Capacity-constrained runs are primary; an
unlimited-capacity run is a sensitivity check, since its latency advantage can be
mechanical.

The informative outcomes are source lag (`effective` → `published` → `observed`), entity
matching precision/recall, namesake false alerts, review workload, coverage gaps and
time from observable event to human disposition, by category and cohort. Use noisy
identifiers, namesake decoys and independent transaction test data so the generator
does not supply both every input and its answer. Perturb future events to test for
look-ahead. Do not claim observed improvements in real-world AML effectiveness.

## Source feasibility before a spec

1. Check the EU sanctions list's usable dated history first. If it lacks reproducible
   history, do not manufacture a historical EU result; begin a prospective collector
   outside the public repository and mark the historical coverage gap. Prefer EU
   transpositions of UN designations where applicable; OFAC remains separately labelled.
   Verify the registration-number-to-GLEIF answer key and an archived path for removals.
2. Confirm GLEIF Level 1 and Level 2 historical snapshots, effective/published dates and
   `SOLE_PROPRIETOR` filtering. Check source-specific redistribution terms.
3. Check dated PEP, official-notice, adverse-media and jurisdiction-list histories and
   personal-data grounds separately. Use no present-day snapshot to fill past knowledge.
4. Document what can be released: generated cases and labels, event metadata, fetch
   scripts and hashes where permitted. Keep raw personal records and per-entity ARGUS
   assessments out of the public release.
5. Put Plaid Sandbox in the source register and verify its developer terms before using
   or publishing test users as negative controls. Record the compute/API cost and approval
   route for each candidate explanation model.

The implementation spec follows these gates. The rule change they needed is in `AGENTS.md`
(#29); natural persons, PEP data and company officers still need their own reviewed decision.
