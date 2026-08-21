import re
import smtplib
import socket
import secrets
import logging
from typing import List, Dict, Optional, Tuple
import dns.resolver
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

def generate_email_permutations(first_name: str, last_name: str, domain: str) -> List[str]:
    """
    Generate standard corporate email permutations for a given first name, last name, and domain.
    """
    fn = re.sub(r'[^a-zA-Z]', '', first_name).lower()
    ln = re.sub(r'[^a-zA-Z]', '', last_name).lower() if last_name else ""
    d = domain.lower().strip()

    # Strip http://, https://, www., and paths
    d = re.sub(r'https?://', '', d).split('/')[0].replace('www.', '')

    permutations = []
    if fn and ln:
        f_initial = fn[0]
        l_initial = ln[0]
        permutations.extend([
            f"{fn}.{ln}@{d}",
            f"{fn}@{d}",
            f"{f_initial}{ln}@{d}",
            f"{fn}{ln}@{d}",
            f"{f_initial}.{ln}@{d}",
            f"{fn}_{ln}@{d}",
            f"{f_initial}_{ln}@{d}",
            f"{fn}{l_initial}@{d}",
            f"{ln}.{fn}@{d}",
        ])
    elif fn:
        permutations.extend([
            f"{fn}@{d}",
            f"founder@{d}",
            f"team@{d}",
            f"contact@{d}",
            f"hello@{d}"
        ])
    
    # Remove duplicates preserving order
    return list(dict.fromkeys(permutations))

class EmailVerifier:
    def __init__(self, timeout: int = 5, sender_email: str = "verify@outreach-engine.io"):
        self.timeout = timeout
        self.sender_email = sender_email
        self._mx_cache: Dict[str, Optional[str]] = {}
        self._catch_all_cache: Dict[str, bool] = {}

    def get_mx_record(self, domain: str) -> Optional[str]:
        """Resolve highest priority MX record for domain."""
        if domain in self._mx_cache:
            return self._mx_cache[domain]

        try:
            records = dns.resolver.resolve(domain, 'MX')
            sorted_records = sorted(records, key=lambda r: r.preference)
            best_mx = str(sorted_records[0].exchange).rstrip('.')
            self._mx_cache[domain] = best_mx
            return best_mx
        except Exception as e:
            logger.debug(f"MX lookup failed for {domain}: {e}")
            self._mx_cache[domain] = None
            return None

    def is_catch_all(self, domain: str, mx_host: str) -> bool:
        """Check if domain accepts emails to random non-existent mailboxes (Catch-All)."""
        if domain in self._catch_all_cache:
            return self._catch_all_cache[domain]

        random_mailbox = f"nonexistent_{secrets.token_hex(6)}@{domain}"
        code, _ = self._ping_smtp(mx_host, random_mailbox)
        # If random non-existent address is accepted with 250, domain is catch-all
        is_catch = (code == 250)
        self._catch_all_cache[domain] = is_catch
        return is_catch

    def _ping_smtp(self, mx_host: str, target_email: str) -> Tuple[int, str]:
        """Perform SMTP handshake up to RCPT TO without issuing DATA."""
        try:
            server = smtplib.SMTP(timeout=self.timeout)
            server.set_debuglevel(0)
            server.connect(mx_host, 25)
            server.helo("outreach-engine.io")
            server.mail(self.sender_email)
            code, message = server.rcpt(target_email)
            server.quit()
            return code, message.decode('utf-8', errors='ignore')
        except (socket.timeout, socket.error, smtplib.SMTPException) as e:
            return -1, str(e)

    def verify(self, email: str) -> Dict[str, any]:
        """
        Full verification pipeline:
        1. Syntax check
        2. DNS MX check
        3. Catch-all detection
        4. SMTP RCPT TO ping
        """
        try:
            valid = validate_email(email, check_deliverability=False)
            normalized_email = valid.normalized
            domain = normalized_email.split('@')[1]
        except EmailNotValidError as e:
            return {
                "email": email,
                "status": "INVALID_SYNTAX",
                "details": str(e)
            }

        mx_host = self.get_mx_record(domain)
        if not mx_host:
            return {
                "email": normalized_email,
                "status": "NO_MX_RECORDS",
                "details": f"No MX records found for domain {domain}"
            }

        is_catchall = self.is_catch_all(domain, mx_host)
        if is_catchall:
            return {
                "email": normalized_email,
                "status": "CATCH_ALL",
                "details": "Domain has catch-all enabled; specific mailbox existence cannot be guaranteed via SMTP ping"
            }

        code, msg = self._ping_smtp(mx_host, normalized_email)
        if code == 250:
            status = "SMTP_VERIFIED"
        elif code in [550, 551, 552, 553, 554]:
            status = "MAILBOX_NOT_FOUND"
        else:
            status = "UNVERIFIED"

        return {
            "email": normalized_email,
            "status": status,
            "smtp_code": code,
            "details": msg
        }

async def verify_email_address(email: str) -> Dict[str, any]:
    verifier = EmailVerifier()
    return verifier.verify(email)
