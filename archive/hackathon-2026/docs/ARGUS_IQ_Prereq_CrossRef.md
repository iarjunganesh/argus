# ARGUS x IQ-Series Prerequisite Cross-Reference

Date: 2026-06-08

## Objective

Verify that Foundry IQ prerequisite work (IQ-Series episodes and badge process) was completed before/alongside ARGUS, and identify any remaining proof gaps for hackathon judging.

## Repository Linkage (verified)

- IQ fork: https://github.com/iarjunganesh/iq-series
- Upstream: https://github.com/microsoft/iq-series
- Local branch: `main`
- Local state: clean (no uncommitted changes)

## Foundry IQ Cookbook Execution Evidence (verified)

All three Foundry IQ cookbooks are present and saved with executed cells and outputs in the fork workspace:

1. Episode 1 notebook
   - Path: `Foundry-IQ/1-Foundry-IQ-Unlocking-Knowledge-for-Agents/cookbook/foundry-iq-cookbook.ipynb`
   - Code cells: 15
   - Executed: 15
   - Cells with output: 14

2. Episode 2 notebook
   - Path: `Foundry-IQ/2-Foundry-IQ-Building-the-Data-Pipeline-with-Knowledge-Sources/cookbook/foundry-iq-cookbook.ipynb`
   - Code cells: 11
   - Executed: 11
   - Cells with output: 10

3. Episode 3 notebook
   - Path: `Foundry-IQ/3-Foundry-IQ-Querying-the-Multi-Source-AI-Knowledge-Bases/cookbook/foundry-iq-cookbook.ipynb`
   - Code cells: 17
   - Executed: 17
   - Cells with output: 16

## Commit-Level Proof (verified)

Recent fork commits touching these notebooks:

- `9d93f46` - Finalize Foundry IQ cookbooks with executed outputs for badge submission
- `672078c` - Run Foundry IQ cookbooks with saved outputs for badge validation

Direct notebook links on fork main:

- https://github.com/iarjunganesh/iq-series/blob/main/Foundry-IQ/1-Foundry-IQ-Unlocking-Knowledge-for-Agents/cookbook/foundry-iq-cookbook.ipynb
- https://github.com/iarjunganesh/iq-series/blob/main/Foundry-IQ/2-Foundry-IQ-Building-the-Data-Pipeline-with-Knowledge-Sources/cookbook/foundry-iq-cookbook.ipynb
- https://github.com/iarjunganesh/iq-series/blob/main/Foundry-IQ/3-Foundry-IQ-Querying-the-Multi-Source-AI-Knowledge-Bases/cookbook/foundry-iq-cookbook.ipynb

## Badge Requirement Cross-Check

Source of truth: `.github/ISSUE_TEMPLATE/foundry-iq-badge-request.yml` in IQ-Series.

Required items include:

- Completion confirmation for all 3 episodes
- Forked notebook URLs with outputs
- Screenshots of final outputs (with username or Azure resource visible)
- Episode takeaways
- Badge form confirmation: https://aka.ms/iq-series/badge-form

## Badge Status (final)

- Issued: Foundry IQ badge process is complete and publicly evidenced.

Primary badge evidence:

- https://globalai.community/badges/b35714f6-9372-4716-985f-ad2058722e76/

Supporting issue evidence:

- https://github.com/microsoft/iq-series/issues/59
- Title: `Arjun Ganesh Foundry IQ Badge Request`
- Includes all 3 episode fork URLs, screenshots, insights, badge form confirmation, and issued status.

## Recommended Closure (completed)

1. Keep badge link in submission evidence: https://globalai.community/badges/b35714f6-9372-4716-985f-ad2058722e76/
2. Keep issue link as supporting technical proof: https://github.com/microsoft/iq-series/issues/59
3. No further badge-tracking action required.

## ARGUS Documentation Alignment

ARGUS architecture already states the prerequisite learning path and badge step in `architecture/ARGUS_Architecture.md` (Section 9).
This cross-reference file adds verifiable, repository-level proof links for judges.

## Runtime IQ Alignment (verified)

ARGUS runtime retrieval is now aligned with the Foundry IQ API shape used in IQ-Series:

- `agents/compliance/tools/regulations_rag.py` queries `knowledge_bases.query(...)` against `argus-kb-regulations`
- `agents/screening/tools/sanctions_checker.py` queries `knowledge_bases.query(...)` against `argus-kb-sanctions`
- `agents/screening/tools/adverse_media_scanner.py` queries `knowledge_bases.query(...)` against `argus-kb-adversemedia`

This means ARGUS is no longer only "IQ-concept aligned" at the documentation level; the runtime retrieval path now uses the Foundry project knowledge base API directly and preserves citations in downstream outputs.
