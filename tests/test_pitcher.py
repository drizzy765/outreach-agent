import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from agents.pitcher import ValueAddPitcherAgent
from tools.llm_router import LLMRouter

def test_ai_engineer_pitch_generation_sync():
    pitcher = ValueAddPitcherAgent()
    pitch = pitcher.generate_pitch(
        lead_name="Alex Mercer",
        lead_role="CTO",
        company_name="DataStore",
        website_url="https://datastore.io",
        audit_findings={"ttfb_ms": 340, "recommended_pitch_angle": "CUSTOM_ML_AUDIT"}
    )
    assert "DataStore" in pitch["subject"]
    assert "vector" in pitch["body"].lower() or "microservice" in pitch["body"].lower()
    assert "DECOUPLED VECTOR RETRIEVAL PIPELINE" in pitch.get("blueprint_snippet", "")

@pytest.mark.asyncio
async def test_llm_router_openrouter_mock():
    pitcher = ValueAddPitcherAgent()
    fake_json_reply = """```json
    {
      "subject": "Quick architecture idea for HighScale search latency",
      "body": "Hi Alex, noticed your TTFB is 450ms. Here is how a Qdrant microservice helps.",
      "blueprint_snippet": "[Client] -> [FastAPI] -> [Qdrant]"
    }
    ```"""

    with patch.object(LLMRouter, "generate_completion", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = (fake_json_reply, "openrouter:meta-llama/llama-3.3-70b-instruct:free")
        
        draft = await pitcher.generate_pitch_async(
            lead_name="Alex Mercer",
            lead_role="CTO",
            company_name="HighScale",
            website_url="https://highscale.io",
            audit_findings={"ttfb_ms": 450, "recommended_pitch_angle": "CUSTOM_ML_AUDIT"}
        )

        assert "HighScale" in draft["subject"]
        assert "Qdrant" in draft["body"]
        assert draft["provider_used"] == "openrouter:meta-llama/llama-3.3-70b-instruct:free"

@pytest.mark.asyncio
async def test_llm_router_offline_synthesizer_fallback():
    pitcher = ValueAddPitcherAgent()
    with patch.object(LLMRouter, "generate_completion", new_callable=AsyncMock) as mock_complete:
        # Simulate network error / all free providers down
        mock_complete.return_value = (None, "offline_fallback")
        
        draft = await pitcher.generate_pitch_async(
            lead_name="Marcus Vance",
            lead_role="VP of Engineering",
            company_name="CloudMatrix",
            website_url="https://cloudmatrix.io",
            audit_findings={"ttfb_ms": 280, "load_time_ms": 500, "recommended_pitch_angle": "CUSTOM_ML_AUDIT"}
        )

        assert "CloudMatrix" in draft["subject"]
        assert "vector" in draft["body"].lower() or "microservice" in draft["body"].lower()
        assert draft["provider_used"] == "deterministic_offline_synthesizer"
