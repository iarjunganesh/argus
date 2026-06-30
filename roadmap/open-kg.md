# Roadmap: Open Knowledge Graph

**Status:** Planned
**Goal:** Publish the ARGUS regulatory knowledge corpus as structured, versioned, open data.

---

## Why open?

The knowledge that determines who gets a bank account is currently locked behind:
- Licensed compliance data providers ($10k–$100k/year)
- Proprietary risk scoring models (opaque, unauditable)
- Vendor-specific knowledge bases (Foundry IQ, Dow Jones, LexisNexis)

Organizations that need this most — NGOs, microfinance lenders, community researchers studying financial exclusion — are priced out. The result: they either skip compliance checks entirely (regulatory risk) or rely on blunt country-level heuristics that create false positives at scale.

The ARGUS Open KG makes the base regulatory layer a public good.

---

## Corpus

### v1 Open KG (launch target)

| Dataset | Source | Format | License |
|---|---|---|---|
| FATF 40 Recommendations | FATF | JSON-LD | Public domain |
| FATF Mutual Evaluation Reports (summaries) | FATF | JSON | Public domain |
| Basel AML Index | Basel Institute | JSON | CC-BY 4.0 |
| Open Sanctions consolidated list | OpenSanctions.org | JSON, CSV | ODC-BY |
| OFAC SDN List | US Treasury | JSON (converted) | Public domain |
| EU Consolidated Sanctions List | European Commission | JSON (converted) | Public domain |
| UN Security Council Sanctions | UN | JSON (converted) | Public domain |

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
- No PII in the corpus
- Available as: GitHub releases, pip package (`argus-open-kg`), and hosted API endpoint
