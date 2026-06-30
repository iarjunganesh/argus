# Roadmap: ARGUS Community Edition

**Status:** Designed — scaffolding in `community/`
**Goal:** Zero-cost, self-hostable ARGUS for NGOs, microfinance institutions, and community banks.

---

## The case for Community Edition

The organizations most likely to be falsely flagged as high risk — NGOs in sanctioned-adjacent jurisdictions, microfinance lenders serving the unbanked, community banks without enterprise compliance budgets — are also the ones who can least afford to integrate licensed KYC tooling.

Community Edition removes every cost barrier:
- No Azure subscription required for the base flow
- No licensed data feeds — open corpus only
- One Docker Compose command to run
- SQLite + Qdrant + Tesseract replace the Azure-backed services

---

## Architecture differences vs full edition

| Component | Full Edition | Community Edition |
|---|---|---|
| LLM | GPT-4o (Azure OpenAI) | GPT-4o-mini (or any OpenAI-compatible endpoint) |
| Entity store | Azure Cosmos DB | SQLite |
| Vector search | Azure AI Search | Qdrant (self-hosted) |
| OCR | Azure Document Intelligence | Tesseract |
| Knowledge base | Foundry IQ (licensed feeds) | Open corpus (FATF, Basel AML Index, Open Sanctions) |
| Hosting | Azure | Docker Compose (Railway, Fly.io, or local) |
| Cost | $$$  | ~$0 for low volume |

---

## Open Corpus

The Community Edition ships a pre-seeded regulatory knowledge base from open sources:

| Dataset | License | Update frequency |
|---|---|---|
| FATF 40 Recommendations | Public domain | Stable |
| Basel AML Index country scores | CC-BY | Annual |
| Open Sanctions consolidated list | ODC-BY | Daily |
| OFAC SDN List | Public domain | Real-time (fetched on startup) |
| EU Consolidated Sanctions List | Public domain | Real-time |

The open corpus does not include proprietary PEP lists or commercial adverse media feeds. Organizations that need those can plug in a licensed provider via the `VectorBackend` abstraction.

---

## NGO Onboarding

Community Edition ships with:

1. **Sample entity dataset** — 200 synthetic entities representing common false-positive patterns in NGO/microfinance KYC:
   - Names that phonetically match sanctions list entries
   - Jurisdictions that score poorly on blunt country-risk rubrics but have legitimate NGO operations
   - Corporate structures that look like layering but are standard for international NGO legal frameworks

2. **False-positive playbook** — documented patterns with Foundry IQ / open-corpus citations showing WHY a given entity is flagged and HOW to distinguish it from genuine risk

3. **Explain Mode output** — every report includes the plain-language version (see `roadmap/explain-mode.md`)

---

## Rollout Plan

### Phase 1 — Docker Compose (this branch)
- [ ] Dockerfile for community image
- [ ] SQLite adapter for entity/transaction store
- [ ] Qdrant adapter for vector search
- [ ] Tesseract OCR path in `identity_validator`
- [ ] Open corpus seed script
- [ ] `CommunityConfig` wired into all agent constructors

### Phase 2 — One-click deploy
- [ ] Railway deploy button in README
- [ ] Fly.io deploy config
- [ ] Health check endpoint that reports edition (community vs full)

### Phase 3 — NGO Program
- [ ] Application form for verified NGOs
- [ ] Pre-verified open corpus with NGO-specific false-positive patterns indexed
- [ ] Community forum / GitHub Discussions for compliance edge cases
