"""Termination logic for negotiation sessions."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .engine import NegotiationTurn


class TerminationReason(Enum):
    """Reason a negotiation was terminated."""

    AGREEMENT = "agreement"
    BUYER_WALK_AWAY = "buyer_walk_away"
    SELLER_WALK_AWAY = "seller_walk_away"
    MAX_TURNS_REACHED = "max_turns_reached"
    ERROR = "error"


class TerminationChecker:
    """Evaluates whether a negotiation should terminate after each turn.

    The checker inspects the latest :class:`NegotiationTurn` and returns
    a :class:`TerminationReason` if the session is over, or *None* if the
    negotiation should continue.
    """

    def check(
        self,
        turn: "NegotiationTurn",
        turn_count: int,
        max_turns: int,
    ) -> Optional[TerminationReason]:
        """Determine whether the negotiation has reached a terminal state.

        Args:
            turn: The most recently completed turn.
            turn_count: Total number of turns played so far (per-agent
                count — e.g. if both agents have spoken 10 times each,
                pass 10).
            max_turns: The per-agent turn limit from configuration.

        Returns:
            A :class:`TerminationReason` if the negotiation is over,
            otherwise *None*.
        """
        if turn.action == "accept":
            return TerminationReason.AGREEMENT

        if turn.action == "walk_away":
            if turn.agent_role == "buyer":
                return TerminationReason.BUYER_WALK_AWAY
            return TerminationReason.SELLER_WALK_AWAY

        if turn_count >= max_turns:
            return TerminationReason.MAX_TURNS_REACHED

        return None
