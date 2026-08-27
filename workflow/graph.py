import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from workflow.state import OutreachState
from agents.discovery import ProspectDiscoveryAgent
from agents.audit import TechnicalAuditAgent
from agents.enrichment import LeadEnrichmentAgent
from agents.pitcher import ValueAddPitcherAgent
from agents.negotiation import NegotiationEngineAgent
from agents.alerts import NotificationDispatcherAgent
from tools.email_sender import OutboundEmailSender
from database.connection import AsyncSessionLocal
from database.models import ProspectCompany, OutreachConversation, EmailSendLog
from sqlalchemy import select
from config import settings

logger = logging.getLogger(__name__)

# Initialize agent singletons
discovery_agent = ProspectDiscoveryAgent()
audit_agent = TechnicalAuditAgent()
enrichment_agent = LeadEnrichmentAgent()
pitcher_agent = ValueAddPitcherAgent()
negotiation_agent = NegotiationEngineAgent()
alerts_agent = NotificationDispatcherAgent()
email_sender = OutboundEmailSender()

# ----------------------------------------------------
# LangGraph Node Definitions
# ----------------------------------------------------

async def node_discovery(state: OutreachState) -> Dict[str, Any]:
    """Node 1: Prospect Discovery & Registration"""
    company_name = state.get("company_name", "Target SaaS")
    url = state.get("target_url")

    prospects = await discovery_agent.discover_from_curated_sources([
        {"company_name": company_name, "website_url": url, "industry": state.get("industry", "SaaS / AI")}
    ])
    saved = await discovery_agent.register_prospects(prospects)
    company_id = str(saved[0].id) if saved else None

    return {
        "company_id": company_id,
        "company_name": company_name,
        "target_url": url
    }

async def node_technical_audit(state: OutreachState) -> Dict[str, Any]:
    """Node 2: Technical Diagnostic & Performance Audit"""
    url = state["target_url"]
    findings = await audit_agent.perform_audit(url)
    
    # Update company audit in CRM if available
    if state.get("company_id"):
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ProspectCompany).where(ProspectCompany.id == state["company_id"])
                res = await session.execute(stmt)
                comp = res.scalar_one_or_none()
                if comp:
                    comp.audit_findings = findings
                    await session.commit()
        except Exception as e:
            logger.debug(f"Audit CRM update skipped: {e}")

    return {
        "audit_findings": findings,
        "pitch_angle": findings.get("recommended_pitch_angle", "CUSTOM_ML_AUDIT")
    }

async def node_lead_enrichment(state: OutreachState) -> Dict[str, Any]:
    """Node 3: Lead Enrichment & Email Extraction"""
    company_id = state.get("company_id")
    url = state["target_url"]

    leads = await enrichment_agent.enrich_company(company_id=company_id, website_url=url)
    
    primary = leads[0] if leads else {
        "id": None,
        "email": f"founder@{url.replace('https://','').replace('http://','').split('/')[0]}",
        "full_name": "Founder",
        "role": "Founder"
    }

    return {
        "leads": leads,
        "primary_lead_id": primary.get("id"),
        "primary_lead_email": primary.get("email"),
        "primary_lead_name": primary.get("full_name"),
        "primary_lead_role": primary.get("role")
    }

async def node_pitch_generator(state: OutreachState) -> Dict[str, Any]:
    """Node 4: Value-Add Pitch Generation"""
    pitch = await pitcher_agent.generate_pitch_async(
        lead_name=state.get("primary_lead_name", "Founder"),
        lead_role=state.get("primary_lead_role", "Founder"),
        company_name=state.get("company_name", "Company"),
        website_url=state.get("target_url", ""),
        audit_findings=state.get("audit_findings", {}),
        pitch_angle=state.get("pitch_angle")
    )

    conv_id = None
    if state.get("primary_lead_id"):
        try:
            async with AsyncSessionLocal() as session:
                conv = OutreachConversation(
                    lead_id=state["primary_lead_id"],
                    pitch_type=pitch["pitch_type"],
                    stage="DRAFTED",
                    last_message_content=pitch["body"],
                    minimum_acceptable_rate=150.00
                )
                session.add(conv)
                await session.commit()
                await session.refresh(conv)
                conv_id = str(conv.id)
        except Exception as e:
            logger.debug(f"Outreach conversation CRM save skipped: {e}")

    return {
        "pitch_subject": pitch["subject"],
        "pitch_body": pitch["body"],
        "pitch_angle": pitch["pitch_type"],
        "conversation_id": conv_id,
        "negotiation_stage": "DRAFTED"
    }

