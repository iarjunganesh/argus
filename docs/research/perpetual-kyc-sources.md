# Sources: perpetual KYC and sanctions scoring (2026-09-27)

Status: **working notes, dated 2026-09-27, not rechecked since; the monitoring work they
support is deferred.** Recheck every source before relying on it. Gathered for two questions: how a sanctions match should
affect the ARGUS risk result, and what "perpetual KYC" (pKYC) after v2 must satisfy.

## Primary sources

- **EU AMLR, Regulation (EU) 2024/1624, Article 26** (applies from 10 July 2027).
  <https://eur-lex.europa.eu/eli/reg/2024/1624/oj/eng>
  - 26(2): customer information updated at most every **1 year for higher-risk** customers and
    every **5 years for all others**; "shall not in any case be exceeded".
  - 26(3): update also when relevant circumstances of the customer change, or relevant facts
    emerge (event-driven).
  - Summary: <https://anti-money-laundering.eu/new-updating-obligations-under-article-262-amlr-and-article-23-draft-rts-cdd/>
- **AMLA consultation paper, draft guidelines on ongoing monitoring under Article 26(5) AMLR**
  (3 June 2026; comments closed 3 Sept 2026; draft, not final).
  <https://www.amla.europa.eu/document/download/46b50078-08ed-4ab1-aea0-28b1a6085755_en?filename=Consultation+Paper+-+Article+26%285%29+AMLR.pdf>
  - Definitions: event-driven review, triggering events, periodic review, pre-transaction,
    real-time and post-transaction monitoring.
  - Para 24-26: define and detect trigger events; handle "without undue delay", prioritised by
    risk; document processes clearly.
  - Para 27 trigger list: (a) identity, legal status or ownership changes (directors, UBOs);
    (b) behavioural or transactional anomalies; (c) new adverse media, new PEP status, legal
    proceedings, regulatory notices, warnings from authorities; (d) financial situation, source of
    funds, higher-risk jurisdictions or counterparties.
  - Para 29(c): use company registries and public databases to detect ownership/status changes.
  - Para 48-50: rules, scenarios, thresholds clearly defined, documented, tested, calibrated;
    vendor defaults not used without a documented assessment.
  - Para 51: CDD, **sanctions screening** and monitoring must operate in an integrated way.
    Sanctions compliance itself is outside these guidelines, but monitoring must escalate
    sanctions-evasion signals.
  - Para 75: explain on request how each output was assessed, escalated and acted on.
  - Para 78-79: automated closure only where no risk indicators; never for higher-risk cases;
    decision logic understood and documented; human oversight with sampling.
  - Para 87-90: AI/ML allowed; outputs reviewable and challengeable; explainability proportional;
    "deployment of such tools should not, in itself, be considered an indicator of effectiveness".
- **FATF Recommendation 10 and its interpretive note**: ongoing due diligence; keep CDD data up to
  date, reviewing existing records particularly for higher-risk categories; risk-based.
  <https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html>
- **FATF Recommendation 6 (and 7)**: targeted financial sanctions require freezing **without
  delay** (hours after a UN designation) and without prior notice. Not a risk-weighted
  obligation. <https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Bpp-finsanctions-tf-r6.html>
- **Wolfsberg Guidance on Sanctions Screening (2019)**: screening design may be risk-based, but
  sanctions compliance is strict liability; a match is dispositioned (true/false), not weighted.
  <https://wolfsberg-group.org/resources/168/53>

## Secondary (vendor explainers; use for vocabulary only)

- <https://kyc360.com/knowledge-hub/resources/what-is-perpetual-kyc>
- <https://www.quantexa.com/resources/perpetual-kyc-guide/>
- Key point they agree on: FATF and the FCA do not mandate "pKYC" as such; periodic, event-driven
  or hybrid are all acceptable if risk-based and documented.

## Public data for event triggers (licence check still needed per source for v0.2.0)

| Trigger (AMLA 27) | Source | Change feed | Licence / caveat |
| --- | --- | --- | --- |
| Sanctions listing | OFAC SDN, UN consolidated, EU FSF, UK list | publisher updates | public; check each |
| Ownership (entities) | GLEIF Level 2 golden copy | delta files every 8 h | CC0 |
| Ownership (UK) | Companies House streaming API (PSC) | real-time stream | free key; **real personal data** |
| Adverse media | GDELT | 15-min updates | check terms |
| PEP status | Wikidata | live SPARQL | CC0; **real personal data** |
| Aggregated lists | OpenSanctions | daily | **CC BY-NC: commercial use needs a paid licence** |

