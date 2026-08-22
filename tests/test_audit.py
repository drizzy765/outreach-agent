import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agents.audit import TechnicalAuditAgent
from tools.playwright_auditor import PlaywrightAuditor

@pytest.mark.asyncio
async def test_audit_with_http_fallback_search_gap():
    agent = TechnicalAuditAgent(enable_playwright=False)
    html_content = """
    <html>
      <head><title>Simple SaaS App</title></head>
      <body>
        <h1>Welcome to Simple SaaS</h1>
        <form action="/search"><input type="text" name="q" placeholder="Keyword search"/></form>
      </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = html_content.encode("utf-8")
    mock_response.text = html_content

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        findings = await agent.perform_audit("https://simple-saas.com")

        assert findings["status_code"] == 200
        assert findings["search_gap_detected"] is True
        assert findings["ai_agent_gap_detected"] is True
        assert findings["recommended_pitch_angle"] == "CUSTOM_ML_AUDIT"
        assert "Audited https://simple-saas.com" in findings["audit_summary"]

@pytest.mark.asyncio
async def test_audit_with_fintech_quantvault_pitch():
    agent = TechnicalAuditAgent(enable_playwright=False)
    html_content = """
    <html>
      <head><title>AlphaQuant Trading & Analytics</title></head>
      <body>
        <h1>Portfolio Telemetry and High Frequency Risk Analytics</h1>
      </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = html_content.encode("utf-8")
    mock_response.text = html_content

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        findings = await agent.perform_audit("https://alphaquant.io")

        assert findings["status_code"] == 200
        assert findings["recommended_pitch_angle"] == "QUANTVAULT_DEMO"

@pytest.mark.asyncio
async def test_audit_with_vector_search_detected():
    agent = TechnicalAuditAgent(enable_playwright=False)
    html_content = """
    <html>
      <head><title>VectorAI Knowledge Base</title></head>
      <body>
        <h1>Powered by Qdrant Semantic Search and Embeddings Reranking</h1>
        <p>Realtime voice agent workflows enabled.</p>
      </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = html_content.encode("utf-8")
    mock_response.text = html_content

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        findings = await agent.perform_audit("https://vectorai.io")

        assert findings["search_gap_detected"] is False
        assert findings["ai_agent_gap_detected"] is False

@pytest.mark.asyncio
async def test_playwright_auditor_mock():
    auditor = PlaywrightAuditor()
    mock_pw_result = {
        "target_url": "https://modern-spa.io",
        "ttfb_ms": 150.0,
        "load_time_ms": 420.0,
        "status_code": 200,
        "js_console_errors": ["TypeError: Cannot read property 'map' of undefined"],
        "failed_network_requests": [{"url": "https://api.modern-spa.io/v1/telemetry", "status": 500}],
        "detected_apis": ["algolia", "stripe"],
        "page_title": "Modern Quantitative Analytics SPA",
        "has_vector_search": False,
        "has_voice_ai": False,
        "engine_used": "playwright"
    }

    agent = TechnicalAuditAgent(enable_playwright=True)
    with patch.object(PlaywrightAuditor, "audit_url", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = mock_pw_result
        findings = await agent.perform_audit("https://modern-spa.io")

        assert findings["diagnostic_engine"] == "playwright_headless"
        assert findings["load_time_ms"] == 420.0
        assert len(findings["js_console_errors"]) == 1
        assert "stripe" in findings["detected_apis"]
        assert findings["search_gap_detected"] is True
        assert findings["recommended_pitch_angle"] == "QUANTVAULT_DEMO"
