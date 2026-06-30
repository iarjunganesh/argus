# Roadmap: ARGUS Witness — Adverse Event Reporting

**Status:** Planned
**Goal:** A whistleblower-safe, anonymous channel for reporting suspicious entities directly into the ARGUS knowledge graph.

---

## The gap

ARGUS currently pulls adverse media from indexed public sources. It has no mechanism for:
- Employees at financial institutions who want to flag suspicious activity without using internal channels
- Journalists who have documented financial crime and want it surfaced in compliance screening
- Regulators who want to share pre-publication adverse event signals with the compliance ecosystem

---

## What ARGUS Witness does

1. A secure, anonymous web form (Tor-accessible) accepts structured adverse event reports
2. Reports are reviewed by a human moderator before indexing (no automated ingestion)
3. Approved reports are indexed into the adverse media knowledge base with a `witness:` provenance tag
4. The ARGUS Screening Agent surfaces `witness:`-tagged findings with a distinct visual treatment — separate from public-source adverse media

This is deliberately modest — no AI processing of raw submissions, no automated entity resolution. The human review step is non-negotiable for whistleblower protection.

---

## Privacy model

- No IP logging on the submission endpoint
- Tor .onion address available
- Submissions encrypted at rest (age encryption)
- Reviewer sees only the structured submission, never metadata
- Approved entries strip all submission metadata before indexing
- Right to erasure: submitter can request removal via a one-time deletion token issued at submission time

---

## Non-goals

ARGUS Witness is NOT:
- A replacement for official regulatory reporting (FinCEN SARs, etc.)
- A real-time intelligence feed
- Fully automated — every submission has a human in the loop

---

## Rollout plan

- [ ] Legal review: whistleblower protection implications by jurisdiction
- [ ] Submission form design (accessibility-first — screen reader compatible, no CAPTCHA)
- [ ] Human review queue (simple Django admin or Retool interface)
- [ ] Moderation guidelines and reviewer training material
- [ ] Integration with `adverse_media_scanner` tool in Screening Agent
- [ ] Tor hidden service configuration
