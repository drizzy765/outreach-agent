import re
import json
import httpx
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional, Any
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# Common founder/exec titles for heuristic extraction
EXECUTIVE_TITLES = [
    "Co-Founder & CEO", "Co-Founder and CEO", "Founder & CEO", "Founder and CEO",
    "Co-Founder & CTO", "Co-Founder and CTO", "Founder & CTO", "Founder and CTO",
    "Chief Executive Officer", "Chief Technology Officer", "Co-Founder", "Founder",
    "CEO", "CTO", "Head of Engineering", "VP of Engineering", "Chief Product Officer",
    "Head of Product", "VP of Product", "Chief Architect", "Head of AI", "VP of AI"
]

CRAWL_SUBPATHS = [
    "",
    "/about",
    "/about-us",
    "/team",
    "/our-team",
    "/leadership",
    "/people",
    "/company",
    "/contact",
    "/contact-us",
    "/privacy",
    "/terms"
]

class DOMDeepCrawler:
    """
    High-depth DOM and metadata crawler.
    Extracts raw mailto addresses, executive profiles (via regex, JSON-LD schema, and DOM hierarchy),
    social media profiles (GitHub, LinkedIn, Twitter/X), and tech stack cues.
    """

    def __init__(self, timeout: float = 10.0):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.timeout = timeout

    async def crawl_site(self, base_url: str) -> Dict[str, Any]:
        """
        Deeply inspect domain across key subpaths.
        """
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        domain = urlparse(base_url).netloc.lower().replace("www.", "")
        extracted_emails: Set[str] = set()
        extracted_executives: List[Dict[str, str]] = []
        social_links: Dict[str, str] = {}
        tech_stack_detected: List[str] = []
        seen_names: Set[str] = set()

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True, verify=False) as client:
            for subpath in CRAWL_SUBPATHS:
                target_url = urljoin(base_url, subpath)
                try:
                    resp = await client.get(target_url)
                    if resp.status_code != 200:
                        continue

                    html = resp.text
                    soup = BeautifulSoup(html, "html.parser")

                    # 1. Parse JSON-LD Schema (Structured data)
                    for script in soup.find_all("script", type="application/ld+json"):
                        try:
                            data = json.loads(script.string or "{}")
                            items = data if isinstance(data, list) else [data]
                            for item in items:
                                if item.get("@type") in ["Person", "Organization"]:
                                    # Person schema
                                    if item.get("@type") == "Person" and item.get("name"):
                                        p_name = item["name"].strip()
                                        p_role = item.get("jobTitle") or "Executive"
                                        if p_name not in seen_names and len(p_name.split()) >= 2:
                                            seen_names.add(p_name)
                                            extracted_executives.append({"name": p_name, "role": p_role})
                                    # Organization founders
                                    for founder in item.get("founder", []) or item.get("founders", []):
                                        if isinstance(founder, dict) and founder.get("name"):
                                            f_name = founder["name"].strip()
                                            if f_name not in seen_names and len(f_name.split()) >= 2:
                                                seen_names.add(f_name)
                                                extracted_executives.append({"name": f_name, "role": "Founder"})
                        except Exception:
                            pass

                    # 2. Extract mailto links
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        if href.startswith('mailto:'):
                            clean_mail = href.replace('mailto:', '').split('?')[0].strip()
                            if EMAIL_REGEX.match(clean_mail):
                                extracted_emails.add(clean_mail.lower())

                        # Social profile links
                        href_lower = href.lower()
                        if 'github.com/' in href_lower and 'github' not in social_links:
                            social_links['github'] = href
                        elif 'linkedin.com/' in href_lower and 'linkedin' not in social_links:
                            social_links['linkedin'] = href
                            # Infer founder name from linkedin url (e.g. /in/john-doe-1234)
                            if "/in/" in href:
                                handle = href.split("/in/")[-1].strip("/").split("?")[0]
                                clean_handle = re.sub(r'-\d+$', '', handle).replace("-", " ").title()
                                if clean_handle and len(clean_handle.split()) >= 2 and clean_handle not in seen_names:
                                    seen_names.add(clean_handle)
                                    extracted_executives.append({"name": clean_handle, "role": "Leadership (LinkedIn)"})
                        elif ('twitter.com/' in href_lower or 'x.com/' in href_lower) and 'twitter' not in social_links:
                            social_links['twitter'] = href

                    # 3. Extract raw regex emails from text
                    matches = EMAIL_REGEX.findall(html)
                    for m in matches:
                        if not any(m.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.js', '.css']):
                            extracted_emails.add(m.lower())

                    # 4. Scan for executive profiles in leadership/about pages
                    if subpath in ["/about", "/about-us", "/team", "/our-team", "/leadership", "/people", "/company", ""]:
                        text = soup.get_text(separator=' ')
                        for title in EXECUTIVE_TITLES:
                            pattern = re.compile(rf'([A-Z][a-z]+ [A-Z][a-z]+)\s*(?:-|–|,|\||\n|—)?\s*{re.escape(title)}', re.IGNORECASE)
                            found_execs = pattern.findall(text)
                            for name in found_execs:
                                name_clean = name.strip()
                                if len(name_clean.split()) == 2 and name_clean not in seen_names:
                                    seen_names.add(name_clean)
                                    extracted_executives.append({
                                        "name": name_clean,
                                        "role": title
                                    })

                    # 5. Detect tech stack cues
                    server_header = resp.headers.get("server", "")
                    if server_header and server_header not in tech_stack_detected:
                        tech_stack_detected.append(server_header)
                    for script in soup.find_all('script', src=True):
                        src = script['src'].lower()
                        for tech in ["react", "next", "vue", "tailwind", "stripe", "algolia", "segment", "posthog"]:
                            if tech in src and tech.title() not in tech_stack_detected:
                                tech_stack_detected.append(tech.title())

                except Exception as e:
                    logger.debug(f"Crawl subpath {subpath} failed for {base_url}: {e}")
                    continue

        return {
            "domain": domain,
            "base_url": base_url,
            "emails": list(extracted_emails),
            "executives": extracted_executives,
            "social_links": social_links,
            "tech_stack": list(set(tech_stack_detected))
        }

async def crawl_domain_for_leads(base_url: str) -> Dict[str, Any]:
    crawler = DOMDeepCrawler()
    return await crawler.crawl_site(base_url)
