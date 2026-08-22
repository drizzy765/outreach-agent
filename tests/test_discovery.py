import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agents.discovery import ProspectDiscoveryAgent, normalize_domain_url

def test_normalize_domain_url():
    assert normalize_domain_url("http://www.example.com/") == "http://example.com"
    assert normalize_domain_url("https://www.startup.io?utm_source=twitter&utm_medium=cpc") == "https://startup.io"
    assert normalize_domain_url("nextgen.ai/pricing?ref=producthunt") == "https://nextgen.ai/pricing"
    assert normalize_domain_url("   https://subdomain.test.org/   ") == "https://subdomain.test.org"

@pytest.mark.asyncio
async def test_discover_from_producthunt_rss_mock():
    agent = ProspectDiscoveryAgent()
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>OmniFlow – Next-gen AI workflow automation</title>
        <link href="https://omniflow-ai.com/?ref=producthunt"/>
        <summary>Automate your developer workflows with AI agents.</summary>
      </entry>
    </feed>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = xml_data.encode("utf-8")

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        prospects = await agent.discover_from_producthunt_rss(limit=5)
        assert len(prospects) == 1
        assert prospects[0]["company_name"] == "OmniFlow"
        assert prospects[0]["website_url"] == "https://omniflow-ai.com"
        assert prospects[0]["source"] == "producthunt"

@pytest.mark.asyncio
async def test_discover_from_hackernews_mock():
    agent = ProspectDiscoveryAgent()
    json_data = {
        "hits": [
            {
                "title": "Show HN: VectorVault – High-speed vector search for Postgres",
                "url": "https://vectorvault-db.io"
            },
            {
                "title": "Show HN: Some Github Repo",
                "url": "https://github.com/someone/repo" # Should be filtered out
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = json_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        prospects = await agent.discover_from_hackernews(limit=5)
        assert len(prospects) == 1
        assert "VectorVault" in prospects[0]["company_name"]
        assert prospects[0]["website_url"] == "https://vectorvault-db.io"
        assert prospects[0]["source"] == "hackernews"

@pytest.mark.asyncio
async def test_discover_from_ycombinator_mock():
    agent = ProspectDiscoveryAgent()
    json_data = {
        "hits": [
            {
                "name": "KiteAI",
                "website": "https://www.kite-ai.com",
                "one_liner": "Autonomous customer support copilots",
                "batch_name": "W24",
                "industry": "B2B / AI"
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = json_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        prospects = await agent.discover_from_ycombinator(query="AI", limit=5)
        assert len(prospects) == 1
        assert prospects[0]["company_name"] == "KiteAI"
        assert prospects[0]["website_url"] == "https://kite-ai.com"
        assert prospects[0]["source"] == "ycombinator"

@pytest.mark.asyncio
async def test_discover_from_github_mock():
    agent = ProspectDiscoveryAgent()
    json_data = {
        "items": [
            {
                "name": "agent-orchestrator",
                "homepage": "https://orchestrator-core.io",
                "description": "Multi-agent runtime for cloud infrastructure",
                "language": "Python"
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = json_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        prospects = await agent.discover_from_github(topic="ai-agent", limit=5)
        assert len(prospects) == 1
        assert prospects[0]["company_name"] == "Agent Orchestrator"
        assert prospects[0]["website_url"] == "https://orchestrator-core.io"
        assert prospects[0]["source"] == "github"
