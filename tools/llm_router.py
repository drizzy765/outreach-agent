import re
import json
import httpx
import logging
from typing import Dict, Any, List, Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)

class LLMRouter:
    """
    Multi-Provider Free-Tier LLM Fallback Router.
    Cascades across free-tier & local model endpoints:
    1. OpenRouter Free Tier (meta-llama/llama-3.3-70b-instruct:free, etc.)
    2. Groq Free Tier (llama-3.3-70b-versatile)
    3. NVIDIA NIM Free Tier (meta/llama-3.3-70b-instruct)
    4. Google Gemini Free Tier (gemini-2.0-flash)
    5. Local Ollama (localhost:11434)
    6. Deterministic Offline Blueprint Synthesizer (Zero token fallback)
    """

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def _get_provider_endpoints(self) -> List[Dict[str, Any]]:
        """Construct ordered list of active providers based on available keys and defaults."""
        endpoints = []

        # 1. OpenRouter Free Tier
        if settings.openrouter_api_key:
            endpoints.append({
                "name": "openrouter",
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "api_key": settings.openrouter_api_key,
                "model": settings.default_free_model,
                "headers": {
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://github.com/drizzy765/outreach-agent",
                    "X-Title": "Autonomous Outreach Engine"
                }
            })

        # 2. Groq Free Tier
        if settings.groq_api_key:
            endpoints.append({
                "name": "groq",
                "base_url": "https://api.groq.com/openai/v1/chat/completions",
                "api_key": settings.groq_api_key,
                "model": settings.default_groq_model,
                "headers": {
                    "Authorization": f"Bearer {settings.groq_api_key}"
                }
            })

        # 3. NVIDIA NIM Free Tier
        if settings.nvidia_api_key:
            endpoints.append({
                "name": "nvidia",
                "base_url": "https://integrate.api.nvidia.com/v1/chat/completions",
                "api_key": settings.nvidia_api_key,
                "model": settings.default_nvidia_model,
                "headers": {
                    "Authorization": f"Bearer {settings.nvidia_api_key}"
                }
            })

        # 4. Google Gemini OpenAI-compatible endpoint
        gemini_key = settings.google_api_key or settings.gemini_api_key
        if gemini_key:
            endpoints.append({
                "name": "gemini",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                "api_key": gemini_key,
                "model": settings.default_gemini_model,
                "headers": {
                    "Authorization": f"Bearer {gemini_key}"
                }
            })

        # 5. Custom OpenAI-compatible Base URL
        if settings.custom_llm_base_url:
            endpoints.append({
                "name": "custom",
                "base_url": f"{settings.custom_llm_base_url.rstrip('/')}/chat/completions",
                "api_key": settings.custom_llm_api_key or "sk-dummy",
                "model": settings.default_model,
                "headers": {
                    "Authorization": f"Bearer {settings.custom_llm_api_key or 'sk-dummy'}"
                }
            })

        # 6. Local Ollama
        if settings.ollama_base_url:
            endpoints.append({
                "name": "ollama",
                "base_url": f"{settings.ollama_base_url.rstrip('/')}/chat/completions",
                "api_key": "ollama",
                "model": "llama3.2",
                "headers": {}
            })

        return endpoints

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 600
    ) -> Tuple[Optional[str], str]:
        """
        Attempts completion across provider fallback hierarchy.
        Returns: (generated_text, provider_used)
        """
        endpoints = self._get_provider_endpoints()

        for ep in endpoints:
            try:
                payload = {
                    "model": ep["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                async with httpx.AsyncClient(headers=ep["headers"], timeout=self.timeout) as client:
                    resp = await client.post(ep["base_url"], json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            if content:
                                return content, f"{ep['name']}:{ep['model']}"
                    else:
                        logger.warning(f"Provider {ep['name']} returned status {resp.status_code}: {resp.text[:120]}")
            except Exception as e:
                logger.debug(f"Provider {ep['name']} failed, cascading: {e}")
                continue

        # Zero-token offline fallback
        return None, "offline_fallback"

    def synthesize_deterministic_pitch(
        self,
        lead_name: str,
        lead_role: str,
        company_name: str,
        website_url: str,
        audit_findings: Dict[str, Any],
        pitch_angle: str
    ) -> Dict[str, str]:
        """
        Intelligent offline synthesizer.
        Dynamically crafts bespoke pitches with exact metrics and architecture blueprints without API tokens.
        """
        first_name = lead_name.split()[0] if lead_name and lead_name != "Founder" else "there"
        role_title = lead_role if lead_role else "Engineering Leadership"
        ttfb = audit_findings.get("ttfb_ms", 180.0)
        load_time = audit_findings.get("load_time_ms", 350.0)
        detected_apis = ", ".join(audit_findings.get("detected_apis", [])) or "Postgres / Next.js"
        search_gap = audit_findings.get("search_gap_detected", True)

        if pitch_angle == "QUANTVAULT_DEMO":
            subject = f"Quick question regarding {company_name}'s telemetry & voice workflows"
            blueprint = f"""
┌────────────────────────────────────────────────────────┐
│             QUANTVAULT WEBRTC VOICE PIPELINE           │
│                                                        │
│  [User Voice / Telemetry] ──► [WebRTC Audio Stream]    │
│                                        │               │
│                                        ▼               │
│  [Real-Time Risk Alerts] ◄── [QuantVault Telemetry]    │
│   (<180ms Latency SLA)        (Async Sub-200ms Core)   │
└────────────────────────────────────────────────────────┘
"""
            body = f"""Hi {first_name},

I took a deep dive into {company_name}'s analytics platform ({website_url}) and was impressed by your market positioning in quantitative telemetry.

While analyzing your user interaction pipeline (load time: ~{load_time}ms), I noticed your platform currently lacks a low-latency agentic voice command interface for real-time risk querying.

I recently built QuantVault — an open-architecture agent that connects directly to analytics streams, enabling sub-200ms natural voice querying and automated telemetry alerts.

Here is a 15-second interactive demonstration showing how it plugs into stacks like {company_name}:
👉 https://quantvault-demo.io/showcase

{blueprint}

Would you be open to a brief 10-minute chat next Tuesday at 2 PM to explore whether this could elevate engagement for {company_name}'s users?

Best regards,
Autonomous Outreach Engine
"""
        else: # CUSTOM_ML_AUDIT
            subject = f"Technical audit findings & vector search latency on {company_name}"
            blueprint = f"""
┌────────────────────────────────────────────────────────┐
│            DECOUPLED VECTOR SEARCH MICROSERVICE        │
│                                                        │
│  [Client App] ──► [FastAPI Middleware] ──► [Qdrant]    │
│                        │ (Semantic Rerank)     │       │
│                        ▼                       ▼       │
│               [Postgres Core DB] ◄── [Embedding Cache] │
│               (Zero Schema Impact)   (<60ms Latency)   │
└────────────────────────────────────────────────────────┘
"""
            body = f"""Hi {first_name},

I ran a performance diagnostic on {company_name} ({website_url}) and noticed an engineering opportunity: your search engine relies on basic keyword matching with an average query TTFB of ~{ttfb}ms ({detected_apis}).

I specialize in building decoupled FastAPI + Qdrant vector search microservices that implement semantic reranking and cut search latency by over 60% with zero downtime to your existing database.

Here is a tailored architecture blueprint designed specifically for {company_name}:

{blueprint}

Are you free for a brief 10-minute chat this Thursday to discuss whether implementing this makes sense for your engineering roadmap?

Best regards,
Autonomous Outreach Engine
"""

        return {
            "subject": subject,
            "body": body,
            "blueprint_snippet": blueprint.strip(),
            "pitch_type": pitch_angle,
            "provider_used": "deterministic_offline_synthesizer"
        }
