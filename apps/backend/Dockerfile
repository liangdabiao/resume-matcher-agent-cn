FROM python:3.12-slim

WORKDIR /app

# 系统依赖（pdfminer/lxml 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用层缓存）
COPY apps/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码（Flask 极简版，7 个文件）
COPY apps/backend/app.py apps/backend/config.py apps/backend/llm.py \
     apps/backend/parser.py apps/backend/prompts.py apps/backend/run.py \
     apps/backend/store.py ./

# 数据与日志目录（卷管理交给 docker-compose）
RUN mkdir -p /app/data /app/logs

EXPOSE 8000

# Flask + gunicorn，宝塔/Docker 通用，无 ASGI/WSGI 坑
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "--timeout", "300", "app:app"]
