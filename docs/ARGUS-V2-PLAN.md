# ARGUS v2: a focused engineering and writing experiment

## Purpose

Spend six weeks investigating one question, improving ARGUS, and publishing an honest technical article. Use the work to explore a direction in reliable, auditable AI systems for regulated environments.

**Research question:** Can ARGUS produce simpler explanations while preserving evidence, uncertainty, and the need for human review?

Success means one answered question, one bounded improvement, and one written account of the results. A peer-reviewed paper is a possible later outcome, not a requirement for this experiment.

## How to use this plan

This is a planning document, not an agent instruction file. Repository rules for contributors and
coding agents live in the repository instructions. Reference this plan explicitly when starting v2
work, and verify behaviour in the code before relying on anything written here.

## Starting evidence and uncertainties

Checked against the code on 2026-09-26:

- **Explain Mode.** `explain_decision()` (analyst-facing) is wired into the Compliance agent.
  `explain_decision_plain_language()` (customer-facing) exists in
  `agents/compliance/tools/explain_decision.py` but nothing calls it and no test covers it.
- **The plain-language prompt works against this plan's criteria by design.** It tells the model
  not to quote findings, forbids tiers and regulatory references, passes only the first two
  findings, and never states that a human still decides.
- **The fallback invents an obligation.** It promises contact "within 5 business days", which
  nothing supports.
- **Fallbacks are silent.** Without a configured model, both explanation paths return template
  text, so a baseline must record whether each output came from the model or a fallback.
- **Foundry IQ queries don't reach Foundry IQ.** The tools call
  `AIProjectClient.knowledge_bases.query`, which doesn't exist in `azure-ai-projects` 1.0.0 or
  2.6.1, so every call falls back to mock results.
- **The demo scenarios use recorded demo profiles** for the parallel agents, not live calls.

Still unverified:

- Which services the hackathon prize's Microsoft credit covers, and its remaining balance.
- Fabric and Work IQ integration feasibility, tenant permissions, licensing, and costs.
- No publication novelty, production readiness, or real-world compliance effectiveness is
  established by this plan.

A cleanup comes before Week 1: archiving the hackathon material, CI, agent instructions, a
single-process runtime on Microsoft Agent Framework, and hosting. Week 1 starts when it is done.

## Scope and architecture

Keep the existing ARGUS flow as the baseline. Improve one explanation path. Preserve the underlying finding, evidence references, uncertainty, and human-review status.

### Core: Explain Mode evaluation

1. Capture the current explanation behavior.
2. Define a fixed evaluation set and scoring rubric.
3. Implement one targeted improvement based on observed failures.
4. Compare baseline and revised outputs under comparable conditions.
5. Publish methods, results, failures, and limitations.

### Supporting integration: Microsoft Fabric

Use Fabric for a small evaluation dataset and analysis of results, if access and cost permit. Suggested records include case ID, experiment version, model configuration, output, rubric scores, latency, and measured cost.

First deliverable: one dataset and one report comparing baseline and revised explanations. Local JSON/CSV remains sufficient to complete the investigation if Fabric setup becomes a distraction.

Microsoft Fabric and Fabric IQ are distinct. Fabric provides data and analytics infrastructure. Fabric IQ is planned for one relationship question, corporate ownership (see *The three IQs*); it is not required for the initial evaluation store or report.

### Later experiment: Work IQ

After the first article draft is complete, investigate a read-only case-handover summary using synthetic analyst notes and discussions in a test Microsoft 365 environment.

Follow-up question: Does analyst workflow context improve case handover completeness, and when does it introduce unsupported or outdated statements?

Compare identical cases with and without the added context. Preserve source references and evaluate conflicting, stale, missing, and inaccessible material. Establish actual access and permission behavior before making claims about it.

Work IQ is optional and must not block the first deliverable.

### The three IQs

ARGUS uses all three Microsoft IQ layers. Each has its own question, and none of them blocks the
first deliverable. All three are reached through Microsoft Agent Framework: Foundry IQ through
the `Retriever` interface, Fabric IQ and Work IQ as MCP tools.

