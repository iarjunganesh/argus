# Related work: where an ARGUS study would stand (2026-09-30)

Status: **working notes, dated 2026-09-30, not rechecked since.** Summaries are the author's
reading of each source; recheck every paper, licence and regulation before citing it. Two
passes on 2026-09-30:

1. ~10 searches (alphaXiv/arXiv plus web), 8 papers read.
2. Caveat pass: OpenAlex (covers journals, ACM, IEEE, SSRN; queried by topic, by title, and inside
   Journal of Money Laundering Control and Journal of Financial Crime), 6 more alphaXiv searches,
   regulation checks, and licence checks through the figshare and Kaggle APIs.

Still not covered: paywalled full texts (Emerald, Elsevier), Google Scholar (no API),
non-English literature, and CHI/FAccT papers that are not on arXiv (OpenAlex indexes their
titles, and none matched). Semantic Scholar was rate-limited.

## Explanations (the Explain Mode idea)

| Paper | What it does | Relevance |
| --- | --- | --- |
| [Explainable AML Triage](https://www.alphaxiv.org/abs/2604.19755) (2026) | Investigator-facing triage: evidence retrieval, citation contract, counterfactual checks. SynthAML + AMLSim. Citation validity 0.98, evidence support 0.88. | Closest AML paper. No expert review (their own limitation); investigators, not customers. |
| [Communicating Credit Risk with LLMs](https://www.alphaxiv.org/abs/2608.17715) (Southampton, Western, Reykjavik; Aug 2026) | **Closest overall.** LLMs turn SHAP/GNNExplainer output into narratives for Freddie Mac loans; 3 LLMs; LLM-judge faithfulness (coverage + direction); survey of credit professionals vs non-professionals on 8 Likert dimensions. Findings: evidence pipeline matters more than the LLM; narratives name factors but get the **direction** wrong; professionals are stricter. | Credit, not KYC. Reference is post-hoc SHAP (an estimate), checked by an LLM judge; no real affected customers (non-professionals as proxy); no disclosure constraints. Its future work asks for "benchmark datasets emphasising faithfulness" and borrower evaluators. |
| [RGDT-Bench](https://www.alphaxiv.org/abs/2609.34455) (2026-09-28) | Rule-governed decisions + "warrants": 40.2% of correct answers have incomplete justifications; the best of 17 evaluators reaches only 57.7% AUROC. Needs heavy reference annotation. | Method to borrow. ARGUS's fixed rules give the reference warrant for free. |
| [Fidelity audit of LLM credit explanations](https://www.alphaxiv.org/abs/2608.08126) (2026) | One customer-facing credit rationale inverted 3 of 4 drivers; generate-then-verify (membership, direction, coverage). | One case, no rate. |
| [VERDICT](https://www.alphaxiv.org/abs/2609.03366) (Stanford OVAL, Sep 2026) | Clinical trial matching: grounded, faithful, consistent, actionable rationales; "self-faithfulness": changing the pivotal conditions must change the decision. | Method to borrow (counterfactual self-faithfulness). Other domain. |
| [Feature Responsiveness Scores](https://www.alphaxiv.org/abs/2410.22598) (ICLR 2025) | Lending reasons often point at features the applicant cannot change; scores features by whether changing them flips the outcome. | Actionability metric. In ARGUS it is exact: which findings, if resolved, change the tier. |
| [Governance at the Boundary / Fiducia-bench](https://www.alphaxiv.org/abs/2608.16055) (Aug 2026) | 100 KYC/AML task variants: splitting an agent into components loses policy-relevant facts at handoffs (32B model: 0% single loop, 56% pipeline, 85% orchestrator-subagent; gpt-4.1-mini 3-6%). | Directly about ARGUS's architecture. ARGUS passes structured findings and lets fixed rules decide, which should not lose facts; testable. |
| [Spectra](https://www.alphaxiv.org/abs/2609.25474) (McGill + RBC, Sep 2026) | Rules engine + LLM agents for KYC document classification/extraction on real documents. | Onboarding documents, not risk decisions or explanations. Related work. |
| Right to explanation / contestability ([2608.24562](https://www.alphaxiv.org/abs/2608.24562), [2608.02699](https://www.alphaxiv.org/abs/2608.02699), [2605.16041](https://www.alphaxiv.org/abs/2605.16041), [2603.22716](https://www.alphaxiv.org/abs/2603.22716)) | Conceptual/legal. | Framing. |

Journals and IEEE/ACM (OpenAlex, 43 AML papers with "explain" in the title since 2020): all explain
a *detection model* to analysts (SHAP, GNN explainers). KYC titles since 2024 (334): mostly
blockchain e-KYC, identity verification, deepfakes. JMLC/JFC: de-risking is discussed as policy
(e.g. [Re-thinking de-risking, JMLC 2021](https://doi.org/10.1108/jmlc-04-2021-0030);
[Financial exclusion as a consequence of CTF, JFC 2020](https://doi.org/10.1108/jfc-09-2019-0121)),
never as an explanation-quality problem.

**Gap (holds after the second pass, narrower wording):** no paper evaluates explanations of
KYC/AML outcomes (refusal, closure, delay, request for documents) *to the affected customer*,
with fidelity measured against the exact decision record and under the legal limits on what may
be said. Customer-facing *credit* explanations are covered (2608.17715); the new parts are the
KYC domain, an exact reference instead of SHAP, deterministic checks instead of an LLM judge, and
disclosure constraints.

**New regulatory anchors:**

- UK [Payment Services and Payment Accounts (Contract Termination) (Amendment) Regulations 2025](https://www.legislation.gov.uk/ukdsi/2025/9780348271485)
  (SI 2025/688): for contracts from 28 April 2026, 90 days' notice and "an explanation of the
  reasons for termination which is sufficiently detailed and specific to enable the payment
  service user to understand why", **"unless providing that information would be unlawful"**;
  exceptions include failed CDD and suspected serious crime.
- EU [AMLR 2024/1624](https://eur-lex.europa.eu/eli/reg/2024/1624/oj/eng) Art. 73: must not
  disclose that information was or will be sent to the FIU or that an ML/TF analysis is or may
  be carried out (applies from 10 July 2027).
- US ECOA/Reg B adverse-action reasons (CFPB Circular 2022-03) for the credit analogue.

This makes the research question sharper: *can an explanation be faithful to the decision and
still lawful to send?* ARGUS can label each finding "disclosable / not disclosable" (for example
a sanctions or suspicion finding vs a missing document) and measure both leaks and omissions
exactly.

## Perpetual KYC

- Second pass found no academic evaluation either. Closest: a practitioner article,
  [Moving to a perpetual KYC model (Journal of Financial Compliance, 2022)](https://doi.org/10.69554/vgve3167),
  and [A Statistical Diagnosis of Customer Risk Ratings in AML Surveillance (Statistics and Public Policy, 2015)](https://doi.org/10.1080/2330443x.2014.1004005).
  Everything else is vendor or consultancy material.
- [FinLifeBench](https://www.alphaxiv.org/abs/2609.01198): keeping customer records current as
  life events surface in banking dialogue (synthetic, Korean). Not KYC, but a precedent for
  exhaustive deterministic gold over changing customer state.
- [KONTOGRAPH](https://www.alphaxiv.org/abs/2608.22389): point-in-time AML features verified with
  property tests that "perturb the future"; found 3 look-ahead leaks code review missed. Method
  for a replay study: prove no future data leaks.
- Regulation: FCA [findings of 8 April 2026](https://www.regulationtomorrow.com/2026/04/fca-publishes-findings-in-relation-to-firms-customer-due-diligence-processes-and-controls/):
  one of the two most common failures was **no defined criteria for triggering periodic or
  event-driven reviews**. AMLA [draft guidelines on ongoing monitoring, Art. 26(5) AMLR](https://www.regulationtomorrow.com/2026/06/amla-consults-on-draft-guidelines-on-ongoing-monitoring-of-a-business-relationship/)
  (consultation 3 June to 3 September 2026, final expected Q4 2026): event-driven reviews on
  changes in identity/ownership/legal status, behavioural anomalies, adverse media or PEP status,
  financial situation. AMLR Art. 26(2): updates at most every 1 year (higher risk) / 5 years.
- [OpenSanctions Pairs](https://www.alphaxiv.org/abs/2603.11051): pairwise matching near ceiling;
  data CC BY-NC 4.0 (excluded).

## Data and benchmark resources (licences checked)

| Resource | Licence (how checked) | Use for ARGUS |
| --- | --- | --- |
| [Tide](https://github.com/mntijn/Tide) ([paper](https://www.alphaxiv.org/abs/2603.01863)) | MIT (repository) | Candidate single transaction generator. |
| [SynthAML](https://www.nature.com/articles/s41597-023-02569-2) (Spar Nord / Scientific Data 2023) | **CC0** (figshare API, both files) | Independent test set; 20,000 alerts, 16M transactions. |
| [IBM AMLworld](https://github.com/IBM/AML-Data) | CDLA-Sharing-1.0 (data), Apache-2.0 (code) | Independent test set; share-alike applies to the data only. |
| SAML-D (Kaggle, Oztas et al.) | **CC BY-NC-SA 4.0** (Kaggle API) | Excluded (non-commercial). |
| IBM AMLSim | Apache-2.0 | Superseded by Tide. |
| [PUN](https://www.alphaxiv.org/abs/2608.21206) | Released names CC BY-NC; protocol public | Re-run the protocol; don't reuse the names. |
| OpenSanctions Pairs | CC BY-NC 4.0 | Excluded. |
| OFAC SDN + consolidated lists | US public domain (17 U.S.C. § 105); [Sanctions List Service](https://ofac.treasury.gov/sanctions-list-service) has delta files | pKYC replay source; recent-actions notices date every change. |
| UK Sanctions List | Open Government Licence v3 | Single UK list since 28 January 2026 (the OFSI consolidated list stopped updating). |
| EU consolidated financial sanctions list | European Commission reuse notice ([data.europa.eu](https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions-fisma?locale=en)) | pKYC replay source; historical versions to confirm. |

## Method lessons

- Keep stated reasoning separate from what the rules enforce (ReguSim).
- Always include transparent baselines. In ReguSim, a logistic regression beat every LLM monitor.
- Fixed seeds, temperature 0, response caching so results replay without API calls.
- A human agreement check on automatic labels (RGDT: 84% agreement, α 0.69).
- Measure direction errors separately from omissions (2608.17715, 2608.08126).
- Counterfactual self-faithfulness: change the pivotal finding, the explanation must change (VERDICT).
- Actionability: point only at findings the customer can resolve (Feature Responsiveness).
- Replay studies: property tests that perturb the future to prove no look-ahead (KONTOGRAPH).
- Test fact loss at agent handoffs (Fiducia-bench) as a system-design claim.
- State plainly what synthetic results cannot show.
