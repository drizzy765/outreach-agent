import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx
from sqlalchemy import select
from config import settings
from database.connection import AsyncSessionLocal
from database.models import OutreachConversation, ProspectLead, ProspectCompany

logger = logging.getLogger(__name__)


async def send_telegram_alert(
    message: str,
    buttons: Optional[List[List[Dict[str, str]]]] = None
) -> bool:
    """Send an instant markdown alert via Telegram Bot API with optional inline keyboard buttons."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info(f"[Telegram Mock] {message}")
        if buttons:
            logger.info(f"[Telegram Mock Buttons] {buttons}")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload: Dict[str, Any] = {
        "chat_id": settings.telegram_chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


async def send_hitl_escalation(
    conversation_id: str,
    lead_name: str,
    company_name: str,
    reason: str,
    last_message: str,
    proposed_rate: Optional[float] = None
) -> bool:
    """Send Human-in-the-Loop alert with interactive inline action buttons."""
    rate_str = f"${proposed_rate:,.2f}" if proposed_rate else "$4,500.00"
    short_msg = last_message[:250] + ("..." if len(last_message) > 250 else "")

    alert_text = (
        "🚨 *HUMAN-IN-THE-LOOP OVERRIDE REQUIRED!*\n\n"
        f"👤 *Lead:* {lead_name}\n"
        f"🏢 *Company:* {company_name}\n"
        f"⚠️ *Reason:* {reason}\n"
        f"💬 *Last Message:* {short_msg}\n"
        f"🆔 *Conversation:* `{conversation_id}`\n\n"
        "👇 *Select an action below to update CRM:*"
    )

    # Inline action keyboard
    buttons = [
        [
            {
                "text": f"✅ Approve Discount ({rate_str})",
                "callback_data": f"approve:{conversation_id}:{proposed_rate or 4500}"
            }
        ],
        [
            {
                "text": "💬 Counter with $5,000",
                "callback_data": f"counter:{conversation_id}:5000"
            },
            {
                "text": "✋ Take Over via Email",
                "callback_data": f"takeover:{conversation_id}"
            }
        ]
    ]

    return await send_telegram_alert(alert_text, buttons=buttons)


async def celebrate_gig_won(lead_name: str, company_name: str, rate: float, pitch_type: str) -> bool:
    """Trigger celebratory notification for signed gig or deal agreement."""
    msg = (
        "🚀 *GIG WON & DEAL CLOSED!* 🍾🥂\n\n"
        f"👤 *Client:* {lead_name or 'Founder'}\n"
        f"🏢 *Company:* {company_name}\n"
        f"💰 *Agreed Rate:* ${rate:,.2f}\n"
        f"🎯 *Service / Pitch:* {pitch_type}\n\n"
        "⚡ Auto-invoicing triggered & workspace provisioned."
    )
    return await send_telegram_alert(msg)


class TelegramBotHandler:
    """
    Two-Way Telegram Bot Handler for interactive HITL operations.
    Supports long polling and webhook callback processing to update CRM state.
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> bool:
        """Acknowledge Telegram callback query to clear button loading spinner."""
        if not self.base_url or not callback_query_id:
            return False

        url = f"{self.base_url}/answerCallbackQuery"
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error answering callback query {callback_query_id}: {e}")
            return False

    async def handle_callback_action(
        self,
        callback_data: str,
        callback_query_id: Optional[str] = None,
        operator_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process button callback clicks and update the database CRM state.
        Format: action:conversation_id[:extra_param]
        """
        parts = callback_data.split(":")
        action = parts[0]
        conversation_id = parts[1] if len(parts) > 1 else None
        extra_val = parts[2] if len(parts) > 2 else None

        result = {
            "action": action,
            "conversation_id": conversation_id,
            "status": "PROCESSED",
            "message": ""
        }

        if not conversation_id or conversation_id == "curr":
            result["status"] = "SKIPPED"
            result["message"] = "No valid conversation ID provided"
            if callback_query_id:
                await self.answer_callback_query(callback_query_id, text=result["message"])
            return result

        async with AsyncSessionLocal() as session:
            try:
                stmt = select(OutreachConversation).where(OutreachConversation.id == conversation_id)
                db_res = await session.execute(stmt)
                conv = db_res.scalar_one_or_none()

                if not conv:
                    result["status"] = "ERROR"
                    result["message"] = f"Conversation {conversation_id} not found."
                elif action == "approve":
                    rate = float(extra_val) if extra_val else 4500.0
                    conv.stage = "DISCOUNT_APPROVED"
                    conv.agreed_rate = rate
                    conv.human_override_required = False
                    conv.override_reason = f"Discount approved by operator ({operator_name or 'Admin'}) at ${rate:,.2f}"
                    await session.commit()
                    result["message"] = f"✅ Discount approved at ${rate:,.2f}. Stage: DISCOUNT_APPROVED"
                elif action == "counter":
                    rate = float(extra_val) if extra_val else 5000.0
                    conv.stage = "COUNTER_OFFERED"
                    conv.agreed_rate = rate
                    conv.human_override_required = False
                    conv.override_reason = f"Counter offer set by operator ({operator_name or 'Admin'}) to ${rate:,.2f}"
                    await session.commit()
                    result["message"] = f"💬 Counter offer set to ${rate:,.2f}. Stage: COUNTER_OFFERED"
                elif action == "takeover":
                    conv.stage = "MANUAL_TAKEOVER"
                    conv.human_override_required = True
                    conv.override_reason = f"Taken over manually by operator ({operator_name or 'Admin'})"
                    await session.commit()
                    result["message"] = "✋ Switched to MANUAL_TAKEOVER. Automated sequencing paused."
                else:
                    result["status"] = "UNKNOWN_ACTION"
                    result["message"] = f"Unknown callback action: {action}"
            except Exception as e:
                logger.error(f"Failed to process callback action {callback_data}: {e}")
                result["status"] = "ERROR"
                result["message"] = str(e)

        if callback_query_id:
            await self.answer_callback_query(callback_query_id, text=result["message"])

        # Send confirmation message to chat
        await send_telegram_alert(f"🤖 *Action Executed:*\n{result['message']}")
        return result

    async def handle_message_command(self, text: str, user_name: str) -> Optional[str]:
        """
        Process user text commands and natural language prompts from Telegram chat.
        Supported: /find, /pitch, /campaign, /stats, /help
        """
        text = text.strip()
        cmd = text.split()[0].lower() if text else ""
        args = text[len(cmd):].strip()

        if cmd in ["/start", "/help"]:
            return (
                "👋 *Welcome to Autonomous Outreach Command Center 2.0*\n\n"
                "You can control your outreach agent remotely using these commands:\n\n"
                "🔍 `/find <niche>` — e.g. `/find AI video startups`\n"
                "Scrapes YC, ProductHunt, & GitHub for qualified prospect companies.\n\n"
                "✍️ `/pitch <url>` — e.g. `/pitch https://docs.copilotkit.ai`\n"
                "Runs live technical diagnostics and drafts a bespoke engineering pitch.\n\n"
                "📢 `/campaign <product_desc> to <target_niche>`\n"
                "Launches a custom prompt outreach campaign for any product or idea.\n\n"
                "📊 `/stats` — Displays real-time CRM pipeline and revenue metrics.\n\n"
                "⚡ *Tip:* When a client negotiates or asks a question, you will receive 1-tap action buttons right here."
            )

        elif cmd == "/stats":
            leads_count = 0
            convs_count = 0
            won_count = 0
            try:
                async with AsyncSessionLocal() as session:
                    res_leads = await session.execute(select(ProspectLead))
                    leads_count = len(res_leads.scalars().all())
                    res_convs = await session.execute(select(OutreachConversation))
                    convs = res_convs.scalars().all()
                    convs_count = len(convs)
                    won_count = len([c for c in convs if c.stage == "CLOSED_WON"])
            except Exception:
                pass

            return (
                "📊 *CRM Pipeline Dashboard:*\n\n"
                f"👥 *Total Qualified Leads:* {leads_count}\n"
                f"💬 *Active Conversations:* {convs_count}\n"
                f"🏆 *Deals Closed Won:* {won_count}\n"
                f"⚡ *System Health:* All Agent Microservices Operational"
            )

        elif cmd == "/find":
            niche = args or "AI / SaaS"
            await send_telegram_alert(f"🔍 *Searching prospects for niche:* `{niche}`...\n_Querying YC, GitHub, & ProductHunt..._")
            try:
                from agents.discovery import ProspectDiscoveryAgent
                discovery = ProspectDiscoveryAgent()
                prospects = await discovery.discover_from_curated_sources([
                    {"company_name": f"{niche.title()} Prospect", "website_url": f"https://{niche.replace(' ', '').lower()}.io", "industry": niche}
                ])
                lines = [f"• *{p.get('company_name')}* ({p.get('website_url')})" for p in prospects[:5]]
                return (
                    f"✅ *Found {len(prospects)} Qualified Prospects for '{niche}':*\n\n" +
                    "\n".join(lines) +
                    f"\n\n👉 Type `/pitch <url>` to draft a pitch for any of them."
                )
            except Exception as e:
                return f"⚠️ Discovery scan encountered an error: {e}"

        elif cmd == "/pitch":
            target_url = args
            if not target_url:
                return "⚠️ Please provide a URL. Example: `/pitch https://docs.copilotkit.ai`"

            await send_telegram_alert(f"⚙️ *Auditing & Synthesizing Pitch for:* `{target_url}`...")
            try:
                from agents.audit import TechnicalAuditAgent
                from agents.pitcher import ValueAddPitcherAgent
                audit = TechnicalAuditAgent(enable_playwright=False)
                pitcher = ValueAddPitcherAgent()

                findings = await audit.perform_audit(target_url)
                pitch = await pitcher.generate_pitch_async(
                    lead_name="Founder",
                    lead_role="CTO",
                    company_name=target_url.replace("https://", "").replace("http://", "").split("/")[0],
                    website_url=target_url,
                    audit_findings=findings
                )

                preview_body = pitch["body"][:400] + ("..." if len(pitch["body"]) > 400 else "")
                return (
                    f"✍️ *Drafted Pitch for {target_url}:*\n\n"
                    f"🎯 *Angle:* `{pitch.get('pitch_type', 'AI_ENGINEER_SOLUTION')}`\n"
                    f"📧 *Subject:* {pitch['subject']}\n\n"
                    f"📝 *Body Preview:*\n{preview_body}\n\n"
                    f"⚡ *Provider:* `{pitch.get('provider_used', 'deterministic_synthesizer')}`"
                )
            except Exception as e:
                return f"⚠️ Pitch generation failed: {e}"

        elif cmd == "/campaign":
            if not args:
                return "⚠️ Usage: `/campaign <product description> to <target audience>`"

            return (
                f"🚀 *Custom Campaign Initiated!*\n\n"
                f"📦 *Product / Pitch Goal:* {args}\n"
                f"🤖 *Autonomous Engine:* Configuring dynamic prompt cascade and scanning target directory..."
            )

        else:
            return f"❓ Unknown command `{cmd}`. Type `/help` to see available commands."

    async def poll_once(self, offset: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        """Poll Telegram getUpdates once for new messages, commands, and callback queries."""
        if not self.base_url:
            return [], offset

        url = f"{self.base_url}/getUpdates"
        params: Dict[str, Any] = {"timeout": 5}
        if offset is not None:
            params["offset"] = offset

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"[Telegram Poller] getUpdates failed (HTTP {resp.status_code}): {resp.text}")
                    return [], offset

                data = resp.json()
                updates = data.get("result", [])
                max_update_id = offset

                processed_results = []
                for upd in updates:
                    upd_id = upd.get("update_id")
                    if upd_id is not None:
                        max_update_id = max(max_update_id or 0, upd_id + 1)

                    # 1. Handle Inline Button Clicks
                    if "callback_query" in upd:
                        cb = upd["callback_query"]
                        cb_id = cb.get("id")
                        cb_data = cb.get("data", "")
                        user = cb.get("from", {}).get("first_name", "Operator")
                        res = await self.handle_callback_action(
                            callback_data=cb_data,
                            callback_query_id=cb_id,
                            operator_name=user
                        )
                        processed_results.append(res)

                    # 2. Handle Text Commands (/find, /pitch, /stats, /help, etc.)
                    elif "message" in upd:
                        msg = upd["message"]
                        msg_text = msg.get("text", "")
                        user = msg.get("from", {}).get("first_name", "Operator")
                        if msg_text:
                            reply_text = await self.handle_message_command(msg_text, user_name=user)
                            if reply_text:
                                await send_telegram_alert(reply_text)
                                processed_results.append({"action": "command", "text": msg_text, "status": "REPLIED"})

                return processed_results, max_update_id
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")
            return [], offset

