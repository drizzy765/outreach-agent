import time
import httpx
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from tools.playwright_auditor import PlaywrightAuditor

logger = logging.getLogger(__name__)

class TechnicalAuditAgent:
    """
    Agent 2: Technical Diagnostic & Performance Audit Agent
    Executes automated, non-invasive diagnostic scans on target websites:
    - Headless Browser (Playwright): SPA rendering, JS console error capture, network latency
    - Search & Intelligence Gaps: Substring/SQL search vs Vector Semantic search
    - Automation & LLM Gaps: Absence of agentic voice command / predictive telemetry
    - Visual Viewport Audit: Full viewport snapshot for UI/UX analysis
    """

    def __init__(self, timeout: float = 12.0, enable_playwright: bool = True):
        self.timeout = timeout
        self.enable_playwright = enable_playwright
        self.pw_auditor = PlaywrightAuditor(timeout_ms=int(timeout * 1000)) if enable_playwright else None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def perform_audit(self, target_url: str, capture_screenshot: bool = False) -> Dict[str, Any]:
        """
        Runs comprehensive technical diagnostics using Playwright with robust HTTP/DOM fallback.
        """
        if not target_url.startswith("http"):
            target_url = f"https://{target_url}"

        audit_results: Dict[str, Any] = {
            "target_url": target_url,
            "ttfb_ms": 0.0,
            "load_time_ms": 0.0,
            "status_code": 200,
            "page_weight_kb": 0.0,
            "js_console_errors": [],
            "failed_network_requests": [],
            "detected_apis": [],
            "search_gap_detected": False,
            "search_diagnosis": "Standard SQL/Substring Search (Lacks Vector Embeddings)",
            "ai_agent_gap_detected": False,
            "ai_agent_diagnosis": "Missing Real-time Agentic Voice / Telemetry Automation",
            "recommended_pitch_angle": "CUSTOM_ML_AUDIT",
            "audit_summary": "",
            "diagnostic_engine": "http_fallback"
        }

        # 1. Try Playwright deep audit if enabled
        if self.enable_playwright and self.pw_auditor:
            try:
                pw_res = await self.pw_auditor.audit_url(target_url, capture_screenshot=capture_screenshot)
                if pw_res.get("engine_used") == "playwright":
                    audit_results["ttfb_ms"] = pw_res.get("ttfb_ms", 0.0)
                    audit_results["load_time_ms"] = pw_res.get("load_time_ms", 0.0)
                    audit_results["status_code"] = pw_res.get("status_code", 200)
                    audit_results["js_console_errors"] = pw_res.get("js_console_errors", [])
                    audit_results["failed_network_requests"] = pw_res.get("failed_network_requests", [])
                    audit_results["detected_apis"] = pw_res.get("detected_apis", [])
                    audit_results["search_gap_detected"] = not pw_res.get("has_vector_search", False)
                    audit_results["ai_agent_gap_detected"] = not pw_res.get("has_voice_ai", False)
                    audit_results["diagnostic_engine"] = "playwright_headless"

                    if not audit_results["search_gap_detected"]:
                        audit_results["search_diagnosis"] = "Vector semantic embeddings detected in frontend/network payload."
                    if not audit_results["ai_agent_gap_detected"]:
                        audit_results["ai_agent_diagnosis"] = "Voice / Real-time copilot workflows detected."

                    # Classify optimal engineering angle using zero-token heuristic rules
                    content_blob = (pw_res.get("page_title", "") + " " + " ".join(audit_results["detected_apis"])).lower()
                    if any(term in content_blob for term in ["llm", "openai", "gpt", "anthropic", "claude", "ai agent", "chatbot", "generative ai"]):
                        audit_results["recommended_pitch_angle"] = "LLM_FINOPS_OPTIMIZATION"
                    elif any(term in content_blob for term in ["search", "catalog", "marketplace", "e-commerce", "docs", "documentation", "kb", "knowledge base"]):
                        audit_results["recommended_pitch_angle"] = "VECTOR_SEMANTIC_SEARCH"
                    elif audit_results["ttfb_ms"] > 900.0:
                        audit_results["recommended_pitch_angle"] = "API_LATENCY_OPTIMIZATION"
                    elif any(term in content_blob for term in ["webhook", "telemetry", "streaming", "events", "analytics", "fintech", "pipeline"]):
                        audit_results["recommended_pitch_angle"] = "REALTIME_INGESTION_PIPELINE"
                    else:
                        audit_results["recommended_pitch_angle"] = "AGENTIC_COPILOT_AUTOMATION"

                    audit_results["audit_summary"] = (
                        f"Audited {target_url} via Playwright (Load: {audit_results['load_time_ms']}ms, TTFB: {audit_results['ttfb_ms']}ms). "
                        f"Angle: {audit_results['recommended_pitch_angle']}."
                    )
                    return audit_results
            except Exception as e:
                logger.debug(f"Playwright audit failed, switching to HTTP fallback: {e}")

        # 2. HTTP + DOM fallback
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True, verify=False) as client:
                response = await client.get(target_url)
                end_time = time.perf_counter()

                audit_results["ttfb_ms"] = round((end_time - start_time) * 1000, 2)
                audit_results["load_time_ms"] = audit_results["ttfb_ms"]
                audit_results["status_code"] = response.status_code
                audit_results["page_weight_kb"] = round(len(response.content) / 1024, 2)

                html = response.text.lower()
                soup = BeautifulSoup(response.text, "html.parser")
                page_text = soup.get_text(separator=" ").lower()[:5000]

                # Inspect Search Capabilities
                has_semantic_search = any(term in html for term in ["semantic search", "vector search", "pinecone", "weaviate", "qdrant", "chroma", "embeddings", "rag"])
                audit_results["search_gap_detected"] = not has_semantic_search
                audit_results["search_diagnosis"] = "Semantic embeddings active" if has_semantic_search else "Lacks semantic vector embeddings"

                # Inspect AI Gaps
                has_ai_agents = any(term in html for term in ["agentic", "langchain", "langgraph", "copilot", "autonomous agent"])
                audit_results["ai_agent_gap_detected"] = not has_ai_agents
                audit_results["ai_agent_diagnosis"] = "AI copilot active" if has_ai_agents else "Missing specialized AI copilot workflows"

                # Determine 6-Angle Problem Classification (0 LLM Tokens)
                if any(term in page_text for term in ["openai", "anthropic", "gpt-4", "claude", "llm", "chatbot", "prompt", "token", "generative ai"]):
                    audit_results["recommended_pitch_angle"] = "LLM_FINOPS_OPTIMIZATION"
                elif any(term in page_text for term in ["webhook", "telemetry", "streaming", "events", "analytics", "fintech", "pipeline", "etl", "trading", "quant"]):
                    audit_results["recommended_pitch_angle"] = "REALTIME_INGESTION_PIPELINE"
                elif any(term in page_text for term in ["search", "catalog", "directory", "docs", "documentation", "kb", "knowledge base", "marketplace"]) or audit_results["search_gap_detected"]:
                    audit_results["recommended_pitch_angle"] = "VECTOR_SEMANTIC_SEARCH"
                elif audit_results["ttfb_ms"] > 900.0:
                    audit_results["recommended_pitch_angle"] = "API_LATENCY_OPTIMIZATION"
                else:
                    audit_results["recommended_pitch_angle"] = "AGENTIC_COPILOT_AUTOMATION"

                audit_results["audit_summary"] = (
                    f"Audited {target_url} (TTFB: {audit_results['ttfb_ms']}ms). "
                    f"Angle: {audit_results['recommended_pitch_angle']}."
                )

        except Exception as e:
            logger.error(f"Audit failed for {target_url}: {e}")
            audit_results["audit_summary"] = f"Diagnostic scan simulated with fallback parameters: {e}"
            audit_results["recommended_pitch_angle"] = "VECTOR_SEMANTIC_SEARCH"

        return audit_results

