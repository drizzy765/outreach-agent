import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from workflow.graph import run_autonomous_outreach_pipeline

@pytest.mark.asyncio
async def test_end_to_end_pipeline_flow():
    with patch("workflow.graph.discovery_agent.discover_from_curated_sources", new_callable=AsyncMock) as mock_disc,          patch("workflow.graph.discovery_agent.register_prospects", new_callable=AsyncMock) as mock_reg,          patch("workflow.graph.audit_agent.perform_audit", new_callable=AsyncMock) as mock_audit,          patch("workflow.graph.enrichment_agent.enrich_company", new_callable=AsyncMock) as mock_enrich,          patch("workflow.graph.pitcher_agent.generate_pitch_async", new_callable=AsyncMock) as mock_pitch,          patch("workflow.graph.alerts_agent.dispatch_stage_update", new_callable=AsyncMock) as mock_alert,          patch("workflow.graph.AsyncSessionLocal") as mock_session_cls:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

        mock_disc.return_value = [{"company_name": "FlowTest AI", "website_url": "https://flowtest.ai"}]
        mock_comp = MagicMock()
        mock_comp.id = "33333333-3333-3333-3333-333333333333"
        mock_reg.return_value = [mock_comp]

        mock_audit.return_value = {
            "ttfb_ms": 240,
            "search_gap_detected": True,
            "recommended_pitch_angle": "CUSTOM_ML_AUDIT",
            "audit_summary": "High search latency detected."
        }

        mock_enrich.return_value = [{
            "id": "22222222-2222-2222-2222-222222222222",
            "full_name": "Elena Rostova",
            "role": "CTO",
            "email": "elena@flowtest.ai",
            "verification_status": "SMTP_VERIFIED"
        }]

        mock_pitch.return_value = {
            "subject": "Fixing search latency at FlowTest",
            "body": "Hi Elena, noticed your search queries are taking >500ms...",
            "pitch_type": "CUSTOM_ML_AUDIT",
            "provider_used": "deterministic_synthesizer"
        }

        mock_alert.return_value = {"status": "DISPATCHED"}

        # Run pipeline
        res = await run_autonomous_outreach_pipeline(
            target_url="https://flowtest.ai",
            company_name="FlowTest AI",
            incoming_reply="Looks interesting, send over pricing options."
        )

        assert res["company_name"] == "FlowTest AI"
        assert res["target_url"] == "https://flowtest.ai"
        assert res["primary_lead_name"] == "Elena Rostova"
        assert res["pitch_angle"] == "CUSTOM_ML_AUDIT"
        assert res["pitch_subject"] == "Fixing search latency at FlowTest"
        assert res["negotiation_stage"] in ("NEGOTIATING", "CLOSED_WON", "HITL_HANDOVER", "SENT")
