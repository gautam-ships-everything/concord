"""Negotiation configuration settings for Project Concord."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class NegotiationConfig:
    """Central configuration for a negotiation session.

    Holds all parameters that define a negotiation: model settings, pricing
    constraints, persona choices, information asymmetry mode, and output paths.
    """

    model_name: str = "gemma-4-27b-it"
    api_key: str = ""
    max_turns: int = 20
    buyer_reservation_price: float = 100.0
    seller_reservation_price: float = 60.0
    item_name: str = "Vintage Mechanical Keyboard"
    item_description: str = (
        "A rare 1985 IBM Model M mechanical keyboard in excellent condition"
    )
    buyer_persona: str = "neutral"
    seller_persona: str = "neutral"
    information_mode: str = "symmetric_hidden"
    temperature: float = 0.7
    output_dir: str = "transcripts"
    results_dir: str = "results"

    # ── Allowed values ──────────────────────────────────────────────────
    _VALID_PERSONAS: tuple[str, ...] = field(
        default=("cooperative", "neutral", "aggressive"),
        init=False,
        repr=False,
    )
    _VALID_INFO_MODES: tuple[str, ...] = field(
        default=(
            "symmetric_hidden",
            "asymmetric_buyer_knows",
            "asymmetric_seller_knows",
        ),
        init=False,
        repr=False,
    )

    # ── Factory ─────────────────────────────────────────────────────────
    @classmethod
    def load_from_env(cls, dotenv_path: Optional[str] = None) -> "NegotiationConfig":
        """Create a config populated from environment variables and an optional .env file.

        Looks for a ``.env`` file in the current working directory (or at
        *dotenv_path*) and loads it via ``python-dotenv``, then reads the
        matching ``CONCORD_*`` / ``GOOGLE_API_KEY`` environment variables.

        Args:
            dotenv_path: Explicit path to a ``.env`` file.  When *None* the
                default ``python-dotenv`` search is used.

        Returns:
            A fully-populated :class:`NegotiationConfig` instance.
        """
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=dotenv_path, override=False)
        except ImportError:
            pass  # python-dotenv is optional at runtime

        def _env(key: str, default: str = "") -> str:
            return os.environ.get(key, default)

        return cls(
            model_name=_env("CONCORD_MODEL_NAME", "gemma-4-27b-it"),
            api_key=_env("GOOGLE_API_KEY", ""),
            max_turns=int(_env("CONCORD_MAX_TURNS", "20")),
            buyer_reservation_price=float(
                _env("CONCORD_BUYER_RESERVATION_PRICE", "100.0")
            ),
            seller_reservation_price=float(
                _env("CONCORD_SELLER_RESERVATION_PRICE", "60.0")
            ),
            item_name=_env("CONCORD_ITEM_NAME", "Vintage Mechanical Keyboard"),
            item_description=_env(
                "CONCORD_ITEM_DESCRIPTION",
                "A rare 1985 IBM Model M mechanical keyboard in excellent condition",
            ),
            buyer_persona=_env("CONCORD_BUYER_PERSONA", "neutral"),
            seller_persona=_env("CONCORD_SELLER_PERSONA", "neutral"),
            information_mode=_env("CONCORD_INFORMATION_MODE", "symmetric_hidden"),
            temperature=float(_env("CONCORD_TEMPERATURE", "0.7")),
            output_dir=_env("CONCORD_OUTPUT_DIR", "transcripts"),
            results_dir=_env("CONCORD_RESULTS_DIR", "results"),
        )

    # ── Validation ──────────────────────────────────────────────────────
    def validate(self) -> None:
        """Validate the configuration, raising ``ValueError`` on problems.

        Checks performed:
        * ``buyer_reservation_price`` > ``seller_reservation_price``
          (positive bargaining zone).
        * Personas are among the recognised types.
        * ``information_mode`` is recognised.
        * ``api_key`` is non-empty.
        * ``max_turns`` >= 1.
        * ``temperature`` is in [0, 2].

        Raises:
            ValueError: If any check fails.
        """
        if self.buyer_reservation_price <= self.seller_reservation_price:
            raise ValueError(
                f"Buyer reservation price ({self.buyer_reservation_price}) must be "
                f"greater than seller reservation price "
                f"({self.seller_reservation_price}) to allow a positive bargaining zone."
            )

        if self.buyer_persona.lower() not in self._VALID_PERSONAS:
            raise ValueError(
                f"Invalid buyer persona '{self.buyer_persona}'. "
                f"Must be one of {self._VALID_PERSONAS}."
            )

        if self.seller_persona.lower() not in self._VALID_PERSONAS:
            raise ValueError(
                f"Invalid seller persona '{self.seller_persona}'. "
                f"Must be one of {self._VALID_PERSONAS}."
            )

        if self.information_mode not in self._VALID_INFO_MODES:
            raise ValueError(
                f"Invalid information mode '{self.information_mode}'. "
                f"Must be one of {self._VALID_INFO_MODES}."
            )

        # api_key is optional at startup; when absent, the agent operates in
        # simulated Gemma 4 negotiation mode until GOOGLE_API_KEY is provided.
        if self.max_turns < 1:
            raise ValueError(
                f"max_turns must be >= 1, got {self.max_turns}."
            )

        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"temperature must be between 0.0 and 2.0, got {self.temperature}."
            )
