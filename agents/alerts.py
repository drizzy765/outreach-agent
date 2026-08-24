import logging
from typing import Dict, Any, Optional
import httpx
from database.connection import AsyncSessionLocal
from database.models import OutreachConversation, ProspectLead, ProspectCompany
from tools.telegram_bot import send_telegram_alert, celebrate_gig_won, send_hitl_escalation
from config import settings
from sqlalchemy import select

logger = logging.getLogger(__name__)

class NotificationDispatcherAgent:
    """
    Agent 6: Notification & CRM Celebration Dispatcher
    Maintains pipeline states in PostgreSQL and dispatches instant push notifications:
    - Interactive Telegram HITL Action Alerts with Inline Buttons
    - Deal Closer & "Gig Won" Confetti Celebration
    - Automated Invoicing Webhook Dispatch (Stripe / InvoiceNinja / QuickBooks)
    - Human-in-the-Loop Handover Escalation
    """

    async def dispatch_auto_invoicing(
        self,
        lead_name: str,
        lead_email: str,
        company_name: str,
        rate: float,
        pitch_type: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Dispatch automated invoice / retainer generation via Stripe, InvoiceNinja, or Webhook.
        Calculates 50% upfront milestone deposit.
        """
        upfront_deposit = round(rate * 0.5, 2)
        invoice_payload = {
            "event": "invoice.create",
            "source": "autonomous_outreach_engine",
            "conversation_id": conversation_id,
            "customer": {
                "name": lead_name,
                "email": lead_email,
                "company": company_name
            },
            "invoice_details": {
                "currency": "USD",
                "total_agreed_rate": rate,
                "milestone_deposit_due": upfront_deposit,
                "payment_terms": "50% upfront deposit upon contract signing",
                "line_items": [
                    {
                        "description": f"AI & Engineering Architecture Implementation: {pitch_type} (50% Upfront Milestone)",
                        "amount": upfront_deposit,
                        "quantity": 1
                    }
                ]
            }
        }

        if settings.invoicing_webhook_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(settings.invoicing_webhook_url, json=invoice_payload)
                    logger.info(f"Auto-invoicing webhook dispatched (Status: {resp.status_code})")
                    return {
                        "status": "DISPATCHED",
                        "status_code": resp.status_code,
                        "deposit_amount": upfront_deposit
                    }
            except Exception as e:
                logger.error(f"Failed to post auto-invoicing webhook: {e}")
                return {"status": "ERROR", "error": str(e)}
        else:
            logger.info(f"[Invoicing Mock Dispatch] Generated invoice payload for {company_name} - ${upfront_deposit:,.2f} deposit due.")
            return {
                "status": "MOCK_DISPATCHED",
                "deposit_amount": upfront_deposit,
                "payload": invoice_payload
            }

    async def dispatch_stage_update(
        self,
        conversation_id: str,
        lead_id: str,
        company_id: str,
        stage: str,
        message_content: str,
        agreed_rate: float = None,
        human_override_required: bool = False,
        override_reason: str = None
    ) -> Dict[str, Any]:
        """Update database and fire immediate alerts based on state transition."""
        
        lead_name = "Lead"
        lead_email = "founder@company.com"
        company_name = "Company"
        pitch_type = "Custom Vector Search & Voice AI"

        async with AsyncSessionLocal() as session:
            # Fetch company and lead names
            if lead_id:
                lead_res = await session.execute(select(ProspectLead).where(ProspectLead.id == lead_id))
                lead = lead_res.scalar_one_or_none()
                if lead:
                    lead_name = lead.full_name or "Lead"
                    lead_email = lead.email or "founder@company.com"

            if company_id:
                comp_res = await session.execute(select(ProspectCompany).where(ProspectCompany.id == company_id))
                company = comp_res.scalar_one_or_none()
                if company:
                    company_name = company.company_name or "Company"

            # Update conversation record
            if conversation_id:
                conv_res = await session.execute(select(OutreachConversation).where(OutreachConversation.id == conversation_id))
                conv = conv_res.scalar_one_or_none()

                if conv:
                    conv.stage = stage
                    conv.last_message_content = message_content
                    if agreed_rate is not None:
                        conv.agreed_rate = agreed_rate
                    conv.human_override_required = human_override_required
                    conv.override_reason = override_reason
                    if conv.pitch_type:
                        pitch_type = conv.pitch_type
                    await session.commit()

        # Fire alerts
        invoicing_result = None
        if stage == "CLOSED_WON":
            rate_val = agreed_rate or 5000.0
            await celebrate_gig_won(
                lead_name=lead_name,
                company_name=company_name,
                rate=rate_val,
                pitch_type=pitch_type
            )
            # Dispatch auto-invoicing trigger
            invoicing_result = await self.dispatch_auto_invoicing(
                lead_name=lead_name,
                lead_email=lead_email,
                company_name=company_name,
                rate=rate_val,
                pitch_type=pitch_type,
                conversation_id=conversation_id
            )
        elif stage == "HITL_HANDOVER" or human_override_required:
            await send_hitl_escalation(
                conversation_id=conversation_id,
                lead_name=lead_name,
                company_name=company_name,
                reason=override_reason or "Negotiation threshold breached",
                last_message=message_content,
                proposed_rate=agreed_rate
            )
        elif stage in ("REPLIED", "NEGOTIATING", "COUNTER_OFFERED"):
            alert_text = (
                "🔥 *PROSPECT ENGAGED & REPLIED!*\n\n"
                f"👤 *Lead:* {lead_name}\n"
                f"🏢 *Company:* {company_name}\n"
                f"📊 *Stage:* {stage}\n"
                f"💬 *Snippet:* {message_content[:150]}..."
            )
            await send_telegram_alert(alert_text)

        return {
            "conversation_id": conversation_id,
            "stage": stage,
            "status": "DISPATCHED",
            "invoicing": invoicing_result
        }

