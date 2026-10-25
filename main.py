#!/usr/bin/env python3
"""
Concord — Multi-Agent Negotiation Simulator

Single entry-point CLI with subcommands for running negotiations,
experiments, analysis, and launching the Streamlit dashboard.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

# Ensure project root is on the path
_PROJECT_ROOT = str(Path(__file__).resolve().parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    # Stub out colorama if not installed
    class _Stub:
        def __getattr__(self, _: str) -> str:
            return ""
    Fore = _Stub()  # type: ignore[assignment]
    Style = _Stub()  # type: ignore[assignment]

from config.personas import InformationMode, PersonaType
from config.settings import NegotiationConfig
from orchestrator.engine import NegotiationEngine


# ── Banner ──────────────────────────────────────────────────────────

BANNER = rf"""
{Fore.CYAN}╔══════════════════════════════════════════════════════╗
║                                                      ║
║   🤝  CONCORD — Multi-Agent Negotiation Simulator    ║
║                                                      ║
╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""


# ── Argument parser ─────────────────────────────────────────────────

def normalize_persona(val: str) -> str:
    """Normalize persona string, handling common abbreviations and misspellings."""
    v = val.strip().lower()
    if v in ("aggressive", "aggresive", "agg", "a"):
        return "aggressive"
    if v in ("cooperative", "coop", "co-operative", "c"):
        return "cooperative"
    if v in ("neutral", "neut", "n"):
        return "neutral"
    return v


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="concord",
        description="Concord — Multi-Agent LLM Negotiation Framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── single ──────────────────────────────────────────────────────
    sp_single = subparsers.add_parser("single", help="Run a single negotiation")
    sp_single.add_argument("--buyer-persona", type=normalize_persona, default="neutral",
                           help="Buyer agent persona: cooperative, neutral, aggressive (default: neutral)")
    sp_single.add_argument("--seller-persona", type=normalize_persona, default="neutral",
                           help="Seller agent persona: cooperative, neutral, aggressive (default: neutral)")
    sp_single.add_argument("--info-mode", type=str, default="symmetric_hidden",
                           choices=[m.value for m in InformationMode],
                           help="Information mode (default: symmetric_hidden)")
    sp_single.add_argument("--buyer-max", type=float, default=100.0,
                           help="Buyer reservation price (default: 100)")
    sp_single.add_argument("--seller-min", type=float, default=60.0,
                           help="Seller reservation price (default: 60)")
    sp_single.add_argument("--max-turns", type=int, default=20,
                           help="Maximum negotiation turns (default: 20)")
    sp_single.add_argument("--item", type=str, default="Vintage Mechanical Keyboard",
                           help="Item being negotiated")
    sp_single.add_argument("--temperature", type=float, default=0.7,
                           help="LLM temperature (default: 0.7)")

    # ── experiment ──────────────────────────────────────────────────
    sp_exp = subparsers.add_parser("experiment", help="Run full experiment matrix")
    sp_exp.add_argument("--trials", type=int, default=25,
                        help="Number of trials per condition (default: 25)")
    sp_exp.add_argument("--parallel", action="store_true",
                        help="Run experiments in parallel (max 3 workers)")

    # ── analyze ─────────────────────────────────────────────────────
    sp_analyze = subparsers.add_parser("analyze", help="Analyze negotiation transcripts")
    sp_analyze.add_argument("--transcripts-dir", type=str, default="transcripts",
                            help="Directory containing transcript JSON files")
    sp_analyze.add_argument("--output-dir", type=str, default="results",
                            help="Directory to save reports and plots")
    sp_analyze.add_argument("--report", action="store_true",
                            help="Print summary report to stdout")
    sp_analyze.add_argument("--plots", action="store_true",
                            help="Generate and save all plots")

    # ── ui ──────────────────────────────────────────────────────────
    subparsers.add_parser("ui", help="Launch Streamlit dashboard")

    return parser


# ── Subcommand handlers ─────────────────────────────────────────────

def _load_base_config() -> NegotiationConfig:
    """Load configuration from .env, falling back to defaults."""
    try:
        return NegotiationConfig.load_from_env()
    except Exception:
        return NegotiationConfig(
            model_name=os.getenv("MODEL_NAME", "gemma-4-27b-it"),
            api_key=os.getenv("GOOGLE_API_KEY", ""),
        )


