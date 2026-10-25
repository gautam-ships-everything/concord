"""
Concord — Streamlit Dashboard Application.

Provides an interactive web interface for running negotiations,
browsing transcripts, and visualizing analysis results.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is on sys.path so relative imports work when
# Streamlit is launched from any directory.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from analysis.metrics import NegotiationAnalyzer
from config.personas import InformationMode, PersonaType
from config.settings import NegotiationConfig
from orchestrator.engine import NegotiationEngine

# ── Page config ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="Concord",
    page_icon="🤝",
    layout="wide",
)

# ── Sidebar navigation ─────────────────────────────────────────────

PAGES = {
    "🏠 Home": "home",
    "🎮 Run Negotiation": "run",
    "📊 Analysis Dashboard": "analysis",
    "📁 Transcript Browser": "browser",
}

with st.sidebar:
    st.title("🤝 Concord")
    st.caption("Multi-Agent Negotiation Simulator")
    st.divider()
    selected_page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")

page_key = PAGES[selected_page]


# ── Helper utilities ────────────────────────────────────────────────

def _transcripts_dir() -> str:
    return os.path.join(_PROJECT_ROOT, "transcripts")


def _results_dir() -> str:
    return os.path.join(_PROJECT_ROOT, "results")


def _load_analyzer() -> NegotiationAnalyzer:
    return NegotiationAnalyzer(transcripts_dir=_transcripts_dir())


def _persona_options() -> list[str]:
    return [p.value for p in PersonaType]


def _info_mode_options() -> list[str]:
    return [m.value for m in InformationMode]


# ════════════════════════════════════════════════════════════════════
# PAGES
# ════════════════════════════════════════════════════════════════════


def page_home() -> None:
    """Home page with project overview and quick statistics."""
    st.title("🤝 Concord: Multi-Agent Negotiation Simulator")
    st.markdown(
        """
        **Concord** is a research framework that uses large language models
        to simulate bilateral price negotiations between autonomous agents.
        Each agent is assigned a *persona* (cooperative, neutral, or
        aggressive) and an *information mode* that controls what it knows
        about the other party's reservation price.

        ---

        ### ✨ Key Features

        - 🤖 **LLM-powered agents** with configurable personas and strategies
        - 📊 **Full experimental matrix** — 27 conditions × configurable trials
        - 📈 **Rich analytics** — success rates, surplus splits, Pareto efficiency
        - 🎨 **Interactive dashboard** — run, explore, and visualize from the browser
        - 📁 **Transcript logging** — every turn is recorded as structured JSON

        ---
        """
    )

    # Quick statistics
    analyzer = _load_analyzer()
    df = analyzer.to_dataframe()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📄 Total Transcripts", len(df))

    with col2:
        if not df.empty:
            rate = (df["outcome"].str.upper() == "AGREEMENT").mean() * 100
            st.metric("✅ Success Rate", f"{rate:.1f}%")
        else:
            st.metric("✅ Success Rate", "N/A")

    with col3:
        if not df.empty:
            st.metric("🔄 Avg Turns", f"{df['num_turns'].mean():.1f}")
        else:
            st.metric("🔄 Avg Turns", "N/A")

    with col4:
        if not df.empty and "final_price" in df.columns:
            successful = df[df["outcome"].str.upper() == "AGREEMENT"]
            if not successful.empty:
                st.metric("💰 Avg Deal Price", f"${successful['final_price'].mean():.2f}")
            else:
                st.metric("💰 Avg Deal Price", "N/A")
        else:
            st.metric("💰 Avg Deal Price", "N/A")


def page_run_negotiation() -> None:
    """Configuration form and real-time negotiation execution."""
    st.title("🎮 Run Negotiation")
    st.markdown("Configure and run a single negotiation between two LLM agents.")

    with st.form("negotiation_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📦 Item")
            item_name = st.text_input("Item Name", value="Vintage Mechanical Keyboard")
            buyer_max = st.number_input(
                "Buyer Reservation Price (max willing to pay)",
                min_value=1.0, value=100.0, step=5.0,
            )
            seller_min = st.number_input(
                "Seller Reservation Price (min willing to accept)",
                min_value=1.0, value=60.0, step=5.0,
            )

        with col2:
            st.subheader("🧠 Agent Configuration")
            buyer_persona = st.selectbox("Buyer Persona", _persona_options(), index=1)
            seller_persona = st.selectbox("Seller Persona", _persona_options(), index=1)
            info_mode = st.selectbox("Information Mode", _info_mode_options(), index=0)

        st.subheader("⚙️ Parameters")
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            max_turns = st.slider("Max Turns", min_value=5, max_value=50, value=20)
        with pcol2:
            temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.7, step=0.05)

        submitted = st.form_submit_button("🚀 Run Negotiation", use_container_width=True)

    if submitted:
        if buyer_max <= seller_min:
            st.warning("⚠️ Buyer reservation price should be higher than seller reservation price for a valid ZOPA.")

        try:
            config = NegotiationConfig.load_from_env()
        except Exception:
            config = NegotiationConfig(
                model_name=os.getenv("MODEL_NAME", "gemma-4-27b-it"),
                api_key=os.getenv("GOOGLE_API_KEY", ""),
            )

        # Override with form values
        from dataclasses import replace as dc_replace
        config = dc_replace(
            config,
            item_name=item_name,
            buyer_reservation_price=buyer_max,
            seller_reservation_price=seller_min,
            buyer_persona=buyer_persona,
            seller_persona=seller_persona,
            information_mode=info_mode,
            max_turns=max_turns,
            temperature=temperature,
        )

        st.divider()
        st.subheader("📜 Negotiation Progress")

        status_placeholder = st.empty()
        turns_container = st.container()

        status_placeholder.info("⏳ Running negotiation...")

        try:
            engine = NegotiationEngine(config)
            result = engine.run()

            status_placeholder.success("✅ Negotiation complete!")

            # Display turns
            with turns_container:
                for turn in result.turns:
                    role = turn.agent_role.upper()
                    if "BUYER" in role:
                        icon = "🔵"
                        color = "blue"
                    else:
                        icon = "🔴"
                        color = "red"

                    with st.chat_message(name=role.lower(), avatar=icon):
                        st.markdown(f"**Turn {turn.turn_number} — {role}** "
                                    f"({turn.agent_persona})")
                        st.write(turn.message)
                        if turn.offer_amount is not None:
                            st.caption(f"💰 Offer: ${turn.offer_amount:.2f} | "
                                       f"Action: {turn.action}")

            # Result summary
            st.divider()
            st.subheader("📊 Result Summary")

            rcol1, rcol2, rcol3, rcol4 = st.columns(4)
            with rcol1:
                st.metric("Outcome", str(result.outcome))
            with rcol2:
                price_display = f"${result.final_price:.2f}" if result.final_price else "N/A"
                st.metric("Final Price", price_display)
            with rcol3:
                st.metric("Turns", result.num_turns)
            with rcol4:
                st.metric("Duration", f"{result.duration_seconds:.1f}s")

            if result.final_price is not None:
                # Surplus visualization
                surplus_data = pd.DataFrame({
                    "Party": ["Buyer", "Seller"],
                    "Surplus": [result.buyer_surplus or 0, result.seller_surplus or 0],
                })
                fig = px.bar(
                    surplus_data, x="Party", y="Surplus",
                    color="Party",
                    color_discrete_map={"Buyer": "#4C72B0", "Seller": "#DD8452"},
                    title="Surplus Distribution",
                )
                st.plotly_chart(fig, use_container_width=True)

        except Exception as exc:
            status_placeholder.error(f"❌ Error: {exc}")


def page_analysis_dashboard() -> None:
    """Analysis dashboard with charts and statistics."""
    st.title("📊 Analysis Dashboard")

    analyzer = _load_analyzer()
    df = analyzer.to_dataframe()

    if df.empty:
        st.warning("No transcripts found. Run some negotiations first!")
        return

    # Filters
    with st.expander("🔍 Filters", expanded=False):
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            filter_buyer = st.multiselect("Buyer Persona", df["buyer_persona"].unique().tolist())
        with fcol2:
            filter_seller = st.multiselect("Seller Persona", df["seller_persona"].unique().tolist())
        with fcol3:
            filter_info = st.multiselect("Information Mode", df["information_mode"].unique().tolist())

    # Apply filters
    filtered = df.copy()
    if filter_buyer:
        filtered = filtered[filtered["buyer_persona"].isin(filter_buyer)]
    if filter_seller:
        filtered = filtered[filtered["seller_persona"].isin(filter_seller)]
    if filter_info:
        filtered = filtered[filtered["information_mode"].isin(filter_info)]

    st.caption(f"Showing {len(filtered)} of {len(df)} transcripts")

    # Summary statistics
    st.subheader("📋 Summary Statistics")
    scol1, scol2, scol3, scol4 = st.columns(4)
    success = filtered[filtered["outcome"].str.upper() == "AGREEMENT"]

    with scol1:
        rate = len(success) / len(filtered) * 100 if len(filtered) > 0 else 0
        st.metric("Success Rate", f"{rate:.1f}%")
    with scol2:
        st.metric("Avg Turns", f"{filtered['num_turns'].mean():.1f}" if not filtered.empty else "N/A")
    with scol3:
        st.metric("Avg Duration", f"{filtered['duration_seconds'].mean():.1f}s" if not filtered.empty else "N/A")
    with scol4:
        if not success.empty and success["total_surplus"].notna().any():
            st.metric("Avg Total Surplus", f"${success['total_surplus'].mean():.2f}")
        else:
            st.metric("Avg Total Surplus", "N/A")

    st.divider()

    # Charts
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Deal Success Rate")
        if not filtered.empty:
            filtered_copy = filtered.copy()
            filtered_copy["is_success"] = (filtered_copy["outcome"].str.upper() == "AGREEMENT").astype(int)
            pair_rate = (
                filtered_copy
                .groupby(["buyer_persona", "seller_persona"])["is_success"]
                .mean()
                .reset_index()
            )
            pair_rate["success_rate"] = pair_rate["is_success"] * 100
            pair_rate["label"] = pair_rate["buyer_persona"] + " vs " + pair_rate["seller_persona"]

            fig = px.bar(
                pair_rate, x="label", y="success_rate",
                color="success_rate",
                color_continuous_scale="Viridis",
                labels={"label": "Persona Pair", "success_rate": "Success Rate (%)"},
                title="Deal Success Rate by Persona Pair",
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader("Rounds Distribution")
        if not success.empty:
            fig = px.box(
                success,
                x="buyer_persona",
                y="num_turns",
                color="seller_persona",
                title="Rounds to Convergence",
                labels={"num_turns": "Number of Turns", "buyer_persona": "Buyer Persona"},
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No successful deals to display.")

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.subheader("Surplus Distribution")
        if not success.empty and success["buyer_surplus"].notna().any():
            surplus_melted = success.melt(
                id_vars=["negotiation_id", "buyer_persona", "seller_persona"],
                value_vars=["buyer_surplus", "seller_surplus"],
                var_name="Party",
                value_name="Surplus",
            )
            surplus_melted["Party"] = surplus_melted["Party"].map({
                "buyer_surplus": "Buyer",
                "seller_surplus": "Seller",
            })
            fig = px.bar(
                surplus_melted.groupby("Party")["Surplus"].mean().reset_index(),
                x="Party", y="Surplus",
                color="Party",
                color_discrete_map={"Buyer": "#4C72B0", "Seller": "#DD8452"},
                title="Average Surplus by Party",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No surplus data available.")

    with chart_col4:
        st.subheader("Persona Heatmap")
        if not filtered.empty:
            filtered_copy = filtered.copy()
            filtered_copy["is_success"] = (filtered_copy["outcome"].str.upper() == "AGREEMENT").astype(int)
            pivot = (
                filtered_copy
                .groupby(["buyer_persona", "seller_persona"])["is_success"]
                .mean()
                .reset_index()
                .pivot(index="buyer_persona", columns="seller_persona", values="is_success")
            ) * 100

            fig = px.imshow(
                pivot,
                text_auto=".0f",
                color_continuous_scale="YlGnBu",
                labels={"x": "Seller Persona", "y": "Buyer Persona", "color": "Success Rate (%)"},
                title="Deal Success Heatmap",
                zmin=0, zmax=100,
            )
            st.plotly_chart(fig, use_container_width=True)

    # Data table
    st.divider()
    st.subheader("📋 Raw Data")
    st.dataframe(filtered, use_container_width=True)


def page_transcript_browser() -> None:
    """Browse and inspect individual negotiation transcripts."""
    st.title("📁 Transcript Browser")

    transcripts_path = Path(_transcripts_dir())

    if not transcripts_path.exists() or not list(transcripts_path.glob("*.json")):
        st.warning("No transcripts found. Run some negotiations first!")
        return

    # List transcripts
    transcript_files = sorted(transcripts_path.glob("*.json"), reverse=True)

    # Metadata table
    metadata_rows: list[dict] = []
    transcripts_data: dict[str, dict] = {}

    for fp in transcript_files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                config = data.get("config", {})
                metadata_rows.append({
                    "file": fp.name,
                    "negotiation_id": data.get("negotiation_id", ""),
                    "outcome": data.get("outcome", "unknown"),
                    "buyer_persona": config.get("buyer_persona", ""),
                    "seller_persona": config.get("seller_persona", ""),
                    "final_price": data.get("final_price"),
                    "num_turns": data.get("num_turns", 0),
                    "timestamp": data.get("timestamp", ""),
                })
                transcripts_data[fp.name] = data
        except (json.JSONDecodeError, OSError):
            continue

    if not metadata_rows:
        st.warning("Could not parse any transcript files.")
        return

    meta_df = pd.DataFrame(metadata_rows)
    st.dataframe(meta_df, use_container_width=True)

    # Transcript selector
    st.divider()
    selected_file = st.selectbox(
        "Select a transcript to view",
        [row["file"] for row in metadata_rows],
    )

    if selected_file and selected_file in transcripts_data:
        data = transcripts_data[selected_file]
        config = data.get("config", {})

        # Header info
        hcol1, hcol2, hcol3, hcol4 = st.columns(4)
        with hcol1:
            st.metric("Outcome", data.get("outcome", "N/A"))
        with hcol2:
            fp = data.get("final_price")
            st.metric("Final Price", f"${fp:.2f}" if fp is not None else "N/A")
        with hcol3:
            st.metric("Turns", data.get("num_turns", "N/A"))
        with hcol4:
            st.metric("Duration", f"{data.get('duration_seconds', 0):.1f}s")

        st.divider()
        st.subheader("💬 Negotiation Transcript")

        turns = data.get("turns", [])
        for turn in turns:
            role = turn.get("agent_role", "unknown").upper()
            is_buyer = "BUYER" in role

            icon = "🔵" if is_buyer else "🔴"
            bg_color = "#e3f2fd" if is_buyer else "#ffebee"

            with st.chat_message(name=role.lower(), avatar=icon):
                st.markdown(
                    f"**Turn {turn.get('turn_number', '?')} — {role}** "
                    f"({turn.get('agent_persona', 'unknown')})"
                )
                st.write(turn.get("message", ""))
                offer = turn.get("offer_amount")
                if offer is not None:
                    st.caption(f"💰 Offer: ${offer:.2f} | Action: {turn.get('action', '')}")
                reasoning = turn.get("reasoning")
                if reasoning:
                    with st.expander("🧠 Reasoning"):
                        st.write(reasoning)

        # Export options
        st.divider()
        st.subheader("📥 Export")

        ecol1, ecol2 = st.columns(2)
        with ecol1:
            st.download_button(
                "Download JSON",
                data=json.dumps(data, indent=2, default=str),
                file_name=selected_file,
                mime="application/json",
            )
        with ecol2:
            # Build a plain-text transcript
            lines = [f"Negotiation: {data.get('negotiation_id', '')}",
                     f"Outcome: {data.get('outcome', '')}",
                     f"Final Price: {data.get('final_price', 'N/A')}",
                     ""]
            for turn in turns:
                lines.append(f"[Turn {turn.get('turn_number', '?')}] "
                             f"{turn.get('agent_role', '').upper()}: "
                             f"{turn.get('message', '')}")
                lines.append("")

            st.download_button(
                "Download as Text",
                data="\n".join(lines),
                file_name=selected_file.replace(".json", ".txt"),
                mime="text/plain",
            )


# ── Page router ─────────────────────────────────────────────────────

_ROUTER = {
    "home": page_home,
    "run": page_run_negotiation,
    "analysis": page_analysis_dashboard,
    "browser": page_transcript_browser,
}

_ROUTER[page_key]()
