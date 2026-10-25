"""Seller agent for Project Concord negotiations."""

from __future__ import annotations

import logging

from config.personas import PersonaType
from config.settings import NegotiationConfig

from .base_agent import AgentResponse, BaseAgent

logger = logging.getLogger(__name__)


class SellerAgent(BaseAgent):
    """LLM-powered seller agent.

    Enforces seller-specific rules: the agent should never accept or offer
    an amount below its reservation (minimum) price.
    """

    def __init__(self, persona: PersonaType, config: NegotiationConfig) -> None:
        """Initialise a seller agent.

        Args:
            persona: Behavioural persona to adopt.
            config: Shared negotiation configuration.
        """
        super().__init__(role="seller", persona=persona, config=config)

    def _validate_response(self, response: AgentResponse) -> None:
        """Validate seller-specific constraints.

        Logs a warning if the seller agrees to a price below its
        reservation price when accepting a deal.

        Args:
            response: The parsed agent response to validate.
        """
        if response.action == "accept" and response.offer_amount is not None:
            if response.offer_amount < self.config.seller_reservation_price:
                logger.warning(
                    "Seller accepted at $%.2f which is below reservation price $%.2f",
                    response.offer_amount,
                    self.config.seller_reservation_price,
                )
