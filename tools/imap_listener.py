import imaplib
import email
from email.header import decode_header
import logging
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)

def _decode_str(header_value: Optional[str]) -> str:
    """Decode encoded MIME header strings safely."""
    if not header_value:
        return ""
    try:
        decoded_parts = decode_header(header_value)
    except Exception:
        return str(header_value)
    result = ""
    for text, encoding in decoded_parts:
        if isinstance(text, bytes):
            try:
                enc = encoding or "utf-8"
                result += text.decode(enc, errors="ignore")
            except (LookupError, UnicodeDecodeError):
                result += text.decode("utf-8", errors="ignore")
        else:
            result += str(text)
    return result

class InboundIMAPListener:
    """
    Inbound IMAP inbox monitor.
    Polls for new prospect replies, extracts message bodies, and correlates threads with CRM records.
    Supports live IMAP SSL polling and local mock reply injection.
    """

    def __init__(self):
        self.imap_host = settings.imap_host
        self.imap_port = settings.imap_port
        self.imap_user = settings.imap_user
        self.imap_password = settings.imap_password
        self._mock_inbox: List[Dict[str, Any]] = []

    def inject_mock_reply(
        self,
        sender: str,
        subject: str,
        body: str,
        in_reply_to: Optional[str] = None
    ) -> None:
        """Inject a test reply into the mock inbox for local simulation & testing."""
        self._mock_inbox.append({
            "sender": sender,
            "subject": subject,
            "body": body,
            "in_reply_to": in_reply_to,
            "source": "mock_inbox"
        })

    async def check_inbox(self) -> List[Dict[str, Any]]:
        """
        Polls IMAP inbox for unread replies or returns pending mock replies.
        """
        # 1. Return any injected mock replies
        if self._mock_inbox:
            replies = list(self._mock_inbox)
            self._mock_inbox.clear()
            return replies

        # 2. If IMAP credentials are not configured, return empty
        if not self.imap_host or not self.imap_user or not self.imap_password:
            logger.debug("IMAP credentials not configured. Returning empty inbox.")
            return []

        # 3. Live IMAP Polling
        messages: List[Dict[str, Any]] = []
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.imap_user, self.imap_password)
            mail.select("INBOX")

            status, search_data = mail.search(None, "UNSEEN")
            if status != "OK":
                mail.logout()
                return []

            mail_ids = search_data[0].split()
            for msg_id in mail_ids:
                res, data = mail.fetch(msg_id, "(RFC822)")
                if res != "OK":
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = _decode_str(msg.get("Subject"))
                sender = _decode_str(msg.get("From"))
                in_reply_to = _decode_str(msg.get("In-Reply-To"))

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body += payload.decode(errors="ignore")
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")

                messages.append({
                    "sender": sender,
                    "subject": subject,
                    "body": body.strip(),
                    "in_reply_to": in_reply_to,
                    "source": "imap_live"
                })

            mail.logout()
        except Exception as e:
            logger.error(f"IMAP poll error: {e}")

        return messages
