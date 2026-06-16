# QWEN.md

Project guidance for AI assistants (Qwen / Tongyi) working in this repository.

## Overview

Resume Matcher is a full-stack application that helps users increase interview chances by tailoring resumes to job descriptions. It consists of a **Flask backend** (Python, sync) with a **Next.js/React frontend**, using **JSON file storage** (no database) and an OpenAI-compatible LLM.

## Tech Stack

- **Backend**: Flask 3.0+, Gunicorn (sync WSGI, Baota/production friendly), Python 3.12+
- **Storage**: JSON files (no SQLite / no ORM / no migration)
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS 4
- **AI**: OpenAI-compatible API (default Zhipu glm-5.1) via official `openai` SDK

## Project Structure

```
apps/
├── backend/           # Flask backend (minimal, 7 files)
│   ├── app.py         # Flask app + all routes
│   ├── config.py      # os.getenv + dotenv config
│   ├── llm.py         # OpenAI call + JSON parse fallback
│   ├── parser.py      # PDF/DOCX text extraction
│   ├── prompts.py     # 3 prompt templates
│   ├── store.py       # JSON file storage
│   ├── run.py         # local dev entry (prod: gunicorn app:app)
│   ├── data/          # JSON storage (resumes/, jobs/)
│   ├── requirements.txt
│   └── .env.sample
└── frontend/          # Next.js/React frontend
    ├── app/           # pages and routes
    ├── components/    # React components
    ├── lib/api/       # backend API client
    ├── public/a4cv/   # a4cv visual resume editor
    ├── package.json
    └── .env.sample
```

## Backend Architecture

- All routes in `app.py`, prefixed `/api/v1/`. Health check at `/ping`.
- LLM: single function `llm.call_llm(prompt, expect_json=False)` with `temperature=0, top_p=0.9`
- Storage: `data/resumes/<uuid>.json`, `data/jobs/<uuid>.json` (no database, no migration)
- `analysis_result` is NOT persisted (returned per-request)

## Run

### Backend
```bash
cd apps/backend
pip install -r requirements.txt
python run.py                                  # dev: http://localhost:8000
gunicorn -w 2 -b 127.0.0.1:8000 --timeout 300 app:app   # production
```

### Frontend
```bash
cd apps/frontend
npm install
npm run dev                       # dev: http://localhost:3000
npm run build && npm run start    # production
```

## API Endpoints

- `POST /api/v1/resumes/upload` — upload & parse resume (PDF/DOCX)
- `POST /api/v1/resumes/improve` — analyze resume vs JD (`?stream=true` for SSE)
- `GET  /api/v1/resumes?resume_id=` — get resume data
- `POST /api/v1/resumes/improved-markdown` — extract optimized resume markdown
- `POST /api/v1/jobs/upload` — upload & parse job description
- `GET  /api/v1/jobs?job_id=` — get job data
- `GET  /ping` — health check

## Config

- Backend `apps/backend/.env`: set `LLM_API_KEY` (required). `ENV=production` validates key/secret.
- Frontend `apps/frontend/.env`: `NEXT_PUBLIC_API_URL=""` for same-origin deploy.
- Full reference: `docs/CONFIGURING.md`

## Test

```bash
cd apps/backend
python test_e2e.py --base-url http://127.0.0.1:8000            # full (calls LLM)
python test_e2e.py --base-url http://127.0.0.1:8000 --skip-llm # fast, no LLM
```

## Deploy

Baota / nginx same-origin reverse proxy is the recommended deploy model.
See `docs/BAOTA_DEPLOY.md` for the step-by-step guide (Gunicorn-native, no ASGI/WSGI pitfalls).

## Key Features

- Resume to job description matching using AI (HRBP-perspective audit)
- HR-style deep audit report with actionable suggestions
- Optimized resume exported to a4cv visual editor
- No database to install/migrate (JSON file storage, zero ops)
- TypeScript type safety on frontend
