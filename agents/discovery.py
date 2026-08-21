import re
import httpx
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from database.connection import AsyncSessionLocal
from database.models import ProspectCompany
from sqlalchemy import select

logger = logging.getLogger(__name__)

class ProspectDiscoveryAgent:
    """
    Agent 1: Prospect Discovery Agent
    Discovers early-stage startups, SaaS products, and fintech/e-commerce platforms.
    Sources: ProductHunt, Hacker News / YCombinator, GitHub Trending, Google Dorks.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def discover_from_producthunt_rss(self) -> List[Dict[str, str]]:
        """Scrape latest launches from ProductHunt public RSS feed."""
        prospects = []
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                resp = await client.get("https://www.producthunt.com/feed")
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, "xml")
                    for entry in soup.find_all("entry"):
                        title = entry.find("title").text if entry.find("title") else ""
                        link = entry.find("link")["href"] if entry.find("link") else ""
                        summary = entry.find("summary").text if entry.find("summary") else ""
                        
                        if link:
                            prospects.append({
                                "company_name": title.split("–")[0].split("-")[0].strip(),
                                "website_url": link,
                                "industry": "SaaS / AI Startup",
                                "description": summary
                            })
        except Exception as e:
            logger.warning(f"ProductHunt RSS scrape failed: {e}")
        return prospects

    async def discover_from_curated_sources(self, custom_urls: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """
        Discovers prospects or accepts targeted inputs for pipeline processing.
        """
        if custom_urls:
            return custom_urls

        discovered = await self.discover_from_producthunt_rss()
        if not discovered:
            # High-value default sample targets
            discovered = [
                {
                    "company_name": "ApexQuant Analytics",
                    "website_url": "https://apexquant-sample.io",
                    "industry": "FinTech / Quantitative Trading",
                    "description": "High-frequency portfolio risk analytics platform."
                },
                {
                    "company_name": "NexStore Commerce",
                    "website_url": "https://nexstore-sample.com",
                    "industry": "E-Commerce / B2B Retail",
                    "description": "Catalog search and inventory automation system."
                }
            ]
        return discovered

    async def register_prospects(self, prospects: List[Dict[str, str]]) -> List[ProspectCompany]:
        """Save newly discovered companies into CRM database."""
        saved_companies = []
        async with AsyncSessionLocal() as session:
            for p in prospects:
                url = p["website_url"]
                # Clean URL
                if not url.startswith("http"):
                    url = f"https://{url}"

                # Check if exists
                stmt = select(ProspectCompany).where(ProspectCompany.website_url == url)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

                if not existing:
                    company = ProspectCompany(
                        company_name=p.get("company_name", "Target Startup"),
                        website_url=url,
                        industry=p.get("industry", "Technology"),
                        tech_stack_detected={"description": p.get("description", "")},
                        audit_findings={}
                    )
                    session.add(company)
                    await session.commit()
                    await session.refresh(company)
                    saved_companies.append(company)
                else:
                    saved_companies.append(existing)
        return saved_companies
