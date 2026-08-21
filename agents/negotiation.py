import re
import logging
from typing import Dict, Any, Tuple
from config import settings

logger = logging.getLogger(__name__)

class NegotiationEngineAgent:
    """
    Agent 5: Conversational Follow-Up & Bounded Negotiation Agent
    Monitors prospect replies and handles responses within strict deterministic bounds:
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

    def extract_counter_offer(self, reply_text: str) -> Tuple[str, float]:
        """Extract pricing intent and any proposed dollar amounts or discount requests from message."""
        text = reply_text.lower()
        amount_match = re.search(r'\$(\d+(?:,\d+)*(?:\.\d+)?)', text)
        proposed_amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0

        percent_match = re.search(r'(\d+)\s*%\s*(?:discount|off|lower)', text)
        discount_percent = float(percent_match.group(1)) if percent_match else 0.0

        # Classify Intent
        if any(w in text for w in ["deal", "let's do it", "sounds good", "ready to move forward", "send invoice", "sign", "send contract"]):
            intent = "ACCEPTANCE"
        elif any(w in text for w in ["nda", "master service agreement", "msa", "custom contract", "indemnity", "legal team", "terms of service"]):
            intent = "CUSTOM_CONTRACT_REQUEST"
        elif any(w in text for w in ["mobile app", "full rewrite", "unrelated", "can you also build", "completely different"]):
            intent = "SCOPE_EXPANSION"
        elif proposed_amount > 0 or discount_percent > 0 or any(w in text for w in ["discount", "expensive", "cheaper", "budget", "rate", "price"]):
            intent = "PRICE_NEGOTIATION"
        elif any(w in text for w in ["unsubscribe", "not interested", "stop", "remove me"]):
            intent = "UNSUBSCRIBE"
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
        first_name = lead_name.split()[0] if lead_name else "there"

        # 1. Direct Acceptance -> Closed Won
        if intent == "ACCEPTANCE":
            return {
                "stage": "CLOSED_WON",
                "human_override_required": False,
                "override_reason": None,
                "agreed_rate": current_quoted_rate,
                "response_text": (
                    f"Hi {first_name},\n\n"
                    f"Fantastic! I am thrilled to partner with {company_name}. "
                    f"I have prepared the standard statement of work at ${current_quoted_rate:,.2f} "
                    f"with our standard milestone structure ({self.milestone_terms}).\n\n"
                    "You can view and execute the onboarding doc here: https://outreach-engine.io/onboarding\n\n"
                    "Looking forward to kicking this off!"
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
                    "Thanks for clarifying. Our team is reviewing the agreement requirements and will get back to you with the adjusted paperwork shortly."
                )
            }

        # 3. Major Scope Expansion -> Human Handover
        if intent == "SCOPE_EXPANSION":
            return {
                "stage": "HITL_HANDOVER",
                "human_override_required": True,
                "override_reason": "Prospect requested out-of-scope development beyond microservice/audit specifications.",
                "agreed_rate": None,
                "response_text": (
                    f"Hi {first_name},\n\n"
                    "That sounds like an intriguing expansion. Let me review the scope details and put together an accurate milestone roadmap for you."
                )
            }

        # 4. Price Negotiation within Bounded Limits
        if intent == "PRICE_NEGOTIATION":
            floor = self.min_hourly if is_hourly else self.min_fixed
            allowed_floor = current_quoted_rate * (1 - (self.max_discount / 100))

            if figure > 0 and figure < floor:
                # Proposed rate is below absolute floor -> Handover
                return {
                    "stage": "HITL_HANDOVER",
                    "human_override_required": True,
                    "override_reason": f"Prospect counter-offered ${figure:,.2f}, which is below our hard floor of ${floor:,.2f}.",
                    "agreed_rate": None,
                    "response_text": (
                        f"Hi {first_name},\n\n"
                        f"Thank you for the proposal. To maintain engineering quality and SLA guarantees, our standard minimum engagement floor is ${floor:,.2f}. "
                        "I am checking with our lead architect to see if we can tailor a phased scope that fits your target budget."
                    )
                }
            else:
                # Concede standard bounded discount (up to 10%)
                discounted_rate = max(allowed_floor, floor)
                return {
                    "stage": "NEGOTIATING",
                    "human_override_required": False,
                    "override_reason": None,
                    "agreed_rate": discounted_rate,
                    "response_text": (
                        f"Hi {first_name},\n\n"
                        f"I understand budget constraints. If we can finalize the agreement this week, I can offer an adjusted rate of ${discounted_rate:,.2f} "
                        f"under our standard milestone terms ({self.milestone_terms}).\n\n"
                        "Does that work for your team?"
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
                    "Great question. Our architecture runs as a standalone containerized service with zero changes to your core database schema. "
                    "We ingest events asynchronously and maintain a 99.9% uptime SLA with <100ms vector lookup latency.\n\n"
                    "Would you like to hop on a quick 10-minute demo this week to review the telemetry graphs?"
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
