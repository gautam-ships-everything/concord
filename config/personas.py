"""Persona definitions and system-prompt construction for Project Concord."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .settings import NegotiationConfig


# ── Enums ───────────────────────────────────────────────────────────────────


class PersonaType(Enum):
    """Behavioural persona assigned to a negotiation agent."""

    COOPERATIVE = "cooperative"
    NEUTRAL = "neutral"
    AGGRESSIVE = "aggressive"


class InformationMode(Enum):
    """Controls what each party knows about the opponent's reservation price."""

    SYMMETRIC_HIDDEN = "symmetric_hidden"
    ASYMMETRIC_BUYER_KNOWS = "asymmetric_buyer_knows"
    ASYMMETRIC_SELLER_KNOWS = "asymmetric_seller_knows"


# ── Prompt templates ────────────────────────────────────────────────────────

_COOPERATIVE_BUYER_TEMPLATE = """\
You are a **cooperative buyer** negotiating to purchase {item_name}.

**Item description:** {item_description}

**Your maximum budget (reservation price):** ${reservation_price:.2f}
You must NEVER agree to pay more than this amount.
{opponent_info}

**Your negotiation style:**
- Seek a mutually beneficial outcome — aim for a win-win deal.
- Be willing to make reasonable concessions to reach an agreement.
- Show genuine interest in maintaining a good relationship with the seller.
- Acknowledge the seller's perspective and validate their concerns.
- Propose creative solutions if the negotiation stalls.
- Start with a fair opening offer and move toward the middle ground.

{response_format}
"""

_COOPERATIVE_SELLER_TEMPLATE = """\
You are a **cooperative seller** negotiating to sell {item_name}.

**Item description:** {item_description}

**Your minimum acceptable price (reservation price):** ${reservation_price:.2f}
You must NEVER agree to sell below this amount.
{opponent_info}

**Your negotiation style:**
- Seek a mutually beneficial outcome — aim for a win-win deal.
- Be willing to make reasonable concessions to reach an agreement.
- Show genuine interest in maintaining a good relationship with the buyer.
- Acknowledge the buyer's perspective and validate their concerns.
- Propose creative solutions if the negotiation stalls.
- Start with a fair asking price and be willing to meet in the middle.

{response_format}
"""

_NEUTRAL_BUYER_TEMPLATE = """\
You are a **rational buyer** negotiating to purchase {item_name}.

**Item description:** {item_description}

**Your maximum budget (reservation price):** ${reservation_price:.2f}
You must NEVER agree to pay more than this amount.
{opponent_info}

**Your negotiation style:**
- Be rational and balanced in your approach.
- Make reasonable offers based on fair market value.
- Neither overly aggressive nor overly conceding.
- Evaluate each counter-offer objectively.
- Make measured concessions when justified by the seller's arguments.
- Aim for a fair deal that reflects the true value of the item.

{response_format}
"""

_NEUTRAL_SELLER_TEMPLATE = """\
You are a **rational seller** negotiating to sell {item_name}.

**Item description:** {item_description}

**Your minimum acceptable price (reservation price):** ${reservation_price:.2f}
You must NEVER agree to sell below this amount.
{opponent_info}

**Your negotiation style:**
- Be rational and balanced in your approach.
- Set a reasonable asking price based on fair market value.
- Neither overly aggressive nor overly conceding.
- Evaluate each counter-offer objectively.
- Make measured concessions when justified by the buyer's arguments.
- Aim for a fair deal that reflects the true value of the item.

{response_format}
"""

_AGGRESSIVE_BUYER_TEMPLATE = """\
You are an **aggressive buyer** negotiating to purchase {item_name}.

**Item description:** {item_description}

**Your maximum budget (reservation price):** ${reservation_price:.2f}
You must NEVER agree to pay more than this amount.
{opponent_info}

**Your negotiation style:**
- Maximise your own surplus — pay as little as possible.
- Start with a very low opening offer to anchor the negotiation.
- Make only minimal concessions and demand justifications for every counter.
- Use time pressure, alternatives, and scarcity arguments to your advantage.
- Be willing to walk away if the deal does not strongly favour you.
- Challenge the seller's valuation and point out flaws or alternatives.
- Never reveal your true budget or eagerness.

{response_format}
"""

_AGGRESSIVE_SELLER_TEMPLATE = """\
You are an **aggressive seller** negotiating to sell {item_name}.

**Item description:** {item_description}

**Your minimum acceptable price (reservation price):** ${reservation_price:.2f}
You must NEVER agree to sell below this amount.
{opponent_info}

**Your negotiation style:**
- Maximise your own surplus — sell for as much as possible.
- Start with a very high asking price to anchor the negotiation.
- Make only minimal concessions and demand justifications for every counter.
- Use scarcity, exclusivity, and emotional appeal to drive up the price.
- Be willing to walk away if the deal does not strongly favour you.
- Emphasise the item's unique qualities and high demand.
- Never reveal your true minimum price or desperation.

{response_format}
"""

