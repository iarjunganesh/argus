# ARGUS v2: a matched explanation study

Revised 2026-11-11. The earlier version of this plan asked only whether explanations could be
made simpler. This version puts a controlled comparison first and keeps simplification as the
follow-up question. The platform sections are unchanged.

## Purpose

Run one bounded study on ARGUS, improve one thing it shows to be wrong, and publish an honest
technical write-up. Use the work to explore a direction in reliable, auditable AI systems for
regulated environments.

In ARGUS, fixed rules decide the score and tier, and a language model only writes the explanation
a human reviewer reads. The study asks what that explanation preserves, and how that depends on
what the model is given.

The research questions:

1. **Preservation.** When a model explains a fixed, rule-determined outcome, does the explanation
   keep the findings, the evidence references, the uncertainty and the human-review status?
2. **Input minimisation.** Does that change when the model receives only minimised, typed findings
   (stable identifiers, categories, bounded scores) instead of the raw case (entity name,
   free-text findings)? What does the model see in each case?
3. **Failure conditions.** What happens to the explanation when case data carries an injected
   instruction, and when one workflow step's result is missing?

**Follow-up question, after the first write-up:** can the explanation be made simpler to read
while still preserving all of the above? This was the earlier plan's only question; it needs the
measures from questions 1 to 3 before it can be answered.

Success means the three questions answered on a small synthetic case set, one bounded improvement,
and one written account of the results, including failures: a short technical report with a
permanent identifier, and an article that summarises it. A peer-reviewed paper is a possible
later outcome, not a requirement for this study.

## How to use this plan

This is a planning document, not an agent instruction file. Repository rules for contributors and
coding agents live in [`AGENTS.md`](../AGENTS.md), and the current state and next step are in
[`HANDOFF.md`](../HANDOFF.md). Reference this plan explicitly when starting v2 work, and verify
behaviour in the code before relying on anything written here.

## Starting evidence and uncertainties

Checked against the code on 2026-11-11 (`main` at `b75d14c`):

- **The analyst explanation receives the raw case.** `explain_decision()` in
  `src/argus/agents/compliance/tools/explain_decision.py` is wired into the Compliance agent. Its
  prompt contains the entity name, type and jurisdiction, the score, tier and tier basis, the
  sanctions and enhanced-due-diligence status, the first five `key_findings` strings, the first
  three regulatory triggers cut to 100 characters, and the five dimension scores.
- **Findings are free text and can carry names.** `_extract_findings()` in the Compliance agent
  builds `key_findings` as strings. A PEP finding includes the matched name from screening.
- **`key_findings` is not a complete record of what set the score.** The scorer also uses
  identity confidence, the corporate score and the transaction risk score, and adds a fixed
  boost for adverse-media-only cases. None of these appears as a finding, so the strings cannot
  serve as the reference for what an explanation must preserve.
- **The explanation records who wrote it.** The result carries `explanation_source` (`model` or
  `fallback`). Without a configured model the fixed template is used and labelled.
- **The customer-facing variant is not wired in.** `explain_decision_plain_language()` has tests
  but nothing calls it. Its prompt tells the model not to quote findings, forbids tiers and
  regulatory references, passes only the first two findings, and never states that a human still
  decides. Its fallback promises contact "within 5 business days", which nothing supports, and it
  does not record whether the model or the fallback wrote the text.
- **The demo scenarios use recorded demo profiles** for the parallel agents, not live calls.
- **Nothing is deployed.** The Azure data plane has not been verified against live services.

Still unverified:

- Which services the hackathon prize's Microsoft credit covers, and its remaining balance.
- Fabric and Work IQ integration feasibility, tenant permissions, licensing, and costs.
- No publication novelty, production readiness, or real-world compliance effectiveness is
  established by this plan.

## Before Week 1

Two pieces of work come first, because the study's reference data depends on them:

1. **Synthetic stand-ins and the data rule.** Three recorded demo profiles carry real company
   names with generated fields. They are replaced by clearly fictional stand-ins, the
   public adverse-media file and the adverse-media boost are removed, and the data rule in
   `AGENTS.md` is reworded. Decided on 2026-10-04; wording and stand-in names accepted on
   2026-11-13; implemented on the stand-in branch on 2026-11-14. Wording:
   [`research/data-rule-proposal.md`](research/data-rule-proposal.md).
