# Roadmap: durable execution and continuous monitoring

Working proposal · 28 September 2026 · Not scheduled and not an implementation commitment.
Deferred until the study in [`../ARGUS-V2-PLAN.md`](../ARGUS-V2-PLAN.md) is written up.

## Recommendation

Keep Microsoft Agent Framework as Argus's orchestration framework. Use Microsoft's supported durability facilities for execution recovery. Add deterministic policy and approval rules, and recovery tests, written for the KYC domain.

Build one durable investigation lifecycle. Let the runtime own execution scheduling and recovery; let Argus own evidence, decisions, authorisation and business-level idempotency. Do not add another orchestration engine, cloud or database merely to reuse a pattern.

For the first pKYC pilot, automate monitoring and evidence preparation under human-on-the-loop (HOTL) supervision. Require human-in-the-loop (HITL) approval for material case dispositions and exceptions. Assign oversight per activity; one investigation can use both patterns.

## Baseline reviewed

Repository: <https://github.com/iarjunganesh/argus>

Reviewed main commit: `29d4d8312a8ad0301e4259907bcc6484603f649e`.

- One in-process Agent Framework workflow runs four parallel assessment functions followed by compliance.
- FastAPI BackgroundTasks starts assessments; workflow checkpoint storage is not configured.
- Progress events support SSE replay/reconnection. This is client reconnection, not investigation recovery after a worker crash.
- A container smoke test exercises a recorded demo scenario through the API.
- Local Tesseract OCR supports synthetic PNG/PDF documents, but the public assessment API has no document input yet.
- Azure adapters are tested with SDK stand-ins; live Azure verification remains outstanding.

Recheck this baseline before implementation. The roadmap does not claim any of the work below has shipped.

## Architectural boundaries

| Responsibility | Owner |
| --- | --- |
| Workflow execution, checkpoints, retry scheduling and waits | Selected Microsoft durability runtime |
| Customer identity, evidence versions, findings and reviewer decisions | Argus domain records |
| Screening, scoring and mandatory completeness checks | Deterministic Argus functions/executors |
| Explanation of recorded findings | Configured language model, with labelled fallback |
| Permission to approve a case | Authenticated reviewer and application authorisation |
| Duplicate case/notification prevention | Argus operation IDs and idempotent destination writes |

Workflow checkpoints are not the permanent business audit record. Keep execution state and domain evidence logically separate, even if their storage shares an Azure service. Agent conversation history is not a substitute for either.

## Human oversight and decision authority

**HITL:** execution waits for an authorised reviewer before a specified decision or action proceeds. **HOTL:** bounded automation runs under human supervision, with an accountable owner who can inspect, intervene and suspend it.

The matrix below is a proposed pilot policy for deployment in a regulated bank, not a statement that Argus is deployed there or a universal legal requirement. The bank must validate the boundaries against applicable requirements and its approved policies. FATF's technology guidance supports automation alongside continued human judgment; it does not prescribe this particular matrix.

| Activity | Pilot authority | Conditions and escalation |
| --- | --- | --- |
| Collect updates and check freshness | HOTL automation | Approved sources; stale or unavailable feeds raise a coverage incident |
| Detect changes, rerun screening and compute scores | HOTL automation | Versioned rules and evidence; incomplete required checks cannot imply clearance |
| Record no material change | HOTL automation | Validated criteria, fresh evidence and sampled review; not blanket customer approval |
| Prepare explanations and review cases | HOTL automation | Preserve evidence, uncertainty and model/fallback provenance |
| Resolve ambiguous matches or ownership conflicts | HITL analyst review | Inspect underlying evidence; unresolved conflicts remain pending |
| Clear a potential sanctions match or approve a false-positive exception | HITL authorised review | Entity/finding-specific scope, supporting evidence, expiry and reopening rules |
| Accept material risk, approve a policy exception or decide customer exit | HITL designated decision authority | Role-based approval; additional reviewer where bank policy requires it |
| Apply an immediate protective hold/block | Separate bank-approved control policy | Define triggers, authority and timing explicitly; review waits must not delay required controls |
| Change thresholds, scoring rules or automation permissions | Human governance approval | Versioned change, validation and rollback plan |
| Monitor automation quality and coverage | HOTL accountable supervisor | Actionable alerts, sampling, intervention authority and escalation deadlines |

For each action, record: policy ID/version, permitted automation, required evidence and freshness, authorised role, any separation-of-duties requirement, review deadline, timeout behaviour, audit fields, and challenge/reopening route. Persist the applied policy with each decision. A model confidence score alone must not authorise an action.

