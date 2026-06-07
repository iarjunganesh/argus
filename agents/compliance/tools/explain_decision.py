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