2. **Typed findings.** Each finding becomes a typed record with a stable identifier, a category,
   evidence references, an uncertainty marker and a human-review state, and typed findings become
   the only inputs to scoring. The score, tier and obligations for a case are then a function of
   its finding set, which gives every explanation an exact reference to be checked against.
   Design: "Shared rule and decision record" in
   [`research/study-data-design.md`](research/study-data-design.md).

Deployment (Azure Container Apps and Vercel) is not needed for the study. The study runs locally
through the local data plane.

## Scope and architecture

Keep the existing ARGUS flow as the baseline. Hold the deterministic findings, score and tier fixed in every comparison; only the model's input and the injected conditions vary. Improve one explanation path. Preserve the underlying finding, evidence references, uncertainty, and human-review status.

### Core: the matched explanation study

1. **Baseline.** Capture today's analyst explanation for every case, with the exact prompt, model
   configuration and `explanation_source`.
2. **Reference.** For each case, write down from the typed findings what a faithful explanation
   must contain: required findings, evidence references, uncertainty and review status. Define
   this before reading any generated output.
3. **Matched arms.** Explain the same findings twice: from the raw case (today's prompt) and from
   minimised typed findings only. Add the fixed template as a no-model control.
4. **Failure conditions.** Paired cases with and without an injected instruction in a case field,
   and paired cases with and without one workflow step's result. Define the expected behaviour
   for each pair before running it.
5. **One improvement.** Implement one targeted change based on the observed failures and rerun.
6. **Publish** methods, results, failures and limitations.

### Later integrations: the three IQs

Optional, and after the first write-up; none of them is needed to answer the research
questions. ARGUS already uses Foundry IQ. Fabric IQ and Work IQ each get one question of their
own. All three are reached through Microsoft Agent Framework: Foundry IQ through the
`Retriever` interface, Fabric IQ and Work IQ as MCP tools. Local JSON or CSV is enough for the
study's data and results; Microsoft Fabric (the analytics platform, distinct from Fabric IQ)
is used only if access and cost permit.

| IQ | Role in ARGUS | Concrete question | When | Access gate |
| --- | --- | --- | --- | --- |
| **Foundry IQ** | Cited regulatory, sanctions and adverse-media knowledge (already in v1) | Do explanations keep the citations that support each claim? (the core experiment's *evidence support* criterion) | The study (optional: it runs on the local retriever too) | Azure AI Search tier and Foundry project; covered by the budget gate |
| **Fabric IQ** | (a) The evaluation dataset and results report. (b) An **ontology of corporate ownership** (entities, owners, jurisdictions), because beneficial-ownership chains are exactly the relationship-based question this plan required before using Fabric IQ. | (b) Does grounding the Corporate agent in a Fabric IQ ownership ontology change which beneficial owners are surfaced, or how accurately explanations describe ownership? | Both after the first write-up | A Fabric capacity (trial or paused-when-idle F SKU) and tenant access. Verify that the Microsoft credit covers it; don't assume. |
| **Work IQ** | Read-only case-handover context from synthetic analyst notes in a test Microsoft 365 tenant | Does analyst workflow context improve the completeness of a case handover, and when does it introduce unsupported or outdated statements? Compare identical cases with and without the context; establish actual access and permission behaviour before claiming anything about it. | After the first write-up | A Microsoft 365 Copilot licence **or** Copilot Credits usage billing, plus a one-time Entra admin consent (`WorkIQAgent.Ask`). Needs a test tenant; never production mail or chat. |

Rules: every IQ call records which IQ answered and with what sources. A missing IQ (no access,
or no budget) degrades to "not available" in the report instead of failing silently. The local
`Retriever` keeps CI and the zero-cost baseline independent of all three.

### Platform stance: neutral at the boundaries, not multi-cloud

ARGUS stays Azure-first. Azure is where the project's credit is, where Foundry IQ's cited
retrieval lives, and where Fabric and Work IQ come from. It becomes provider-neutral only at
boundaries where neutrality is almost free with current tools. At each of those boundaries,
swapping providers means changing configuration, not rewriting code.

| Layer | Stance | Mechanism |
| --- | --- | --- |
| **Models** | Neutral | Microsoft Agent Framework chat clients, created by one factory and selected with `ARGUS_MODEL_PROVIDER`. There are integrations for Azure OpenAI/Foundry and OpenAI (stable), and for Anthropic, Amazon Bedrock, Gemini, Ollama and Foundry Local (beta as of 2026-09-26). |
| **Compute** | Neutral | One container image. It runs unchanged on Azure Container Apps, other container platforms, or locally. |
| **Tools and data sources** | Neutral | MCP. Fabric IQ, the Fabric data agent and Work IQ are reached as MCP tools (Work IQ also over A2A), not through custom integrations. |
| **Telemetry** | Neutral | OpenTelemetry, using its GenAI conventions for model calls. |
| **Data plane** | **Azure + local only** | A small interface for each of `Retriever`, `EntityStore`, `ReportStore` and `OCR`, each with exactly two implementations. **Azure** (Foundry IQ / AI Search, Cosmos DB, Document Intelligence) is for deployment. **Local** (keyword or local vector search, SQLite, Tesseract) is for CI, the zero-cost baseline and a future community edition. |

Rules:

- **No third data-plane implementation** (AWS, GCP or other) until a concrete question needs
  one. Foundry IQ's agentic retrieval with citations has no drop-in equivalent elsewhere, and
  it's central to ARGUS.
- **Being able to switch models is not a reason to switch.** Every evaluation comparison runs
  on one fixed, recorded model configuration (see Evaluation design).
- **Credits don't decide the architecture.** ARGUS doesn't consume credits from unrelated cloud
  accounts. The one allowed exception is a small, bounded cross-model check (for example, the same
  evaluation cases on a second provider's model). It's allowed only if it answers a question
  the article asks, and it must be reported as a separate run.
- Every result records its provider, model, and whether an output came from the model, a
  fallback or a demo profile. That makes the stance checkable instead of assumed.

### Deferred work

- The customer-facing letter. It needs legal and practitioner review of what may be disclosed, and it is not part of this study (design draft: [`research/study-data-design.md`](research/study-data-design.md), "Paper 1").
- Continuous monitoring, dated event replay and public reference data (same draft, "Paper 2").
- Durable execution and recovery ([`roadmap/durable-execution.md`](roadmap/durable-execution.md)).
- Broad architecture rewrites or additional agents.
- Implementations of the data plane on other clouds (see Platform stance).
- Full community-edition deployment.
- Open knowledge graph and voice input.
- Fabric IQ beyond the ownership-ontology question in the table above.
- Production use or claims of improved real-world screening outcomes.

## Cadence

Planned as about three short engineering sessions and one writing session per week. At the end of
each session, record what changed, what evidence was collected, and the next small step. Scope is
reviewed after two weeks and reduced if the milestones slip.

## Six-week milestones

These are study weeks; they start after the two changes in "Before Week 1". Calendar dates are
in [`HANDOFF.md`](../HANDOFF.md).

| Week | Work | Acceptance gate |
| --- | --- | --- |
| 1 | Write the study protocol; reproduce today's analyst explanation; outline the article. | The protocol is committed before any model run. A documented command produces a saved baseline with its prompt, model configuration and source. |
| 2 | Create the synthetic case set and the per-case reference; build the minimised input. | Cases and expected facts are versioned; tuning cases are separated from held-out cases; the minimised input is generated by code from the typed findings. |
| 3 | Run the matched arms and the template control. | Both arms use the same cases, findings and recorded model configuration; repeated runs capture variability; every request and response is saved. |
| 4 | Run the injection and missing-step pairs. | Expected behaviour was written before the run; each pair differs in one field only. |
| 5 | Implement one improvement for an observed failure pattern and rerun; examine cost and latency; seek independent critique. | Before and after use the same cases; results include regressions; any reviewer assessment method is documented. |
| 6 | Finish and publish the technical report and its summary article, with reproducible artifacts. | Claims trace to results; limitations are explicit; decide whether to take up the simplification question. |

## Evaluation design

Start with roughly 20–30 synthetic cases for a pilot, explicitly acknowledging that this is a small study. Include straightforward findings, missing evidence, conflicting findings, ambiguous matches, and cases requiring human review. Expand only when a specific unanswered question warrants it.

For each case, record required facts, available evidence, uncertainty, and permitted next steps. Define these before judging generated outputs.

Assess:

- **Model input exposure:** Which case strings (entity names, matched names, free-text findings) reach the model in each arm? Measured by exact and normalised string matching on the saved requests; this is not a privacy guarantee against inference or paraphrase.
- **Factual preservation:** Are required findings retained without changing their meaning?
- **Evidence support:** Are assertions supported by the provided evidence, and do references support the specific claim?
- **Uncertainty preservation:** Does an ambiguous match remain ambiguous?
- **Human-review status:** Does the explanation preserve who must decide and what remains unresolved?
- **Unsupported instructions:** Does it invent obligations, assurances, or next steps?
- **Behaviour under injection:** Does an instruction placed in a case field change the explanation, and does the minimised arm ever receive that field?
- **Behaviour with a missing step:** Does the explanation say that a result is missing, or does it describe the case as complete?
- **Readability:** Recorded as a descriptive measure in this study. Whether wording can be made simpler is the follow-up question. Treat automated readability scores as a proxy, not proof of understanding.
- **Operational cost:** What are latency, token usage, and attributable service costs?

Structural checks (identifiers present, counts, deterministic fields unchanged) are computed by code. Meaning-level judgements (a finding reversed, an ambiguity dropped) need human annotation against the per-case reference; say how many annotators there were and how disagreements were handled.

Report numerators and denominators, variation across runs, and representative failures. Keep model settings and evidence inputs comparable; document any unavoidable differences. Record provider, model, version, and settings with every run. Exclude, or report separately, any output produced by a fallback rather than the model. Blind output labels during human comparison where practical.

An automated judge can assist triage but should not be the sole basis for correctness claims. Reader feedback is needed to claim improved comprehension. Synthetic results do not establish reduced financial exclusion or real-world compliance effectiveness.

## Budget and access gate

Before provisioning services, verify the prize's exact product entitlement, eligible charges, expiry, and balance. Verify Fabric capacity requirements and Work IQ tenant/licensing/access prerequisites separately. Do not assume an Azure credit or subscription benefit covers every Microsoft service.

Agree a small experiment budget after checking current pricing. Use bounded workloads and pause or remove idle resources where supported. Keep local evaluation possible so access issues do not stall the article.

## Writing alongside implementation

Working title: **What Does a Model Need to See to Explain a Decision It Did Not Make?**

Keep a short experiment log from the first session. Draft sections as evidence becomes available:

1. Problem and narrowly defined question.
2. Existing ARGUS behavior and observed failure examples.
3. Evaluation cases, per-case reference, and baseline.
4. Matched raw and minimised arms; injection and missing-step pairs.
5. One targeted change, why it was chosen, and results, regressions, latency, and cost.
6. Limitations and what remains unknown.
7. Reproduction instructions, and the simplification question as the next investigation.

A result showing no improvement is still useful if the methods and analysis are sound. Adding products is an integration achievement; a research contribution requires a defensible question and evidence. Consider a paper only after reviewing related work and identifying a contribution beyond the integration itself.

## Session log template

```text
Date:
Question for this session:
Change or experiment:
Evidence / artifact paths:
Result, including failures:
Time and measured cost:
Next small step:
```

## Reference documentation

Product descriptions were checked on 2026-09-26. Recheck availability, APIs, licensing, and pricing before implementation.

- Microsoft Fabric: <https://learn.microsoft.com/fabric/fundamentals/microsoft-fabric-overview>
- OneLake: <https://learn.microsoft.com/fabric/onelake/onelake-overview>
- Microsoft IQ, including Work IQ and Fabric IQ: <https://learn.microsoft.com/en-us/microsoft-iq/>
