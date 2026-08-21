import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# Common founder/exec titles
EXECUTIVE_TITLES = [
    "Founder", "Co-Founder", "CEO", "Chief Executive Officer",
    "CTO", "Chief Technology Officer", "Head of Engineering",
    "VP of Engineering", "Head of Product", "Chief Product Officer", "Director of Engineering"
]

CRAWL_SUBPATHS = [
    "",
    "/about",
    "/about-us",
    "/team",
    "/contact",
    "/contact-us",
    "/leadership",
    "/privacy",
    "/terms"
]

class DOMDeepCrawler:
    def __init__(self, timeout: float = 10.0):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.timeout = timeout

    async def crawl_site(self, base_url: str) -> Dict[str, any]:
        """
        Deeply inspect domain for:
        1. mailto: links and raw emails
        2. Leadership names & roles
        3. Social links (GitHub, LinkedIn, Twitter/X)
        4. Tech stack clues in HTML/headers
        """
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        domain = urlparse(base_url).netloc
        extracted_emails: Set[str] = set()
        extracted_executives: List[Dict[str, str]] = []
        social_links: Dict[str, str] = {}
        tech_stack_detected: List[str] = []

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True, verify=False) as client:
            for subpath in CRAWL_SUBPATHS:
                target_url = urljoin(base_url, subpath)
                try:
                    resp = await client.get(target_url)
                    if resp.status_code != 200:
                        continue

                    html = resp.text
                    soup = BeautifulSoup(html, "html.parser")

                    # Extract mailto links
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        if href.startswith('mailto:'):
                            clean_mail = href.replace('mailto:', '').split('?')[0].strip()
                            if EMAIL_REGEX.match(clean_mail):
                                extracted_emails.add(clean_mail.lower())

                        # Socials
                        if 'github.com/' in href:
                            social_links['github'] = href
                        elif 'linkedin.com/' in href:
                            social_links['linkedin'] = href
                        elif 'twitter.com/' in href or 'x.com/' in href:
                            social_links['twitter'] = href

                    # Extract raw regex emails from text
                    matches = EMAIL_REGEX.findall(html)
                    for m in matches:
                        # Avoid image/asset false positives
                        if not any(m.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']):
                            extracted_emails.add(m.lower())

                    # Scan for executive profiles in team/about pages
                    if subpath in ["/about", "/about-us", "/team", "/leadership", ""]:
                        for title in EXECUTIVE_TITLES:
                            pattern = re.compile(rf'([A-Z][a-z]+ [A-Z][a-z]+)\s*(?:-|–|,|\||\n)?\s*{re.escape(title)}', re.IGNORECASE)
                            found_execs = pattern.findall(soup.get_text(separator=' '))
                            for name in found_execs:
                                if len(name.split()) == 2:
                                    extracted_executives.append({
                                        "name": name.strip(),
                                        "role": title
                                    })

                    # Detect tech stack cues in script tags or headers
                    server_header = resp.headers.get("server", "")
                    if server_header:
                        tech_stack_detected.append(server_header)
                    for script in soup.find_all('script', src=True):
                        src = script['src'].lower()
                        if 'react' in src and 'React' not in tech_stack_detected:
                            tech_stack_detected.append("React")
                        elif 'next' in src and 'Next.js' not in tech_stack_detected:
                            tech_stack_detected.append("Next.js")
                        elif 'vue' in src and 'Vue.js' not in tech_stack_detected:
                            tech_stack_detected.append("Vue.js")
                        elif 'tailwind' in src and 'TailwindCSS' not in tech_stack_detected:
                            tech_stack_detected.append("TailwindCSS")
                        elif 'stripe' in src and 'Stripe' not in tech_stack_detected:
                            tech_stack_detected.append("Stripe")
                        elif 'algolia' in src and 'Algolia' not in tech_stack_detected:
                            tech_stack_detected.append("Algolia")

                except Exception as e:
                    # Ignore single page timeout/error
                    continue

        return {
            "domain": domain,
            "base_url": base_url,
            "emails": list(extracted_emails),
            "executives": extracted_executives,
            "social_links": social_links,
            "tech_stack": list(set(tech_stack_detected))
        }

async def crawl_domain_for_leads(base_url: str) -> Dict[str, any]:
    crawler = DOMDeepCrawler()
    return await crawler.crawl_site(base_url)
