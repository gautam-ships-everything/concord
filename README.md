# 🤝 Project Concord

**An Experimental Study of Autonomous Negotiation Strategies Between Large Language Model Agents**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Model: Gemma 4](https://img.shields.io/badge/Model-Gemma%204-purple.svg)](https://deepmind.google/technologies/gemma/)

Concord is a research-grade multi-agent negotiation simulation framework. It places two independently prompted instances of Google's **Gemma 4** model on opposite sides of a commercial bargaining scenario — a **Buyer** (with a private maximum willingness to pay) and a **Seller** (with a private minimum reservation cost) — and allows them to negotiate autonomously over several conversational turns in natural language.

---

## 🌟 Key Capabilities

- 🤖 **Autonomous Multi-Turn Dialogue:** Agents make offers, counter-offers, concessions, and walk-away decisions using structured JSON formatting.
- 🎭 **Persona Variations:** Test combinations of **Cooperative**, **Neutral**, and **Aggressive** bargaining styles.
- 👁️ **Information Asymmetry:** Study the economic impact of hidden vs. revealed reservation prices (`symmetric_hidden`, `asymmetric_buyer_knows`, `asymmetric_seller_knows`).
- 📝 **Structured JSON Transcripts:** Every round, reasoning trace, offer amount, and message is preserved as machine-readable data.
- 📊 **Quantitative Economic Metrics:** Computes deal success rates, rounds to convergence, surplus splits, and Pareto efficiency using `pandas` and `matplotlib`.
- 🎮 **Streamlit Demonstration UI:** Interactive turn-by-turn simulation viewer, transcript browser, and comparative analytics dashboard.
- ⚡ **Dual Engine (Simulated + Live Gemma 4):** Runs out of the box in simulation mode; automatically switches to live Gemma 4 calls when `GOOGLE_API_KEY` is provided.

---

## 🚀 Quick Start (One Command)

### Option 1: Run the Master Launcher
```bash
python run.py
```
This automatically verifies dependencies, runs a sample negotiation, computes metrics, and gives you an interactive menu to launch the UI or run experiments.

### Option 2: CLI Subcommands (`main.py`)

```bash
# 1. Run a single negotiation between two neutral agents
python main.py single

# 2. Run an aggressive seller against a cooperative buyer
python main.py single --buyer-persona cooperative --seller-persona aggressive

# 3. Test asymmetric information (buyer knows seller's bottom line)
python main.py single --info-mode asymmetric_buyer_knows

# 4. Run an experimental matrix batch (e.g. 5 trials per condition)
python main.py experiment --trials 5

# 5. Analyze existing transcripts and generate a summary report
python main.py analyze --report

# 6. Launch the interactive Streamlit dashboard
python main.py ui
```

---

## 📁 Repository Structure

```
E:\Gautam Minor\
├── docs/                                # Full project documentation
│   ├── ARCHITECTURE.md                  # System design & data flow
│   ├── EXPERIMENT_DESIGN.md             # 18-condition matrix & hypotheses
│   ├── SETUP_GUIDE.md                   # Installation & troubleshooting
│   ├── TASK_LIST.md                     # Phased task checklist
│   └── DEPLOYMENT.md                    # Cloud & Docker deployment guide
│
└── Concord/
    ├── run.py                           # 🚀 Master single-click runner
    ├── run.bat                          # Windows double-click batch launcher
    ├── main.py                          # CLI entry point (single/experiment/analyze/ui)
    ├── requirements.txt                 # Project dependencies
    ├── .env.example                     # Environment configuration template
    ├── Dockerfile                       # Container definition
    ├── docker-compose.yml               # Docker Compose setup
    │
    ├── config/                          # Central configuration & persona prompts
    │   ├── settings.py                  # NegotiationConfig dataclass
    │   └── personas.py                  # Cooperative / Neutral / Aggressive templates
    │
    ├── agents/                          # LLM agent definitions
    │   ├── base_agent.py                # Abstract base + Gemma 4 client + fallback
    │   ├── buyer_agent.py               # Buyer agent constraints
    │   └── seller_agent.py              # Seller agent constraints
    │
    ├── orchestrator/                    # Turn-taking & termination logic
    │   ├── engine.py                    # NegotiationEngine loop
    │   └── termination.py               # Agreement, walk-away & timeout rules
    │
    ├── transcript_logger/               # Structured JSON logger
    │   └── logger.py                    # File-based transcript storage
    │
    ├── analysis/                        # Quantitative metrics & plots
    │   └── metrics.py                   # NegotiationAnalyzer (success rate, surplus, Pareto)
    │
    ├── experiments/                     # Experimental batch runner
    │   └── runner.py                    # Factorial matrix runner
    │
    ├── ui/                              # Web application
    │   └── app.py                       # Streamlit multi-page dashboard
    │
    ├── transcripts/                     # Stored JSON session transcripts
    └── results/                         # Output plots & summary reports
```

---

## 🔑 Gemma 4 API Configuration

When your Google AI Studio / Gemini API key is ready:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and paste your key:
   ```env
   GOOGLE_API_KEY=AIzaSy...your_actual_api_key_here
   MODEL_NAME=gemma-4-27b-it
   ```
3. Run `python main.py single` — the agents will now query live Gemma 4 instances!

---

## 📊 Economic & Game-Theoretic Metrics

| Metric | Definition | Purpose |
|---|---|---|
| **Deal Success Rate** | $\frac{\text{Agreements}}{\text{Total Runs}} \times 100$ | Measures contract viability across persona pairs |
| **Rounds to Convergence** | $\mu(\text{turns})$ for successful deals | Measures negotiation friction and speed |
| **Surplus Split** | $\frac{P_{\text{deal}} - C_{\text{min}}}{B_{\text{max}} - C_{\text{min}}}$ | Evaluates bargaining power and division of gains |
| **Pareto Efficiency** | $\mathbb{I}(C_{\text{min}} \le P_{\text{deal}} \le B_{\text{max}})$ | Checks if mutually profitable trades are realized |

---

## 🚢 Deployment

The project can be deployed locally or to cloud platforms:
- **Streamlit Community Cloud:** Connect your GitHub repo, set `ui/app.py` as main file, and add `GOOGLE_API_KEY` under Secrets.
- **Docker:**
  ```bash
  docker-compose up --build
  ```
  Access the web interface at `http://localhost:8501`.

---
