import re
import json
import logging
from typing import Dict, Any, Optional
from tools.llm_router import LLMRouter

logger = logging.getLogger(__name__)

PITCH_SYSTEM_PROMPT = """You are an elite AI Engineering Consultant & Principal Architect.
You write hyper-personalized, value-first, problem-solving cold outreach emails to founders and CTOs.

Rules for outreach:
1. Under 150 words. Zero fluff, zero generic sales buzzwords.
2. Directly reference specific technical bottlenecks found during website diagnostic audit (TTFB latency, basic SQL keyword search, missing voice/telemetry agent).
3. Offer an immediate tangible solution:
   - Angle A (CUSTOM_ML_AUDIT): Decoupled FastAPI + Qdrant vector search microservice cutting latency by 60%.
   - Angle B (QUANTVAULT_DEMO): QuantVault real-time WebRTC voice & risk telemetry command center.
4. Output JSON strictly matching format:
{
  "subject": "Compelling subject line",
  "body": "Personalized email body",
  "blueprint_snippet": "ASCII or architecture summary"
}
"""

class ValueAddPitcherAgent:
    """
    Agent 4: Dynamic Free-Tier LLM Pitch & Blueprint Showcase Agent
    Synthesizes technical diagnostics into bespoke outreach using:
    - Multi-provider free tier router (OpenRouter, Groq, NVIDIA NIM, Google Gemini, Ollama)
    - Zero-token deterministic architecture synthesizer fallback
    """

    def __init__(self):
        self.router = LLMRouter()

    async def generate_pitch_async(
        self,
        lead_name: str,
        lead_role: str,
        company_name: str,
        website_url: str,
        audit_findings: Dict[str, Any],
        pitch_angle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate hyper-personalized pitch using LLM fallback router or intelligent offline synthesizer.
        """
        first_name = lead_name.split()[0] if lead_name and lead_name != "Founder" else "there"
        chosen_angle = pitch_angle or audit_findings.get("recommended_pitch_angle", "CUSTOM_ML_AUDIT")
        ttfb = audit_findings.get("ttfb_ms", 180.0)
        load_time = audit_findings.get("load_time_ms", 350.0)
        detected_apis = ", ".join(audit_findings.get("detected_apis", [])) or "Postgres"

        user_prompt = f"""Target Company: {company_name} ({website_url})
Recipient: {first_name} ({lead_role or 'Founder'})
Diagnostic Findings:
- TTFB Latency: {ttfb}ms
- Page Load Time: {load_time}ms
- Detected Stack / APIs: {detected_apis}
- Search Gap: {audit_findings.get('search_gap_detected', True)} ({audit_findings.get('search_diagnosis', 'SQL Substring')})
- AI Voice/Telemetry Gap: {audit_findings.get('ai_agent_gap_detected', True)}
- Pitch Angle: {chosen_angle}

Write the hyper-personalized pitch following the system rules. Return JSON only."""

        # 1. Attempt LLM generation across free providers
        content, provider = await self.router.generate_completion(
            system_prompt=PITCH_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3
        )

        if content and provider != "offline_fallback":
            try:
                # Find JSON block enclosed in { ... }
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if "subject" in parsed and "body" in parsed:
                        return {
                            "subject": parsed["subject"],
                            "body": parsed["body"],
                            "blueprint_snippet": parsed.get("blueprint_snippet", ""),
                            "pitch_type": chosen_angle,
                            "provider_used": provider
                        }
            except Exception as e:
                logger.debug(f"LLM JSON parsing failed, using synthesizer: {e}")

        # 2. Resilient Deterministic Synthesizer Fallback
        return self.router.synthesize_deterministic_pitch(
            lead_name=lead_name,
            lead_role=lead_role,
            company_name=company_name,
            website_url=website_url,
            audit_findings=audit_findings,
            pitch_angle=chosen_angle
        )

    def generate_pitch(
        self,
        lead_name: str,
        lead_role: str,
        company_name: str,
        website_url: str,
        audit_findings: Dict[str, Any],
        pitch_angle: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for backwards compatibility."""
        chosen_angle = pitch_angle or audit_findings.get("recommended_pitch_angle", "CUSTOM_ML_AUDIT")
        return self.router.synthesize_deterministic_pitch(
            lead_name=lead_name,
            lead_role=lead_role,
            company_name=company_name,
            website_url=website_url,
            audit_findings=audit_findings,
            pitch_angle=chosen_angle
        )
