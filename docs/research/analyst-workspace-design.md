# Design: the web UI as an analyst's workspace

Status: **approved by the maintainer on 2026-11-18. A is built (2026-11-19, its pull request
is next); B is not yet.** It covers
two changes the maintainer chose to make together: the report as a case file an analyst can read
quickly (A), and a simulated review with decisions kept in the visitor's browser (B).

## Why

The person this is for is a KYC analyst at a retail or investment bank who works cases in ARGUS
all day. That person needs the site to be fast, dense and calm, not decorative: the verdict and
the next step at the top, every finding one click from its evidence, the arithmetic behind the
score in plain view, and a clear place where a person records the decision. Today the live site
works, but after an assessment finishes the agent diagram fills the top of the page, the verdict
sits below it, "Why this rating" is a flat list with no link to evidence, the score's arithmetic
is not shown, and nothing shows that a person decides.

## Goals

- The case header answers in seconds: tier, score, what sets the tier, what blocks the case, and
  the next step.
- The score's arithmetic is shown exactly, from the report's dimension scores and weights.
- Every finding shows its uncertainty state, where it came from and when, and opens its evidence
  record and any regulation it triggers.
- The six demo cases appear as a queue with their state in this browser.
- A visitor can play the review: resolve a sanctions match, decide the case with a reason, and
  have a second role sign off on high-risk cases. All of it stays in the visitor's browser and is
  labelled as a demo.
- The layout is the same for every case and every visit, and works at phone width.

## Non-goals

- Accounts, roles enforced by a server, or decisions stored by the API (that is option C, a
  separate product).
- Changes to the score, the tier, the policy or the recorded demo profiles.
- Editing the model's explanation, or showing a diff of an analyst's edits (a possible later
  study measure).
- Due dates or service levels: ARGUS has no policy for them, and invented ones would look real.
- A chat assistant.

## Anti-goals

The change fails, even if it works, if it:

- suggests the model or ARGUS decides, instead of fixed rules recommending and a person deciding;
- shows a confidence figure ARGUS does not have, or a per-finding score ARGUS does not compute;
- hides evidence behind summaries so that it can no longer be found;
- lets a visitor believe a decision was stored, sent or made for real;
- rearranges itself by behaviour or time, so two analysts would see a case differently;
- claims that it improves real-world screening.

## Constraints

- The rules in `AGENTS.md`: every case synthetic; no real decisions and no effectiveness claims;
  explanations keep the findings, evidence references, uncertainty and review status; docs match
  the code; no named inspirations.
- The public deployment: the API accepts only the six demo cases (`ARGUS_DEMO_ONLY`), there are
  no accounts, reports expire 24 hours after their last change, and entity names never go into a
  URL (`web/src/lib/session.ts`).
- Accessibility: the Playwright tests check every page with axe (WCAG 2.2 AA) in light, dark and
  phone layouts; they keep passing.
