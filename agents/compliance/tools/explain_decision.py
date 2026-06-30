"""Plain-English explanation generator for compliance risk decisions."""
from config import MODEL_NAME, get_llm_client


async def explain_decision(
    entity: dict,
    risk_summary: dict,
    dimension_scores: dict,
    key_findings: list,
    regulatory_triggers: list,
) -> str:
    tier = risk_summary.get("overall_risk_tier", "UNKNOWN")
    score = risk_summary.get("overall_risk_score", 0)

    findings_text = "\n".join(f"- {finding}" for finding in key_findings[:5]) or "- No material findings"
    regs_text = "\n".join(
        f"- {trigger.get('rule', '')[:100]}" for trigger in regulatory_triggers[:3]
    ) or "- No regulatory triggers"

    dim = dimension_scores or {}
    dim_text = "\n".join([
        f"- Identity: {dim.get('identity', {}).get('score', 0)}/100",
        f"- Screening: {dim.get('screening', {}).get('score', 0)}/100",
        f"- Corporate/UBO: {dim.get('corporate_ubo', {}).get('score', 0)}/100",
        f"- Transaction: {dim.get('transaction', {}).get('score', 0)}/100",
        f"- Regulatory: {dim.get('regulatory', {}).get('score', 0)}/100",
    ])

    prompt = f"""You are a senior KYC compliance analyst writing a risk assessment note.

Entity: {entity.get('name')} ({entity.get('type')}, jurisdiction: {entity.get('jurisdiction')})
Risk Score: {score}/100
Risk Tier: {tier}

Key findings identified:
{findings_text}

Regulatory rules triggered:
{regs_text}

Dimension risk scores (0=low risk, 100=high risk):
{dim_text}

Write exactly 3 to 5 sentences explaining WHY this entity received a {tier} risk rating.
Rules:
- Use plain English. Assume the reader is a bank manager, not a lawyer.
- Reference specific findings.
- Reference specific regulations by name when present.
- Do NOT use bullet points or numbered lists.
- Do NOT start with 'The entity'.
- Be direct and professional."""

    try:
        client = get_llm_client()
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return _fallback_explanation(tier, key_findings)


def _fallback_explanation(tier: str, findings: list) -> str:
    if not findings:
        return f"This case was assessed as {tier} risk based on the combined screening and compliance analysis."
    primary_finding = findings[0]
    return (
        f"This case was assessed as {tier} risk primarily because {primary_finding.lower()}. "
        "The final recommendation combines screening, ownership, transaction, and regulatory signals. "
        "A reviewer should confirm the findings before making an onboarding decision."
    )


async def explain_decision_plain_language(
    entity: dict,
    risk_summary: dict,
    key_findings: list,
    reference_id: str = "",
) -> dict:
    """
    Generate a plain-language explanation for the person being screened —
    not for the compliance analyst. Uses Flesch-Kincaid grade ≤ 8 language.

    Returns a dict with keys: what_happened, what_we_found, what_happens_next,
    contact_info. Each is a human-readable paragraph.
    """
    tier = risk_summary.get("overall_risk_tier", "UNKNOWN")
    ref = reference_id or "your application"

    tier_framing = {
        "LOW": "completed successfully and did not raise any concerns",
        "MEDIUM": "raised some items that need a closer look before we can proceed",
        "HIGH": "flagged several concerns that require a detailed review before we can make a decision",
        "CRITICAL": "flagged serious concerns that require immediate review by our compliance team",
        "UNKNOWN": "has been received and is under review",
    }
    framing = tier_framing.get(tier, tier_framing["UNKNOWN"])

    findings_summary = ". ".join(key_findings[:2]) if key_findings else ""

    prompt = f"""You are writing a customer-facing letter explaining a KYC review outcome.
The tone must be calm, professional, and empathetic. The reader may be anxious.

Entity name: {entity.get('name')}
Review outcome: {framing}
Internal findings (do NOT quote these directly — reframe in plain English): {findings_summary}
Reference number: {ref}

Write four short paragraphs labeled exactly:
WHAT_HAPPENED: (one sentence — what the review process was)
WHAT_WE_FOUND: (one or two sentences — what was flagged, in general terms, no jargon, no regulatory citations)
WHAT_HAPPENS_NEXT: (one or two sentences — what the person should expect next, including any documents they might need to provide)
CONTACT_INFO: (one sentence — how to reach the compliance team with the reference number)

Rules:
- No acronyms. No regulatory codes (FATF, AMLD, BSA). No risk tier labels (HIGH/MEDIUM).
- Grade 8 reading level or below.
- Active voice. First person plural (we/our).
- Never say the word "suspicious" or "flagged".
- Do not apologize excessively."""

    try:
        client = get_llm_client()
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.3,
        )
        raw = (response.choices[0].message.content or "").strip()
        return _parse_plain_language_response(raw, tier, ref)
    except Exception:
        return _fallback_plain_language(tier, ref)


def _parse_plain_language_response(raw: str, tier: str, ref: str) -> dict:
    sections = {
        "what_happened": "",
        "what_we_found": "",
        "what_happens_next": "",
        "contact_info": "",
    }
    key_map = {
        "WHAT_HAPPENED:": "what_happened",
        "WHAT_WE_FOUND:": "what_we_found",
        "WHAT_HAPPENS_NEXT:": "what_happens_next",
        "CONTACT_INFO:": "contact_info",
    }
    current_key = None
    for line in raw.splitlines():
        matched = False
        for prefix, section in key_map.items():
            if line.strip().startswith(prefix):
                current_key = section
                sections[current_key] = line.strip()[len(prefix):].strip()
                matched = True
                break
        if not matched and current_key:
            sections[current_key] = (sections[current_key] + " " + line.strip()).strip()

    if not any(sections.values()):
        return _fallback_plain_language(tier, ref)
    return sections


def _fallback_plain_language(tier: str, ref: str) -> dict:
    return {
        "what_happened": (
            "We completed an account review as part of our standard onboarding process."
        ),
        "what_we_found": (
            "Our review identified some items that require further information before "
            "we can complete your application."
        ),
        "what_happens_next": (
            "A member of our compliance team will be in touch within 5 business days. "
            "You may be asked to provide additional documents."
        ),
        "contact_info": (
            f"If you have questions, please contact our compliance team and quote "
            f"reference number: {ref}."
        ),
    }