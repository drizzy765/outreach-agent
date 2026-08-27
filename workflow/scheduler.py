import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select

from config import settings
from database.connection import AsyncSessionLocal, init_db
from database.models import OutreachConversation, ProspectLead, ProspectCompany
from tools.imap_listener import InboundIMAPListener
from tools.email_sender import OutboundEmailSender
from tools.telegram_bot import TelegramBotHandler, send_telegram_alert
from agents.discovery import ProspectDiscoveryAgent
from agents.negotiation import NegotiationEngineAgent
from agents.alerts import NotificationDispatcherAgent

logger = logging.getLogger(__name__)

class AutonomousOutreachScheduler:
    """
    Background Task Scheduler Daemon.
    Manages automated recurring jobs:
    1. Periodic IMAP Inbox Polling & Reply Handling
    2. Multi-source Prospect Discovery
    3. Automated Follow-Up Sequencing (3-day bump)
    4. Two-Way Telegram HITL Interaction Polling
    """

    def __init__(self):
        self.imap_listener = InboundIMAPListener()
        self.email_sender = OutboundEmailSender()
        self.telegram_handler = TelegramBotHandler()
        self.discovery_agent = ProspectDiscoveryAgent()
        self.negotiation_agent = NegotiationEngineAgent()
        self.alerts_agent = NotificationDispatcherAgent()
        self.is_running = False
        self._telegram_offset = None

    async def check_inbound_replies_job(self) -> List[Dict[str, Any]]:
        """Poll IMAP mailbox for prospect replies and advance negotiation / HITL."""
        logger.info("[Scheduler] Running Inbound Reply Monitoring Job...")
        replies = await self.imap_listener.check_inbox()
        results = []

        for msg in replies:
            sender = msg.get("sender", "")
            body = msg.get("body", "")
            thread_id = msg.get("thread_id", "")
            logger.info(f"[Scheduler] Processing incoming reply from {sender}...")

            # Match sender or thread to CRM lead and conversation
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(OutreachConversation, ProspectLead, ProspectCompany)
                    .join(ProspectLead, OutreachConversation.lead_id == ProspectLead.id)
                    .join(ProspectCompany, ProspectLead.company_id == ProspectCompany.id)
                    .where(
                        (ProspectLead.email == sender) |
                        (OutreachConversation.email_thread_id == thread_id)
                    )
                    .order_by(OutreachConversation.updated_at.desc())
                )
                res = await session.execute(stmt)
                match = res.first()

                if match:
                    conv, lead, company = match
                    conv_id = str(conv.id)
                    lead_id = str(lead.id)
                    comp_id = str(company.id)
                    lead_name = lead.full_name or "Founder"
                    comp_name = company.company_name or "Company"
                else:
                    conv_id = None
                    lead_id = None
                    comp_id = None
                    lead_name = sender.split("@")[0]
                    comp_name = "Prospect"

            # Run negotiation agent
            outcome = await self.negotiation_agent.process_reply_async(
                lead_name=lead_name,
                company_name=comp_name,
                incoming_reply=body,
                current_quoted_rate=6500.0
            )

            # Dispatch alerts & database updates
            if conv_id and lead_id and comp_id:
                dispatch_res = await self.alerts_agent.dispatch_stage_update(
                    conversation_id=conv_id,
                    lead_id=lead_id,
                    company_id=comp_id,
                    stage=outcome["stage"],
                    message_content=outcome.get("response_text", body),
                    agreed_rate=outcome.get("agreed_rate"),
                    human_override_required=outcome.get("human_override_required", False),
                    override_reason=outcome.get("override_reason")
                )
                results.append(dispatch_res)
            else:
                results.append(outcome)

        return results

    async def run_pending_outreach_job(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Scan CRM for registered companies without sent outreach and autonomously audit, pitch, and dispatch emails."""
        logger.info(f"[Scheduler] Running Autonomous Pitching on Pending Prospects (Limit: {limit})...")
        from workflow.graph import run_autonomous_outreach_pipeline

        dispatched = []
        async with AsyncSessionLocal() as session:
            try:
                # Find companies that have no conversations in SENT, REPLIED, or CLOSED stages
                stmt = select(ProspectCompany).order_by(ProspectCompany.discovered_at.desc()).limit(limit * 3)
                res = await session.execute(stmt)
                companies = res.scalars().all()

                for comp in companies:
                    if len(dispatched) >= limit:
                        break

                    # Check if already pitched
                    conv_stmt = (
                        select(OutreachConversation)
                        .join(ProspectLead, OutreachConversation.lead_id == ProspectLead.id)
                        .where(
                            ProspectLead.company_id == comp.id,
                            OutreachConversation.stage.in_(["SENT", "REPLIED", "NEGOTIATING", "COUNTER_OFFERED", "CLOSED_WON", "FOLLOWED_UP"])
                        )
                    )
                    conv_res = await session.execute(conv_stmt)
                    existing_conv = conv_res.first()

                    if existing_conv:
                        continue

                    logger.info(f"[Scheduler] Autonomously executing pipeline for {comp.company_name} ({comp.website_url})...")
                    result = await run_autonomous_outreach_pipeline(
                        target_url=comp.website_url,
                        company_name=comp.company_name,
                        auto_send=settings.auto_send_outreach
                    )

                    dispatched.append({
                        "company_id": str(comp.id),
                        "company_name": comp.company_name,
                        "website_url": comp.website_url,
                        "lead_email": result.get("primary_lead_email"),
                        "dispatch_status": result.get("email_dispatch_status"),
                        "stage": result.get("negotiation_stage")
                    })

                    # Small polite async delay between company dispatches
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"[Scheduler] Error running pending outreach job: {e}")

        logger.info(f"[Scheduler] Autonomous outreach completed: dispatched {len(dispatched)} emails.")
        return dispatched

    async def run_discovery_job(self, limit_per_source: int = 5, auto_pitch: bool = True) -> List[Dict[str, Any]]:
        """Execute scheduled multi-source prospect discovery and immediately pitch worthy candidates."""
        logger.info(f"[Scheduler] Running Multi-Source Discovery Job (Limit: {limit_per_source})...")
        prospects = await self.discovery_agent.discover_multi_source(limit_per_source=limit_per_source)
        if prospects:
            saved = await self.discovery_agent.register_prospects(prospects)
            logger.info(f"[Scheduler] Registered {len(saved)} new prospects to CRM.")

            # Autonomously audit, pitch, and dispatch to top worthy candidates
            dispatched = []
            if auto_pitch and settings.auto_send_outreach:
                dispatched = await self.run_pending_outreach_job(limit=settings.max_auto_pitches_per_discovery_cycle)

            if getattr(settings, "alert_on_outbound_send", False):
                await send_telegram_alert(
                    f"🔍 *Scheduled Discovery & Outreach Completed:*\n"
                    f"• Found & registered *{len(saved)}* new companies to CRM.\n"
                    f"• Autonomously pitched & dispatched outreach to *{len(dispatched)}* qualified leads."
                )
            return prospects
        return []

    async def run_followup_sequencing_job(self, days_threshold: int = 3) -> List[Dict[str, Any]]:
        """Scan for stale unreplied pitches and schedule follow-up sequence bump."""
        logger.info(f"[Scheduler] Checking for outreach needing follow-up (Threshold: {days_threshold} days)...")
        cutoff = datetime.utcnow() - timedelta(days=days_threshold)
        followups_triggered = []

        async with AsyncSessionLocal() as session:
            stmt = (
                select(OutreachConversation, ProspectLead, ProspectCompany)
                .join(ProspectLead, OutreachConversation.lead_id == ProspectLead.id)
                .join(ProspectCompany, ProspectLead.company_id == ProspectCompany.id)
                .where(
                    OutreachConversation.stage == "SENT",
                    OutreachConversation.updated_at <= cutoff
                )
            )
            res = await session.execute(stmt)
            stale_convs = res.all()

            for conv, lead, company in stale_convs:
                lead_name = lead.full_name or "Founder"
                comp_name = company.company_name or "your team"
                bump_subject = f"Quick follow-up — AI architecture for {comp_name}"
                bump_body = (
                    f"Hi {lead_name},\n\n"
                    f"Following up on my previous note regarding the technical diagnostic for {comp_name}. "
                    f"Wanted to see if you had 5 minutes this week to review the vector search latency benchmarks.\n\n"
                    "Best,\nAI Engineering Team"
                )

                # Send outbound follow-up email
                send_res = await self.email_sender.send_email(
                    recipient_email=lead.email,
                    subject=bump_subject,
                    body_text=bump_body,
                    conversation_id=str(conv.id)
                )

                # Update conversation stage to FOLLOWED_UP
                conv.stage = "FOLLOWED_UP"
                conv.last_message_content = bump_body
                conv.updated_at = datetime.utcnow()
                await session.commit()

                followups_triggered.append({
                    "conversation_id": str(conv.id),
                    "lead_email": lead.email,
                    "company": comp_name,
                    "status": "FOLLOWED_UP",
                    "delivery_status": send_res.get("status")
                })

                logger.info(f"[Scheduler] Follow-up bump dispatched for {lead.email} ({comp_name}) - Status: {send_res.get('status')}")

        if followups_triggered and getattr(settings, "alert_on_outbound_send", False):
            await send_telegram_alert(
                f"📬 *Follow-up Sequence Triggered:*\nBumped *{len(followups_triggered)}* stale prospect conversations."
            )

        return followups_triggered



    async def poll_telegram_step(self) -> List[Dict[str, Any]]:
        """Execute a single polling step for Telegram bot callback queries."""
        results, next_offset = await self.telegram_handler.poll_once(self._telegram_offset)
        if next_offset is not None:
            self._telegram_offset = next_offset
        return results

    async def start_daemon(
        self,
        inbox_interval_minutes: int = 15,
        discovery_interval_hours: int = 24,
        followup_interval_hours: int = 12
    ):
        """Run the scheduler daemon continuously in an asynchronous event loop."""
        self.is_running = True
        try:
            await init_db()
        except Exception as e:
            logger.warning(f"Database initialization warning (proceeding with fallback): {e}")

        # Start lightweight cloud health-check HTTP server if PORT is set (Render / Cloud deployment)
        import os
        port_env = os.environ.get("PORT")
        if port_env:
            try:
                port = int(port_env)
                async def handle_health_check(reader, writer):
                    await reader.readline()
                    response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK"
                    writer.write(response)
                    await writer.drain()
                    writer.close()
                await asyncio.start_server(handle_health_check, "0.0.0.0", port)
                logger.info(f"🚀 Cloud Health check HTTP server active on 0.0.0.0:{port}")
            except Exception as e:
                logger.debug(f"Cloud health server init skipped: {e}")

        logger.info("🚀 Autonomous Outreach Scheduler Daemon started.")

        last_inbox_check = datetime.min
        last_discovery_run = datetime.min
        last_followup_run = datetime.min

        inbox_delta = timedelta(minutes=inbox_interval_minutes)
        discovery_delta = timedelta(hours=discovery_interval_hours)
        followup_delta = timedelta(hours=followup_interval_hours)

        while self.is_running:
            now = datetime.utcnow()

            # 1. Telegram Polling (every loop cycle ~2s)
            try:
                await self.poll_telegram_step()
            except Exception as e:
                logger.error(f"[Scheduler] Telegram poll error: {e}")

            # 2. Inbound IMAP Check
            if now - last_inbox_check >= inbox_delta:
                try:
                    await self.check_inbound_replies_job()
                    last_inbox_check = now
                except Exception as e:
                    logger.error(f"[Scheduler] Inbound check error: {e}")

            # 3. Follow-up Sequencing
            if now - last_followup_run >= followup_delta:
                try:
                    await self.run_followup_sequencing_job()
                    last_followup_run = now
                except Exception as e:
                    logger.error(f"[Scheduler] Follow-up job error: {e}")

            # 4. Multi-Source Discovery
            if now - last_discovery_run >= discovery_delta:
                try:
                    await self.run_discovery_job(limit_per_source=5)
                    last_discovery_run = now
                except Exception as e:
                    logger.error(f"[Scheduler] Discovery job error: {e}")

            await asyncio.sleep(2.0)

    def stop(self):
        """Signal daemon loop to stop."""
        self.is_running = False
        logger.info("Autonomous Outreach Scheduler stopped.")
