FROM python:3.12-slim

WORKDIR /app

# System deps for python-docx (resume parsing) and lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (used by the project)
RUN pip install --no-cache-dir uv

# Install Python deps first (better layer caching).
# 以 pyproject.toml + uv.lock 为唯一权威依赖来源，用 uv pip sync 精确复现锁定版本，
# 避免 requirements.txt 与 pyproject.toml 双入口漂移。
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN uv pip sync --system uv.lock

# Copy backend source
COPY apps/backend/app ./app

# Persist SQLite + logs.
# 卷管理统一交给 docker-compose.yml 的 named volumes，这里只确保目录存在，
# 不再声明 VOLUME（否则 Docker 会额外创建匿名卷，与 compose 的命名卷冲突）。
RUN mkdir -p /app/data /app/logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
