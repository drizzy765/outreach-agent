import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from workflow.graph import run_autonomous_outreach_pipeline
from tools.telegram_bot import TelegramBotHandler
from workflow.scheduler import AutonomousOutreachScheduler
from config import settings

@pytest.mark.asyncio
async def test_autonomous_email_dispatch_pipeline():
    """Verify pipeline automatically sends email for qualified prospect when auto_send is True."""
    with patch("workflow.graph.discovery_agent.discover_from_curated_sources", new_callable=AsyncMock) as mock_disc, \
         patch("workflow.graph.discovery_agent.register_prospects", new_callable=AsyncMock) as mock_reg, \
         patch("workflow.graph.audit_agent.perform_audit", new_callable=AsyncMock) as mock_audit, \
         patch("workflow.graph.enrichment_agent.enrich_company", new_callable=AsyncMock) as mock_enrich, \
         patch("workflow.graph.pitcher_agent.generate_pitch_async", new_callable=AsyncMock) as mock_pitch, \
         patch("workflow.graph.email_sender.send_email", new_callable=AsyncMock) as mock_send, \
         patch("workflow.graph.alerts_agent.dispatch_stage_update", new_callable=AsyncMock) as mock_alert, \
         patch("workflow.graph.AsyncSessionLocal") as mock_session_cls:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

        mock_disc.return_value = [{"company_name": "QuantVault AI", "website_url": "https://quantvault.io"}]
        mock_comp = MagicMock()
        mock_comp.id = "44444444-4444-4444-4444-444444444444"
        mock_reg.return_value = [mock_comp]

        mock_audit.return_value = {
            "ttfb_ms": 190,
            "search_gap_detected": True,
            "recommended_pitch_angle": "QUANTVAULT_DEMO",
            "audit_summary": "Vector search latency gap identified."
        }

        mock_enrich.return_value = [{
            "id": "55555555-5555-5555-5555-555555555555",
            "full_name": "Marcus Vance",
            "role": "VP Engineering",
            "email": "marcus@quantvault.io",
            "verification_status": "SMTP_VERIFIED"
        }]

        mock_pitch.return_value = {
            "subject": "QuantVault search latency & vector cache architecture",
            "body": "Hi Marcus, noticed your search cluster response times...",
            "pitch_type": "QUANTVAULT_DEMO",
            "provider_used": "deterministic_synthesizer"
        }

        mock_send.return_value = {
            "status": "SENT",
            "message_id": "<msg-test-123@yourname-labs.com>",
            "sender": "outreach@yourname-labs.com",
            "recipient": "marcus@quantvault.io",
            "details": "Successfully dispatched via authenticated SMTP."
        }

        # Run pipeline with autonomous auto_send=True
        res = await run_autonomous_outreach_pipeline(
            target_url="https://quantvault.io",
            company_name="QuantVault AI",
            auto_send=True
        )

        # Assertions
        assert res["company_name"] == "QuantVault AI"
        assert res["primary_lead_email"] == "marcus@quantvault.io"
        assert res["is_worthy_prospect"] is True
        assert res["email_dispatch_status"] == "SENT"
        assert res["negotiation_stage"] == "SENT"
        assert mock_send.called
        assert mock_send.call_args[1]["recipient_email"] == "marcus@quantvault.io"
        # Alert should NOT be sent on routine outbound dispatch (silent autopilot)
        assert not mock_alert.called