def cmd_single(args: argparse.Namespace) -> None:
    """Run a single negotiation with CLI-specified parameters."""
    config = _load_base_config()
    config = replace(
        config,
        buyer_persona=args.buyer_persona,
        seller_persona=args.seller_persona,
        information_mode=args.info_mode,
        buyer_reservation_price=args.buyer_max,
        seller_reservation_price=args.seller_min,
        max_turns=args.max_turns,
        item_name=args.item,
        temperature=args.temperature,
    )

    print(f"\n{Fore.GREEN}▶ Running single negotiation{Style.RESET_ALL}")
    print(f"  Item:          {config.item_name}")
    print(f"  Buyer:         {config.buyer_persona} (max ${config.buyer_reservation_price:.2f})")
    print(f"  Seller:        {config.seller_persona} (min ${config.seller_reservation_price:.2f})")
    print(f"  Info mode:     {config.information_mode}")
    print(f"  Max turns:     {config.max_turns}")
    print(f"  Temperature:   {config.temperature}")
    print()

    engine = NegotiationEngine(config)
    result = engine.run()

    # Print transcript
    print(f"\n{Fore.CYAN}{'═' * 55}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  NEGOTIATION TRANSCRIPT{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 55}{Style.RESET_ALL}\n")

    for turn in result.turns:
        role = (turn.agent_role if hasattr(turn, "agent_role") else turn.get("agent_role", "")).upper()
        persona = turn.agent_persona if hasattr(turn, "agent_persona") else turn.get("agent_persona", "")
        turn_num = turn.turn_number if hasattr(turn, "turn_number") else turn.get("turn_number", 0)
        action = turn.action if hasattr(turn, "action") else turn.get("action", "")
        amount = turn.offer_amount if hasattr(turn, "offer_amount") else turn.get("offer_amount")
        msg = turn.message if hasattr(turn, "message") else turn.get("message", "")
        color = Fore.BLUE if "BUYER" in role else Fore.RED
        print(f"{color}[Turn {turn_num}] {role} ({persona}){Style.RESET_ALL}")
        print(f"  {msg}")
        if amount is not None:
            print(f"  💰 Offer: ${amount:.2f} | Action: {action}")
        print()

    # Print result summary
    print(f"{Fore.CYAN}{'═' * 55}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  RESULT SUMMARY{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 55}{Style.RESET_ALL}")
    print(f"  Outcome:        {result.outcome}")
    price_str = f"${result.final_price:.2f}" if result.final_price is not None else "N/A"
    print(f"  Final Price:    {price_str}")
    print(f"  Buyer Surplus:  {result.buyer_surplus}")
    print(f"  Seller Surplus: {result.seller_surplus}")
    print(f"  Total Surplus:  {result.total_surplus}")
    print(f"  Turns:          {result.num_turns}")
    print(f"  Duration:       {result.duration_seconds:.1f}s")
    print()


def cmd_experiment(args: argparse.Namespace) -> None:
    """Run the full experiment matrix."""
    from experiments.runner import ExperimentRunner

    config = _load_base_config()
    runner = ExperimentRunner(base_config=config, trials_per_condition=args.trials)
    results = runner.run_all(parallel=args.parallel)

    # Summary
    total = len(results)
    agreements = sum(1 for r in results if str(r.outcome).upper() == "AGREEMENT")

    print(f"\n{Fore.GREEN}{'═' * 55}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  EXPERIMENT SUMMARY{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 55}{Style.RESET_ALL}")
    print(f"  Total runs:     {total}")
    print(f"  Agreements:     {agreements} ({agreements / total * 100:.1f}%)" if total > 0 else "")
    print(f"  Failed/errors:  {len(runner.generate_experiment_matrix()) - total}")

    if agreements > 0:
        prices = [r.final_price for r in results if r.final_price is not None]
        if prices:
            print(f"  Avg deal price: ${sum(prices) / len(prices):.2f}")
        surpluses = [r.total_surplus for r in results if r.total_surplus is not None]
        if surpluses:
            print(f"  Avg surplus:    ${sum(surpluses) / len(surpluses):.2f}")
    print()


def cmd_analyze(args: argparse.Namespace) -> None:
    """Analyze transcripts and optionally generate reports/plots."""
    from analysis.metrics import NegotiationAnalyzer

    analyzer = NegotiationAnalyzer(transcripts_dir=args.transcripts_dir)
    df = analyzer.to_dataframe()

    if df.empty:
        print(f"{Fore.YELLOW}⚠  No transcripts found in '{args.transcripts_dir}'.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.GREEN}▶ Analyzing {len(df)} transcripts from '{args.transcripts_dir}'{Style.RESET_ALL}\n")

    if args.report:
        report = analyzer.generate_summary_report(
            output_path=os.path.join(args.output_dir, "summary_report.txt")
        )
        print(report)

    if args.plots:
        print(f"\n{Fore.GREEN}▶ Generating plots...{Style.RESET_ALL}")
        analyzer.export_all_plots(output_dir=args.output_dir)

    if not args.report and not args.plots:
        # Default: print quick stats
        report = analyzer.generate_summary_report()
        print(report)


def cmd_ui(_args: argparse.Namespace) -> None:
    """Launch the Streamlit dashboard."""
    ui_path = os.path.join(_PROJECT_ROOT, "ui", "app.py")

    if not os.path.exists(ui_path):
        print(f"{Fore.RED}Error: UI file not found at {ui_path}{Style.RESET_ALL}")
        sys.exit(1)

    print(f"\n{Fore.GREEN}▶ Launching Streamlit dashboard...{Style.RESET_ALL}")
    print(f"  Open your browser at http://localhost:8501\n")

    subprocess.run([sys.executable, "-m", "streamlit", "run", ui_path], check=True)


# ── Main entry point ────────────────────────────────────────────────

def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate handler."""
    print(BANNER)

    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    handlers = {
        "single": cmd_single,
        "experiment": cmd_experiment,
        "analyze": cmd_analyze,
        "ui": cmd_ui,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