**Maintainer decision 2026-09-27: no licensed data at all** (OpenSanctions out). Only public data that
is free to use, commercial reuse included.

**Bolagsverket (Sweden), "värdefulla datamängder" API** (EU high-value datasets): free, no
agreement, commercial and non-commercial reuse allowed as long as data-protection and secrecy law
is respected; OAuth 2 client registration ("kundanmälan"); REST API plus weekly bulk files; ~60
requests/minute (secondary source). Company name, org number, legal form, status (incl. bankruptcy
and liquidation), address, SNI code, registration date, annual reports. Beneficial owners are NOT
included (register closed to the public after the CJEU ruling of 22 Nov 2022). Whether officers
are named is unconfirmed; check the API spec. Fits: Swedish registry_lookup, legal-status change
as an AMLA 27(a) trigger. Refs: <https://bolagsverket.se/apierochoppnadata/hamtaforetagsinformation/vardefulladatamangder/apiforvardefulladatamangder.5513.html> ,
<https://www.dataportal.se/en> (national catalogue).

Real personal data (PSC, Wikidata PEPs) collides with AGENTS.md "Synthetic data only"; the v0.2.0
rule change must decide how that is scoped (e.g. entities only, or public officials only).

## Implications for ARGUS

1. **Sanctions should gate, not weigh.** A potential sanctions match should force the outcome to
   "hold for human disposition" regardless of the weighted score; a weighted 30% term (today's
   design, scoring ~18 = LOW for a sanctions-only case) is inconsistent with R.6 and Wolfsberg.
2. pKYC maps onto the existing agents: (a) identity + corporate, (b) transaction, (c) screening,
   (d) transaction/corporate. What's missing is a trigger source, a re-run on trigger, a diff
   against the previous report, and the 1-year/5-year periodic floor.
3. ARGUS's fixed rules + provenance + human review already match para 48, 75, 79, 88-90.
   Keep: no automated closure of risky cases; document thresholds; explain outputs.

## PEP minimum tier? (researched 2026-09-27)

- FATF R.12 (text checked): foreign PEPs -> senior management approval, source of wealth/funds,
  enhanced ongoing monitoring, always. Domestic / international-organisation PEPs -> same measures
  only for higher-risk relationships. Family members and close associates included.
- FATF PEP Guidance 2013: "foreign PEPs are always high risk" (quoted by secondary sources; the FATF
  PDF could not be fetched). <https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Peps-r12-r22.html>
- EU AMLR Art. 42(1): the three measures apply to all PEPs, no domestic/foreign split.
  <https://amlr.eu/article-42-specific-provisions-regarding-politically-exposed-persons/>
- UK MLR reg 35(3A) + FCA FG25/3 (July 2025): EDD for all PEPs but risk-sensitive; domestic PEPs
  start as LOWER risk; "No one risk factor ... means a customer should automatically be treated as
  posing a higher risk"; don't decline merely for PEP status; >= 12 months after leaving office.
  <https://www.fca.org.uk/publication/finalised-guidance/fg25-3.pdf>
- Conclusion: PEP status mandates MEASURES (EDD), not a RISK TIER. Recommend: no tier floor; an
  EDD-required flag + recommendation whatever the tier. Later: classify foreign vs domestic with
  the EU prominent-public-functions lists (5AMLD Art 20a; OJ C/2023/724) + Wikidata; FATF's
  foreign-PEP rule could then set HIGH for foreign PEPs.

## Free company data for lookups (no licensed data)

- EU HVD Implementing Reg. 2023/138: every member state publishes basic company data + accounts
  free, via API (+ bulk), under CC0 / CC BY 4.0 or less restrictive, applicable since June 2024.
- GLEIF (CC0, global, parents). Norway Brønnøysund Enhetsregisteret (NLOD, no key, commercial OK
  with attribution). UK Companies House (OGL v3, free key; officers + PSC = real personal data).
- Individuals: no open register by design; only PEPs (Wikidata CC0) and sanctions lists.
