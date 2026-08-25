from agents.negotiation import NegotiationEngineAgent

def test_acceptance_flow():
    agent = NegotiationEngineAgent()
    res = agent.process_reply(
        lead_name="Sarah Connor",
        company_name="Cyberdyne",
        incoming_reply="Sounds great, let's do it. Send over the invoice and contract.",
        current_quoted_rate=6500.0
    )
    assert res["stage"] == "CLOSED_WON"
    assert res["human_override_required"] is False
    assert res["agreed_rate"] == 6500.0

def test_below_floor_negotiation_triggers_hitl():
    agent = NegotiationEngineAgent()
    # Micro-floor is < 500, prospect offers 300
    res = agent.process_reply(
        lead_name="John Doe",
        company_name="Acme Corp",
        incoming_reply="We only have a budget of $300 for this project.",
        current_quoted_rate=6500.0
    )
    assert res["stage"] == "HITL_HANDOVER"
    assert res["human_override_required"] is True
    assert "below $500 micro-tier" in res["override_reason"]

def test_sprint_mvp_tier_negotiation():
    agent = NegotiationEngineAgent()
    # Prospect offers $2,000 -> Never turns away, triggers Phase 1 Sprint MVP
    res = agent.process_reply(
        lead_name="Marcus Aurelius",
        company_name="Rome AI",
        incoming_reply="We have a budget of $2000 for this project.",
        current_quoted_rate=6500.0
    )
    assert res["stage"] == "NEGOTIATING"
    assert res["human_override_required"] is False
    assert res["agreed_rate"] == 2000.0
    assert "Phase 1 Sprint" in res["response_text"]

def test_custom_contract_triggers_hitl():
    agent = NegotiationEngineAgent()
    res = agent.process_reply(
        lead_name="Alice Smith",
        company_name="FinCorp",
        incoming_reply="We need your team to sign our custom Enterprise MSA and NDA indemnity terms.",
        current_quoted_rate=6500.0
    )
    assert res["stage"] == "HITL_HANDOVER"
    assert res["human_override_required"] is True
    assert "custom contract" in res["override_reason"]

def test_bounded_discount_acceptance():
    agent = NegotiationEngineAgent()
    res = agent.process_reply(
        lead_name="Bob Miller",
        company_name="SaaSify",
        incoming_reply="Can you do any discount on this initial package?",
        current_quoted_rate=6000.0
    )
    assert res["stage"] == "NEGOTIATING"
    assert res["human_override_required"] is False
    # Max discount is 10% -> 6000 * 0.9 = 5400
    assert res["agreed_rate"] == 5400.0

import pytest

@pytest.mark.asyncio
async def test_scope_expansion_triggers_hitl():
    agent = NegotiationEngineAgent()
    res = await agent.process_reply_async(
        lead_name="Derrick Rose",
        company_name="Apex App",
        incoming_reply="Can you also build a complete mobile app for iOS and Android as part of this?",
        current_quoted_rate=6500.0
    )
    assert res["stage"] == "HITL_HANDOVER"
    assert res["human_override_required"] is True
    assert "out-of-scope" in res["override_reason"]

@pytest.mark.asyncio
async def test_technical_question_negotiation_async():
    agent = NegotiationEngineAgent()
    res = await agent.process_reply_async(
        lead_name="Liam Neeson",
        company_name="Security Labs",
        incoming_reply="How does this vector service integrate with our existing Postgres schema without migration locks?",
        current_quoted_rate=6500.0
    )
    assert res["stage"] == "NEGOTIATING"
    assert res["human_override_required"] is False
    assert "architecture" in res["response_text"].lower() or "service" in res["response_text"].lower()
