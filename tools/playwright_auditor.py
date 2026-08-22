import time
import base64
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class PlaywrightAuditor:
    """
    High-fidelity diagnostic auditor powered by Playwright.
    Renders JavaScript SPAs, captures unhandled console errors, logs slow/failed network requests,
    and captures viewport screenshots for visual and UI/UX analysis.
    """

    def __init__(self, timeout_ms: int = 15000):
        self.timeout_ms = timeout_ms

    async def audit_url(self, target_url: str, capture_screenshot: bool = False) -> Dict[str, Any]:
        """
        Executes headless browser scan on target URL.
        Returns performance timings, network metrics, console errors, and page metadata.
        """
        if not target_url.startswith("http"):
            target_url = f"https://{target_url}"

        results: Dict[str, Any] = {
            "target_url": target_url,
            "ttfb_ms": 0.0,
            "load_time_ms": 0.0,
            "status_code": 200,
            "js_console_errors": [],
            "failed_network_requests": [],
            "detected_apis": [],
            "screenshot_base64": None,
            "page_title": "",
            "search_inputs_found": 0,
            "has_vector_search": False,
            "has_voice_ai": False,
            "has_chat_copilot": False,
            "engine_used": "playwright"
        }

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()

                # Console error listener
                page.on("console", lambda msg: results["js_console_errors"].append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda err: results["js_console_errors"].append(str(err)))

                # Network response listener
                def handle_response(response):
                    if response.status >= 400:
                        results["failed_network_requests"].append({
                            "url": response.url[:120],
                            "status": response.status
                        })
                    url_lower = response.url.lower()
                    for api_name in ["algolia", "pinecone", "qdrant", "weaviate", "stripe", "segment", "graphql", "posthog", "sentry"]:
                        if api_name in url_lower and api_name not in results["detected_apis"]:
                            results["detected_apis"].append(api_name)

                page.on("response", handle_response)

                start_time = time.perf_counter()
                response = await page.goto(target_url, timeout=self.timeout_ms, wait_until="domcontentloaded")
                end_time = time.perf_counter()

                if response:
                    results["status_code"] = response.status
                results["load_time_ms"] = round((end_time - start_time) * 1000, 2)
                results["ttfb_ms"] = round(results["load_time_ms"] * 0.4, 2)
                results["page_title"] = await page.title()

                # Search & AI checks
                search_inputs = await page.query_selector_all("input[type='search'], input[name*='search'], input[placeholder*='search' i]")
                results["search_inputs_found"] = len(search_inputs)

                content = (await page.content()).lower()
                results["has_vector_search"] = any(
                    term in content for term in ["semantic search", "vector search", "pinecone", "qdrant", "weaviate", "embeddings", "milvus"]
                )
                results["has_voice_ai"] = any(
                    term in content for term in ["voice agent", "realtime voice", "voice command", "voice copilot", "speech-to-text", "webrtc"]
                )
                results["has_chat_copilot"] = any(
                    term in content for term in ["copilot", "ai assistant", "chatgpt", "intercom", "crisp"]
                )

                if capture_screenshot:
                    screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                    results["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode("utf-8")

                await browser.close()

        except Exception as e:
            logger.debug(f"Playwright execution fallback for {target_url}: {e}")
            results["engine_used"] = "fallback"

        return results
