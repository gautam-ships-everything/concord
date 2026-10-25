#!/usr/bin/env python3
"""
Concord — Master Project Runner

Single script to run, test, analyze, and launch the entire Concord multi-agent
negotiation platform. Automatically verifies environment, runs simulated or
live Gemma 4 agents, and provides an interactive terminal dashboard.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BANNER = r"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     🤝  PROJECT CONCORD — LLM Multi-Agent Negotiation Simulator   ║
║         B.Tech Mini Project | Autonomous Gemma 4 Agents           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""


def check_and_setup_environment() -> None:
    """Check environment variables and dependencies."""
    print("\n🔍 Checking environment...")
    dotenv_file = PROJECT_ROOT / ".env"
    if not dotenv_file.exists():
        example = PROJECT_ROOT / ".env.example"
        if example.exists():
            try:
                import shutil
                shutil.copy(example, dotenv_file)
                print("  ℹ️ Created .env from .env.example")
            except Exception:
                pass

    from config.settings import NegotiationConfig
    config = NegotiationConfig.load_from_env()
    api_key = config.api_key.strip()
    if api_key and api_key != "your_api_key_here":
        print(f"  ✨ Live Google GenAI API key detected! Using model: {config.model_name}")
    else:
        print("  ⚡ Running in Gemma 4 Strategic Simulator mode.")
        print("     (To switch to live API, add your key to Concord/.env: GOOGLE_API_KEY=AIza...)")


def run_demo_negotiation() -> None:
    """Run a quick demonstration negotiation between two agents."""
    print("\n" + "=" * 65)
    print("▶ 1. RUNNING DEMONSTRATION NEGOTIATION")
    print("=" * 65)
    from config.personas import PersonaType
    from config.settings import NegotiationConfig
    from orchestrator.engine import NegotiationEngine

    cfg = NegotiationConfig.load_from_env()
    cfg.buyer_persona = "cooperative"
    cfg.seller_persona = "aggressive"
    cfg.item_name = "Vintage Mechanical Keyboard"

    engine = NegotiationEngine(cfg)
    result = engine.run()
    return result


def show_quick_analytics() -> None:
    """Compute and display summary report of all stored transcripts."""
    print("\n" + "=" * 65)
    print("▶ 2. AGGREGATE ECONOMIC ANALYSIS")
    print("=" * 65)
    from analysis.metrics import NegotiationAnalyzer

    analyzer = NegotiationAnalyzer(transcripts_dir=str(PROJECT_ROOT / "transcripts"))
    report = analyzer.generate_summary_report(output_path=str(PROJECT_ROOT / "results" / "summary_report.txt"))
    print(report)


def launch_web_ui() -> None:
    """Launch the interactive Streamlit dashboard."""
    print("\n🚀 Launching Streamlit web interface...")
    ui_script = PROJECT_ROOT / "ui" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(ui_script)])


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


def interactive_menu() -> None:
    """Interactive loop for user navigation."""
    while True:
        print("\n" + "─" * 65)
        print("🎯 WHAT WOULD YOU LIKE TO DO NEXT?")
        print("─" * 65)
        print("  [1] Run a custom Single Negotiation")
        print("  [2] Run Multi-Trial Experiment Matrix")
        print("  [3] Re-run Analysis Report")
        print("  [4] Launch Web Dashboard (Streamlit UI)")
        print("  [5] Exit")
        print("─" * 65)
        try:
            choice = input("Enter choice [1-5] (default 1): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

        if choice in ("", "1"):
            b_p = normalize_persona(input("Buyer persona (cooperative/neutral/aggressive) [neutral]: ").strip() or "neutral")
            s_p = normalize_persona(input("Seller persona (cooperative/neutral/aggressive) [neutral]: ").strip() or "neutral")
            cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), "single", "--buyer-persona", b_p, "--seller-persona", s_p]
            subprocess.run(cmd)
        elif choice == "2":
            trials = input("Number of trials per condition [5]: ").strip() or "5"
            cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), "experiment", "--trials", trials]
            subprocess.run(cmd)
        elif choice == "3":
            show_quick_analytics()
        elif choice == "4":
            launch_web_ui()
        elif choice == "5":
            print("\nThank you for using Concord! Goodbye.")
            break
        else:
            print("Invalid choice, please select between 1 and 5.")


def main() -> None:
    # Check CLI arguments first
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        remaining = sys.argv[2:]
        if arg in ("--ui", "-u", "ui"):
            launch_web_ui()
            return
        elif arg in ("--experiment", "-e", "experiment"):
            subprocess.run([sys.executable, str(PROJECT_ROOT / "main.py"), "experiment", *remaining])
            return
        elif arg in ("--single", "-s", "single"):
            subprocess.run([sys.executable, str(PROJECT_ROOT / "main.py"), "single", *remaining])
            return
        elif arg in ("--analyze", "-a", "analyze"):
            show_quick_analytics()
            return

    print(BANNER)

    check_and_setup_environment()
    run_demo_negotiation()
    show_quick_analytics()
    interactive_menu()


if __name__ == "__main__":
    main()
