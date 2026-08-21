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
from database.connection import AsyncSessionLocal
from database.models import ProspectCompany, OutreachConversation
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Initialize agent singletons
discovery_agent = ProspectDiscoveryAgent()
audit_agent = TechnicalAuditAgent()
enrichment_agent = LeadEnrichmentAgent()
pitcher_agent = ValueAddPitcherAgent()
negotiation_agent = NegotiationEngineAgent()
alerts_agent = NotificationDispatcherAgent()

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
    
    # Update company audit in CRM
    if state.get("company_id"):
        async with AsyncSessionLocal() as session:
            stmt = select(ProspectCompany).where(ProspectCompany.id == state["company_id"])
            res = await session.execute(stmt)
            comp = res.scalar_one_or_none()
            if comp:
                comp.audit_findings = findings
                await session.commit()

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
    pitch = pitcher_agent.generate_pitch(
        lead_name=state.get("primary_lead_name", "Founder"),
        lead_role=state.get("primary_lead_role", "Founder"),
        company_name=state.get("company_name", "Company"),
        website_url=state.get("target_url", ""),
        audit_findings=state.get("audit_findings", {}),
        pitch_angle=state.get("pitch_angle")
    )

    conv_id = None
    if state.get("primary_lead_id"):
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

    return {
        "pitch_subject": pitch["subject"],
        "pitch_body": pitch["body"],
        "pitch_angle": pitch["pitch_type"],
        "conversation_id": conv_id,
        "negotiation_stage": "DRAFTED"
    }

async def node_negotiation_handler(state: OutreachState) -> Dict[str, Any]:
    """Node 5: Conversational Reply & Bounded Negotiation"""
    incoming = state.get("incoming_reply")
    if not incoming:
        return {
            "negotiation_stage": state.get("negotiation_stage", "SENT"),
            "human_override_required": False
        }

    outcome = negotiation_agent.process_reply(
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
    """Node 6: Deal Closer, Notifications & Celebrations"""
    conv_id = state.get("conversation_id")
    lead_id = state.get("primary_lead_id")
    company_id = state.get("company_id")
    stage = state.get("negotiation_stage", "DRAFTED")
    response_msg = state.get("negotiation_response") or state.get("pitch_body", "")

    if conv_id and lead_id and company_id:
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
    workflow.add_node("negotiation_handler", node_negotiation_handler)
    workflow.add_node("alert_dispatcher", node_alert_dispatcher)

    # Set Entry Point
    workflow.set_entry_point("discovery")

    # Connect Edges
    workflow.add_edge("discovery", "technical_audit")
    workflow.add_edge("technical_audit", "lead_enrichment")
    workflow.add_edge("lead_enrichment", "pitch_generator")
    workflow.add_edge("pitch_generator", "negotiation_handler")
    workflow.add_edge("negotiation_handler", "alert_dispatcher")
    workflow.add_edge("alert_dispatcher", END)

    return workflow.compile()

async def run_autonomous_outreach_pipeline(target_url: str, company_name: str, incoming_reply: str = None) -> OutreachState:
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
        "errors": []
    }
    result = await app.ainvoke(initial_state)
    return result
