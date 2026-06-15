# Configuration

Resume Matcher uses two environment files:

- `apps/backend/.env` for backend, database, and AI settings
- `apps/frontend/.env` for frontend API settings

## Backend

Create `apps/backend/.env` from `apps/backend/.env.sample` and fill in the API key:

```env
SESSION_SECRET_KEY="change-me"
SYNC_DATABASE_URL="sqlite:///./Data/app.db"
ASYNC_DATABASE_URL="sqlite+aiosqlite:///./Data/app.db"
PYTHONDONTWRITEBYTECODE=1
ENV="local"

LLM_API_KEY="your-zhipu-api-key"
LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
LL_MODEL="glm-5.1"

EMBEDDING_API_KEY="your-zhipu-api-key"
EMBEDDING_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
EMBEDDING_MODEL="embedding-3"
```

`EMBEDDING_API_KEY` can use the same value as `LLM_API_KEY`.

## AI provider

The backend calls Zhipu through the OpenAI-compatible API using the official OpenAI Python SDK. The provider layer no longer supports Ollama or LlamaIndex selection.

The default models are:

- LLM: `glm-5.1`
- Embedding: `embedding-3`

You can override the model names in `.env` if your account uses a different available model.

## Frontend

Create `apps/frontend/.env` and set the backend URL:

```env
NEXT_PUBLIC_API_URL="http://localhost:8000"
```

When running behind a reverse proxy, set `NEXT_PUBLIC_API_URL` to the externally reachable backend URL.
