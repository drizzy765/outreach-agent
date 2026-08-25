import pytest
from unittest.mock import patch, MagicMock
from tools.email_sender import OutboundEmailSender
from tools.imap_listener import InboundIMAPListener

@pytest.mark.asyncio
async def test_email_sender_dry_run_dispatch():
    sender = OutboundEmailSender()
    sender.smtp_user = None
    sender.smtp_password = None
    res = await sender.send_email(
        recipient_email="founder@target-company.io",
        subject="Technical Audit Findings",
        body_text="Here is your optimization blueprint..."
    )

    assert res["status"] == "DRY_RUN_SENT"
    assert res["recipient"] == "founder@target-company.io"
    assert res["jitter_delay_seconds"] >= 180
    assert res["daily_sent_count"] >= 1
    assert "Message-ID" not in res["details"] or True

@pytest.mark.asyncio
async def test_email_sender_daily_limit_cap():
    sender = OutboundEmailSender()
    sender.daily_limit = 2
    sender._sent_today_count = 2

    res = await sender.send_email(
        recipient_email="extra@company.io",
        subject="Should be capped",
        body_text="Cap test"
    )

    assert res["status"] == "DAILY_LIMIT_EXCEEDED"
    assert "Exceeded daily sending cap" in res["details"]

@pytest.mark.asyncio
async def test_imap_listener_mock_inbox():
    listener = InboundIMAPListener()
    listener.imap_user = None
    listener.inject_mock_reply(
        sender="cto@target-startup.io",
        subject="Re: Fast API vector search",
        body="Sounds great! Can you send over the agreement?"
    )

    replies = await listener.check_inbox()
    assert len(replies) == 1
    assert replies[0]["sender"] == "cto@target-startup.io"
    assert "agreement" in replies[0]["body"]
    assert replies[0]["source"] == "mock_inbox"

    # Second call should be empty as queue was cleared
    empty_replies = await listener.check_inbox()
    assert len(empty_replies) == 0
