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
    # Floor is 5000, prospect offers 2000
    res = agent.process_reply(
        lead_name="John Doe",
        company_name="Acme Corp",
        incoming_reply="We only have a budget of $2000 for this project.",
        current_quoted_rate=6500.0
    )
    assert res["stage"] == "HITL_HANDOVER"
    assert res["human_override_required"] is True
    assert "below our hard floor" in res["override_reason"]

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
