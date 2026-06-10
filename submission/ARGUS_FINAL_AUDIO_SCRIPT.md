# ARGUS_FINAL_AUDIO_SCRIPT.md

Know Your Customer investigations are essential for financial institutions, but they are often slow, expensive, and highly manual.

Analysts must verify identities, investigate ownership structures, screen sanctions and watchlists, review adverse media, and assess transaction risks before making a compliance decision.

ARGUS addresses this challenge using Microsoft Foundry and a team of specialized AI agents that collaborate through the Agent-to-Agent protocol to automate and explain the KYC investigation process.

At the center of ARGUS is an orchestrator agent responsible for coordinating a team of specialist compliance agents.

The Identity Agent validates customer and entity information.

The Screening Agent performs sanctions, watchlist, and adverse media checks.

The Corporate Agent analyzes ownership structures and beneficial ownership relationships.

The Transaction Agent evaluates transaction patterns and behavioral risks.

The Compliance Agent consolidates findings and produces a final compliance assessment.

Rather than relying on a single AI assistant, ARGUS decomposes complex investigations into specialized tasks and distributes them across multiple agents.

Each agent reasons independently within its domain, and the orchestrator synthesizes the results into a unified assessment.

This multi-agent approach improves transparency, explainability, reliability, and auditability while reducing investigation time.

Before we begin, here's the ARGUS repository.

Now let's see ARGUS in action.

We're submitting a KYC investigation request.

The orchestrator distributes work to specialist agents, which independently analyze identity, screening, ownership, transaction, and compliance risks before returning structured findings.

As the investigation progresses, ARGUS performs identity verification, screening analysis, ownership assessment, transaction risk evaluation, and compliance review in parallel.

Findings from specialist agents are continuously aggregated into a unified compliance assessment.

ARGUS has completed the investigation and produced a risk assessment. Let's examine the results and understand the factors behind this rating.

The Executive Decision summarizes the overall assessment, confidence score, and recommended action.

Directly beneath it, ARGUS explains why the rating was assigned by highlighting the primary risk drivers identified during the investigation.

This allows compliance analysts to quickly understand both the decision and the reasoning behind it.

ARGUS also exposes operational transparency metrics, including the number of agents invoked, tool calls executed, Foundry IQ queries when available, and total investigation runtime.

These metrics provide visibility into how the investigation was performed and reinforce the auditability of the system.

Risk is evaluated across multiple dimensions including identity, screening, corporate ownership, transaction activity, and compliance exposure.

This provides a structured view of where risk originates and helps analysts focus on the areas requiring additional scrutiny.

The investigation timeline provides a complete audit trail showing how specialist agents collaborated throughout the assessment.

Every recommendation is supported by evidence, key findings, regulatory triggers, and available regulatory grounding sources. When Foundry IQ citations are available, they are surfaced directly within the investigation report.

This enables compliance analysts to understand, validate, and defend every recommendation produced by the system.

Rather than acting as a black-box AI, ARGUS provides transparent and traceable reasoning that can be reviewed by both analysts and auditors.

ARGUS demonstrates how Microsoft Foundry-powered reasoning agents can automate compliance investigations through orchestration, multi-step reasoning, explainability, regulatory grounding, evidence-based decision making, and auditability.

By combining specialized agents, regulatory intelligence, transparent reasoning, and explainable risk assessment, ARGUS transforms a traditionally manual compliance process into a workflow completed in seconds.

Thank you for watching.
