# Project Concord — Setup Guide

> **Multi-Agent LLM Negotiation Simulation Framework**

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11 or higher | [Download from python.org](https://www.python.org/downloads/) |
| pip | Latest | Bundled with Python. Upgrade: `python -m pip install --upgrade pip` |
| Git | Any recent version | [Download from git-scm.com](https://git-scm.com/downloads) |

---

## 1. Clone the Repository

```bash
git clone <repository-url> concord
cd concord
```

Or if you already have the project folder:

```bash
cd "E:\Gautam Minor\Concord"
```

---

## 2. Create a Virtual Environment

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

> [!TIP]
> You should see `(venv)` prefixed to your terminal prompt when the environment is active.

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages:

| Package | Purpose |
|---|---|
| `google-genai` | Google Gemma 4 / Gemini LLM SDK |
| `pandas` | Data analysis and metrics computation |
| `matplotlib` | Static chart generation |
| `plotly` | Interactive chart generation |
| `streamlit` | Web dashboard UI |
| `python-dotenv` | Environment variable management |

---

## 4. Configure Environment Variables

### Step 1: Copy the example file

```bash
cp .env.example .env
```

On Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

### Step 2: Edit `.env` and add your API key

Open `.env` in any text editor and set your Google API key:

```env
# Google AI API Key (required)
GOOGLE_API_KEY=your-api-key-here

# Optional: Model name override
# MODEL_NAME=gemma-4

# Optional: Logging level
# LOG_LEVEL=INFO
```

> [!IMPORTANT]
> **Never commit your `.env` file to version control.** The `.gitignore` file is already configured to exclude it.

### How to obtain a Google API key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Navigate to **API Keys** in the left sidebar
4. Click **Create API Key**
5. Copy the key and paste it into your `.env` file

---

## 5. Verify Installation

Run a quick check to ensure everything is set up correctly:

```bash
python -c "from concord.config import NegotiationConfig; print('✓ Configuration module OK')"
python -c "import pandas; import matplotlib; import streamlit; print('✓ All dependencies OK')"
```

---

## 6. Running the Application

Project Concord provides a unified CLI entry point via `main.py` with four modes:

### 6.1 Single Negotiation

Run one negotiation session with default or custom parameters:

```bash
python main.py single
```

**Optional flags:**

```bash
python main.py single --buyer-persona cooperative --seller-persona aggressive --info-mode symmetric_hidden
python main.py single --buyer-max 100 --seller-min 60 --max-turns 20
python main.py single --item "Vintage Mechanical Keyboard"
```

### 6.2 Experiment Mode

Run the full experimental matrix (18 conditions × N trials):

```bash
python main.py experiment
```

**Optional flags:**

```bash
python main.py experiment --trials 25 --concurrency 5
python main.py experiment --conditions cooperative,aggressive --info-mode symmetric_hidden
```

> [!NOTE]
> Full experiment runs (360–540 negotiations) can take significant time depending on API rate limits. Progress is displayed in the terminal with an ETA.

### 6.3 Analyze Mode

Generate analysis reports and charts from saved transcripts:

```bash
python main.py analyze
```

**Optional flags:**

```bash
python main.py analyze --input data/transcripts/ --output data/analysis/
python main.py analyze --metrics success_rate,surplus_split,convergence
```

Output is saved to `data/analysis/` including:
- Summary statistics (CSV)
- Comparison charts (PNG / HTML)
- Full analysis report (Markdown)

### 6.4 Dashboard UI

Launch the Streamlit web dashboard:

```bash
python main.py ui
```

This starts a local web server. Open the URL displayed in the terminal (typically `http://localhost:8501`) in your browser.

**Dashboard pages:**
- **Live Viewer** — Run and watch a negotiation in real time
- **Transcript Browser** — Search and replay past sessions
- **Analysis Charts** — Interactive experiment result visualizations
- **Experiment Launcher** — Configure and run experiments from the UI

---

## 7. Project Structure

```
Concord/
├── main.py                     # Unified CLI entry point
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .env                        # Your API keys (git-ignored)
├── concord/
│   ├── __init__.py
│   ├── config.py               # NegotiationConfig, personas, info modes
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # NegotiationAgent base class
│   │   ├── buyer.py            # BuyerAgent implementation
│   │   └── seller.py           # SellerAgent implementation
│   ├── orchestrator.py         # NegotiationOrchestrator
│   ├── transcript_logger.py    # Structured JSON logging
│   ├── analysis.py             # Quantitative analysis engine
│   ├── experiments.py          # Experiment matrix runner
│   └── ui/
│       ├── app.py              # Streamlit dashboard
│       └── components/         # Reusable UI components
├── data/
│   ├── transcripts/            # Saved negotiation logs
│   └── analysis/               # Generated reports & charts
└── docs/
    ├── TASK_LIST.md
    ├── ARCHITECTURE.md
    ├── SETUP_GUIDE.md
    └── EXPERIMENT_DESIGN.md
```

---

## 8. Troubleshooting

### `ModuleNotFoundError: No module named 'concord'`

**Cause:** The virtual environment is not activated, or the project root is not in the Python path.

**Fix:**
```bash
# Activate the virtual environment
.\venv\Scripts\Activate.ps1    # Windows PowerShell
source venv/bin/activate        # macOS/Linux

# Or install the project in editable mode
pip install -e .
```

### `google.genai.errors.AuthenticationError`

**Cause:** Missing or invalid API key.

**Fix:**
1. Verify `.env` file exists and contains a valid `GOOGLE_API_KEY`.
2. Ensure the key is active in [Google AI Studio](https://aistudio.google.com/).
3. Check for leading/trailing whitespace in the key value.

### `RateLimitError` or `429 Too Many Requests`

**Cause:** API rate limits exceeded during experiment runs.

**Fix:**
- Reduce concurrency: `python main.py experiment --concurrency 2`
- The experiment runner includes automatic retry with exponential backoff.
- Consider running experiments in smaller batches.

### `StreamlitAPIException` or Dashboard won't load

**Cause:** Port conflict or Streamlit installation issue.

**Fix:**
```bash
# Try a different port
streamlit run concord/ui/app.py --server.port 8502

# Or reinstall Streamlit
pip install --force-reinstall streamlit
```

### `FileNotFoundError: .env`

**Cause:** The `.env` file was not created.

**Fix:**
```bash
cp .env.example .env
# Then edit .env and add your API key
```

### Charts or plots not displaying

**Cause:** Missing visualization dependencies.

**Fix:**
```bash
pip install matplotlib plotly kaleido
```

---

> [!TIP]
> For additional help, check the project documentation in the `docs/` folder or open an issue in the repository.
