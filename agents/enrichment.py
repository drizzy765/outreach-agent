import logging
from typing import Dict, Any, List, Optional
from tools.web_crawler import DOMDeepCrawler
from tools.email_verifier import EmailVerifier, generate_email_permutations
from database.connection import AsyncSessionLocal
from database.models import ProspectCompany, ProspectLead
from sqlalchemy import select

logger = logging.getLogger(__name__)

class LeadEnrichmentAgent:
    """
    Agent 3: Lead Enrichment & Email Extraction Engine
    Extracts, reconstructs, and verifies founder/CTO emails without commercial SaaS fees:
    1. Deep DOM Crawling for mailto links, executive profiles, and JSON-LD schema
    2. Corporate email permutation generation ({first}.{last}, {first}, {f}{last}, etc.)
    3. DNS MX & Catch-All detection
    4. Safe SMTP RFC 5321 deliverability handshake
    """

    def __init__(self):
        self.crawler = DOMDeepCrawler()
        self.verifier = EmailVerifier()

    async def enrich_company(self, company_id: Optional[str], website_url: str) -> List[Dict[str, Any]]:
        """Crawl website, extract leadership, generate permutations, and verify emails."""
        crawl_data = await self.crawler.crawl_site(website_url)
        domain = crawl_data["domain"]
        discovered_leads: List[Dict[str, Any]] = []
        seen_emails = set()

        # 1. Process executive names found on leadership/about pages or structured schema
        for exec_info in crawl_data["executives"]:
            name = exec_info["name"]
            parts = name.split()
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

            permutations = generate_email_permutations(first_name, last_name, domain)
            best_email = None
            best_status = "UNVERIFIED"

            for candidate in permutations:
                ver_res = self.verifier.verify(candidate)
                if ver_res["status"] == "SMTP_VERIFIED":
                    best_email = candidate
                    best_status = "SMTP_VERIFIED"
                    break
                elif ver_res["status"] in ["CATCH_ALL", "PORT_25_BLOCKED"] and not best_email:
                    best_email = candidate
                    best_status = ver_res["status"]

            if not best_email and permutations:
                best_email = permutations[0]

            if best_email and best_email not in seen_emails:
                seen_emails.add(best_email)
                discovered_leads.append({
                    "company_id": company_id,
                    "full_name": name,
                    "role": exec_info.get("role", "Executive / Founder"),
                    "email": best_email,
                    "verification_status": best_status
                })

        # 2. Process directly found mailto: and page emails
        for direct_email in crawl_data["emails"]:
            if direct_email not in seen_emails:
                seen_emails.add(direct_email)
                ver_res = self.verifier.verify(direct_email)
                name_prefix = direct_email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                discovered_leads.append({
                    "company_id": company_id,
                    "full_name": name_prefix if len(name_prefix.split()) > 1 else f"Lead ({name_prefix})",
                    "role": "Contact / Team",
                    "email": direct_email,
                    "verification_status": ver_res["status"]
                })

        # 3. Fallback if no leads found at all
        if not discovered_leads:
            fallback_email = f"founder@{domain}"
            ver_res = self.verifier.verify(fallback_email)
            discovered_leads.append({
                "company_id": company_id,
                "full_name": "Founder",
                "role": "Founder / CEO",
                "email": fallback_email,
                "verification_status": ver_res["status"]
            })

        # 4. Save/update to database if company_id is provided
        saved_leads: List[Dict[str, Any]] = []
        if company_id:
            async with AsyncSessionLocal() as session:
                for lead in discovered_leads:
                    stmt = select(ProspectLead).where(ProspectLead.email == lead["email"])
                    res = await session.execute(stmt)
                    existing = res.scalar_one_or_none()

                    if not existing:
                        new_lead = ProspectLead(
                            company_id=company_id,
                            full_name=lead["full_name"],
                            role=lead["role"],
                            email=lead["email"],
                            verification_status=lead["verification_status"]
                        )
                        session.add(new_lead)
                        await session.commit()
                        await session.refresh(new_lead)
                        saved_leads.append({
                            "id": str(new_lead.id),
                            "company_id": str(new_lead.company_id),
                            "full_name": new_lead.full_name,
                            "role": new_lead.role,
                            "email": new_lead.email,
                            "verification_status": new_lead.verification_status
                        })
                    else:
                        saved_leads.append({
                            "id": str(existing.id),
                            "company_id": str(existing.company_id),
                            "full_name": existing.full_name,
                            "role": existing.role,
                            "email": existing.email,
                            "verification_status": existing.verification_status
                        })
        else:
            saved_leads = discovered_leads

        return saved_leads