HOTL requires staffed ownership and intervention capability, not just a dashboard. Track source freshness, monitoring coverage, backlog age, overdue reviews, sampled false positives and missed material changes against reviewed labels or evaluation cases. Alert counts alone cannot establish that changes are being detected correctly.

A review timeout must not silently approve or reject a customer. Escalate overdue work and retain an explicit pending/incomplete state; any separate protective control follows its approved policy. Approval must bind to the reviewed evidence version. Material evidence arriving during review invalidates stale approval or creates an explicit reassessment before disposition.

## Phase 0 — Select and prove the durability path

**Goal:** choose one supported recovery mechanism before expanding the architecture.

- [ ] Test compatibility with Argus's pinned Python, Agent Framework and dependencies; record exact versions and package lifecycle status.
- [ ] First evaluate the Durable Extension with the existing container/FastAPI direction. Confirm support for the actual Python graph and hosting combination using a minimal runnable example.
- [ ] If that combination is unsuitable, evaluate the documented Azure Functions path. Make hosting changes explicit rather than assuming an example for another language applies.
- [ ] Compare ordinary checkpoint storage only if a smaller, explicitly resumed workflow is sufficient. A storage provider alone does not provide dispatch or automatic recovery.
- [ ] Choose one path and record its checkpoint boundaries, recovery trigger, concurrency behaviour and deployment/version constraints.
- [ ] Record local-development requirements and estimated deployment costs before provisioning paid services.

**Exit evidence:** a minimal workflow pauses, its process terminates, and a new process continues from persisted state. An interrupted step may retry; externally visible duplicate effects must be prevented separately. If the spike fails, record the limitation and revise the choice before porting more code.

## Phase 1 — Make one Argus assessment durable

**Goal:** a submitted assessment survives a worker restart.

- [ ] Replace BackgroundTasks as the authoritative job execution mechanism with durable submission and dispatch.
- [ ] Define stable investigation, source-event and operation IDs. Repeated submission with the same idempotency key must return the existing investigation; reject conflicting payloads under the same key.
- [ ] Persist request, evidence references, workflow version and scoring-policy version before acknowledging durable acceptance.
- [ ] Use the selected runtime's checkpoints. Preserve recorded operation inputs across retries; do not silently generate a different action when resuming.
- [ ] Make report publication and case creation idempotent. Design atomic writes around the selected store's actual transaction boundaries.
- [ ] Keep SSE as a view of recorded progress, with stable event IDs across restart and replay.
- [ ] Distinguish workflow execution status from assessment validity: completed execution can produce an incomplete assessment.

**Exit evidence:** one non-demo-profile assessment is interrupted and recovered using persistent storage. It produces one authoritative result, preserves evidence provenance and never silently remains stuck in processing.

## Phase 2 — Add governance rules

**Goal:** a recoverable investigation also has controlled decisions.

- [ ] Add deterministic completeness gates before recommendations or case closure. Missing required evidence produces an incomplete/review-needed outcome; an outage must not automatically imply low risk or customer rejection.
- [ ] Add a human-review state and authorised approval endpoint. Derive reviewer identity from authentication, never a caller-supplied name.
- [ ] Prevent worker identities from approving their own findings.
- [ ] Record the decision, reason, evidence version, policy version, reviewer and timestamp.
- [ ] Scope false-positive clearances to an entity/finding match and supporting evidence. Define expiry and invalidation on material changes; do not suppress all future alerts for a customer.
- [ ] Minimise model and notification payloads while allowing authorised reviewers to inspect underlying evidence.
- [ ] Implement the decision-authority matrix as versioned policy with explicit HITL gates and HOTL automation boundaries.
- [ ] Assign review owners, deadlines and escalation routes; persist pending approvals across restarts without default approval on timeout.
- [ ] Bind approval to the reviewed evidence version; reject stale or conflicting decisions atomically.
- [ ] Define any immediate protective controls separately from analyst review, including their authority and timing.
- [ ] Provide supervisors with coverage/quality metrics, sampled review and controls to suspend affected automation without losing incoming events.

**Exit evidence:** a review survives restart, an unauthorised or stale approval is rejected, a valid decision is recorded once, and changed evidence reopens the relevant review. Overdue work escalates without implicit clearance, and the supervisor can suspend and safely resume affected automation.

## Phase 3 — Prove failure behaviour

**Goal:** test the guarantees at the points where they can fail.

