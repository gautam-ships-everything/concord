"""Base agent abstraction for LLM-powered negotiation agents."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

try:
    from google import genai
    from google.genai import types
    _HAS_GENAI = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    _HAS_GENAI = False

from config.personas import InformationMode, PersonaType, build_system_prompt
from config.settings import NegotiationConfig

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────────────


@dataclass
class AgentResponse:
    """Parsed response from a negotiation agent.

    Attributes:
        action: One of ``"offer"``, ``"counter"``, ``"accept"``,
            ``"reject"``, ``"walk_away"``.
        offer_amount: The monetary amount associated with the action,
            or *None* when not applicable (e.g. ``walk_away``).
        message: The natural-language message visible to the opponent.
        reasoning: The agent's private internal reasoning.
        raw_response: The verbatim text returned by the LLM.
    """

    action: str
    offer_amount: Optional[float]
    message: str
    reasoning: str
    raw_response: str


# ── Abstract base agent ────────────────────────────────────────────────────


class BaseAgent(ABC):
    """Abstract base class for negotiation agents backed by an LLM (Gemma 4).

    When a Google API key is configured and google-genai is installed,
    queries the live Gemma 4 model. If no API key is yet configured,
    seamlessly falls back to an intelligent strategic simulation agent
    matching the configured persona and information state.
    """

    VALID_ACTIONS: set[str] = {"offer", "counter", "accept", "reject", "walk_away"}
    MAX_RETRIES: int = 3

    def __init__(
        self,
        role: str,
        persona: PersonaType,
        config: NegotiationConfig,
    ) -> None:
        """Initialise the agent.

        Args:
            role: ``"buyer"`` or ``"seller"``.
            persona: Behavioural persona to adopt.
            config: Shared negotiation configuration.
        """
        self.role = role
        self.persona = persona
        self.config = config
        self.system_prompt = build_system_prompt(role, persona, config)
        self.is_live = False
        self._client = self._init_client()

    def _init_client(self) -> Any:
        """Initialise the LLM client or flag for simulation fallback."""
        key = self.config.api_key.strip()
        if _HAS_GENAI and key and key != "your_api_key_here":
            try:
                client = genai.Client(api_key=key)
                self.is_live = True
                return client
            except Exception as exc:
                logger.warning("[%s] Could not init live GenAI client: %s. Using simulator.", self.role, exc)
        self.is_live = False
        return None

    # ── Public API ──────────────────────────────────────────────────────

    def generate_response(
        self, conversation_history: list[dict[str, str]]
    ) -> AgentResponse:
        """Query Gemma 4 (or the strategy engine) and return structured response."""
        if self.is_live and self._client is not None:
            return self._generate_live_response(conversation_history)
        return self._simulate_strategic_response(conversation_history)

    def _generate_live_response(
        self, conversation_history: list[dict[str, str]]
    ) -> AgentResponse:
        """Query the live Gemma 4 endpoint via google-genai."""
        messages = self._build_conversation_messages(conversation_history)
        last_error: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.config.model_name,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        temperature=self.config.temperature,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = response.text
                agent_response = self._parse_response(raw_text)
                self._validate_response(agent_response)
                return agent_response

            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
                last_error = exc
                logger.warning(
                    "[%s] Attempt %d/%d failed to parse LLM response: %s",
                    self.role,
                    attempt,
                    self.MAX_RETRIES,
                    exc,
                )

        raise RuntimeError(
            f"[{self.role}] Failed to get a valid response from Gemma 4 after "
            f"{self.MAX_RETRIES} attempts. Last error: {last_error}"
        )

    # ── Intelligent Strategic Simulator (Offline / Pre-API Mode) ──────────

    def _simulate_strategic_response(
        self, conversation_history: list[dict[str, str]]
    ) -> AgentResponse:
        """Simulate realistic Gemma 4 negotiation dialogue and decisions."""
        buyer_max = self.config.buyer_reservation_price
        seller_min = self.config.seller_reservation_price
        midpoint = round((buyer_max + seller_min) / 2.0, 2)
        turn_idx = len(conversation_history)

        # Extract last opponent offer if available
        last_opponent_offer: Optional[float] = None
        for entry in reversed(conversation_history):
            if entry["role"] != self.role:
                matches = re.findall(r"\$(\d+(?:\.\d+)?)", entry["content"])
                if matches:
                    last_opponent_offer = float(matches[-1])
                    break

        persona_val = self.persona.value if isinstance(self.persona, PersonaType) else str(self.persona)
        info_mode = self.config.information_mode

        # 1. SELLER OPENING TURN
        if self.role == "seller" and turn_idx == 0:
            if persona_val == "aggressive":
                ask = round(buyer_max * 1.15, 2)
                msg = f"This vintage {self.config.item_name} is in collector-grade mint condition. I'm asking ${ask:.2f}."
                reasoning = "Anchor high above buyer budget to test constraints and capture surplus."
            elif persona_val == "cooperative":
                ask = round(midpoint + (buyer_max - midpoint) * 0.45, 2)
                msg = f"Hello! I am offering this wonderful {self.config.item_name} for ${ask:.2f}. Open to discussing fair terms!"
                reasoning = "Start with a reasonable asking price to establish trust and reach mutually beneficial deal."
            else:  # neutral
                ask = round(buyer_max * 0.95, 2)
                msg = f"I am listing the {self.config.item_name} for ${ask:.2f} based on fair market value."
                reasoning = "Standard market-based anchor just under typical ceiling."
            return AgentResponse(action="offer", offer_amount=ask, message=msg, reasoning=reasoning, raw_response="[simulated]")

        # 2. BUYER FIRST RESPONSE
        if self.role == "buyer" and turn_idx == 1:
            opp_ask = last_opponent_offer or 100.0
            if persona_val == "aggressive":
                bid = round(seller_min * 0.9 if info_mode == "asymmetric_buyer_knows" else seller_min * 0.95, 2)
                msg = f"Your ask of ${opp_ask:.2f} is steep. Considering wear, my initial offer is ${bid:.2f}."
                reasoning = "Anchor aggressively low to shift the surplus split in our favor."
            elif persona_val == "cooperative":
                bid = round(seller_min + (midpoint - seller_min) * 0.6, 2)
                msg = f"Thank you for showing the item! I appreciate its quality. Would you consider ${bid:.2f}?"
                reasoning = "Offer a respectable starting bid to invite constructive counter-proposals."
            else:  # neutral
                bid = round(seller_min + (midpoint - seller_min) * 0.35, 2)
                msg = f"Thanks. Based on recent market sales, I can offer ${bid:.2f} for the item."
                reasoning = "Balanced starting bid leaving room for moderate upward adjustment."
            return AgentResponse(action="counter", offer_amount=bid, message=msg, reasoning=reasoning, raw_response="[simulated]")

        # 3. SUBSEQUENT TURNS (CONCESSION & SETTLEMENT LOGIC)
        # Check if opponent's offer is already acceptable
        if self.role == "buyer" and last_opponent_offer is not None:
            if last_opponent_offer <= buyer_max:
                # Accept criteria based on persona
                if persona_val == "cooperative" and (last_opponent_offer <= midpoint + 5 or turn_idx >= 5):
                    return AgentResponse(
                        action="accept",
                        offer_amount=last_opponent_offer,
                        message=f"That sounds very fair. I accept your offer of ${last_opponent_offer:.2f}. We have a deal!",
                        reasoning=f"Offer ${last_opponent_offer:.2f} is below my max of ${buyer_max:.2f}. Cooperative goal met.",
                        raw_response="[simulated]"
                    )
                elif persona_val == "neutral" and (last_opponent_offer <= midpoint or turn_idx >= 7):
                    return AgentResponse(
                        action="accept",
                        offer_amount=last_opponent_offer,
                        message=f"I agree to ${last_opponent_offer:.2f}. Thank you for negotiating with me.",
                        reasoning=f"Offer ${last_opponent_offer:.2f} meets rational market threshold.",
                        raw_response="[simulated]"
                    )
                elif persona_val == "aggressive" and (last_opponent_offer <= seller_min + 5 or turn_idx >= 11):
                    return AgentResponse(
                        action="accept",
                        offer_amount=last_opponent_offer,
                        message=f"Alright, I will take it for ${last_opponent_offer:.2f}, but that is my absolute limit.",
                        reasoning=f"Surplus extracted successfully at ${last_opponent_offer:.2f}.",
                        raw_response="[simulated]"
                    )

        if self.role == "seller" and last_opponent_offer is not None:
            if last_opponent_offer >= seller_min:
                if persona_val == "cooperative" and (last_opponent_offer >= midpoint - 5 or turn_idx >= 6):
                    return AgentResponse(
                        action="accept",
                        offer_amount=last_opponent_offer,
                        message=f"I can accept ${last_opponent_offer:.2f}. It is a pleasure doing business with you!",
                        reasoning=f"Buyer offer ${last_opponent_offer:.2f} guarantees profit above cost ${seller_min:.2f}.",
                        raw_response="[simulated]"
                    )
                elif persona_val == "neutral" and (last_opponent_offer >= midpoint or turn_idx >= 8):
                    return AgentResponse(
                        action="accept",
                        offer_amount=last_opponent_offer,
                        message=f"${last_opponent_offer:.2f} is acceptable. We have an agreement.",
                        reasoning=f"Reached acceptable Nash equilibrium around ${last_opponent_offer:.2f}.",
                        raw_response="[simulated]"
                    )
                elif persona_val == "aggressive" and (last_opponent_offer >= buyer_max - 5 or turn_idx >= 12):
                    return AgentResponse(
                        action="accept",
                        offer_amount=last_opponent_offer,
                        message=f"Fine, I accept ${last_opponent_offer:.2f}. Deal sealed.",
                        reasoning="Secured maximum attainable surplus.",
                        raw_response="[simulated]"
                    )

        # Walk away check
        if turn_idx >= 14 and persona_val == "aggressive":
            return AgentResponse(
                action="walk_away",
                offer_amount=None,
                message="We are too far apart on price. I must walk away from this negotiation.",
                reasoning="Bargaining impasse reached; continuing yields diminishing expected returns.",
                raw_response="[simulated]"
            )

        # Counter offer calculation
        if self.role == "buyer":
            base_bid = last_opponent_offer - 5.0 if last_opponent_offer else 70.0
            step = 6.0 if persona_val == "cooperative" else (3.5 if persona_val == "neutral" else 1.5)
            # Find previous bid
            prev_bid = 65.0
            for entry in reversed(conversation_history):
                if entry["role"] == "buyer":
                    m = re.findall(r"\$(\d+(?:\.\d+)?)", entry["content"])
                    if m:
                        prev_bid = float(m[-1])
                        break
            new_bid = min(buyer_max, round(prev_bid + step, 2))
            if last_opponent_offer and new_bid >= last_opponent_offer:
                new_bid = last_opponent_offer
                return AgentResponse(action="accept", offer_amount=new_bid, message=f"I accept ${new_bid:.2f}.", reasoning="Meeting opponent offer.", raw_response="[simulated]")

            msg = f"I can come up to ${new_bid:.2f}. Can you meet me there?"
            reasoning = f"Conceding ${step} towards agreement while preserving budget cap of ${buyer_max}."
            return AgentResponse(action="counter", offer_amount=new_bid, message=msg, reasoning=reasoning, raw_response="[simulated]")

        else:  # seller
            step = 5.5 if persona_val == "cooperative" else (3.5 if persona_val == "neutral" else 1.5)
            prev_ask = 95.0
            for entry in reversed(conversation_history):
                if entry["role"] == "seller":
                    m = re.findall(r"\$(\d+(?:\.\d+)?)", entry["content"])
                    if m:
                        prev_ask = float(m[-1])
                        break
            new_ask = max(seller_min, round(prev_ask - step, 2))
            if last_opponent_offer and new_ask <= last_opponent_offer:
                new_ask = last_opponent_offer
                return AgentResponse(action="accept", offer_amount=new_ask, message=f"I accept ${new_ask:.2f}.", reasoning="Meeting opponent bid.", raw_response="[simulated]")

            msg = f"I appreciate your bid, but the lowest I can do right now is ${new_ask:.2f}."
            reasoning = f"Lowering asking price by ${step} to keep talks alive above cost ${seller_min}."
            return AgentResponse(action="counter", offer_amount=new_ask, message=msg, reasoning=reasoning, raw_response="[simulated]")

    # ── Internal helpers ────────────────────────────────────────────────

    def _parse_response(self, raw_text: str) -> AgentResponse:
        """Extract and validate a JSON response from the LLM's output."""
        json_text = raw_text.strip()
        code_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```", json_text, re.DOTALL
        )
        if code_block_match:
            json_text = code_block_match.group(1).strip()

        data: dict[str, Any] = json.loads(json_text)

        action = data["action"].strip().lower()
        if action not in self.VALID_ACTIONS:
            raise ValueError(
                f"Invalid action '{action}'. Must be one of {self.VALID_ACTIONS}."
            )

        offer_amount: Optional[float] = None
        if data.get("offer_amount") is not None:
            offer_amount = float(data["offer_amount"])

        return AgentResponse(
            action=action,
            offer_amount=offer_amount,
            message=str(data.get("message", "")),
            reasoning=str(data.get("reasoning", "")),
            raw_response=raw_text,
        )

    def _build_conversation_messages(
        self, conversation_history: list[dict[str, str]]
    ) -> list[Any]:
        """Convert negotiation history to google-genai Content objects."""
        if not _HAS_GENAI:
            return []
        messages: list[Any] = []
        for entry in conversation_history:
            api_role = "model" if entry["role"] == self.role else "user"
            messages.append(
                types.Content(
                    role=api_role,
                    parts=[types.Part.from_text(text=entry["content"])],
                )
            )
        return messages

    @abstractmethod
    def _validate_response(self, response: AgentResponse) -> None:
        """Apply role-specific validation rules to the agent's response."""
        ...
