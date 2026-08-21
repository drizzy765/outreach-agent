from agents.pitcher import ValueAddPitcherAgent

def test_custom_ml_pitch_generation():
    pitcher = ValueAddPitcherAgent()
    pitch = pitcher.generate_pitch(
        lead_name="Alex Mercer",
        lead_role="CTO",
        company_name="DataStore",
        website_url="https://datastore.io",
        audit_findings={"ttfb_ms": 340, "recommended_pitch_angle": "CUSTOM_ML_AUDIT"}
    )
    assert "DataStore" in pitch["subject"]
    assert "vector search microservice" in pitch["body"]
    assert pitch["pitch_type"] == "CUSTOM_ML_AUDIT"

def test_quantvault_pitch_generation():
    pitcher = ValueAddPitcherAgent()
    pitch = pitcher.generate_pitch(
        lead_name="Elena Rostova",
        lead_role="Head of Trading",
        company_name="AlphaQuant",
        website_url="https://alphaquant.io",
        audit_findings={"ttfb_ms": 110, "recommended_pitch_angle": "QUANTVAULT_DEMO"}
    )
    assert "analytics & voice workflows" in pitch["subject"]
    assert "QuantVault" in pitch["body"]
    assert pitch["pitch_type"] == "QUANTVAULT_DEMO"
