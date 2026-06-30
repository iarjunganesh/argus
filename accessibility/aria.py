"""
Standardized ARIA label strings for the ARGUS UI.

Centralizing these means screen-reader copy can be reviewed and updated
in one place without touching rendering logic.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ARIALabels:
    # Report header
    report_region: str = "ARGUS risk assessment report"
    decision_card: str = "Executive risk decision summary"
    risk_tier_value: str = "Overall risk tier"
    risk_score_value: str = "Overall risk score out of 100"
    confidence_value: str = "Assessment confidence percentage"

    # Agent timeline
    timeline_region: str = "Agent investigation timeline"
    agent_status_prefix: str = "Agent status:"

    # Dimension table
    dimensions_region: str = "Risk dimension breakdown table"
    dimension_score_suffix: str = "risk score"
    dimension_bar_suffix: str = "risk level bar"

    # Audit trace
    audit_region: str = "Audit trace and tool call log"

    # Live region for async updates
    live_region_label: str = "Assessment progress"
    live_region_status_idle: str = "Awaiting assessment submission."
    live_region_status_running: str = "Assessment in progress. Agents are running."
    live_region_status_done: str = "Assessment complete. Report is ready."
    live_region_status_error: str = "Assessment failed. See error details below."

    # Form
    entity_name_label: str = "Entity name to assess"
    entity_type_label: str = "Entity type: individual or corporate"
    jurisdiction_label: str = "Jurisdiction ISO code, for example DE for Germany"
    submit_button: str = "Run KYC assessment"

    # Explain Mode
    explain_toggle: str = "Switch to plain language report"
    analyst_toggle: str = "Switch to analyst report"


LABELS = ARIALabels()