@pytest.mark.asyncio
async def test_manual_mode_skips_outbound_send():
    """Verify pipeline respects auto_send=False and keeps pitch in DRAFTED state."""
    with patch("workflow.graph.discovery_agent.discover_from_curated_sources", new_callable=AsyncMock) as mock_disc, \
         patch("workflow.graph.discovery_agent.register_prospects", new_callable=AsyncMock) as mock_reg, \
         patch("workflow.graph.audit_agent.perform_audit", new_callable=AsyncMock) as mock_audit, \
         patch("workflow.graph.enrichment_agent.enrich_company", new_callable=AsyncMock) as mock_enrich, \
         patch("workflow.graph.pitcher_agent.generate_pitch_async", new_callable=AsyncMock) as mock_pitch, \
         patch("workflow.graph.email_sender.send_email", new_callable=AsyncMock) as mock_send, \
         patch("workflow.graph.AsyncSessionLocal") as mock_session_cls:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

        mock_disc.return_value = [{"company_name": "TestCo", "website_url": "https://testco.io"}]
        mock_comp = MagicMock()
        mock_comp.id = "11111111-1111-1111-1111-111111111111"
        mock_reg.return_value = [mock_comp]
        mock_audit.return_value = {"ttfb_ms": 100}
        mock_enrich.return_value = [{
            "id": "22222222-2222-2222-2222-222222222222",
            "full_name": "Alice",
            "role": "CTO",
            "email": "alice@testco.io",
            "verification_status": "SMTP_VERIFIED"
        }]
        mock_pitch.return_value = {
            "subject": "Architecture idea",
            "body": "Hi Alice...",
            "pitch_type": "CUSTOM_ML_AUDIT"
        }

        res = await run_autonomous_outreach_pipeline(
            target_url="https://testco.io",
            company_name="TestCo",
            auto_send=False
        )

        assert res["email_dispatch_status"] == "SKIPPED_MANUAL_MODE"
        assert res["negotiation_stage"] == "DRAFTED"
        assert not mock_send.called


@pytest.mark.asyncio
async def test_telegram_pitch_command_autonomous_dispatch():
    """Verify /pitch telegram command executes full pipeline and auto-sends."""
    handler = TelegramBotHandler()

    with patch("tools.telegram_bot.send_telegram_alert", new_callable=AsyncMock) as mock_alert, \
         patch("workflow.graph.run_autonomous_outreach_pipeline", new_callable=AsyncMock) as mock_pipeline:

        mock_pipeline.return_value = {
            "company_name": "CopilotKit",
            "target_url": "https://docs.copilotkit.ai",
            "primary_lead_name": "Atai Barkai",
            "primary_lead_email": "atai@copilotkit.ai",
            "pitch_subject": "FastAPI Vector Cache for CopilotKit",
            "pitch_angle": "CUSTOM_ML_AUDIT",
            "pitch_body": "Hi Atai, noticed your indexing pipeline...",
            "email_dispatch_status": "SENT",
            "negotiation_stage": "SENT"
        }

        response = await handler.handle_message_command("/pitch https://docs.copilotkit.ai", "Admin")

        assert "Autonomous Outreach Dispatched" in response
        assert "CopilotKit" in response
        assert "atai@copilotkit.ai" in response
        assert "Autopilot Active" in response
        assert mock_pipeline.called
        assert mock_pipeline.call_args[1]["auto_send"] is True


@pytest.mark.asyncio
async def test_scheduler_run_pending_outreach_job():
    """Verify scheduler pending outreach job audits and pitches registered CRM companies."""
    scheduler = AutonomousOutreachScheduler()

    with patch("workflow.scheduler.AsyncSessionLocal") as mock_session_cls, \
         patch("workflow.graph.run_autonomous_outreach_pipeline", new_callable=AsyncMock) as mock_pipeline:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        comp1 = MagicMock()
        comp1.id = "11111111-1111-1111-1111-111111111111"
        comp1.company_name = "Agentic Systems"
        comp1.website_url = "https://agentic.systems"

        # First query gets companies
        mock_res_comps = MagicMock()
        mock_res_comps.scalars.return_value.all.return_value = [comp1]

        # Second query checks existing convs (returns None -> not pitched yet)
        mock_res_conv = MagicMock()
        mock_res_conv.first.return_value = None

        mock_session.execute.side_effect = [mock_res_comps, mock_res_conv]

        mock_pipeline.return_value = {
            "primary_lead_email": "founder@agentic.systems",
            "email_dispatch_status": "SENT",
            "negotiation_stage": "SENT"
        }

        dispatched = await scheduler.run_pending_outreach_job(limit=1)

        assert len(dispatched) == 1
        assert dispatched[0]["company_name"] == "Agentic Systems"
        assert dispatched[0]["dispatch_status"] == "SENT"
        assert mock_pipeline.called
