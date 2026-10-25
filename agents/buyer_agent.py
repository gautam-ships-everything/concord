"""Buyer agent for Project Concord negotiations."""

from __future__ import annotations

import logging

from config.personas import PersonaType
from config.settings import NegotiationConfig

from .base_agent import AgentResponse, BaseAgent

logger = logging.getLogger(__name__)


class BuyerAgent(BaseAgent):
    """LLM-powered buyer agent.

    Enforces buyer-specific rules: the agent should never accept or offer
    an amount that exceeds its reservation (maximum) price.
    """

    def __init__(self, persona: PersonaType, config: NegotiationConfig) -> None:
        """Initialise a buyer agent.

        Args:
            persona: Behavioural persona to adopt.
            config: Shared negotiation configuration.
        """
        super().__init__(role="buyer", persona=persona, config=config)

    def _validate_response(self, response: AgentResponse) -> None:
        """Validate buyer-specific constraints.

        Logs a warning if the buyer proposes to pay more than its
        reservation price when accepting a deal.

        Args:
            response: The parsed agent response to validate.
        """
        if response.action == "accept" and response.offer_amount is not None:
            if response.offer_amount > self.config.buyer_reservation_price:
                logger.warning(
                    "Buyer accepted at $%.2f which exceeds reservation price $%.2f",
                    response.offer_amount,
                    self.config.buyer_reservation_price,
                )
