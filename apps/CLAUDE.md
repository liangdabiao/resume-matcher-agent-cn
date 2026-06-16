# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resume Matcher is an AI-powered platform that helps users optimize their resumes to match job descriptions. The application consists of:
- Backend: **Flask (Python, sync)** with **JSON file storage** (no database)
- Frontend: Next.js (React/TypeScript) with Tailwind CSS
- AI: any OpenAI-compatible API (default Zhipu glm-5.1)

## Common Development Commands

### Installation
```bash
npm run setup          # install root + frontend + backend deps
```

### Development
```bash
npm run dev            # run both frontend and backend
npm run dev:backend    # backend only (python app.py)
npm run dev:frontend   # frontend only (npm run dev)
```

### Building / Linting
```bash
npm run build          # build frontend + compile-check backend
npm run lint           # frontend ESLint
```

### Production
```bash
npm run start          # start both (gunicorn + next start)
```

## Code Architecture

### Backend (Flask) — `apps/backend/`, 7 files
- `app.py` — Flask app + all routes (8 endpoints, incl. SSE streaming)
- `config.py` — config via os.getenv + dotenv
- `llm.py` — OpenAI call + 3-level JSON parsing fallback
- `parser.py` — PDF (pdfminer) / DOCX (stdlib zip+xml) text extraction
- `prompts.py` — 3 prompt templates (structured_resume / structured_job / hr_judge)
- `store.py` — JSON file storage (resumes/<uuid>.json, jobs/<uuid>.json)
- `run.py` — local dev entry (`python run.py`); production uses `gunicorn app:app`

API routes are in `app.py` directly (prefix `/api/v1/`). Health check at `/ping`.
LLM call is a single function `llm.call_llm(prompt, expect_json=False)` — `temperature=0, top_p=0.9`.

### Frontend (Next.js) — `apps/frontend/`
- API client: `apps/frontend/lib/api/`
- API base URL: `apps/frontend/lib/api/config.ts` (reads `NEXT_PUBLIC_API_URL`)
- `next.config.ts` rewrites `/api/*` → backend
- Pages: `apps/frontend/app/`, Components: `apps/frontend/components/`

## Storage
- JSON files under `apps/backend/data/` (`resumes/`, `jobs/`)
- No database to install/migrate; backup = copy the `data/` directory
- `analysis_result` is NOT persisted (returned per-request, same as before refactor)

## Environment Configuration
- Backend: `apps/backend/.env` (from `.env.sample`) — must set `LLM_API_KEY`
- Frontend: `apps/frontend/.env` (from `.env.sample`) — `NEXT_PUBLIC_API_URL=""` for same-origin deploy
- See `docs/CONFIGURING.md` for full details

## AI Integration
- Calls any OpenAI-compatible endpoint via the official `openai` SDK
- Default model: `glm-5.1`, base URL: Zhipu. Override `LLM_MODEL` / `LLM_BASE_URL` in `.env`
- `LLM_API_KEY` required; `ENV=production` refuses to start without it
