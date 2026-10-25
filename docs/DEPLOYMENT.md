# 🚢 Project Concord — Deployment Guide

This guide details how to deploy **Project Concord** across different environments, from local Docker containers to free cloud hosting platforms.

---

## 1. Option 1: Streamlit Community Cloud (Recommended & Easiest)

Streamlit Community Cloud offers free hosting for public GitHub repositories with zero configuration.

### Steps:
1. Push your repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Concord"
   git remote add origin https://github.com/<your-username>/concord.git
   git push -u origin main
   ```
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **"New app"**:
   - **Repository:** `<your-username>/concord`
   - **Branch:** `main`
   - **Main file path:** `ui/app.py`
4. Expand **"Advanced settings..."**:
   - In **Secrets**, paste your Google API key:
     ```toml
     GOOGLE_API_KEY = "AIzaSy..."
     MODEL_NAME = "gemma-4-27b-it"
     ```
5. Click **"Deploy!"**. Your application will be live at `https://<your-app>.streamlit.app`.

---

## 2. Option 2: Docker / Docker Compose (Local or Cloud VPS)

Run Concord in an isolated container on any Linux/macOS/Windows server.

### Local Docker Build:
```bash
# Build the Docker image
docker build -t concord-app .

# Run container mapping port 8501
docker run -d -p 8501:8501 \
  -e GOOGLE_API_KEY="your_api_key_here" \
  -v $(pwd)/transcripts:/app/transcripts \
  --name concord \
  concord-app
```

### Docker Compose (One-Command):
```bash
# 1. Edit .env with your GOOGLE_API_KEY
# 2. Launch
docker-compose up -d --build
```
Navigate to `http://localhost:8501`. Transcripts are persisted in the `./transcripts` directory on the host.

---

## 3. Option 3: Hugging Face Spaces

1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces).
2. Select **Streamlit** as the Space SDK.
3. Upload the project files or push via Git.
4. Under **Settings → Variables and Secrets**, add:
   - Secret Name: `GOOGLE_API_KEY`
   - Secret Value: Your Google AI Studio API key.
5. Space automatically builds and launches.

---

## 4. Option 4: Render / Railway

1. Connect your GitHub repository to [Render.com](https://render.com) or [Railway.app](https://railway.app).
2. Create a new **Web Service**.
3. Build command:
   ```bash
   pip install -r requirements.txt
   ```
4. Start command:
   ```bash
   streamlit run ui/app.py --server.port=$PORT --server.address=0.0.0.0
   ```
5. Under Environment Variables, add `GOOGLE_API_KEY`.

---

## 5. Security & Production Checklist

- [x] `.env` is listed in `.gitignore` so secrets are never pushed to version control.
- [x] Streamlit CORS and XSRF protections configured in `.streamlit/config.toml`.
- [x] Output paths (`transcripts/`, `results/`) are mounted via volumes in Docker so data persists across restarts.
- [x] Dual-mode fallback ensures the dashboard remains operable even if API limits are reached.