| IQ | Role in ARGUS | Concrete question | When | Access gate |
| --- | --- | --- | --- | --- |
| **Foundry IQ** | Cited regulatory, sanctions and adverse-media knowledge (already in v1) | Do explanations keep the citations that support each claim? (the core experiment's *evidence support* criterion) | Weeks 1–6 | Azure AI Search tier and Foundry project; covered by the budget gate |
| **Fabric IQ** | (a) The evaluation dataset and results report. (b) An **ontology of corporate ownership** (entities, owners, jurisdictions), because beneficial-ownership chains are exactly the relationship-based question this plan required before using Fabric IQ. | (b) Does grounding the Corporate agent in a Fabric IQ ownership ontology change which beneficial owners are surfaced, or how accurately explanations describe ownership? | (a) Week 4 (optional); (b) after the article draft | A Fabric capacity (trial or paused-when-idle F SKU) and tenant access. Verify that the Microsoft credit covers it; don't assume. |
| **Work IQ** | Read-only case-handover context from synthetic analyst notes in a test Microsoft 365 tenant | See *Later experiment: Work IQ* | After the article draft | A Microsoft 365 Copilot licence **or** Copilot Credits usage billing, plus a one-time Entra admin consent (`WorkIQAgent.Ask`). Needs a test tenant; never production mail or chat. |

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

- Broad architecture rewrites or additional agents.
- Implementations of the data plane on other clouds (see Platform stance).
- Full community-edition deployment.
- Open knowledge graph, voice input, or continuous event monitoring.
- Fabric IQ beyond the ownership-ontology question in *The three IQs*.
- Production use or claims of improved real-world screening outcomes.

## Cadence

Planned as about three short engineering sessions and one writing session per week. At the end of
each session, record what changed, what evidence was collected, and the next small step. Scope is
reviewed after two weeks and reduced if the milestones slip.

## Six-week milestones

| Week | Work | Acceptance gate |
| --- | --- | --- |
| 1 | Inspect implementation and reproduce current Explain Mode; outline the article. | A documented command produces a saved baseline example; implementation gaps and external dependencies are recorded. |
| 2 | Create a small synthetic evaluation set and explicit rubric; verify platform entitlements. | Cases and expected facts are versioned; tuning cases are separated from held-out evaluation cases. |
| 3 | Implement one improvement addressing an observed failure pattern. | Relevant checks pass; before/after examples demonstrate the intended behavior without changing underlying findings. |
| 4 | Run comparable evaluations; optionally ingest results into Fabric. | Baseline and revised runs use the same evaluation cases and recorded configurations; repeated runs capture variability. |
| 5 | Examine failures, cost, and latency; seek independent critique. | Results include regressions and limitations; any reviewer assessment method is documented. |
| 6 | Finish and publish a technical article with reproducible artifacts. | Claims trace to results; limitations are explicit; decide whether to continue with Work IQ. |

## Evaluation design

Start with roughly 20–30 synthetic cases for a pilot, explicitly acknowledging that this is a small study. Include straightforward findings, missing evidence, conflicting findings, ambiguous matches, and cases requiring human review. Expand only when a specific unanswered question warrants it.

For each case, record required facts, available evidence, uncertainty, and permitted next steps. Define these before judging generated outputs.

Assess:

- **Factual preservation:** Are required findings retained without changing their meaning?
- **Evidence support:** Are assertions supported by the provided evidence, and do references support the specific claim?
- **Uncertainty preservation:** Does an ambiguous match remain ambiguous?
- **Human-review status:** Does the explanation preserve who must decide and what remains unresolved?
- **Unsupported instructions:** Does it invent obligations, assurances, or next steps?
- **Readability:** Is the wording simpler? Treat automated readability scores as a proxy, not proof of understanding.
- **Operational cost:** What are latency, token usage, and attributable service costs?

Report numerators and denominators, variation across runs, and representative failures. Keep model settings and evidence inputs comparable; document any unavoidable differences. Record provider, model, version, and settings with every run. Exclude, or report separately, any output produced by a fallback rather than the model. Blind output labels during human comparison where practical.

An automated judge can assist triage but should not be the sole basis for correctness claims. Reader feedback is needed to claim improved comprehension. Synthetic results do not establish reduced financial exclusion or real-world compliance effectiveness.

## Budget and access gate

Before provisioning services, verify the prize's exact product entitlement, eligible charges, expiry, and balance. Verify Fabric capacity requirements and Work IQ tenant/licensing/access prerequisites separately. Do not assume an Azure credit or subscription benefit covers every Microsoft service.

Agree a small experiment budget after checking current pricing. Use bounded workloads and pause or remove idle resources where supported. Keep local evaluation possible so access issues do not stall the article.

## Writing alongside implementation

Working title: **What Gets Lost When an AI Compliance Report Becomes Plain English?**

Keep a short experiment log from the first session. Draft sections as evidence becomes available:

1. Problem and narrowly defined question.
2. Existing ARGUS behavior and observed failure examples.
3. Evaluation cases, rubric, and baseline.
4. One targeted change and why it was chosen.
5. Results, regressions, latency, and cost.
6. Limitations and what remains unknown.
7. Reproduction instructions and next investigation.

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