- The data in a report today, which this change uses and does not extend:
  - `risk_summary` (tier, score, `tier_basis`, sanctions state, EDD flag, recommendation);
  - `dimension_scores` with weights: the score is their weighted sum (Cayman Synth Capital:
    30×20% + 100×30% + 40×15% + 100×25% + 90×10% = 76);
  - `findings`: category, kind, summary, uncertainty (`observed`, `potential`, `unknown`),
    source, `observed_at`, `evidence_refs`, review status `pending`;
  - `evidence` records (source, reference, data; a sanctions record carries the listing's
    programme, entry ID, whether it is active, and the screening source's own match score);
  - `decision_record` (obligations, recommended actions, `reviewer`, `decided_at` and
    `rationale`, all empty today), `regulatory_triggers` with citations, `audit_trace` and
    `timeline`.
- Not in a report today: how many points each finding added to its dimension, and identifiers
  (date of birth, nationality, registration number) for the listing or the customer.
- Cold start: at zero replicas the API takes about 15 to 25 seconds to answer the first request.

## Approaches considered

| | What it is | Trade-off |
| --- | --- | --- |
| A | The report becomes a case file and the demo cases a queue; nothing is stored | Smallest; uses only data the API returns; shows no human step |
| B | A, plus a simulated review: decisions, reasons and a second sign-off, kept in the browser | Shows the whole loop without accounts; must be labelled so no one mistakes it for a record |
| C | Real case management: accounts, roles, stored decisions and their audit | A separate product; does not fit the demo-only public site |

**Chosen: A and B together** (the maintainer, 2026-11-18). C is out of scope.

## Design

```text
ARGUS   Cases   New assessment (local only)                     Role: Analyst ▾
┌ Cases ─────────────────┐┌ Cayman Synth Capital · Company, KY ────────────────────┐
│ CRITICAL Cayman    Rev ││ CRITICAL  76/100   Tier set by: sanctions hold          │
│ HIGH     Payments  Run ││ ⛔ Do not onboard until a person confirms or clears the  │
│ —        Holdings  —   ││    potential sanctions match.      [Review the match]   │
│ —        Jane      —   ││ Review: awaiting analyst · Demo, kept in this browser   │
│ …                      ││─────────────────────────────────────────────────────────│
└────────────────────────┘│ Why 76   Screening 100 × 30% = 30 ▸ 6 findings          │
                          │          Regulatory 100 × 25% = 25 ▸ obligations        │
                          │ Explanation (model) · Regulations · Actions · Audit     │
                          └─────────────────────────────────────────────────────────┘
```

### 1. Cases (the queue)

In demo mode the start page is a table of the six demo cases: entity, type and jurisdiction, and,
once run in this browser, the tier, score and review state. Before a run it shows "Not run" and a
Run action; nothing runs on its own, so a visitor's visit costs no model calls until they choose.
The table sorts by tier, then name. On wide screens it stays as a narrow list beside the open
case; on phones it is its own page. Outside demo mode the form for a new assessment stays.

### 2. Case header

Name, type and jurisdiction; the tier badge and score; what set the tier (score band or sanctions
hold) and the sanctions state; the recommendation as one sentence, with a hold shown as a blocking
notice; the next step as one button (for a sanctions hold, "Review the match"); and the review
state with the demo label (section 8). Without a hold, the button is "Decide the case" and moves
to the decision panel. The report ID and generation time move to the audit trail.

### 3. Why this score

One row per dimension: label, score, weight, its weighted points and tier, and the total that
equals the overall score. When a sanctions hold sets the tier (`tier_basis` is
`sanctions_match`), a line says that the hold, not the score band, sets the tier; the score
bands themselves are not in the report and are not repeated in the UI. Each row expands to the
findings in that category (`corporate_ubo` shows the `corporate` findings), in the order
potential, unknown, observed. Regulatory has no findings of its own; it expands to the
obligations. No per-finding points are shown.

### 4. Findings and their evidence

Each finding shows its summary, an uncertainty label in words ("Observed", "Potential: a person
must confirm", "Unknown: not assessed"), where it came from ("Recorded demo profile", "Computed
from the data plane", "Fallback") and when it was observed. Findings of kind `assessment` have
no summary: they record that a check ran, with the check in `scope` (identity, sanctions, pep,
adverse_media, corporate, transaction) and its state in `value` (for example `completed`). They
are shown as one line per category ("Checks: sanctions, PEP and adverse media completed"), and a
state other than completed is shown as its own finding, because a check that did not run is
something the analyst must see. Opening a finding shows its evidence records: source, reference
fields and data, in labelled fields with the raw JSON one step further. Regulations cited stay a
section of their own, each with its knowledge base, document and article.

### 5. Sanctions match panel

For a potential match, a panel puts the listing beside the customer, using only the fields that
exist: on the listing side the programme, entry ID, whether it is active, the match description
and the screening source's own match score, labelled as the source's score; on the customer side
the name, type and jurisdiction. A line says that identifier comparison (date of birth,
nationality, registration number) needs data the synthetic records do not yet hold. The panel is
where the analyst resolves the match (section 8).

### 6. Explanation, actions and audit

- **Explanation:** labelled with who wrote it ("Written by the language model from the findings"
  or "from a template"), unchanged in content.
- **Actions:** the recommendation's hold first when there is one, then the recommended actions
  in the order the API gives them, leaving out any whose text is identical to an obligation
  already listed under the regulatory row (section 3). For Cayman Synth Capital two are.
- **Audit trail:** collapsed by default; times in the reader's local time, statuses in words;
  the visitor's own review steps are listed here as well, marked "this browser only".
- **Investigation:** shown in full while the assessment runs; once it completes, it shrinks to
  one line ("5 agents finished in 4.4 s; 4 from recorded demo profiles") that expands to the
  diagram.
- The cards "Agents that ran", "Data", "Knowledge-base searches" and "Run time" fold into that
  line and the audit trail.

### 7. Cold start and errors

If the API has not answered after three seconds, the page says that it is starting because it
sleeps when nobody is using it, and that this takes about 20 seconds. Existing error messages
stay.

### 8. Simulated review (option B)

- **Label:** a fixed notice on every case: "Demo review: kept in this browser only and sent
  nowhere. ARGUS recommends; a person decides."
- **Roles:** a switch in the header, Analyst or Approver. The demo cannot check that they are
  two different people, and says so.
- **Steps:**
  1. If a sanctions hold applies, the analyst resolves the match: confirm (true match), clear
     (false positive) or escalate, with a reason (required).
  2. The analyst decides the case: approve, approve with enhanced due diligence (offered, and
     the only approve option, when EDD is required), decline, or escalate, with a reason
     (required). A confirmed match leaves decline or escalate.
  3. For HIGH and CRITICAL, the case then waits for the approver, who signs off or returns it
     with a comment; the analyst cannot approve their own decision.
- **States** shown in the queue and header: not run, awaiting analyst, awaiting approver,
  returned, decided, escalated.
- **Storage:** `localStorage`. The review is keyed by report ID and holds only the steps (role,
  choice, reason, time). The queue keeps, per demo case (by its position in `DEMO_CASES`, not
  its name), the last report ID, tier and score. Nothing stored names the entity. Entries older
  than 24 hours are dropped, matching the API's retention, and a report the API no longer has
  (404) returns its case to "Not run". If storage is blocked, the review still works for the
  open page and says it will not be kept.
- **Shape:** each step uses the same fields as the API's empty `decision_record` slots
  (`reviewer` as the role, `decided_at`, `rationale`), so a later server-side version (option C)
  could take them over. Nothing is sent to the API.

### 9. Phone layout

One column: header, notice, "Why this score", findings, explanation, actions; the queue is its
own page; tables become label and value pairs, so no column is cut off.

## Testing

- Unit tests (Vitest) for the new pure logic: the score arithmetic, the finding labels, the queue
  sorting, the review state machine (every allowed and refused step), and storage expiry and
  failure.
- Playwright: the six scenarios keep their tier and score checks and gain checks on the score
  arithmetic, each finding's evidence, and the hold notice; new tests walk the review for
  Cayman Synth Capital (match, decision, approval) and for Jane Synthetic (no second sign-off);
  axe passes on every new state in light, dark and phone.
- The existing gates: lint, format, type check, build.

## Docs to update in the same pull requests

`web/README.md` (what the UI shows; the demo review), `docs/ARCHITECTURE.md` (the web UI
section), `CHANGELOG.md`, and `HANDOFF.md`.

## Delivery

Two pull requests, in order: A (queue, header, score, findings and evidence, match panel, layout,
cold start), then B (the review). Each passes every check on its own.

## Calls made in this design (the maintainer may change them)

- Per-finding points and identifier comparison are left out: each needs a change outside the
  web UI (the scoring code, or the synthetic data and recorded profiles).
- The queue shows nothing until a case is run in this browser, rather than recorded results.
- The roles are a switch in one browser; the second sign-off applies to HIGH and CRITICAL.
- Decisions are kept 24 hours, like reports.
- Two pull requests, A then B.

## Calls made while building A

- Each dimension's points are exact (a whole score times a whole percentage has at most two
  decimal places), and the total is the API's overall score. The API rounds the sum to one
  decimal place; where the sum has two, the page says so (Synthetic Pacific Banking Corporation:
  18.25 and 18.2).
- Without a sanctions hold, the header's button reads "Review the findings" and moves to "Why
  this score"; "Decide the case" comes with B's decision panel.
- In demo mode the start page's heading and the navigation read "Cases".
- The narrow case list beside an open case has no Run buttons; cases run from the start page.

## Left to the builder

Component structure, styling within the existing shadcn/ui tokens, wording beyond what is fixed
above, and the exact expanded and collapsed states.
