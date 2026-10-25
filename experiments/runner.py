"""
Experiment runner for systematic negotiation experiments.

Generates a full factorial experiment matrix across persona types and
information modes, runs each condition for multiple trials, and collects
results for downstream analysis.
"""

from __future__ import annotations

import copy
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from typing import Optional

from config.personas import InformationMode, PersonaType
from config.settings import NegotiationConfig
from orchestrator.engine import NegotiationEngine, NegotiationResult

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Run systematic experiments across persona and information-mode conditions.

    Generates a full factorial design of buyer persona × seller persona ×
    information mode, repeating each condition for a configurable number of
    trials, then collects all :class:`NegotiationResult` objects.

    Args:
        base_config: A baseline :class:`NegotiationConfig` whose fields are
            overridden per condition.
        trials_per_condition: Number of independent trials for each
            experimental condition.
    """

    def __init__(
        self,
        base_config: NegotiationConfig,
        trials_per_condition: int = 25,
    ) -> None:
        self.base_config: NegotiationConfig = base_config
        self.trials_per_condition: int = trials_per_condition

    # ------------------------------------------------------------------
    # Experiment matrix generation
    # ------------------------------------------------------------------

    def generate_experiment_matrix(self) -> list[NegotiationConfig]:
        """Generate all experimental condition configurations.

        Creates a full factorial combination of:
        - buyer_persona: cooperative, neutral, aggressive
        - seller_persona: cooperative, neutral, aggressive
        - information_mode: symmetric_hidden, asymmetric_buyer_knows,
          asymmetric_seller_knows

        Each combination is repeated ``trials_per_condition`` times.

        Returns:
            A list of :class:`NegotiationConfig` objects (one per trial).
        """
        personas = [p.value for p in PersonaType]
        info_modes = [m.value for m in InformationMode]

        configs: list[NegotiationConfig] = []
        for buyer_p in personas:
            for seller_p in personas:
                for info_mode in info_modes:
                    for _trial in range(self.trials_per_condition):
                        cfg = replace(
                            self.base_config,
                            buyer_persona=buyer_p,
                            seller_persona=seller_p,
                            information_mode=info_mode,
                        )
                        configs.append(cfg)

        return configs

    # ------------------------------------------------------------------
    # Running experiments
    # ------------------------------------------------------------------

    @staticmethod
    def _run_single(config: NegotiationConfig, label: str) -> Optional[NegotiationResult]:
        """Execute a single negotiation, catching any errors.

        Args:
            config: The negotiation configuration.
            label: A human-readable label for logging progress.

        Returns:
            The :class:`NegotiationResult`, or ``None`` if an error occurred.
        """
        try:
            engine = NegotiationEngine(config)
            result = engine.run()
            return result
        except Exception:
            logger.exception("Error running experiment %s", label)
            return None

    def run_all(self, parallel: bool = False) -> list[NegotiationResult]:
        """Run all experiments defined by the experiment matrix.

        Args:
            parallel: If ``True``, use a :class:`ThreadPoolExecutor` with
                ``max_workers=3`` for concurrent execution.

        Returns:
            A list of :class:`NegotiationResult` objects (failed runs
            are excluded).
        """
        configs = self.generate_experiment_matrix()
        total = len(configs)
        results: list[NegotiationResult] = []

        print(f"\n🔬 Starting experiment run: {total} negotiations")
        print(f"   Conditions: {total // self.trials_per_condition} | "
              f"Trials per condition: {self.trials_per_condition}")
        print()

        start_time = time.time()

        if parallel:
            results = self._run_parallel(configs, total)
        else:
            results = self._run_sequential(configs, total)

        elapsed = time.time() - start_time
        print(f"\n✅ Completed {len(results)}/{total} experiments "
              f"in {elapsed:.1f}s")

        return results

    def _run_sequential(
        self,
        configs: list[NegotiationConfig],
        total: int,
    ) -> list[NegotiationResult]:
        """Run experiments one at a time."""
        results: list[NegotiationResult] = []
        for idx, cfg in enumerate(configs, 1):
            label = f"{idx}/{total}"
            print(f"Running experiment {label}...", end="\r")
            result = self._run_single(cfg, label)
            if result is not None:
                results.append(result)
        return results

    def _run_parallel(
        self,
        configs: list[NegotiationConfig],
        total: int,
    ) -> list[NegotiationResult]:
        """Run experiments using a thread pool."""
        results: list[NegotiationResult] = []
        completed = 0

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_idx = {
                executor.submit(self._run_single, cfg, f"{i}/{total}"): i
                for i, cfg in enumerate(configs, 1)
            }

            for future in as_completed(future_to_idx):
                completed += 1
                print(f"Running experiment {completed}/{total}...", end="\r")
                result = future.result()
                if result is not None:
                    results.append(result)

        return results

    # ------------------------------------------------------------------
    # Single condition runner
    # ------------------------------------------------------------------

    def run_condition(
        self,
        buyer_persona: str,
        seller_persona: str,
        info_mode: str,
        trials: int,
    ) -> list[NegotiationResult]:
        """Run a specific experimental condition for multiple trials.

        Args:
            buyer_persona: Buyer persona value (e.g. ``'cooperative'``).
            seller_persona: Seller persona value.
            info_mode: Information mode value (e.g.
                ``'symmetric_hidden'``).
            trials: Number of independent trials to run.

        Returns:
            A list of :class:`NegotiationResult` objects for this condition.
        """
        results: list[NegotiationResult] = []
        print(f"\n🔬 Running condition: {buyer_persona} buyer vs "
              f"{seller_persona} seller | {info_mode} | {trials} trials")

        for i in range(1, trials + 1):
            cfg = replace(
                self.base_config,
                buyer_persona=buyer_persona,
                seller_persona=seller_persona,
                information_mode=info_mode,
            )
            label = f"{i}/{trials}"
            print(f"  Trial {label}...", end="\r")
            result = self._run_single(cfg, label)
            if result is not None:
                results.append(result)

        print(f"  ✅ {len(results)}/{trials} trials completed")
        return results
