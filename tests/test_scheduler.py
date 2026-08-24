import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from workflow.scheduler import AutonomousOutreachScheduler

@pytest.mark.asyncio
async def test_scheduler_inbound_replies_job():
    scheduler = AutonomousOutreachScheduler()

    mock_replies = [
        {
            "sender": "alex@startup.io",
            "subject": "Re: Technical audit",
            "body": "Sounds great, let's do it. Send over contract.",
            "thread_id": "thread-123"
        }
    ]

    with patch.object(scheduler.imap_listener, "check_inbox", new_callable=AsyncMock) as mock_inbox,          patch("workflow.scheduler.AsyncSessionLocal") as mock_session_cls,          patch.object(scheduler.alerts_agent, "dispatch_stage_update", new_callable=AsyncMock) as mock_dispatch:

        mock_inbox.return_value = mock_replies

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        mock_conv = MagicMock()
        mock_conv.id = "11111111-1111-1111-1111-111111111111"
        mock_lead = MagicMock()
        mock_lead.id = "22222222-2222-2222-2222-222222222222"
        mock_lead.full_name = "Alex Mercer"
        mock_company = MagicMock()
        mock_company.id = "33333333-3333-3333-3333-333333333333"
        mock_company.company_name = "Startup IO"

        mock_res = MagicMock()
        mock_res.first.return_value = (mock_conv, mock_lead, mock_company)
        mock_session.execute.return_value = mock_res

        mock_dispatch.return_value = {"status": "DISPATCHED", "stage": "CLOSED_WON"}

        results = await scheduler.check_inbound_replies_job()

        assert len(results) == 1
        assert results[0]["stage"] == "CLOSED_WON"

@pytest.mark.asyncio
async def test_scheduler_followup_sequencing_job():
    scheduler = AutonomousOutreachScheduler()

    with patch("workflow.scheduler.AsyncSessionLocal") as mock_session_cls,          patch("workflow.scheduler.send_telegram_alert", new_callable=AsyncMock) as mock_alert:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        mock_conv = MagicMock()
        mock_conv.id = "11111111-1111-1111-1111-111111111111"
        mock_lead = MagicMock()
        mock_lead.email = "founder@slowstartup.io"
        mock_lead.full_name = "Bob Miller"
        mock_company = MagicMock()
        mock_company.company_name = "SlowStartup"

        mock_res = MagicMock()
        mock_res.all.return_value = [(mock_conv, mock_lead, mock_company)]
        mock_session.execute.return_value = mock_res

        results = await scheduler.run_followup_sequencing_job(days_threshold=3)

        assert len(results) == 1
        assert results[0]["status"] == "FOLLOWED_UP"
        assert mock_conv.stage == "FOLLOWED_UP"
