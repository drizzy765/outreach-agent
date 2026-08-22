import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from tools.email_verifier import generate_email_permutations, EmailVerifier
from tools.web_crawler import DOMDeepCrawler
from agents.enrichment import LeadEnrichmentAgent

def test_generate_email_permutations():
    perms = generate_email_permutations("Elon", "Musk", "x.com")
    assert "elon.musk@x.com" in perms
    assert "elon@x.com" in perms
    assert "emusk@x.com" in perms
    assert "elonmusk@x.com" in perms
    assert "e.musk@x.com" in perms
    assert "musk.elon@x.com" in perms

def test_generate_email_permutations_single_name():
    perms = generate_email_permutations("Satoshi", "", "bitcoin.org")
    assert "satoshi@bitcoin.org" in perms
    assert "founder@bitcoin.org" in perms

def test_email_verifier_syntax():
    verifier = EmailVerifier()
    res = verifier.verify("invalid-email-format")
    assert res["status"] == "INVALID_SYNTAX"

def test_email_verifier_no_mx():
    verifier = EmailVerifier()
    with patch.object(EmailVerifier, "get_mx_record", return_value=None):
        res = verifier.verify("test@nonexistent-domain-12345.com")
        assert res["status"] == "NO_MX_RECORDS"

def test_email_verifier_catch_all():
    verifier = EmailVerifier()
    with patch.object(EmailVerifier, "get_mx_record", return_value="mail.example.com"), \
         patch.object(EmailVerifier, "is_catch_all", return_value=True):
        res = verifier.verify("contact@example.com")
        assert res["status"] == "CATCH_ALL"

def test_email_verifier_smtp_verified():
    verifier = EmailVerifier()
    with patch.object(EmailVerifier, "get_mx_record", return_value="mail.example.com"), \
         patch.object(EmailVerifier, "is_catch_all", return_value=False), \
         patch.object(EmailVerifier, "_ping_smtp", return_value=(250, "OK")):
        res = verifier.verify("founder@example.com")
        assert res["status"] == "SMTP_VERIFIED"

def test_email_verifier_mailbox_not_found():
    verifier = EmailVerifier()
    with patch.object(EmailVerifier, "get_mx_record", return_value="mail.example.com"), \
         patch.object(EmailVerifier, "is_catch_all", return_value=False), \
         patch.object(EmailVerifier, "_ping_smtp", return_value=(550, "No such user")):
        res = verifier.verify("nobody@example.com")
        assert res["status"] == "MAILBOX_NOT_FOUND"

@pytest.mark.asyncio
async def test_crawler_jsonld_and_mailto_extraction():
    crawler = DOMDeepCrawler()
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Acme AI",
          "founder": [{"@type": "Person", "name": "Sarah Connor"}]
        }
        </script>
      </head>
      <body>
        <a href="mailto:support@acme-ai.io">Contact Us</a>
        <a href="https://linkedin.com/in/sarah-connor-99">LinkedIn</a>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.headers = {}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        crawl_data = await crawler.crawl_site("https://acme-ai.io")
        assert "support@acme-ai.io" in crawl_data["emails"]
        assert any(e["name"] == "Sarah Connor" for e in crawl_data["executives"])

@pytest.mark.asyncio
async def test_enrichment_agent_integration():
    agent = LeadEnrichmentAgent()
    mock_crawl = {
        "domain": "quantlabs.io",
        "base_url": "https://quantlabs.io",
        "emails": ["info@quantlabs.io"],
        "executives": [{"name": "David Marcus", "role": "Co-Founder & CTO"}],
        "social_links": {},
        "tech_stack": ["React"]
    }

    with patch.object(DOMDeepCrawler, "crawl_site", new_callable=AsyncMock) as mock_crawler_call, \
         patch.object(EmailVerifier, "verify", return_value={"status": "SMTP_VERIFIED", "email": "david.marcus@quantlabs.io"}):
        mock_crawler_call.return_value = mock_crawl
        leads = await agent.enrich_company(company_id=None, website_url="https://quantlabs.io")

        assert len(leads) >= 1
        assert leads[0]["full_name"] == "David Marcus"
        assert leads[0]["email"] == "david.marcus@quantlabs.io"
        assert leads[0]["verification_status"] == "SMTP_VERIFIED"
