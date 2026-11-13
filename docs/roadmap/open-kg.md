# Roadmap: Open Knowledge Graph

**Status:** idea, not scheduled. Licences below were corrected on 2026-11-11 and still need checking.
**Goal:** Publish the ARGUS regulatory knowledge corpus as structured, versioned, open data.

---

## Why open?

The knowledge that determines who gets a bank account is currently locked behind:

- Licensed compliance data providers ($10k–$100k/year)
- Proprietary risk scoring models (opaque, unauditable)
- Vendor-specific knowledge bases

Organizations that need this most — NGOs, microfinance lenders, community researchers studying financial exclusion — are priced out. The result: they either skip compliance checks entirely (regulatory risk) or rely on blunt country-level heuristics that create false positives at scale.

The ARGUS Open KG makes the base regulatory layer a public good.

---

## Corpus

### v1 Open KG (launch target)

No source has been approved. Each needs its reuse terms and personal-data basis recorded first
(see [`../research/data-rule-proposal.md`](../research/data-rule-proposal.md)); the reuse column
is the current understanding from [`../research/related-work.md`](../research/related-work.md)
and [`../research/study-data-design.md`](../research/study-data-design.md), not a legal check.

| Dataset | Source | Reuse terms, to verify |
| --- | --- | --- |
| FATF Recommendations | FATF | Copyright FATF/OECD; redistribution needs permission, so link and cite, do not republish |
| Basel AML Index | Basel Institute | Not checked |
| OFAC SDN and consolidated lists | US Treasury | US public domain |
| EU consolidated financial sanctions list | European Commission | Commission reuse notice |
| UK Sanctions List | UK government | Open Government Licence v3, which excludes personal data |
| UN Security Council list | UN | UN website terms allow personal non-commercial use only; use the EU transpositions instead |

Aggregated lists under non-commercial licences are excluded (maintainer decision, 2026-09-27).
List entries about natural persons need their own privacy decision before any are published.

### v2 Open KG (contribution target)

Community-contributed, peer-reviewed:

- NGO legal structure templates (common UBO patterns that look like layering but aren't)
- Microfinance typology library (legitimate high-volume small transactions vs. structuring)
- Country risk narrative summaries (FATF language translated to plain English per jurisdiction)

---

## Schema

Regulatory knowledge is structured as a graph:

```json
{
  "id": "fatf:r16",
  "type": "Recommendation",
  "title": "Wire Transfers",
  "jurisdiction": "*",
  "risk_indicators": [
    "cross_border_wire",
    "nested_correspondent",
    "missing_originator_info"
  ],
  "cites": ["fatf:r1", "fatf:r10"],
  "plain_language": "When money is sent electronically across borders, banks must include information about who is sending it and who is receiving it...",
  "source_url": "https://www.fatf-gafi.org/en/recommendations/fatfrecommendations.html"
}
```

---

## Governance

- Versioned with SemVer (regulatory changes are breaking changes)
- All contributions require a source citation
- No personal data in the corpus without a recorded lawful basis
- Available as: GitHub releases, pip package (`argus-open-kg`), and hosted API endpoint