async def node_email_dispatcher(state: OutreachState) -> Dict[str, Any]:
    """Node 4.5: Autonomous Email Dispatch for Qualified/Worthy Prospects"""
    # If this run is handling an incoming reply, skip outbound send
    if state.get("incoming_reply"):
        return {
            "email_dispatch_status": "SKIPPED_REPLY_INCOMING",
            "is_worthy_prospect": True
        }

    recipient_email = state.get("primary_lead_email")
    subject = state.get("pitch_subject")
    body = state.get("pitch_body")
    conv_id = state.get("conversation_id")
    auto_send = state.get("auto_send", settings.auto_send_outreach)

    # Check if prospect is worthy / qualified
    is_worthy = bool(recipient_email and "@" in recipient_email and body and subject)

    if not is_worthy:
        logger.info(f"Prospect {state.get('company_name')} skipped from auto-pitch: missing lead email or pitch content.")
        return {
            "email_dispatch_status": "UNQUALIFIED",
            "is_worthy_prospect": False,
            "negotiation_stage": state.get("negotiation_stage", "DRAFTED")
        }

    if not auto_send:
        logger.info(f"Auto-send disabled. Pitch drafted for {recipient_email} ({state.get('company_name')}).")
        return {
            "email_dispatch_status": "SKIPPED_MANUAL_MODE",
            "is_worthy_prospect": True,
            "negotiation_stage": "DRAFTED"
        }

    # Dispatch outbound email
    sender_name = getattr(settings, "sender_name", "Technical Architecture Team")
    res = await email_sender.send_email(
        recipient_email=recipient_email,
        subject=subject,
        body_text=body,
        conversation_id=conv_id,
        custom_from_name=sender_name
    )

    status = res.get("status", "FAILED")
    msg_id = res.get("message_id")
    new_stage = "SENT" if status in ("SENT", "DRY_RUN_SENT") else "DRAFTED"

    # Update CRM record & record send log
    if conv_id:
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(OutreachConversation).where(OutreachConversation.id == conv_id)
                db_res = await session.execute(stmt)
                conv = db_res.scalar_one_or_none()
                if conv:
                    conv.stage = new_stage
                    if msg_id:
                        conv.email_thread_id = msg_id
                    
                    send_log = EmailSendLog(
                        conversation_id=conv.id,
                        sender_domain=email_sender.secondary_domain,
                        recipient_email=recipient_email,
                        subject=subject,
                        status=status
                    )
                    session.add(send_log)
                    await session.commit()
        except Exception as e:
            logger.debug(f"CRM email send log save skipped: {e}")

    logger.info(f"🚀 Autonomous outreach dispatched to {recipient_email} ({state.get('company_name')}) - Status: {status}")

    return {
        "email_dispatch_status": status,
        "email_message_id": msg_id,
        "negotiation_stage": new_stage,
        "is_worthy_prospect": True
    }

async def node_negotiation_handler(state: OutreachState) -> Dict[str, Any]:
    """Node 5: Conversational Reply & Bounded Negotiation"""
    incoming = state.get("incoming_reply")
    if not incoming:
        return {
            "negotiation_stage": state.get("negotiation_stage", "SENT"),
            "human_override_required": False
        }

    outcome = await negotiation_agent.process_reply_async(
        lead_name=state.get("primary_lead_name", "Founder"),
        company_name=state.get("company_name", "Company"),
        incoming_reply=incoming,
        current_quoted_rate=state.get("quoted_rate", 6500.0)
    )

    return {
        "negotiation_stage": outcome["stage"],
        "negotiation_response": outcome["response_text"],
        "agreed_rate": outcome.get("agreed_rate"),
        "human_override_required": outcome["human_override_required"],
        "override_reason": outcome.get("override_reason")
    }

