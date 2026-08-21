import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)

async def send_telegram_alert(message: str) -> bool:
    """Send an instant markdown alert via Telegram Bot API."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info(f"[Telegram Mock] {message}")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False

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
