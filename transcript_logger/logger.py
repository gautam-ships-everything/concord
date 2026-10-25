"""Transcript logging — persists negotiation turns and results to JSON files."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator.engine import NegotiationResult, NegotiationTurn


class TranscriptLogger:
    """Records negotiation turns and saves complete transcripts as JSON.

    Each negotiation session is persisted to its own file named
    ``<negotiation_id>.json`` inside the configured output directory.
    """

    def __init__(self, output_dir: str) -> None:
        """Initialise the logger.

        Creates the output directory if it does not already exist.

        Args:
            output_dir: Directory path where transcript JSON files are saved.
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._turns: list["NegotiationTurn"] = []

    def log_turn(self, turn: "NegotiationTurn") -> None:
        """Append a turn to the in-memory transcript.

        Args:
            turn: The :class:`NegotiationTurn` to record.
        """
        self._turns.append(turn)

    def save(self, result: "NegotiationResult") -> str:
        """Write the complete negotiation result to a JSON file.

        The file is saved with pretty-printed formatting at
        ``<output_dir>/<negotiation_id>.json``.

        Args:
            result: The :class:`NegotiationResult` to persist.

        Returns:
            The absolute path to the saved JSON file.
        """
        file_path = self.get_transcript_path(result.negotiation_id)
        data = asdict(result) if hasattr(result, "__dataclass_fields__") else {
            "negotiation_id": result.negotiation_id,
            "config": result.config,
            "turns": result.turns,
            "outcome": result.outcome,
            "final_price": result.final_price,
            "buyer_surplus": result.buyer_surplus,
            "seller_surplus": result.seller_surplus,
            "total_surplus": result.total_surplus,
            "num_turns": result.num_turns,
            "duration_seconds": result.duration_seconds,
            "timestamp": result.timestamp,
        }

        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

        return file_path

    def get_transcript_path(self, negotiation_id: str) -> str:
        """Return the file path for a given negotiation ID.

        Args:
            negotiation_id: The UUID string of the negotiation.

        Returns:
            Absolute path to the transcript JSON file.
        """
        return str(Path(self.output_dir) / f"{negotiation_id}.json")
