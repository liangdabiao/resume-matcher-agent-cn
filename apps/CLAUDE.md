# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resume Matcher is an AI-powered platform that helps users optimize their resumes to match job descriptions. The application consists of:
- Backend: FastAPI (Python) with SQLite database
- Frontend: Next.js (React/TypeScript) with Tailwind CSS
- AI: Zhipu OpenAI-compatible API for LLM and embedding calls

## Common Development Commands

### Installation
```bash
# Install all dependencies
npm run install

# Or install frontend and backend separately
npm run install:frontend
npm run install:backend
```

### Development
```bash
# Run both frontend and backend in development mode
npm run dev

# Run only backend
npm run dev:backend

# Run only frontend
npm run dev:frontend
```

### Building
```bash
# Build the entire project
npm run build

# Build frontend only
npm run build:frontend

# Build backend only
npm run build:backend
```

### Linting
```bash
# Run linting
npm run lint
```

### Production
```bash
# Start production servers
npm run start

# Start production backend only
npm run start:backend

# Start production frontend only
npm run start:frontend
```

## Code Architecture

### Backend (FastAPI)
- Entry point: `apps/backend/app/main.py`
- Configuration: `apps/backend/app/core/config.py`
- API routes: `apps/backend/app/api/router/v1/`
- Services: `apps/backend/app/services/`
- Database models: `apps/backend/app/models/`
- Schemas: `apps/backend/app/schemas/`

Key services:
- `resume_service.py`: Handles resume parsing and storage
- `job_service.py`: Handles job description processing
- `score_improvement_service.py`: Core logic for matching resumes with job descriptions

### Frontend (Next.js)
- Entry point: `apps/frontend/`
- API proxy configuration: `apps/frontend/next.config.ts` (proxies `/api_be/` to backend)
- Components: `apps/frontend/components/`
- Pages: `apps/frontend/app/`

## Database
- SQLite is used for local development
- Database file: `apps/backend/app.db`
- Async SQLAlchemy is used for database operations

## Environment Configuration
- Root `.env` file (copied from `.env.example`)
- Backend `.env` file (copied from `apps/backend/.env.sample`)

## AI Integration
- Zhipu is used through the OpenAI-compatible API.
- Default models:
  - LLM: glm-5.1
  - Embedding: embedding-3
- Configure `LLM_API_KEY` in `apps/backend/.env` before running LLM-backed flows.