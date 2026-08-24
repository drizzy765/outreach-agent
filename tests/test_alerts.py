import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agents.alerts import NotificationDispatcherAgent

@pytest.mark.asyncio
async def test_dispatch_stage_update_closed_won():
    agent = NotificationDispatcherAgent()

    with patch("agents.alerts.AsyncSessionLocal") as mock_session_cls,          patch("agents.alerts.celebrate_gig_won", new_callable=AsyncMock) as mock_celeb:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        mock_lead = MagicMock()
        mock_lead.full_name = "Sarah Connor"
        mock_lead.email = "sarah@cyberdyne.com"

        mock_comp = MagicMock()
        mock_comp.company_name = "Cyberdyne Systems"

        mock_conv = MagicMock()
        mock_conv.pitch_type = "Custom Vector Search"

        mock_res_lead = MagicMock()
        mock_res_lead.scalar_one_or_none.return_value = mock_lead
        mock_res_comp = MagicMock()
        mock_res_comp.scalar_one_or_none.return_value = mock_comp
        mock_res_conv = MagicMock()
        mock_res_conv.scalar_one_or_none.return_value = mock_conv

        mock_session.execute.side_effect = [mock_res_lead, mock_res_comp, mock_res_conv]

        res = await agent.dispatch_stage_update(
            conversation_id="11111111-1111-1111-1111-111111111111",
            lead_id="22222222-2222-2222-2222-222222222222",
            company_id="33333333-3333-3333-3333-333333333333",
            stage="CLOSED_WON",
            message_content="Let's sign the contract and start.",
            agreed_rate=6500.0
        )

        assert res["stage"] == "CLOSED_WON"
        assert res["status"] == "DISPATCHED"
        assert res["invoicing"] is not None
        assert res["invoicing"]["deposit_amount"] == 3250.0  # 50% milestone
        mock_celeb.assert_called_once()

@pytest.mark.asyncio
async def test_dispatch_stage_update_hitl_escalation():
    agent = NotificationDispatcherAgent()

    with patch("agents.alerts.AsyncSessionLocal") as mock_session_cls,          patch("agents.alerts.send_hitl_escalation", new_callable=AsyncMock) as mock_hitl:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_res

        res = await agent.dispatch_stage_update(
            conversation_id="11111111-1111-1111-1111-111111111111",
            lead_id="22222222-2222-2222-2222-222222222222",
            company_id="33333333-3333-3333-3333-333333333333",
            stage="HITL_HANDOVER",
            message_content="We only have 000 budget",
            agreed_rate=None,
            human_override_required=True,
            override_reason="Below rate floor"
        )

        assert res["stage"] == "HITL_HANDOVER"
        mock_hitl.assert_called_once()
