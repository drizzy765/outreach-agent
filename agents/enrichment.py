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
    Extracts, reconstructs, and verifies founder/CTO emails without expensive SaaS tools:
    1. Deep DOM Crawling for mailto links & executive names
    2. OSINT permutation generation ({first}.{last}, {first}@{domain}, etc.)
    3. DNS MX & Catch-all check
    4. SMTP deliverability verification (port 25 ping without sending)
    """

    def __init__(self):
        self.crawler = DOMDeepCrawler()
        self.verifier = EmailVerifier()

    async def enrich_company(self, company_id: str, website_url: str) -> List[Dict[str, Any]]:
        """Crawl website, extract leadership, generate permutations, and verify emails."""
        crawl_data = await self.crawler.crawl_site(website_url)
        domain = crawl_data["domain"]
        discovered_leads = []

        # 1. Process directly found emails
        for direct_email in crawl_data["emails"]:
            ver_res = self.verifier.verify(direct_email)
            lead_info = {
                "company_id": company_id,
                "full_name": direct_email.split('@')[0].replace('.', ' ').title(),
                "role": "Contact / Team",
                "email": direct_email,
                "verification_status": ver_res["status"]
            }
            discovered_leads.append(lead_info)

        # 2. Process executive names found on pages
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
                elif ver_res["status"] == "CATCH_ALL" and not best_email:
                    best_email = candidate
                    best_status = "CATCH_ALL"

            if not best_email and permutations:
                best_email = permutations[0]

            discovered_leads.append({
                "company_id": company_id,
                "full_name": name,
                "role": exec_info["role"],
                "email": best_email,
                "verification_status": best_status
            })

        # Fallback if no leads found
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

        # Save to database
        saved_leads = []
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
                        "company_id": company_id,
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

        return saved_leads