| Failure or race | Required observable result |
| --- | --- |
| Kill a worker during an assessment | Recovery follows documented checkpoint boundaries; unfinished work is retry-safe |
| Kill after creating a case but before acknowledging it | Retry finds the existing case; no duplicate case |
| Deliver one source event concurrently to multiple workers | One authoritative investigation and deduplicated effects |
| Model service unavailable | Deterministic checks still run where possible; explanation fallback is labelled |
| Required screening source unavailable | Assessment is incomplete, not falsely cleared |
| Restart during human review | Pending review and evidence references survive |
| Repeat an approval request | No duplicate or conflicting final decision |
| Evidence changes while an approval is pending | The old approval cannot authorise disposition against new evidence |
| Review deadline expires | Escalation occurs; no implicit approval or rejection |
| Monitoring feed becomes stale | Coverage degradation is visible; absence of updates is not recorded as no material change |
| Supervisor suspends automation | Affected automated actions stop; incoming events remain recoverable and pending work remains visible |
| Reconnect to SSE | Stable progress replay without duplicate business actions |
| Deploy new code while work is pending | Compatible recovery, or an explicit drain/migration/version-routing policy |

Use real persistent storage for recovery/concurrency tests. Add tests for competing resumed workers, not just initial claims. Do not label the entire system exactly-once based on unique database rows alone. Keep test evidence synthetic and record what ran, where and with which build.

## Phase 4 — Validate the Azure path

- [ ] Exercise live retrieval, report storage and document analysis with controlled synthetic cases outside the six recorded demo profiles.
- [ ] Validate deployed identity permissions, retry handling, timeouts and data-source failures.
- [ ] Connect document submission to the identity assessment, with explicit input limits and provenance.
- [ ] Repeat the recovery and duplicate-delivery drill on the chosen deployed runtime.
- [ ] Capture latency, operational cost, incomplete assessments and failed/retried investigations.

**Exit evidence:** one deployed, non-profile assessment traverses real Azure services; its recovery and evidence trail are inspectable. Passing local stand-in tests is not this gate.

## Phase 5 — Add the first pKYC loop

**Scope:** one monitored corporate portfolio, ownership changes and sanctions re-screening.

- [ ] Maintain versioned customer/ownership snapshots with source timestamps.
- [ ] Ingest one reliable change source using polling or events; distinguish ingestion time from effective time.
- [ ] Match updates to stable customer identities and detect material changes; do not use name equality as the complete entity-resolution strategy.
- [ ] Trigger affected checks and record the before/after evidence and assessment difference.
- [ ] Create one review case, record its human resolution, and maintain monitoring coverage/freshness status.
- [ ] Handle cleared matches and reduced risk as well as risk increases.
- [ ] Exercise HOTL detection and evidence preparation followed by a HITL material decision in the same investigation.
- [ ] Sample no-material-change outcomes and evaluate missed changes as well as false positives before broadening automation permissions.

**Exit evidence:** ownership changes, the assessment updates under HOTL supervision, an authorised reviewer resolves the material case through HITL, and repeated delivery produces no duplicate case. A subsequent material change triggers a new review. Coverage incidents and overdue reviews reach their assigned owners.

## Defer until the first loop works

- Similar-case vector memory: later reviewer assistance, never automatic clearance based on resemblance.
- Broad MCP query access: later, behind case/customer-level authorisation and constrained query tools.
- Extra agent frameworks, cross-cloud hosting and an independent recovery engine.
- Additional IQ integrations or UI rewrites that do not unblock the selected end-to-end flow.
- Automated material dispositions or broad exception suppression before measured validation and bank policy approval.

## What to reuse

Keep Argus's assessment functions, scoring, data interfaces, provenance and API contracts. Rework submission, case history and the reviewer workflow for durability. Write behavioural contracts and tests first; adapt SDK calls and database operations deliberately.

## Next concrete task

Complete Phase 0 with one assessment-shaped workflow: parallel checks, deterministic fan-in, a human-review wait and a recorded result. Prove restart recovery with the selected Microsoft runtime before adding monitoring feeds.

## Sources and review notes

Microsoft documentation checked 28 September 2026. Examples and available features must be validated against the pinned Python packages; documentation is not proof that the chosen Argus deployment works.

- Durable Extension: <https://learn.microsoft.com/en-us/agent-framework/hosting/azure-functions>
- Standard workflow checkpoints: <https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints>
- Argus orchestration: <https://github.com/iarjunganesh/argus/blob/29d4d8312a8ad0301e4259907bcc6484603f649e/src/argus/agents/orchestrator/agent.py>
- Argus API: <https://github.com/iarjunganesh/argus/blob/29d4d8312a8ad0301e4259907bcc6484603f649e/src/argus/api/main.py>
- FATF, Opportunities and Challenges of New Technologies for AML/CFT (2021), checked 28 September 2026: <https://www.fatf-gafi.org/en/publications/Digitaltransformation/Opportunities-challenges-new-technologies-for-aml-cft.html>

The human-oversight matrix is an engineering recommendation informed by this guidance, not a legal classification or a claim of regulatory approval.
