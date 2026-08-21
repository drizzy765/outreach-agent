import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ValueAddPitcherAgent:
    """
    Agent 4: Value-Add Pitch & Product Showcase Agent
    Drafts highly personalized, problem-first cold outreach:
    - Angle A (Custom ML/AI Engineering): Decoupled FastAPI vector search microservice cutting latency by 60%.
    - Angle B (Product-Led Pitch — QuantVault): Agentic voice command center for financial & telemetry pipelines.
    """

    def generate_pitch(
        self,
        lead_name: str,
        lead_role: str,
        company_name: str,
        website_url: str,
        audit_findings: Dict[str, Any],
        pitch_angle: Optional[str] = None
    ) -> Dict[str, str]:
        """Craft personalized pitch tailored to company diagnostics."""
        first_name = lead_name.split()[0] if lead_name else "there"
        chosen_angle = pitch_angle or audit_findings.get("recommended_pitch_angle", "CUSTOM_ML_AUDIT")
        ttfb = audit_findings.get("ttfb_ms", 120)

        if chosen_angle == "QUANTVAULT_DEMO":
            subject = f"Quick question regarding {company_name}'s analytics & voice workflows"
            body = f"""Hi {first_name},

I took a close look at {company_name}'s analytics platform ({website_url}) and was really impressed by your market focus.

While analyzing your user workflow, I noticed your data telemetry currently lacks a low-latency agentic voice command center for real-time querying.

I recently built QuantVault — an open-architecture agent that plugs directly into quantitative & telemetry pipelines, enabling natural voice querying and real-time risk alerts in under 200ms.

Here is a 15-second interactive demonstration of how it integrates with platforms like {company_name}:
👉 https://quantvault-demo.io/showcase

Would you be open to a 10-minute coffee chat next Tuesday at 2 PM to explore if this could boost user retention on {company_name}?

Best regards,
Autonomous Outreach Engine
"""
        else: # Angle A: Custom ML/AI Engineering
            subject = f"Technical audit findings & vector search latency on {company_name}"
            body = f"""Hi {first_name},

I ran a performance and architecture diagnostic on {company_name} ({website_url}) and noticed an engineering bottleneck: your search engine relies on basic keyword matching with an average query TTFB of ~{ttfb}ms.

I specialize in building decoupled FastAPI + Qdrant/Milvus vector search microservices that implement semantic reranking and cut search latency by over 60%.

I put together a quick architecture blueprint showing how this can be deployed alongside your existing stack with zero downtime:
👉 https://architecture-blueprints.io/{company_name.lower().replace(' ', '-')}-optimization

Are you free for a brief 10-minute chat this Thursday to discuss whether implementing this makes sense for your engineering roadmap?

Best regards,
Autonomous Outreach Engine
"""

        return {
            "subject": subject,
            "body": body,
            "pitch_type": chosen_angle
        }
