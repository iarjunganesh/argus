# Roadmap: ARGUS Community Edition

**Status:** idea, not scheduled. Revised 2026-11-16 to match the current runtime and data rule.
**Goal:** a self-hostable ARGUS with no cloud bill, for NGOs, microfinance institutions and
community banks.

## What already exists

Most of the base is the default today:

- The **local data plane** runs with no cloud account: keyword search over the knowledge
  documents, entities and reports from local files and memory, and Tesseract for OCR.
- **No model is needed.** Scores, tiers and findings come from fixed rules; without a model the
  explanation is a labelled template. Any provider the model factory supports can be configured.
- **One container image** runs the API.

## What a community edition would add

| Gap | Today | Needed |
| --- | --- | --- |
| Reports survive a restart | In memory with the local backend | A file-backed `ReportStore` |
| Data | Synthetic only | Official reference data, which the data rule allows once each source is recorded (see below) |
| Packaging | API image only | The web UI in the same deployment, and one command to start both |
| Guidance | None | A guide to common false-positive patterns, written with practitioners |

No third data-plane implementation is planned: the local one is extended instead (decision D6).

## Reference data

A useful community edition needs real sanctions and regulatory reference data. The data rule
in [`AGENTS.md`](../../AGENTS.md) allows official list entries and public legal-entity records,
unmodified and attributed, once each source's reuse terms and personal-data basis are recorded
in [`../DATA-SOURCES.md`](../DATA-SOURCES.md); none is yet. Sources that are licensed or
non-commercial are
excluded by the maintainer's decision of 2026-09-27, which rules out the aggregated lists an
earlier version of this page named. Source notes are in
[`../research/perpetual-kyc-sources.md`](../research/perpetual-kyc-sources.md).

## Not claimed

ARGUS is a demonstration. A community edition would not make it a licensed compliance tool, and
nothing here says it reduces false positives or financial exclusion.
