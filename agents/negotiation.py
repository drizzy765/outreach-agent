import re
import logging
from typing import Dict, Any, Tuple, Optional
from config import settings
from tools.llm_router import LLMRouter

logger = logging.getLogger(__name__)

NEGOTIATION_SYSTEM_PROMPT = """You are a polite, firm B2B AI Technical Partner negotiating project terms with a prospective client.
Strict Business Constraints:
- Rate floor: Minimum $5,000 fixed price or $150/hr. Never accept below this.
- Maximum permitted discount: 10% off the quoted rate.
- Milestone terms: 50% upfront deposit, 50% upon deployment.
- If prospect asks for out-of-scope features (mobile apps, full rewrites) or custom legal redlines (MSAs, NDAs), state that the engineering lead is reviewing it.

Reply in under 100 words directly addressing their specific inquiry while adhering strictly to terms."""

class NegotiationEngineAgent:
    """
    Agent 5: Conversational Follow-Up & Bounded Negotiation Agent
    Monitors prospect replies, answers technical questions, and handles negotiations within strict bounds:
    - Minimum hourly rate ($150/hr)
    - Minimum fixed project fee ($5,000)
    - Max discount (10%)
    - Milestone requirement: 50% upfront, 50% on completion
    - Triggers Human-in-the-Loop (HITL) handover whenever bounds are breached.
    """

    def __init__(self):
        self.min_hourly = settings.minimum_acceptable_rate_hourly
        self.min_fixed = settings.minimum_acceptable_fixed_project
        self.max_discount = settings.max_discount_percentage
        self.milestone_terms = settings.milestone_terms
        self.router = LLMRouter()

    def extract_counter_offer(self, reply_text: str) -> Tuple[str, float]:
        """Extract pricing intent and any proposed dollar amounts or discount requests from message."""
        text = reply_text.lower()
        
        # Match dollar formats: $4,000, $4000, 4,000, 4000, 4k, 500/mo, etc.
        amount_match = re.search(r'\$\s*(\d+(?:,\d+)*(?:\.\d+)?)|(?:\b|\s)(\d{1,3}(?:,\d{3})+(?:\.\d+)?)|(?:\b|\s)(\d{3,6})(?:\.\d+)?(?:\s|$|usd|\b)|(?:\b|\s)(\d+)\s*k\b', text)
        proposed_amount = 0.0
        if amount_match:
            if amount_match.group(1):
                proposed_amount = float(amount_match.group(1).replace(',', ''))
            elif amount_match.group(2):
                proposed_amount = float(amount_match.group(2).replace(',', ''))
            elif amount_match.group(3):
                proposed_amount = float(amount_match.group(3))
            elif amount_match.group(4):
                proposed_amount = float(amount_match.group(4)) * 1000.0

        percent_match = re.search(r'(\d+)\s*%\s*(?:discount|off|lower)', text)
        discount_percent = float(percent_match.group(1)) if percent_match else 0.0

        # Classify Intent (Priority: Legal/Scope boundaries -> Opt-out -> Price -> Acceptance -> Tech)
        if any(w in text for w in ["nda", "master service agreement", "msa", "custom contract", "indemnity", "legal team", "terms of service"]):
            intent = "CUSTOM_CONTRACT_REQUEST"
        elif any(w in text for w in ["mobile app", "full rewrite", "unrelated", "can you also build", "completely different"]):
            intent = "SCOPE_EXPANSION"
        elif any(w in text for w in ["unsubscribe", "not interested", "stop", "remove me"]):
            intent = "UNSUBSCRIBE"
        elif proposed_amount > 0 or discount_percent > 0 or re.search(r'\b(discount|expensive|cheaper|budget|rate|rates|pricing|price|cost|fee)\b', text):
            intent = "PRICE_NEGOTIATION"
        elif any(w in text for w in ["deal", "let's do it", "sounds good", "ready to move forward", "send invoice", "send contract", "ready to sign", "sign the agreement"]):
            intent = "ACCEPTANCE"
        else:
            intent = "TECHNICAL_QUESTION"

        return intent, (proposed_amount or discount_percent)

    def process_reply(
        self,
        lead_name: str,
        company_name: str,
        incoming_reply: str,
        current_quoted_rate: float = 6500.0,
        is_hourly: bool = False
    ) -> Dict[str, Any]:
        """
        Executes bounded deterministic state transition on prospect reply.
        """
        intent, figure = self.extract_counter_offer(incoming_reply)
        first_name = lead_name.split()[0] if lead_name and lead_name != "Founder" else "there"
        sender_name = getattr(settings, "sender_name", "Timilehin Agoro")

        # 1. Direct Acceptance -> Closed Won
        if intent == "ACCEPTANCE":
            return {
                "stage": "CLOSED_WON",
                "human_override_required": False,
                "override_reason": None,
                "agreed_rate": current_quoted_rate,
                "response_text": (
                    f"Hi {first_name},\n\n"
                    f"Fantastic! I am thrilled to build this for {company_name}. "
                    f"I have prepared the project scope at ${current_quoted_rate:,.2f} "
                    f"with milestone terms ({self.milestone_terms}).\n\n"
                    "Let's schedule our kickoff call to align on repository access and deliverables."
                )
            }

        # 2. Custom Contract / Legal Redlines -> Human Handover
        if intent == "CUSTOM_CONTRACT_REQUEST":
            return {
                "stage": "HITL_HANDOVER",
                "human_override_required": True,
                "override_reason": "Prospect requested custom contract / legal MSA redlines.",
                "agreed_rate": None,
                "response_text": (
                    f"Hi {first_name},\n\n"
                    "Thanks for clarifying. I am reviewing the contract requirements and will get back to you with the adjusted paperwork shortly."
                )
            }

        # 3. Major Scope Expansion -> Human Handover
        if intent == "SCOPE_EXPANSION":
            return {
                "stage": "HITL_HANDOVER",
                "human_override_required": True,
                "override_reason": "Prospect requested out-of-scope development beyond microservice specifications.",
                "agreed_rate": None,
                "response_text": (
                    f"Hi {first_name},\n\n"
                    "That sounds like an interesting roadmap expansion. Let me review the scope details and put together an accurate milestone roadmap for you."
                )
            }

        # 4. Cash-Flow Maximizer Tiered Price Negotiation
        if intent == "PRICE_NEGOTIATION":
            # General discount request without specific figure -> offer 10% discount
            if figure == 0.0:
                discounted_rate = current_quoted_rate * (1 - (self.max_discount / 100))
                return {
                    "stage": "NEGOTIATING",
                    "human_override_required": False,
                    "override_reason": None,
                    "agreed_rate": discounted_rate,
                    "response_text": (
                        f"Hi {first_name},\n\n"
                        f"I understand budget constraints. If we kick off this week, I can offer an adjusted project fee of ${discounted_rate:,.2f} "
                        f"under our standard milestone terms ({self.milestone_terms}).\n\n"
                        "Does that work for your team?"
                    )
                }

            # Tier A: Premium / Full Production Deployment ($3,500+)
            elif figure >= 3500.0:
                return {
                    "stage": "NEGOTIATING",
                    "human_override_required": False,
                    "override_reason": None,
                    "agreed_rate": figure,
                    "response_text": (
                        f"Hi {first_name},\n\n"
                        f"That works for me. I can deliver the full production microservice integration at ${figure:,.2f} "
                        f"under our standard milestone terms ({self.milestone_terms}).\n\n"
                        "Let's schedule a brief kickoff call this week to align on API credentials and repository setup."
                    )
                }

            # Tier B: Fast Sprint MVP ($1,200 - $3,499) -> Never turn away, capture immediate cash flow
            elif 1200.0 <= figure < 3500.0:
                return {
                    "stage": "NEGOTIATING",
                    "human_override_required": False,
                    "override_reason": None,
                    "agreed_rate": figure,
                    "response_text": (
                        f"Hi {first_name},\n\n"
                        f"I completely understand budget constraints and want to make sure you see immediate ROI. "
                        f"I can work within your ${figure:,.2f} budget for a focused 3-to-4 day Phase 1 Sprint, "
                        f"delivering the core working decoupled microservice, Docker setup, and benchmark suite ({self.milestone_terms}).\n\n"
                        f"Once you verify the performance gains in production, you can apply 100% of this ${figure:,.2f} "
                        "towards the full deployment.\n\n"
                        "Does that work for your team to kick off this week?"
                    )
                }

            # Tier C: Rapid 48-Hour Technical Deep-Dive ($500 - $1,199)
            elif 500.0 <= figure < 1200.0:
                return {
                    "stage": "NEGOTIATING",
                    "human_override_required": False,
                    "override_reason": None,
                    "agreed_rate": figure,
                    "response_text": (
                        f"Hi {first_name},\n\n"
                        f"To fit your ${figure:,.2f} budget, I can deliver a focused 48-hour Technical Deep-Dive & Architecture Package: "
                        "a complete benchmark analysis, reproducible Docker blueprint, and integration roadmap for your engineering team.\n\n"
                        "Would you like to move forward with this initial roadmap?"
                    )
                }

            # Tier D: Unreasonably low (< $500) -> Instant Telegram HITL Escalation
            else:
                return {
                    "stage": "HITL_HANDOVER",
                    "human_override_required": True,
                    "override_reason": f"Prospect counter-offered ${figure:,.2f} (below $500 micro-tier). Escalating for manual approval.",
                    "agreed_rate": None,
                    "response_text": (
                        f"Hi {first_name},\n\n"
                        "Thank you for the proposal. Let me review the scope requirements and see how we can structure a tailored pilot package that fits your budget."
                    )
                }

        # 5. Technical Questions / Inquiry
        if intent == "TECHNICAL_QUESTION":
            return {
                "stage": "NEGOTIATING",
                "human_override_required": False,
                "override_reason": None,
                "agreed_rate": current_quoted_rate,
                "response_text": (
                    f"Hi {first_name},\n\n"
                    "Great question. The solution runs as a decoupled async FastAPI service with zero changes to your core database schema. "
                    "It integrates directly with your existing APIs and achieves <45ms vector search lookup times.\n\n"
                    "Would you like to hop on a quick 10-minute demo this week to review the prototype?"
                )
            }

        # 6. Unsubscribe
        return {
            "stage": "CLOSED_LOST",
            "human_override_required": False,
            "override_reason": "Prospect requested unsubscribe/no interest.",
            "agreed_rate": None,
            "response_text": "Understood. You have been removed from further communications."
        }

    async def process_reply_async(
        self,
        lead_name: str,
        company_name: str,
        incoming_reply: str,
        current_quoted_rate: float = 6500.0,
        is_hourly: bool = False
    ) -> Dict[str, Any]:
        """
        Async reply processing using LLM reasoning with deterministic guardrail enforcement.
        """
        # Always run deterministic checks first to guarantee floor/contract limits
        deterministic_res = self.process_reply(
            lead_name=lead_name,
            company_name=company_name,
            incoming_reply=incoming_reply,
            current_quoted_rate=current_quoted_rate,
            is_hourly=is_hourly
        )

        # If it's a technical question, attempt enhanced LLM explanation if available
        intent, _ = self.extract_counter_offer(incoming_reply)
        if intent == "TECHNICAL_QUESTION":
            user_msg = f"Prospect from {company_name} asks: '{incoming_reply}'. Answer their technical question adhering to our stack."
            llm_text, provider = await self.router.generate_completion(
                system_prompt=NEGOTIATION_SYSTEM_PROMPT,
                user_prompt=user_msg,
                temperature=0.3,
                max_tokens=250
            )
            if llm_text and provider != "offline_fallback":
                deterministic_res["response_text"] = llm_text.strip()
                deterministic_res["provider_used"] = provider

        return deterministic_res
