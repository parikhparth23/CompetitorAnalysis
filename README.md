# Competitor Analysis Pro

Beginner-friendly guide for setting up, running, and understanding this project.

This repository contains a full-stack app:
- Frontend: React + TypeScript + Vite
- Backend: FastAPI (Python)
- Database: Supabase (Postgres)
- Scraper: Firecrawl wrapper (used by backend scraper)
- AI: Google Generative AI (Gemini family)

If you're new to this project or to web development, this README walks you through everything step-by-step.

---

## Quick Summary (10-minute version)

1. Copy an `.env` file with required secrets into the project root (see **Environment** section).
2. Start the backend:

```bash
cd backend
pip install -r ../requirements.txt   # create venv if you like
uvicorn main:app --reload
```

3. Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

4. Open `http://localhost:5173` (or the Vite URL shown in terminal).

---

## Prerequisites

- Node.js (>=16) and npm
- Python 3.10+ (recommended)
- A Supabase project (optional but used by the app)
- API keys: `GOOGLE_AI_API_KEY`, `FIRECRAWL_API_KEY`, `SUPABASE_*` (see below)

On macOS you can install with Homebrew:

```bash
brew install node python
```

---

## Project Structure (high level)

- `backend/` — FastAPI app, scraping, DB manager.
- `frontend/` — React + TypeScript UI built with Vite.
- `database_schema.sql` — SQL to set up the expected tables in Supabase.
- `.env` — local environment variables (not committed!).

---

## Environment variables (what you must provide)

Create a `.env` file in the project root with the following names (DO NOT commit this file):

- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase service role key (server-only)
- `GOOGLE_AI_API_KEY` — API key for Google Generative AI
- `FIRECRAWL_API_KEY` — Firecrawl scraping key (or scraper provider key)

Example (DO NOT copy real keys into a public repo):

```env
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
GOOGLE_AI_API_KEY=your_google_ai_key_here
FIRECRAWL_API_KEY=your_scraper_key_here
```

Security note: Keep these keys secret. Add `.env` to `.gitignore` (it already is in this repo).

---

## How the Model Selection Works (important)

- The frontend shows a Model dropdown populated from the backend `/models` endpoint.
- When a user starts an analysis, the frontend sends `model` with the `POST /analyze` payload.
- The backend validates the requested `model` against a safe `SUPPORTED_MODELS` whitelist. If the selected id isn't allowed, the backend returns HTTP 400.
- If allowed, the backend tries to instantiate and use the requested model via the Google AI client. If the requested model isn't available (or instantiation fails), the backend falls back to a server default model.

This prevents arbitrary/unsafe model ids from being used while letting the user choose available models.

---

## Running Locally — Backend (detailed)

1. Create and activate a Python virtual environment (recommended):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

2. Ensure `.env` has your keys.

3. Run the server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. Health checks:

- `GET http://localhost:8000/` — simple health endpoint
- `GET http://localhost:8000/models` — returns supported model list
- `GET http://localhost:8000/env-check` — shows which env vars are present (debug only)

If you change backend code, the `--reload` option will auto-reload.

---

## Running Locally — Frontend (detailed)

1. Install Node deps and run dev server:

```bash
cd frontend
npm install
npm run dev
```

2. Open the Vite URL shown in the terminal (usually `http://localhost:5173`).

3. The frontend will attempt to fetch `http://localhost:8000/models` on load. If the backend is unavailable it falls back to a built-in list.

Notes:
- If you added the `jspdf` PDF export dependency, run `npm install jspdf` inside `frontend/` and restart dev server.

---

## Exporting Reports

- CSV: client-side CSV generator; click `Export CSV` on the Results page to download.
- PDF: client-side using `jspdf`. If missing, the app shows an alert instructing you to install `jspdf`.

Commands to add PDF support:

```bash
cd frontend
npm install jspdf
```

---

## Design & Tech Notes (for product and dev teams)

- UI: React + TypeScript, organized in `frontend/src`. Styling is place-based CSS in `App.css` and `index.css` with responsive breakpoints.
- Backend: FastAPI provides endpoints, scraping orchestration, AI prompt handling, and DB persistence.
- Models: Backend holds a server default model; it accepts a `model` in `POST /analyze` which must match the server whitelist. This is safer for production.
- Storage: Supabase is used for storing competitors and insights. `database_schema.sql` contains the schema expected.
- Scraper: `backend/scraper.py` handles fetching content from the provided URL. The project currently expects a Firecrawl API key.

Design decisions:
- Validation and whitelist of model IDs protects against arbitrary model requests.
- Frontend stores user model choice in `localStorage` and rehydrates it when starting a new analysis.

---

## Common Issues & Troubleshooting

- Vite import error for `jspdf`: install it in `frontend/` and restart Vite.
- Backend can't load env vars: ensure `.env` exists in project root and `backend/main.py` is starting from repo root. The backend prints helpful logs when env vars aren't found.
- CORS errors: backend allows `http://localhost:5173` and similar origins — if you serve frontend on a different port add that origin in `main.py` CORS list.
- Model requests failing: check backend logs — it will print whether the requested model was used or why it fell back.

---


---

## Where to change things

- Change supported models list: `backend/main.py` `SUPPORTED_MODELS`
- Change prompt or AI call: `backend/main.py` inside `/analyze` handler
- Change UI text / layout: `frontend/src/App.tsx` and `frontend/src/App.css`

