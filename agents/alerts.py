import logging
from typing import Dict, Any
from database.connection import AsyncSessionLocal
from database.models import OutreachConversation, ProspectLead, ProspectCompany
from tools.telegram_bot import send_telegram_alert, celebrate_gig_won
from sqlalchemy import select

logger = logging.getLogger(__name__)

class NotificationDispatcherAgent:
    """
    Agent 6: Notification & CRM Celebration Dispatcher
    Maintains pipeline states in PostgreSQL and dispatches instant push notifications:
    - Telegram / Webhook Alerts
    - Deal Closer & "Gig Won" Confetti Celebration
    - Human-in-the-Loop Handover Escalation
    """

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
        
        async with AsyncSessionLocal() as session:
            # Fetch company and lead names
            lead_res = await session.execute(select(ProspectLead).where(ProspectLead.id == lead_id))
            lead = lead_res.scalar_one_or_none()

            comp_res = await session.execute(select(ProspectCompany).where(ProspectCompany.id == company_id))
            company = comp_res.scalar_one_or_none()

            lead_name = lead.full_name if lead else "Lead"
            company_name = company.company_name if company else "Company"

            # Update conversation record
            conv_res = await session.execute(select(OutreachConversation).where(OutreachConversation.id == conversation_id))
            conv = conv_res.scalar_one_or_none()

            if conv:
                conv.stage = stage
                conv.last_message_content = message_content
                conv.agreed_rate = agreed_rate
                conv.human_override_required = human_override_required
                conv.override_reason = override_reason
                await session.commit()

        # Fire alerts
        if stage == "CLOSED_WON":
            await celebrate_gig_won(
                lead_name=lead_name,
                company_name=company_name,
                rate=agreed_rate or 5000.0,
                pitch_type="Custom Vector Search & Voice AI"
            )
        elif stage == "HITL_HANDOVER" or human_override_required:
            alert_text = (
                "🚨 *HUMAN-IN-THE-LOOP OVERRIDE REQUIRED!*\n\n"
                f"👤 *Lead:* {lead_name}\n"
                f"🏢 *Company:* {company_name}\n"
                f"⚠️ *Reason:* {override_reason}\n"
                f"💬 *Last Message:* {message_content[:200]}..."
            )
            await send_telegram_alert(alert_text)
        elif stage == "REPLIED" or stage == "NEGOTIATING":
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
            "status": "DISPATCHED"
        }