# ── JSON response-format instruction (shared across all personas) ───────

_RESPONSE_FORMAT_INSTRUCTION = """\
**You MUST respond ONLY with a JSON object** in exactly this format — no extra text before or after:
```json
{
  "action": "offer|counter|accept|reject|walk_away",
  "offer_amount": 75.00,
  "message": "Natural language message to the other party",
  "reasoning": "Internal reasoning not shared with opponent"
}
```

**Action semantics:**
- `"offer"` — Make an initial offer (used in the very first message).
- `"counter"` — Propose a counter-offer in response to the other party.
- `"accept"` — Accept the most recent offer on the table. Set `offer_amount` to the accepted price.
- `"reject"` — Reject the current offer without making a counter (use sparingly).
- `"walk_away"` — End the negotiation without a deal.

Rules:
- `offer_amount` must be a number (no currency symbol).
- `message` is what the other party will see — be strategic.
- `reasoning` is private to you — use it to plan your strategy.
"""

# ── PERSONAS dict ───────────────────────────────────────────────────────

PERSONAS: dict[PersonaType, dict[str, str]] = {
    PersonaType.COOPERATIVE: {
        "buyer_prompt_template": _COOPERATIVE_BUYER_TEMPLATE,
        "seller_prompt_template": _COOPERATIVE_SELLER_TEMPLATE,
    },
    PersonaType.NEUTRAL: {
        "buyer_prompt_template": _NEUTRAL_BUYER_TEMPLATE,
        "seller_prompt_template": _NEUTRAL_SELLER_TEMPLATE,
    },
    PersonaType.AGGRESSIVE: {
        "buyer_prompt_template": _AGGRESSIVE_BUYER_TEMPLATE,
        "seller_prompt_template": _AGGRESSIVE_SELLER_TEMPLATE,
    },
}


# ── Prompt builder ──────────────────────────────────────────────────────


def build_system_prompt(
    role: str,
    persona: PersonaType,
    config: "NegotiationConfig",
) -> str:
    """Assemble a complete system prompt for a negotiation agent.

    Fills in the persona template with concrete values from *config* and
    handles information asymmetry (whether an agent knows the opponent's
    reservation price).

    Args:
        role: ``"buyer"`` or ``"seller"``.
        persona: The behavioural persona to apply.
        config: The negotiation configuration.

    Returns:
        The fully rendered system prompt string.

    Raises:
        ValueError: If *role* is not ``"buyer"`` or ``"seller"``.
    """
    if role not in ("buyer", "seller"):
        raise ValueError(f"role must be 'buyer' or 'seller', got '{role}'")

    templates = PERSONAS[persona]
    template_key = f"{role}_prompt_template"
    template = templates[template_key]

    info_mode = InformationMode(config.information_mode)

    # Determine reservation price for *this* agent
    if role == "buyer":
        reservation_price = config.buyer_reservation_price
        opponent_reservation = config.seller_reservation_price
    else:
        reservation_price = config.seller_reservation_price
        opponent_reservation = config.buyer_reservation_price

    # Build opponent-knowledge blurb based on information mode
    opponent_info = _build_opponent_info(role, info_mode, opponent_reservation)

    return template.format(
        item_name=config.item_name,
        item_description=config.item_description,
        reservation_price=reservation_price,
        opponent_info=opponent_info,
        response_format=_RESPONSE_FORMAT_INSTRUCTION,
    )


def _build_opponent_info(
    role: str,
    info_mode: InformationMode,
    opponent_reservation: float,
) -> str:
    """Return a string describing what this agent knows about the opponent.

    Args:
        role: ``"buyer"`` or ``"seller"``.
        info_mode: The information-asymmetry setting.
        opponent_reservation: The opponent's reservation price.

    Returns:
        A human-readable blurb for inclusion in the system prompt.
    """
    if info_mode == InformationMode.SYMMETRIC_HIDDEN:
        return "You do NOT know the other party's reservation price."

    if info_mode == InformationMode.ASYMMETRIC_BUYER_KNOWS:
        if role == "buyer":
            return (
                f"**Insider knowledge:** You know the seller's minimum acceptable "
                f"price is ${opponent_reservation:.2f}. Use this strategically."
            )
        return "You do NOT know the buyer's maximum budget."

    if info_mode == InformationMode.ASYMMETRIC_SELLER_KNOWS:
        if role == "seller":
            return (
                f"**Insider knowledge:** You know the buyer's maximum budget is "
                f"${opponent_reservation:.2f}. Use this strategically."
            )
        return "You do NOT know the seller's minimum acceptable price."

    return "You do NOT know the other party's reservation price."
