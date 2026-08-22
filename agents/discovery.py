import re
import asyncio
import httpx
import logging
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from database.connection import AsyncSessionLocal
from database.models import ProspectCompany
from sqlalchemy import select

logger = logging.getLogger(__name__)

def normalize_domain_url(url: str) -> str:
    """Normalize a target URL: enforce https, strip www, paths, trailing slashes, and UTM tracking params."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Remove UTM and tracking params
    query_params = parse_qsl(parsed.query)
    clean_params = [(k, v) for k, v in query_params if not k.lower().startswith("utm_") and k.lower() not in ["ref", "source"]]
    clean_query = urlencode(clean_params)

    # For company discovery, we normalize to scheme + host or path without trailing slash
    path = parsed.path.rstrip("/")
    normalized = urlunparse((parsed.scheme or "https", netloc, path, "", clean_query, ""))
    return normalized

class ProspectDiscoveryAgent:
    """
    Agent 1: Multi-Source Prospect Discovery Agent
    Continuously discovers early-stage startups, SaaS products, and fintech/e-commerce platforms.
    Ingestion Channels:
    - ProductHunt Daily RSS / Launches
    - Y Combinator Startup Directory (Algolia / Web)
    - Hacker News API (Show HN & Ask HN)
    - GitHub Trending / AI-Agent Search
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def discover_from_producthunt_rss(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape latest launches from ProductHunt public RSS feed."""
        prospects = []
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get("https://www.producthunt.com/feed")
                if resp.status_code == 200:
                    import warnings
                    from bs4 import XMLParsedAsHTMLWarning
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
                        soup = BeautifulSoup(resp.content, "html.parser")
                    for entry in soup.find_all("entry")[:limit]:
                        title = entry.find("title").text if entry.find("title") else ""
                        link = entry.find("link")["href"] if entry.find("link") else ""
                        summary = entry.find("summary").text if entry.find("summary") else ""

                        if link:
                            clean_name = title.split("–")[0].split("-")[0].strip()
                            clean_url = normalize_domain_url(link)
                            prospects.append({
                                "company_name": clean_name or "ProductHunt Launch",
                                "website_url": clean_url,
                                "industry": "SaaS / AI Startup",
                                "description": summary.strip(),
                                "source": "producthunt"
                            })
        except Exception as e:
            logger.warning(f"ProductHunt RSS scrape error: {e}")
        return prospects

    async def discover_from_hackernews(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Query Hacker News Algolia API for recent 'Show HN' startups and products."""
        prospects = []
        try:
            url = f"https://hn.algolia.com/api/v1/search_by_date?tags=show_hn&hitsPerPage={limit * 2}"
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    for hit in hits:
                        target_url = hit.get("url")
                        title = hit.get("title", "")
                        # Remove 'Show HN: ' prefix
                        clean_title = re.sub(r"^Show\s+HN:\s*", "", title, flags=re.IGNORECASE).strip()
                        company_name = clean_title.split("–")[0].split("-")[0].split("—")[0].split(":")[0].strip()

                        if target_url and not any(skip in target_url for skip in ["github.com", "twitter.com", "x.com", "youtube.com"]):
                            clean_url = normalize_domain_url(target_url)
                            prospects.append({
                                "company_name": company_name or "HN Show Startup",
                                "website_url": clean_url,
                                "industry": "Developer Tools / Early-Stage Tech",
                                "description": title,
                                "source": "hackernews"
                            })
                        if len(prospects) >= limit:
                            break
        except Exception as e:
            logger.warning(f"Hacker News discovery failed: {e}")
        return prospects

    async def discover_from_ycombinator(self, query: str = "AI", limit: int = 10) -> List[Dict[str, Any]]:
        """Query Y Combinator directory (Algolia public endpoint)."""
        prospects = []
        try:
            url = "https://45bwyd1znc-dsn.algolia.net/1/indexes/YCCompany_production/query"
            headers = {
                **self.headers,
                "X-Algolia-Application-Id": "45BWYD1ZNC",
                "X-Algolia-API-Key": "d16fb92c1f725e4063fb6281d0d9ce30"
            }
            payload = {
                "query": query,
                "hitsPerPage": limit,
                "attributesToRetrieve": ["name", "website", "one_liner", "batch_name", "industry"]
            }
            async with httpx.AsyncClient(headers=headers, timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    for hit in hits:
                        site = hit.get("website")
                        if site:
                            clean_url = normalize_domain_url(site)
                            prospects.append({
                                "company_name": hit.get("name", "YC Startup"),
                                "website_url": clean_url,
                                "industry": hit.get("industry") or f"YC Startup ({hit.get('batch_name', '')})",
                                "description": hit.get("one_liner", ""),
                                "source": "ycombinator"
                            })
        except Exception as e:
            logger.warning(f"Y Combinator directory query failed: {e}")
        return prospects

    async def discover_from_github(self, topic: str = "ai-agent", limit: int = 10) -> List[Dict[str, Any]]:
        """Query GitHub Public API for newly updated SaaS and AI repositories with project homepages."""
        prospects = []
        try:
            url = f"https://api.github.com/search/repositories?q=topic:{topic}+stars:>30&sort=updated&order=desc&per_page={limit * 2}"
            gh_headers = {
                **self.headers,
                "Accept": "application/vnd.github.v3+json"
            }
            async with httpx.AsyncClient(headers=gh_headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    for item in items:
                        homepage = item.get("homepage")
                        if homepage and homepage.startswith("http") and "github.com" not in homepage:
                            clean_url = normalize_domain_url(homepage)
                            prospects.append({
                                "company_name": item.get("name", "GitHub Project").replace("-", " ").title(),
                                "website_url": clean_url,
                                "industry": f"AI / Open Core Software ({item.get('language') or 'Software'})",
                                "description": item.get("description") or "",
                                "source": "github"
                            })
                        if len(prospects) >= limit:
                            break
        except Exception as e:
            logger.warning(f"GitHub search failed: {e}")
        return prospects

    async def discover_multi_source(
        self,
        sources: Optional[List[str]] = None,
        limit_per_source: int = 5
    ) -> List[Dict[str, Any]]:
        """Execute discovery across multiple channels concurrently."""
        active_sources = sources or ["producthunt", "hackernews", "ycombinator", "github"]
        tasks = []

        if "producthunt" in active_sources:
            tasks.append(self.discover_from_producthunt_rss(limit=limit_per_source))
        if "hackernews" in active_sources:
            tasks.append(self.discover_from_hackernews(limit=limit_per_source))
        if "ycombinator" in active_sources:
            tasks.append(self.discover_from_ycombinator(limit=limit_per_source))
        if "github" in active_sources:
            tasks.append(self.discover_from_github(limit=limit_per_source))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        aggregated: List[Dict[str, Any]] = []
        seen_urls = set()

        for batch in results:
            if isinstance(batch, list):
                for item in batch:
                    u = item.get("website_url")
                    if u and u not in seen_urls:
                        seen_urls.add(u)
                        aggregated.append(item)

        return aggregated

    async def discover_from_curated_sources(self, custom_urls: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """Discovers prospects or accepts targeted inputs for pipeline processing."""
        if custom_urls:
            return custom_urls

        discovered = await self.discover_multi_source(limit_per_source=3)
        if not discovered:
            # High-value fallback sample targets
            discovered = [
                {
                    "company_name": "ApexQuant Analytics",
                    "website_url": "https://apexquant-sample.io",
                    "industry": "FinTech / Quantitative Trading",
                    "description": "High-frequency portfolio risk analytics platform.",
                    "source": "curated_fallback"
                },
                {
                    "company_name": "NexStore Commerce",
                    "website_url": "https://nexstore-sample.com",
                    "industry": "E-Commerce / B2B Retail",
                    "description": "Catalog search and inventory automation system.",
                    "source": "curated_fallback"
                }
            ]
        return discovered

    async def register_prospects(self, prospects: List[Dict[str, Any]]) -> List[ProspectCompany]:
        """Save newly discovered companies into CRM database with URL normalization and deduplication."""
        saved_companies = []
        async with AsyncSessionLocal() as session:
            for p in prospects:
                raw_url = p.get("website_url", "")
                norm_url = normalize_domain_url(raw_url)
                if not norm_url:
                    continue

                # Check if exists
                stmt = select(ProspectCompany).where(ProspectCompany.website_url == norm_url)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

                if not existing:
                    company = ProspectCompany(
                        company_name=p.get("company_name", "Target Startup"),
                        website_url=norm_url,
                        industry=p.get("industry", "Technology"),
                        tech_stack_detected={"description": p.get("description", ""), "source": p.get("source", "manual")},
                        audit_findings={}
                    )
                    session.add(company)
                    await session.commit()
                    await session.refresh(company)
                    saved_companies.append(company)
                else:
                    saved_companies.append(existing)
        return saved_companies

