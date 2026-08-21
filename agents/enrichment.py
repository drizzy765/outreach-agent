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

cat << 'EOF' > agents/pitcher.py
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ValueAddPitcherAgent:
    """
    Agent 4: Value-Add Pitch & Product Showcase Agent
    Drafts highly personalized, problem-first cold outreach:
    - Angle A (Custom ML/AI Engineering): Decoupled FastAPI vector search microservice cutting latency by 60%.
    - Angle B (Product-Led Pitch — QuantVault): Agentic voice command center for financial & telemetry pipelines.
    """

    def generate_pitch(
        self,
        lead_name: str,
        lead_role: str,
        company_name: str,
        website_url: str,
        audit_findings: Dict[str, Any],
        pitch_angle: Optional[str] = None
    ) -> Dict[str, str]:
        """Craft personalized pitch tailored to company diagnostics."""
        first_name = lead_name.split()[0] if lead_name else "there"
        chosen_angle = pitch_angle or audit_findings.get("recommended_pitch_angle", "CUSTOM_ML_AUDIT")
        ttfb = audit_findings.get("ttfb_ms", 120)

        if chosen_angle == "QUANTVAULT_DEMO":
            subject = f"Quick question regarding {company_name}'s analytics & voice workflows"
            body = f"""Hi {first_name},

I took a close look at {company_name}'s analytics platform ({website_url}) and was really impressed by your market focus.

While analyzing your user workflow, I noticed your data telemetry currently lacks a low-latency agentic voice command center for real-time querying.

I recently built QuantVault — an open-architecture agent that plugs directly into quantitative & telemetry pipelines, enabling natural voice querying and real-time risk alerts in under 200ms.

Here is a 15-second interactive demonstration of how it integrates with platforms like {company_name}:
👉 https://quantvault-demo.io/showcase

Would you be open to a 10-minute coffee chat next Tuesday at 2 PM to explore if this could boost user retention on {company_name}?

Best regards,
Autonomous Outreach Engine
"""
        else: # Angle A: Custom ML/AI Engineering
            subject = f"Technical audit findings & vector search latency on {company_name}"
            body = f"""Hi {first_name},

I ran a performance and architecture diagnostic on {company_name} ({website_url}) and noticed an engineering bottleneck: your search engine relies on basic keyword matching with an average query TTFB of ~{ttfb}ms.

I specialize in building decoupled FastAPI + Qdrant/Milvus vector search microservices that implement semantic reranking and cut search latency by over 60%.

I put together a quick architecture blueprint showing how this can be deployed alongside your existing stack with zero downtime:
👉 https://architecture-blueprints.io/{company_name.lower().replace(' ', '-')}-optimization

Are you free for a brief 10-minute chat this Thursday to discuss whether implementing this makes sense for your engineering roadmap?

Best regards,
Autonomous Outreach Engine
"""

        return {
            "subject": subject,
            "body": body,
            "pitch_type": chosen_angle
        }
