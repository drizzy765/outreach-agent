import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tools.telegram_bot import send_telegram_alert, send_hitl_escalation, celebrate_gig_won, TelegramBotHandler
from config import settings

@pytest.mark.asyncio
async def test_telegram_mock_alert():
    with patch.object(settings, "telegram_bot_token", ""):
        res = await send_telegram_alert("Test alert message")
        assert res is False

@pytest.mark.asyncio
async def test_celebrate_gig_won_mock():
    with patch.object(settings, "telegram_bot_token", ""):
        res = await celebrate_gig_won(
            lead_name="Alex Mercer",
            company_name="DataSync",
            rate=5500.0,
            pitch_type="Custom Vector Search"
        )
        assert res is False

@pytest.mark.asyncio
async def test_send_hitl_escalation_mock():
    with patch.object(settings, "telegram_bot_token", ""):
        res = await send_hitl_escalation(
            conversation_id="conv-123",
            lead_name="Elon",
            company_name="X Corp",
            reason="Discount requested below floor",
            last_message="Can we do $3,000 for this?",
            proposed_rate=3000.0
        )
        assert res is False

@pytest.mark.asyncio
async def test_telegram_message_commands():
    handler = TelegramBotHandler()
    res_help = await handler.handle_message_command("/help", "Admin")
    assert "Autonomous Outreach" in res_help
    assert "/find" in res_help

    res_stats = await handler.handle_message_command("/stats", "Admin")
    assert "CRM Pipeline Dashboard" in res_stats

@pytest.mark.asyncio
async def test_telegram_bot_handler_actions():
    handler = TelegramBotHandler()

    with patch("tools.telegram_bot.AsyncSessionLocal") as mock_session_cls,          patch("tools.telegram_bot.send_telegram_alert", new_callable=AsyncMock) as mock_alert:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        mock_conv = MagicMock()
        mock_conv.id = "11111111-1111-1111-1111-111111111111"
        mock_conv.stage = "HITL_HANDOVER"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_result

        # Test approve action
        res_approve = await handler.handle_callback_action(
            callback_data="approve:11111111-1111-1111-1111-111111111111:4500",
            operator_name="DevOpsLead"
        )
        assert res_approve["status"] == "PROCESSED"
        assert mock_conv.stage == "DISCOUNT_APPROVED"
        assert mock_conv.agreed_rate == 4500.0
        assert mock_conv.human_override_required is False

        # Test counter action
        res_counter = await handler.handle_callback_action(
            callback_data="counter:11111111-1111-1111-1111-111111111111:5000",
            operator_name="DevOpsLead"
        )
        assert res_counter["status"] == "PROCESSED"
        assert mock_conv.stage == "COUNTER_OFFERED"
        assert mock_conv.agreed_rate == 5000.0

        # Test takeover action
        res_takeover = await handler.handle_callback_action(
            callback_data="takeover:11111111-1111-1111-1111-111111111111",
            operator_name="DevOpsLead"
        )
        assert res_takeover["status"] == "PROCESSED"
        assert mock_conv.stage == "MANUAL_TAKEOVER"
        assert mock_conv.human_override_required is True
