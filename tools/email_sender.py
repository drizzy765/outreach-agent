import smtplib
import random
import logging
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from datetime import datetime, date
from typing import Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)

class OutboundEmailSender:
    """
    Outbound SMTP email transmission engine with deliverability guardrails:
    - Secondary lookalike domain enforcement
    - Daily sending limits (15-25 emails/day)
    - Jitter delay calculation (180s - 600s)
    - Graceful dry-run preview mode when credentials are not configured
    """

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.secondary_domain = settings.outbound_secondary_domain
        self.daily_limit = settings.daily_email_limit
        self._sent_today_count = 0
        self._last_reset_date = date.today()

    def _check_and_reset_daily_limit(self) -> bool:
        """Enforce daily sending cap."""
        today = date.today()
        if today > self._last_reset_date:
            self._sent_today_count = 0
            self._last_reset_date = today
        return self._sent_today_count < self.daily_limit

    def calculate_jitter_delay_seconds(self, min_seconds: int = 180, max_seconds: int = 600) -> int:
        """Calculate randomized delay between sends to prevent ESP spam filtering."""
        return random.randint(min_seconds, max_seconds)

    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        body_text: str,
        conversation_id: Optional[str] = None,
        custom_from_name: str = "Technical Architecture Team"
    ) -> Dict[str, Any]:
        """
        Sends email via SMTP or records dry-run dispatch if credentials are not configured.
        """
        if not self._check_and_reset_daily_limit():
            return {
                "status": "DAILY_LIMIT_EXCEEDED",
                "message_id": None,
                "details": f"Exceeded daily sending cap of {self.daily_limit} emails."
            }

        sender_email = f"outreach@{self.secondary_domain}" if "@" not in (self.smtp_user or "") else self.smtp_user
        msg_id = make_msgid(domain=self.secondary_domain)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{custom_from_name} <{sender_email}>"
        msg["To"] = recipient_email
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = msg_id

        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        jitter = self.calculate_jitter_delay_seconds()

        # 1. Dry-run Mode (if SMTP host or user is missing)
        if not self.smtp_host or not self.smtp_user or not self.smtp_password:
            logger.info(f"[Outbound Email DRY-RUN] To: {recipient_email} | Subject: {subject} | Jitter: {jitter}s")
            self._sent_today_count += 1
            return {
                "status": "DRY_RUN_SENT",
                "message_id": msg_id,
                "sender": sender_email,
                "recipient": recipient_email,
                "jitter_delay_seconds": jitter,
                "daily_sent_count": self._sent_today_count,
                "details": "Outbound email formatted and logged in dry-run mode (SMTP credentials unset)."
            }

        # 2. Live SMTP Dispatch
        try:
            is_gmail = "gmail" in (self.smtp_host or "").lower()
            if self.smtp_port == 465 or is_gmail:
                try:
                    with smtplib.SMTP_SSL(self.smtp_host, 465, timeout=12) as server:
                        server.login(self.smtp_user, self.smtp_password)
                        server.send_message(msg)
                except Exception as ssl_err:
                    logger.debug(f"SMTP SSL 465 failed, trying STARTTLS {self.smtp_port}: {ssl_err}")
                    with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=12) as server:
                        server.ehlo()
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_password)
                        server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=12) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

            self._sent_today_count += 1
            logger.info(f"Outbound email sent to {recipient_email} (MsgID: {msg_id})")

            return {
                "status": "SENT",
                "message_id": msg_id,
                "sender": sender_email,
                "recipient": recipient_email,
                "jitter_delay_seconds": jitter,
                "daily_sent_count": self._sent_today_count,
                "details": "Successfully dispatched via authenticated SMTP."
            }
        except Exception as e:
            logger.error(f"SMTP send failed for {recipient_email}: {e}")
            return {
                "status": "FAILED",
                "message_id": msg_id,
                "sender": sender_email,
                "recipient": recipient_email,
                "details": str(e)
            }
