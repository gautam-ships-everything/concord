# Project Concord — Task List

> **Multi-Agent LLM Negotiation Simulation Framework**
> B.Tech CSE Minor Project

---

## Phase 1: Project Setup
- [x] Initialize repository structure with modular package layout
- [x] Create `requirements.txt` with all dependencies
- [x] Create `.env.example` with placeholder API key configuration
- [x] Set up Python virtual environment and verify dependency installation
- [x] Add `.gitignore` for environment files, caches, and data artifacts

## Phase 2: Configuration Layer
- [x] Define `NegotiationConfig` dataclass with all session parameters
- [x] Define persona profiles with system prompts:
  - [x] **Cooperative** — prioritizes mutual gain, willing to concede
  - [x] **Neutral** — balanced strategy, moderate concessions
  - [x] **Aggressive** — maximizes own surplus, minimal concessions
- [x] Implement information symmetry modes:
  - [x] **Symmetric Hidden** — neither agent knows the other's reservation price
  - [x] **Asymmetric Buyer Knows** — buyer knows seller's minimum price
  - [x] **Asymmetric Seller Knows** — seller knows buyer's maximum budget

## Phase 3: Agent Framework
- [x] Implement base `NegotiationAgent` class with:
  - [x] Structured JSON output parsing from LLM responses
  - [x] Conversation history management
  - [x] System prompt construction from persona + role + scenario
- [x] Implement `BuyerAgent`:
  - [x] Has a maximum budget (reservation price)
  - [x] Objective: minimize purchase price
- [x] Implement `SellerAgent`:
  - [x] Has a minimum acceptable cost (reservation price)
  - [x] Objective: maximize sale price

## Phase 4: Orchestrator Engine
- [x] Implement `NegotiationOrchestrator` with turn management
- [x] Maintain shared conversation history visible to both agents
- [x] Implement termination conditions:
  - [x] **Agreement** — both parties accept a price
  - [x] **Walk-Away** — one party exits the negotiation
  - [x] **Max Turns Reached** — configurable turn limit exceeded
- [x] Generate `NegotiationResult` dataclass with outcome, final price, turn count, and metadata

## Phase 5: Transcript Logging
- [x] Implement structured JSON logging for every negotiation turn:
  - [x] Turn number, role, persona, action, offer amount, message text, reasoning, timestamp
- [x] Log session-level metadata (config, outcome, duration)
- [x] Save transcripts to `data/transcripts/` with unique session identifiers
- [x] Support both human-readable and machine-parseable formats

## Phase 6: Quantitative Analysis
- [x] Build pandas-based analysis pipeline computing:
  - [x] **Deal Success Rate** — percentage of negotiations reaching agreement
  - [x] **Rounds to Convergence** — average turns to reach a deal
  - [x] **Surplus Split** — buyer surplus % vs. seller surplus %
  - [x] **Pareto Efficiency** — whether value was left on the table
- [x] Generate comparative charts (matplotlib / plotly):
  - [x] Per-persona bar charts
  - [x] Information mode comparison plots
  - [x] Convergence trend lines

## Phase 7: Experiment Runner
- [x] Build full experimental matrix:
  - [x] 3 buyer personas × 3 seller personas × 2 information modes = **18 conditions**
  - [x] 20–30 trials per condition = **360–540 total negotiation runs**
- [x] Implement batch execution with progress tracking
- [x] Handle failures gracefully (retry logic, partial result saving)
- [x] Aggregate results into summary DataFrames

## Phase 8: Streamlit Dashboard
- [x] **Live Negotiation Viewer** — watch a negotiation unfold in real time
- [x] **Transcript Browser** — search, filter, and replay past sessions
- [x] **Comparative Analysis Charts** — interactive plots of experiment results
- [x] **Experiment Configuration UI** — configure and launch experiments from the browser

## Phase 9: Integration & Entry Point
- [x] Create unified `main.py` CLI entry point with modes:
  - [x] `python main.py single` — run a single negotiation
  - [x] `python main.py experiment` — run the full experimental matrix
  - [x] `python main.py analyze` — generate analysis reports from saved transcripts
  - [x] `python main.py ui` — launch the Streamlit dashboard

## Phase 10: API Integration
- [ ] Obtain Google Gemma 4 API key from user
- [ ] Configure `google-genai` SDK with production credentials
- [ ] Validate API connectivity and rate-limit handling
- [ ] Run smoke tests with live model responses

## Phase 11: Deployment
- [x] Create `Dockerfile` for containerized execution
- [x] Write `docker-compose.yml` for reproducible local or cloud VM deployment
- [x] Create `Procfile` and Streamlit theme configurations (`.streamlit/config.toml`)
- [x] Document cloud deployment options (Streamlit Community Cloud, Hugging Face Spaces, Render, Docker) in `docs/DEPLOYMENT.md`
- [x] Provide single-click launchers: `run.py` and `run.bat`

---

> **Status:** Phases 1–9 and Phase 11 complete. Ready to run immediately out-of-the-box (in simulation mode). Once the Google Gemma 4 API key is provided, Phase 10 seamlessly activates live LLM calls!