async def node_alert_dispatcher(state: OutreachState) -> Dict[str, Any]:
    """Node 6: Deal Closer, Notifications & Celebrations (Silent on regular outbound drafts)"""
    conv_id = state.get("conversation_id")
    lead_id = state.get("primary_lead_id")
    company_id = state.get("company_id")
    stage = state.get("negotiation_stage", "DRAFTED")
    response_msg = state.get("negotiation_response") or state.get("pitch_body", "")

    # Only fire Telegram alerts if there is an active incoming reply, negotiation event, HITL, or won deal
    should_alert = (
        state.get("incoming_reply") is not None
        or stage in ("REPLIED", "NEGOTIATING", "COUNTER_OFFERED", "HITL_HANDOVER", "CLOSED_WON")
        or state.get("human_override_required", False)
        or getattr(settings, "alert_on_outbound_send", False)
    )

    if conv_id and lead_id and company_id and should_alert:
        await alerts_agent.dispatch_stage_update(
            conversation_id=conv_id,
            lead_id=lead_id,
            company_id=company_id,
            stage=stage,
            message_content=response_msg,
            agreed_rate=state.get("agreed_rate"),
            human_override_required=state.get("human_override_required", False),
            override_reason=state.get("override_reason")
        )

    return {"negotiation_stage": stage}

# ----------------------------------------------------
# LangGraph Workflow Construction
# ----------------------------------------------------

def create_outreach_graph() -> StateGraph:
    """Build LangGraph workflow connecting nodes 1-6 with deterministic state transitions."""
    workflow = StateGraph(OutreachState)

    # Add Nodes
    workflow.add_node("discovery", node_discovery)
    workflow.add_node("technical_audit", node_technical_audit)
    workflow.add_node("lead_enrichment", node_lead_enrichment)
    workflow.add_node("pitch_generator", node_pitch_generator)
    workflow.add_node("email_dispatcher", node_email_dispatcher)
    workflow.add_node("negotiation_handler", node_negotiation_handler)
    workflow.add_node("alert_dispatcher", node_alert_dispatcher)

    # Set Entry Point
    workflow.set_entry_point("discovery")

    # Connect Edges
    workflow.add_edge("discovery", "technical_audit")
    workflow.add_edge("technical_audit", "lead_enrichment")
    workflow.add_edge("lead_enrichment", "pitch_generator")
    workflow.add_edge("pitch_generator", "email_dispatcher")
    workflow.add_edge("email_dispatcher", "negotiation_handler")
    workflow.add_edge("negotiation_handler", "alert_dispatcher")
    workflow.add_edge("alert_dispatcher", END)

    return workflow.compile()

async def run_autonomous_outreach_pipeline(
    target_url: str,
    company_name: str,
    incoming_reply: str = None,
    auto_send: bool = True
) -> OutreachState:
    """Helper to execute graph synchronously."""
    app = create_outreach_graph()
    initial_state: OutreachState = {
        "target_url": target_url,
        "company_name": company_name,
        "company_id": None,
        "industry": "SaaS / Technology",
        "audit_findings": {},
        "tech_stack": [],
        "leads": [],
        "primary_lead_id": None,
        "primary_lead_email": None,
        "primary_lead_name": None,
        "primary_lead_role": None,
        "pitch_angle": "CUSTOM_ML_AUDIT",
        "pitch_subject": "",
        "pitch_body": "",
        "conversation_id": None,
        "incoming_reply": incoming_reply,
        "negotiation_stage": "DRAFTED",
        "negotiation_response": None,
        "quoted_rate": 6500.0,
        "agreed_rate": None,
        "human_override_required": False,
        "override_reason": None,
        "email_dispatch_status": None,
        "email_message_id": None,
        "is_worthy_prospect": False,
        "auto_send": auto_send,
        "errors": []
    }
    result = await app.ainvoke(initial_state)
    return result

