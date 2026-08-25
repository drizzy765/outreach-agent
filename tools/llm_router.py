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

        # 1. Groq Free Tier (Ultra-fast, standard models)
        if settings.groq_api_key:
            for model_name in [settings.default_groq_model, "llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama3-70b-8192"]:
                endpoints.append({
                    "name": f"groq ({model_name})",
                    "base_url": "https://api.groq.com/openai/v1/chat/completions",
                    "api_key": settings.groq_api_key,
                    "model": model_name,
                    "headers": {
                        "Authorization": f"Bearer {settings.groq_api_key}"
                    }
                })

        # 2. OpenRouter Free Tier (Cascading active free models)
        if settings.openrouter_api_key:
            for model_name in [settings.default_free_model, "meta-llama/llama-3.1-8b-instruct:free", "qwen/qwen-2.5-coder-32b-instruct:free", "deepseek/deepseek-r1:free", "google/gemini-2.0-flash-exp:free"]:
                endpoints.append({
                    "name": f"openrouter ({model_name})",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions",
                    "api_key": settings.openrouter_api_key,
                    "model": model_name,
                    "headers": {
                        "Authorization": f"Bearer {settings.openrouter_api_key}",
                        "HTTP-Referer": "https://github.com/drizzy765/outreach-agent",
                        "X-Title": "Autonomous Outreach Engine"
                    }
                })

        # 3. Google Gemini Free Tier
        gemini_key = settings.google_api_key or settings.gemini_api_key
        if gemini_key:
            for model_name in [settings.default_gemini_model, "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]:
                endpoints.append({
                    "name": f"gemini ({model_name})",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    "api_key": gemini_key,
                    "model": model_name,
                    "headers": {
                        "Authorization": f"Bearer {gemini_key}"
                    }
                })

        # 4. NVIDIA NIM Free Tier
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

        # 5. Custom OpenAI-compatible Base URL
        if settings.custom_llm_base_url:
            endpoints.append({
                "name": "custom",
                "base_url": f"{settings.custom_llm_base_url.rstrip('/')}/chat/completions",
                "api_key": settings.custom_llm_api_key or "sk-dummy",
                "model": "gpt-3.5-turbo",
                "headers": {
                    "Authorization": f"Bearer {settings.custom_llm_api_key or 'sk-dummy'}"
                }
            })

        # 6. Local Ollama (only if configured)
        if settings.ollama_base_url and settings.ollama_base_url.strip():
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
                                return content, f"{ep['name']}"
                    else:
                        logger.debug(f"Provider {ep['name']} returned status {resp.status_code}: {resp.text[:100]}")
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
        pitch_angle: str = "CUSTOM_ML_AUDIT"
    ) -> Dict[str, str]:
        """
        Intelligent offline synthesizer.
        Positions the sender as an AI/ML Engineer proposing a bespoke technical solution.
        """
        first_name = lead_name.split()[0] if lead_name and lead_name != "Founder" else "there"
        ttfb = audit_findings.get("ttfb_ms", 180.0)
        load_time = audit_findings.get("load_time_ms", 350.0)
        detected_apis = ", ".join(audit_findings.get("detected_apis", [])) or "Modern Web Stack"
        search_diagnosis = audit_findings.get("search_diagnosis", "Standard Keyword Matching")

        sender_name = getattr(settings, "sender_name", "Timilehin Agoro")
        sender_title = getattr(settings, "sender_title", "AI / ML Engineer")
        portfolio_url = getattr(settings, "sender_portfolio_url", "https://github.com/drizzy765")
        resume_url = getattr(settings, "sender_resume_url", "https://linkedin.com/in/timilehin-agoro")

        subject = f"Engineered solution for {company_name}'s search & latency architecture"
        blueprint = f"""
┌────────────────────────────────────────────────────────┐
│            DECOUPLED VECTOR RETRIEVAL PIPELINE         │
│                                                        │
│  [Client App] ──► [FastAPI Async Core] ──► [Qdrant]    │
│                        │ (Semantic Rerank)     │       │
│                        ▼                       ▼       │
│               [Primary DB] ◄── [Embedding Cache Layer] │
│               (Zero Downtime)     (<45ms Query Latency)│
└────────────────────────────────────────────────────────┘
"""
        body = f"""Hi {first_name},

I’m {sender_name}, a recent AI/ML engineering graduate. I’ve been following {company_name} ({website_url}) and recently built production projects around high-performance vector retrieval and LLM agents.

I ran a quick technical diagnostic on {company_name} and noticed a high-impact engineering opportunity:
• Query latency / TTFB is around ~{ttfb}ms ({detected_apis}).
• Current search relies on {search_diagnosis}, which could be upgraded to semantic embeddings for much higher user conversion.

To demonstrate how this would work on your stack, I drafted a lightweight, decoupled microservice blueprint designed to cut search response times and deliver instant semantic relevance:

{blueprint}

I would love the opportunity to prove my skills and build this working prototype for {company_name}. 

You can check out my projects and background here:
• Portfolio / GitHub: {portfolio_url}
• Resume / LinkedIn: {resume_url}

Would you be open to a quick 10-minute chat this week to see the prototype in action?

Best regards,
{sender_name}
{sender_title}
"""

        return {
            "subject": subject,
            "body": body,
            "blueprint_snippet": blueprint.strip(),
            "pitch_type": "AI_ENGINEER_SOLUTION",
            "provider_used": "deterministic_offline_synthesizer"
        }
