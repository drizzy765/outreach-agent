from typing import TypedDict, List, Dict, Any, Optional

class OutreachState(TypedDict):
    # Pipeline Metadata
    target_url: str
    company_name: str
    company_id: Optional[str]
    industry: Optional[str]

    # Diagnostics & Audit
    audit_findings: Dict[str, Any]
    tech_stack: List[str]

    # Lead Enrichment
    leads: List[Dict[str, Any]]
    primary_lead_id: Optional[str]
    primary_lead_email: Optional[str]
    primary_lead_name: Optional[str]
    primary_lead_role: Optional[str]

    # Pitch & Sequence
    pitch_angle: str
    pitch_subject: str
    pitch_body: str
    conversation_id: Optional[str]

    # Reply & Negotiation
    incoming_reply: Optional[str]
    negotiation_stage: str # DRAFTED, SENT, REPLIED, NEGOTIATING, HITL_HANDOVER, CLOSED_WON, CLOSED_LOST
    negotiation_response: Optional[str]
    quoted_rate: float
    agreed_rate: Optional[float]
    human_override_required: bool
    override_reason: Optional[str]

    # Autonomous Outbound Dispatch
    email_dispatch_status: Optional[str] # SENT, DRY_RUN_SENT, SKIPPED, FAILED, DAILY_LIMIT_EXCEEDED
    email_message_id: Optional[str]
    is_worthy_prospect: bool
    auto_send: bool

    # Status
    errors: List[str]

