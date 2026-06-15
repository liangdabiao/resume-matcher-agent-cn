# Resume Matcher Project Overview

## Project Description
Resume Matcher is a full-stack application that helps users increase their interview chances by tailoring their resumes to specific job descriptions. The application consists of a FastAPI backend with a Next.js/React frontend.

## Project Structure
```
apps/
├── backend/           # Python FastAPI backend
│   ├── app/           # Main application code
│   │   ├── api/       # API routes and middleware
│   │   ├── core/      # Configuration and core functionality
│   │   ├── models/    # Database models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   ├── main.py    # Application entry point
│   │   └── base.py    # App configuration
│   ├── requirements.txt  # Python dependencies
│   ├── pyproject.toml    # Project metadata and dependencies
│   └── .env.sample       # Sample environment variables
└── frontend/          # Next.js/React frontend
    ├── app/           # Application routes and pages
    ├── components/    # React components
    ├── public/        # Static assets
    ├── package.json   # Node.js dependencies and scripts
    └── .env.sample    # Sample environment variables
```

## Technologies Used

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy (async using aiosqlite)
- **LLM Integration**: Ollama with support for other providers
- **Embeddings**: Qwen3-Embedding model via Ollama
- **Key Dependencies**:
  - FastAPI for API development
  - SQLAlchemy for database ORM
  - Pydantic for data validation
  - OpenAI/Ollama for LLM integration
  - Uvicorn for ASGI server

### Frontend
- **Framework**: Next.js 15 (React 19)
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI, Lucide React icons
- **Key Dependencies**:
  - Next.js for React framework
  - React 19 for UI library
  - Tailwind CSS for styling
  - TypeScript for type safety

## Development Setup

### Backend Setup
1. Navigate to the backend directory: `cd backend`
2. Install Python dependencies: `pip install -r requirements.txt`
3. Copy `.env.sample` to `.env` and configure values
4. Run the development server: `python -m app.main`

### Frontend Setup
1. Navigate to the frontend directory: `cd frontend`
2. Install Node.js dependencies: `npm install`
3. Copy `.env.sample` to `.env` and configure values
4. Run the development server: `npm run dev`

## Key Commands

### Backend
- Development server: `python -m app.main`
- The server will run on `http://localhost:8000`
- API documentation available at `http://localhost:8000/api/docs`

### Frontend
- Development server: `npm run dev`
- Build for production: `npm run build`
- Start production server: `npm run start`
- Lint code: `npm run lint`
- Format code: `npm run format`
- The server will run on `http://localhost:3000`

## API Endpoints
The backend provides RESTful APIs for:
- Job description upload and processing
- Resume upload and processing
- Matching resumes with job descriptions

Key endpoints:
- `POST /api/v1/job/upload` - Upload job description
- `GET /api/v1/job` - Get job data
- `POST /api/v1/resume/upload` - Upload resume
- `GET /api/v1/resume` - Get resume data

## Environment Variables

### Backend (.env)
- `SESSION_SECRET_KEY` - Secret key for session management
- `SYNC_DATABASE_URL` - SQLite database URL for synchronous operations
- `ASYNC_DATABASE_URL` - SQLite database URL for asynchronous operations
- `LLM_API_KEY` - Zhipu API key for OpenAI-compatible LLM calls
- `LLM_BASE_URL` - OpenAI-compatible API base URL (default: https://open.bigmodel.cn/api/paas/v4/)
- `LL_MODEL` - Language model to use (default: glm-5.1)
- `EMBEDDING_API_KEY` - Zhipu API key for embeddings, usually same as `LLM_API_KEY`
- `EMBEDDING_BASE_URL` - OpenAI-compatible embedding API base URL
- `EMBEDDING_MODEL` - Embedding model to use (default: embedding-3)

### Frontend (.env)
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

## Development Workflow
1. Start the backend server: `cd backend && python -m app.main`
2. In another terminal, start the frontend development server: `cd frontend && npm run dev`
3. Access the application at `http://localhost:3000`
4. API documentation is available at `http://localhost:8000/api/docs`

## Key Features
- Resume to job description matching using AI
- Tailwind CSS styling with modern UI components
- Responsive design for all device sizes
- SQLite database for local storage
- RESTful API with comprehensive documentation
- TypeScript type safety on frontend
- FastAPI automatic OpenAPI documentation generation