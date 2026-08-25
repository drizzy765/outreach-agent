import re
import json
import logging
from typing import Dict, Any, Optional
from tools.llm_router import LLMRouter

from config import settings

logger = logging.getLogger(__name__)

PITCH_SYSTEM_PROMPT = """You are an ambitious, high-agency AI/ML Engineer with deep expertise in high-performance FastAPI microservices, Qdrant vector search, Redis caching, and LLM systems.
You write hyper-personalized, technical, problem-solving cold outreach emails to founders and CTOs using proven B2B engineering outreach psychology.

Strict Psychological & Writing Rules:
1. Under 150 words. Zero sales fluff, zero generic compliments, zero buzzwords ("synergy", "revolutionize").
2. Pattern Interrupt Opening: Open directly with an engineering observation about their actual platform (e.g. latency, prompt caching, search intent drop-off).
3. De-Risking Upfront: Explicitly emphasize zero core schema changes, non-blocking async architecture, and no rip-and-replace.
4. Business / FinOps ROI: Clearly state the tangible benefit (e.g. cutting LLM API costs by 40-60%, dropping P99 latency to <45ms, or boosting search conversion).
5. Frictionless CTA: Ask a low-friction interest question (e.g. "Open to taking a look at a 2-minute architecture breakdown on GitHub?" or "Worth a quick 5-minute chat to compare notes?").
6. Include portfolio (GitHub) and resume (LinkedIn) links.
7. Return JSON strictly matching:
{
  "subject": "Direct, curiosity-inducing technical subject line",
  "body": "Personalized email body",
  "blueprint_snippet": "Tailored ASCII architecture box diagram"
}
"""

class ValueAddPitcherAgent:
    """
    Agent 4: Dynamic Free-Tier LLM Pitch & Blueprint Showcase Agent
    Synthesizes technical diagnostics into bespoke outreach using:
    - Multi-provider free tier router (Groq, OpenRouter, NVIDIA NIM, Google Gemini)
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
        sender_name = getattr(settings, "sender_name", "Timilehin Agoro")
        sender_title = getattr(settings, "sender_title", "AI / ML Engineer")
        portfolio = getattr(settings, "sender_portfolio_url", "https://github.com/drizzy765")
        resume = getattr(settings, "sender_resume_url", "https://linkedin.com/in/timilehin-agoro")

        user_prompt = f"""Sender Profile: {sender_name}, {sender_title}
Portfolio: {portfolio} | Resume: {resume}

Target Company: {company_name} ({website_url})
Recipient: {first_name} ({lead_role or 'Engineering Team'})
Diagnostic Findings:
- TTFB Latency: {ttfb}ms | Page Load Time: {load_time}ms
- Detected Stack / APIs: {detected_apis}
- Search Gap: {audit_findings.get('search_gap_detected', True)} ({audit_findings.get('search_diagnosis', 'SQL Substring')})
- AI / Automation Gap: {audit_findings.get('ai_agent_gap_detected', True)}

Write a concise, compelling technical pitch offering to build a working solution for {company_name}. Return JSON only."""

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
