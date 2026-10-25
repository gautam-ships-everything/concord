"""
Negotiation analysis metrics and visualization module.

Provides comprehensive analysis of negotiation transcripts including
deal success rates, surplus analysis, convergence metrics, and
Pareto efficiency evaluation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    _HAS_PLT = True
except ImportError:
    matplotlib = None  # type: ignore
    plt = None  # type: ignore
    sns = None  # type: ignore
    _HAS_PLT = False


class NegotiationAnalyzer:
    """Analyzes negotiation transcripts and generates reports and visualizations.

    Loads JSON transcripts from a directory, computes metrics such as deal
    success rate, surplus split, and rounds to convergence, and produces
    publication-quality charts.

    Args:
        transcripts_dir: Path to the directory containing JSON transcript files.
    """

    def __init__(self, transcripts_dir: str = "transcripts") -> None:
        self.transcripts_dir: str = transcripts_dir
        self.transcripts: list[dict] = self.load_transcripts()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_transcripts(self) -> list[dict]:
        """Read all JSON transcript files from the transcripts directory.

        Returns:
            A list of transcript dictionaries parsed from JSON files.
        """
        transcripts: list[dict] = []
        transcript_path = Path(self.transcripts_dir)

        if not transcript_path.exists():
            print(f"[WARN] Transcripts directory '{self.transcripts_dir}' not found.")
            return transcripts

        for filepath in sorted(transcript_path.glob("*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    transcripts.append(data)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[WARN] Skipping {filepath.name}: {exc}")

        return transcripts

    def to_dataframe(self) -> pd.DataFrame:
        """Convert loaded transcripts to a pandas DataFrame.

        Returns:
            DataFrame with columns: negotiation_id, buyer_persona,
            seller_persona, information_mode, outcome, final_price,
            buyer_surplus, seller_surplus, total_surplus, num_turns,
            duration_seconds.
        """
        if not self.transcripts:
            return pd.DataFrame(columns=[
                "negotiation_id", "buyer_persona", "seller_persona",
                "information_mode", "outcome", "final_price",
                "buyer_surplus", "seller_surplus", "total_surplus",
                "num_turns", "duration_seconds",
            ])

        rows: list[dict] = []
        for t in self.transcripts:
            config = t.get("config", {})
            rows.append({
                "negotiation_id": t.get("negotiation_id", ""),
                "buyer_persona": config.get("buyer_persona", "unknown"),
                "seller_persona": config.get("seller_persona", "unknown"),
                "information_mode": config.get("information_mode", "unknown"),
                "outcome": t.get("outcome", "unknown"),
                "final_price": t.get("final_price"),
                "buyer_surplus": t.get("buyer_surplus"),
                "seller_surplus": t.get("seller_surplus"),
                "total_surplus": t.get("total_surplus"),
                "num_turns": t.get("num_turns", 0),
                "duration_seconds": t.get("duration_seconds", 0.0),
            })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _successful(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return rows where the outcome was an agreement."""
        return df[df["outcome"].str.upper() == "AGREEMENT"]

    def deal_success_rate(self, group_by: Optional[str] = None) -> pd.DataFrame:
        """Compute the percentage of negotiations ending in agreement.

        Args:
            group_by: Optional column name (e.g. ``'buyer_persona'``,
                ``'seller_persona'``, ``'information_mode'``) or the
                special value ``'persona_pair'`` to group by both personas.

        Returns:
            DataFrame with success rate as a percentage.
        """
        df = self.to_dataframe()
        if df.empty:
            return pd.DataFrame(columns=["success_rate"])

        df["is_success"] = (df["outcome"].str.upper() == "AGREEMENT").astype(int)

        if group_by == "persona_pair":
            grouped = df.groupby(["buyer_persona", "seller_persona"])
        elif group_by is not None:
            grouped = df.groupby(group_by)
        else:
            rate = df["is_success"].mean() * 100
            return pd.DataFrame({"success_rate": [rate]})

        result = grouped["is_success"].mean() * 100
        return result.rename("success_rate").reset_index()

    def rounds_to_convergence(self, group_by: Optional[str] = None) -> pd.DataFrame:
        """Compute mean and std of turn count for successful deals.

        Args:
            group_by: Optional grouping column or ``'persona_pair'``.

        Returns:
            DataFrame with ``num_turns_mean`` and ``num_turns_std`` columns.
        """
        df = self._successful(self.to_dataframe())
        if df.empty:
            return pd.DataFrame(columns=["num_turns_mean", "num_turns_std"])

        if group_by == "persona_pair":
            grouped = df.groupby(["buyer_persona", "seller_persona"])
        elif group_by is not None:
            grouped = df.groupby(group_by)
        else:
            return pd.DataFrame({
                "num_turns_mean": [df["num_turns"].mean()],
                "num_turns_std": [df["num_turns"].std()],
            })

        agg = grouped["num_turns"].agg(["mean", "std"]).reset_index()
        agg.columns = [*agg.columns[:-2], "num_turns_mean", "num_turns_std"]
        return agg

    def surplus_split(self, group_by: Optional[str] = None) -> pd.DataFrame:
        """Compute mean buyer and seller surplus percentages for deals.

        The surplus percentage is each party's surplus as a fraction of the
        total surplus.

        Args:
            group_by: Optional grouping column or ``'persona_pair'``.

        Returns:
            DataFrame with ``buyer_surplus_pct`` and ``seller_surplus_pct``.
        """
        df = self._successful(self.to_dataframe()).copy()
        if df.empty:
            return pd.DataFrame(columns=["buyer_surplus_pct", "seller_surplus_pct"])

        # Avoid division by zero
        total = df["total_surplus"].replace(0, np.nan)
        df["buyer_surplus_pct"] = (df["buyer_surplus"] / total) * 100
        df["seller_surplus_pct"] = (df["seller_surplus"] / total) * 100

        if group_by == "persona_pair":
            grouped = df.groupby(["buyer_persona", "seller_persona"])
        elif group_by is not None:
            grouped = df.groupby(group_by)
        else:
            return pd.DataFrame({
                "buyer_surplus_pct": [df["buyer_surplus_pct"].mean()],
                "seller_surplus_pct": [df["seller_surplus_pct"].mean()],
            })

        agg = grouped[["buyer_surplus_pct", "seller_surplus_pct"]].mean().reset_index()
        return agg

    def pareto_efficiency(self) -> pd.DataFrame:
        """Evaluate Pareto efficiency for each negotiation.

        For each transcript, determines:
        - ``in_zopa``: whether the final price is within the Zone of
          Possible Agreement (between seller reservation and buyer
          reservation prices).
        - ``surplus_maximized``: whether the total surplus equals the
          maximum possible surplus (buyer_max - seller_min).

        Returns:
            DataFrame with negotiation_id, in_zopa, surplus_maximized,
            and efficiency_ratio columns.
        """
        if not self.transcripts:
            return pd.DataFrame(columns=[
                "negotiation_id", "in_zopa", "surplus_maximized",
                "efficiency_ratio",
            ])

        rows: list[dict] = []
        for t in self.transcripts:
            config = t.get("config", {})
            buyer_max = config.get("buyer_reservation_price", 0)
            seller_min = config.get("seller_reservation_price", 0)
            final_price = t.get("final_price")
            total_surplus = t.get("total_surplus", 0)
            max_possible_surplus = buyer_max - seller_min

            in_zopa = False
            surplus_maximized = False
            efficiency_ratio = 0.0

            if final_price is not None and max_possible_surplus > 0:
                in_zopa = seller_min <= final_price <= buyer_max
                efficiency_ratio = (total_surplus / max_possible_surplus) if max_possible_surplus > 0 else 0.0
                surplus_maximized = abs(total_surplus - max_possible_surplus) < 1e-6

            rows.append({
                "negotiation_id": t.get("negotiation_id", ""),
                "in_zopa": in_zopa,
                "surplus_maximized": surplus_maximized,
                "efficiency_ratio": round(efficiency_ratio, 4),
            })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def generate_summary_report(self, output_path: Optional[str] = None) -> str:
        """Generate a text summary of all negotiation metrics.

        Args:
            output_path: Optional file path to write the report to.

        Returns:
            The report as a string.
        """
        df = self.to_dataframe()
        lines: list[str] = []
        sep = "=" * 60

        lines.append(sep)
        lines.append("  CONCORD — Negotiation Analysis Summary Report")
        lines.append(sep)
        lines.append("")

        if df.empty:
            lines.append("No transcripts found. Nothing to report.")
            report = "\n".join(lines)
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_text(report, encoding="utf-8")
            return report

        # Overview
        lines.append(f"Total negotiations: {len(df)}")
        success_df = self.deal_success_rate()
        rate = success_df["success_rate"].iloc[0] if not success_df.empty else 0.0
        lines.append(f"Overall deal success rate: {rate:.1f}%")
        lines.append("")

        # Deal success by persona pair
        lines.append("--- Deal Success Rate by Persona Pair ---")
        pair_rate = self.deal_success_rate(group_by="persona_pair")
        if not pair_rate.empty:
            lines.append(pair_rate.to_string(index=False))
        else:
            lines.append("  (no data)")
        lines.append("")

        # Deal success by information mode
        lines.append("--- Deal Success Rate by Information Mode ---")
        info_rate = self.deal_success_rate(group_by="information_mode")
        if not info_rate.empty:
            lines.append(info_rate.to_string(index=False))
        else:
            lines.append("  (no data)")
        lines.append("")

        # Rounds to convergence
        lines.append("--- Rounds to Convergence (successful deals) ---")
        rtc = self.rounds_to_convergence()
        if not rtc.empty:
            lines.append(
                f"  Mean: {rtc['num_turns_mean'].iloc[0]:.1f}  "
                f"Std: {rtc['num_turns_std'].iloc[0]:.1f}"
            )
        else:
            lines.append("  (no successful deals)")
        lines.append("")

        # Surplus split
        lines.append("--- Surplus Split (successful deals) ---")
        ss = self.surplus_split()
        if not ss.empty:
            lines.append(
                f"  Buyer surplus:  {ss['buyer_surplus_pct'].iloc[0]:.1f}%\n"
                f"  Seller surplus: {ss['seller_surplus_pct'].iloc[0]:.1f}%"
            )
        else:
            lines.append("  (no successful deals)")
        lines.append("")

        # Pareto efficiency
        lines.append("--- Pareto Efficiency ---")
        pe = self.pareto_efficiency()
        if not pe.empty:
            in_zopa_pct = pe["in_zopa"].mean() * 100
            max_surplus_pct = pe["surplus_maximized"].mean() * 100
            avg_eff = pe["efficiency_ratio"].mean() * 100
            lines.append(f"  Deals in ZOPA: {in_zopa_pct:.1f}%")
            lines.append(f"  Surplus maximised: {max_surplus_pct:.1f}%")
            lines.append(f"  Avg efficiency ratio: {avg_eff:.1f}%")
        else:
            lines.append("  (no data)")
        lines.append("")

        lines.append(sep)

        report = "\n".join(lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(report, encoding="utf-8")
            print(f"Report saved to {output_path}")

        return report

    # ------------------------------------------------------------------
    # Visualizations
    # ------------------------------------------------------------------

    def _apply_style(self) -> None:
        """Apply a consistent visual style for all charts."""
        if _HAS_PLT and sns is not None:
            sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)

    def plot_deal_success_rate(self, save_path: Optional[str] = None) -> None:
        """Bar chart of deal success rate grouped by persona pair."""
        if not _HAS_PLT:
            print("[WARN] matplotlib/seaborn not installed. Run 'pip install matplotlib seaborn' to generate plots.")
            return
        self._apply_style()
        pair_rate = self.deal_success_rate(group_by="persona_pair")

        if pair_rate.empty:
            print("[WARN] No data to plot deal success rate.")
            return

        pair_rate["label"] = (
            pair_rate["buyer_persona"] + "\nvs\n" + pair_rate["seller_persona"]
        )

        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(pair_rate["label"], pair_rate["success_rate"], color=sns.color_palette("viridis", len(pair_rate)))
        ax.set_ylabel("Success Rate (%)")
        ax.set_xlabel("Buyer vs Seller Persona")
        ax.set_title("Deal Success Rate by Persona Pair")
        ax.set_ylim(0, 105)

        for bar, val in zip(bars, pair_rate["success_rate"]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{val:.0f}%", ha="center", va="bottom", fontsize=9)

        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to {save_path}")

        plt.close(fig)

    def plot_surplus_distribution(self, save_path: Optional[str] = None) -> None:
        """Grouped bar chart of mean buyer and seller surplus percentages."""
        if not _HAS_PLT:
            return
        self._apply_style()
        ss = self.surplus_split(group_by="persona_pair")

        if ss.empty:
            print("[WARN] No data to plot surplus distribution.")
            return

        ss["label"] = ss["buyer_persona"] + " vs " + ss["seller_persona"]

        fig, ax = plt.subplots(figsize=(14, 6))
        x = np.arange(len(ss))
        width = 0.35

        ax.bar(x - width / 2, ss["buyer_surplus_pct"], width, label="Buyer Surplus %", color="#4C72B0")
        ax.bar(x + width / 2, ss["seller_surplus_pct"], width, label="Seller Surplus %", color="#DD8452")

        ax.set_xticks(x)
        ax.set_xticklabels(ss["label"], rotation=45, ha="right")
        ax.set_ylabel("Surplus Share (%)")
        ax.set_title("Surplus Distribution by Persona Pair")
        ax.legend()

        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to {save_path}")

        plt.close(fig)

    def plot_rounds_distribution(self, save_path: Optional[str] = None) -> None:
        """Box plot of turn count distribution for successful deals."""
        if not _HAS_PLT:
            return
        self._apply_style()
        df = self._successful(self.to_dataframe())

        if df.empty:
            print("[WARN] No successful deals to plot rounds distribution.")
            return

        df = df.copy()
        df["persona_pair"] = df["buyer_persona"] + " vs " + df["seller_persona"]

        fig, ax = plt.subplots(figsize=(12, 6))
        sns.boxplot(data=df, x="persona_pair", y="num_turns", ax=ax, palette="Set2")
        ax.set_xlabel("Persona Pair")
        ax.set_ylabel("Number of Turns")
        ax.set_title("Rounds to Convergence Distribution")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to {save_path}")

        plt.close(fig)

    def plot_persona_heatmap(self, save_path: Optional[str] = None) -> None:
        """Heatmap of deal success rate by buyer × seller persona."""
        if not _HAS_PLT:
            return
        self._apply_style()
        pair_rate = self.deal_success_rate(group_by="persona_pair")

        if pair_rate.empty:
            print("[WARN] No data to plot persona heatmap.")
            return

        pivot = pair_rate.pivot(
            index="buyer_persona",
            columns="seller_persona",
            values="success_rate",
        )

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".0f",
            cmap="YlGnBu",
            vmin=0,
            vmax=100,
            ax=ax,
            linewidths=0.5,
            cbar_kws={"label": "Success Rate (%)"},
        )
        ax.set_title("Deal Success Rate: Buyer × Seller Persona")
        ax.set_ylabel("Buyer Persona")
        ax.set_xlabel("Seller Persona")
        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to {save_path}")

        plt.close(fig)
        pair_rate = self.deal_success_rate(group_by="persona_pair")

        if pair_rate.empty:
            print("[WARN] No data to plot persona heatmap.")
            return

        pivot = pair_rate.pivot(
            index="buyer_persona",
            columns="seller_persona",
            values="success_rate",
        )

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".0f",
            cmap="YlGnBu",
            vmin=0,
            vmax=100,
            ax=ax,
            linewidths=0.5,
            cbar_kws={"label": "Success Rate (%)"},
        )
        ax.set_title("Deal Success Rate: Buyer × Seller Persona")
        ax.set_ylabel("Buyer Persona")
        ax.set_xlabel("Seller Persona")
        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to {save_path}")

        plt.close(fig)

    def export_all_plots(self, output_dir: str = "results") -> None:
        """Generate and save all plots to the specified directory.

        Args:
            output_dir: Directory to save plots into.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        self.plot_deal_success_rate(
            save_path=os.path.join(output_dir, "deal_success_rate.png")
        )
        self.plot_surplus_distribution(
            save_path=os.path.join(output_dir, "surplus_distribution.png")
        )
        self.plot_rounds_distribution(
            save_path=os.path.join(output_dir, "rounds_distribution.png")
        )
        self.plot_persona_heatmap(
            save_path=os.path.join(output_dir, "persona_heatmap.png")
        )

        print(f"All plots exported to {output_dir}/")
