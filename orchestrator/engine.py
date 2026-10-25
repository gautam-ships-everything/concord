"""Core negotiation engine — runs the turn-by-turn negotiation loop."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from agents.buyer_agent import BuyerAgent
from agents.seller_agent import SellerAgent
from config.personas import PersonaType
from config.settings import NegotiationConfig
from transcript_logger.logger import TranscriptLogger

from .termination import TerminationChecker, TerminationReason

logger = logging.getLogger(__name__)


# ── ANSI colour helpers (work on modern Windows terminals) ──────────────


class _Colours:
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# ── Data classes ────────────────────────────────────────────────────────────


@dataclass
class NegotiationTurn:
    """Record of a single turn in the negotiation.

    Attributes:
        turn_number: 1-based ordinal of this turn.
        agent_role: ``"buyer"`` or ``"seller"``.
        agent_persona: Persona string (e.g. ``"neutral"``).
        action: The action taken (e.g. ``"offer"``, ``"accept"``).
        offer_amount: Monetary amount, if applicable.
        message: Natural-language message shown to the opponent.
        reasoning: The agent's private reasoning.
        timestamp: ISO-8601 timestamp of when this turn occurred.
    """

    turn_number: int
    agent_role: str
    agent_persona: str
    action: str
    offer_amount: Optional[float]
    message: str
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class NegotiationResult:
    """Summary of a completed negotiation.

    Attributes:
        negotiation_id: Unique identifier (UUID) for this session.
        config: Snapshot of the configuration used.
        turns: Chronological list of turn records (as dicts).
        outcome: Human-readable outcome label.
        final_price: Agreed price, or *None* if no agreement.
        buyer_surplus: Buyer's surplus, or *None* if no agreement.
        seller_surplus: Seller's surplus, or *None* if no agreement.
        total_surplus: Combined surplus, or *None* if no agreement.
        num_turns: Total number of turns played.
        duration_seconds: Wall-clock duration of the negotiation.
        timestamp: ISO-8601 timestamp of completion.
    """

    negotiation_id: str
    config: dict
    turns: list[dict]
    outcome: str
    final_price: Optional[float]
    buyer_surplus: Optional[float]
    seller_surplus: Optional[float]
    total_surplus: Optional[float]
    num_turns: int
    duration_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Engine ──────────────────────────────────────────────────────────────────


class NegotiationEngine:
    """Orchestrates a complete negotiation between a buyer and a seller.

    Creates the agents, runs the alternating turn loop, checks for
    termination, computes surpluses, and persists the transcript.
    """

    def __init__(self, config: NegotiationConfig) -> None:
        """Initialise the engine with a validated configuration.

        Args:
            config: Fully-populated :class:`NegotiationConfig`.
        """
        self.config = config
        self.buyer = BuyerAgent(
            persona=PersonaType(config.buyer_persona.lower()),
            config=config,
        )
        self.seller = SellerAgent(
            persona=PersonaType(config.seller_persona.lower()),
            config=config,
        )
        self.termination_checker = TerminationChecker()
        self.transcript_logger = TranscriptLogger(output_dir=config.output_dir)

    # ── Public API ──────────────────────────────────────────────────────

    def run(self) -> NegotiationResult:
        """Execute the full negotiation loop and return the result.

        1. The **seller** makes the opening offer.
        2. Turns alternate: buyer → seller → buyer → …
        3. After each turn the :class:`TerminationChecker` evaluates.
        4. On termination, surpluses are computed and the transcript saved.

        Returns:
            A :class:`NegotiationResult` summarising the session.
        """
        negotiation_id = str(uuid.uuid4())
        conversation_history: list[dict[str, str]] = []
        turns: list[NegotiationTurn] = []
        turn_number = 0
        buyer_turns = 0
        seller_turns = 0
        start_time = time.monotonic()

        self._print_header()

        termination_reason: Optional[TerminationReason] = None

        while termination_reason is None:
            # Determine whose turn it is (seller goes first, then alternate)
            if turn_number % 2 == 0:
                current_agent = self.seller
                current_role = "seller"
            else:
                current_agent = self.buyer
                current_role = "buyer"

            turn_number += 1

            # Generate response
            try:
                response = current_agent.generate_response(conversation_history)
            except RuntimeError as exc:
                logger.error("Agent error: %s", exc)
                turn = NegotiationTurn(
                    turn_number=turn_number,
                    agent_role=current_role,
                    agent_persona=getattr(current_agent, "persona", PersonaType.NEUTRAL).value,
                    action="error",
                    offer_amount=None,
                    message=str(exc),
                    reasoning="",
                )
                turns.append(turn)
                self.transcript_logger.log_turn(turn)
                termination_reason = TerminationReason.ERROR
                break

            # Create turn record
            turn = NegotiationTurn(
                turn_number=turn_number,
                agent_role=current_role,
                agent_persona=current_agent.persona.value,
                action=response.action,
                offer_amount=response.offer_amount,
                message=response.message,
                reasoning=response.reasoning,
            )
            turns.append(turn)
            self.transcript_logger.log_turn(turn)

            # Update shared conversation history (message only, no reasoning)
            conversation_history.append(
                {"role": current_role, "content": response.message}
            )

            # Pretty-print the turn
            self._print_turn(turn)

            # Track per-agent turn counts
            if current_role == "buyer":
                buyer_turns += 1
            else:
                seller_turns += 1

            # Check termination (use the larger of the two per-agent counts)
            per_agent_count = max(buyer_turns, seller_turns)
            termination_reason = self.termination_checker.check(
                turn, per_agent_count, self.config.max_turns
            )

        # ── Post-negotiation ────────────────────────────────────────────
        duration = time.monotonic() - start_time
        final_price, buyer_surplus, seller_surplus, total_surplus = (
            None,
            None,
            None,
            None,
        )
        outcome = termination_reason.value if termination_reason else "unknown"

        if termination_reason == TerminationReason.AGREEMENT:
            # The accepted price is in the last turn, or the previous turn if last turn just said accept
            final_price = turns[-1].offer_amount
            if final_price is None and len(turns) >= 2:
                final_price = turns[-2].offer_amount
            if final_price is not None:
                buyer_surplus, seller_surplus, total_surplus = (
                    self._compute_surpluses(final_price, self.config)
                )

        result = NegotiationResult(
            negotiation_id=negotiation_id,
            config=self._config_to_dict(),
            turns=[asdict(t) for t in turns],
            outcome=outcome,
            final_price=final_price,
            buyer_surplus=buyer_surplus,
            seller_surplus=seller_surplus,
            total_surplus=total_surplus,
            num_turns=turn_number,
            duration_seconds=round(duration, 2),
        )

        self.transcript_logger.save(result)
        self._print_summary(result, termination_reason)

        return result

    # ── Surplus computation ─────────────────────────────────────────────

    @staticmethod
    def _compute_surpluses(
        final_price: float, config: NegotiationConfig
    ) -> tuple[float, float, float]:
        """Compute buyer, seller, and total surplus.

        Args:
            final_price: The agreed transaction price.
            config: The negotiation config (for reservation prices).

        Returns:
            A tuple of ``(buyer_surplus, seller_surplus, total_surplus)``.
        """
        buyer_surplus = round(config.buyer_reservation_price - final_price, 2)
        seller_surplus = round(final_price - config.seller_reservation_price, 2)
        total_surplus = round(buyer_surplus + seller_surplus, 2)
        return buyer_surplus, seller_surplus, total_surplus

    # ── Console output helpers ──────────────────────────────────────────

    def _config_to_dict(self) -> dict:
        """Serialise config to a plain dict (exclude private fields)."""
        return {
            "model_name": self.config.model_name,
            "max_turns": self.config.max_turns,
            "buyer_reservation_price": self.config.buyer_reservation_price,
            "seller_reservation_price": self.config.seller_reservation_price,
            "item_name": self.config.item_name,
            "item_description": self.config.item_description,
            "buyer_persona": self.config.buyer_persona,
            "seller_persona": self.config.seller_persona,
            "information_mode": self.config.information_mode,
            "temperature": self.config.temperature,
        }

    def _print_header(self) -> None:
        """Print a coloured header to the console."""
        c = _Colours
        print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")
        print(f"{c.BOLD}{c.MAGENTA}  PROJECT CONCORD — Negotiation Engine{c.RESET}")
        print(f"{c.BOLD}{'=' * 70}{c.RESET}")
        print(f"  Item: {c.CYAN}{self.config.item_name}{c.RESET}")
        print(
            f"  Buyer persona: {c.YELLOW}{self.config.buyer_persona}{c.RESET}  |  "
            f"Seller persona: {c.YELLOW}{self.config.seller_persona}{c.RESET}"
        )
        print(
            f"  Buyer max: {c.GREEN}${self.config.buyer_reservation_price:.2f}{c.RESET}  |  "
            f"Seller min: {c.GREEN}${self.config.seller_reservation_price:.2f}{c.RESET}"
        )
        print(f"  Info mode: {c.CYAN}{self.config.information_mode}{c.RESET}")
        print(f"{c.BOLD}{'-' * 70}{c.RESET}\n")

    def _print_turn(self, turn: NegotiationTurn) -> None:
        """Print a single turn with colour coding."""
        c = _Colours
        if turn.agent_role == "seller":
            role_colour = c.CYAN
        else:
            role_colour = c.YELLOW

        action_colour = c.GREEN if turn.action == "accept" else (
            c.RED if turn.action in ("reject", "walk_away") else c.RESET
        )

        amount_str = (
            f" ${turn.offer_amount:.2f}" if turn.offer_amount is not None else ""
        )

        print(
            f"  {c.DIM}Turn {turn.turn_number:>2}{c.RESET}  "
            f"{role_colour}{c.BOLD}{turn.agent_role.upper():>6}{c.RESET}  "
            f"[{action_colour}{turn.action}{c.RESET}{amount_str}]"
        )
        print(f"          {turn.message}")
        print(f"          {c.DIM}(reasoning: {turn.reasoning}){c.RESET}")
        print()

    @staticmethod
    def _print_summary(
        result: NegotiationResult,
        reason: Optional[TerminationReason],
    ) -> None:
        """Print a coloured post-negotiation summary."""
        c = _Colours
        print(f"{c.BOLD}{'-' * 70}{c.RESET}")
        print(f"{c.BOLD}{c.MAGENTA}  NEGOTIATION COMPLETE{c.RESET}")
        print(f"{c.BOLD}{'-' * 70}{c.RESET}")
        print(f"  Outcome    : {c.BOLD}{result.outcome}{c.RESET}")
        if result.final_price is not None:
            print(f"  Final price: {c.GREEN}${result.final_price:.2f}{c.RESET}")
            print(f"  Buyer surplus : {c.YELLOW}${result.buyer_surplus:.2f}{c.RESET}")
            print(f"  Seller surplus: {c.YELLOW}${result.seller_surplus:.2f}{c.RESET}")
            print(f"  Total surplus : {c.GREEN}${result.total_surplus:.2f}{c.RESET}")
        print(f"  Turns      : {result.num_turns}")
        print(f"  Duration   : {result.duration_seconds:.1f}s")
        print(f"  ID         : {result.negotiation_id}")
        print(f"{c.BOLD}{'=' * 70}{c.RESET}\n")
