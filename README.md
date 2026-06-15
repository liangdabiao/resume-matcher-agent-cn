# HR批评简历

HR批评简历是一个面向中文用户的 AI 简历深度优化工具。上传简历并粘贴目标岗位 JD 后，系统会解析简历与岗位要求，生成岗位匹配分析、HR 视角审计报告和可执行的简历修改建议。

本项目保留 SQLite 作为轻量本地状态存储，用于保存简历、岗位描述、结构化解析结果和流程 ID。SQLite 不需要单独部署数据库服务，适合本地使用、演示和轻量部署。

本项目整合了阿真的开源简历编辑器 a4cv：https://github.com/irenerachel/a4cv

## 核心功能

- 上传 PDF / DOCX 简历并提取文本
- 粘贴岗位 JD 并解析岗位职责、要求和关键词
- 使用 OpenAI 兼容 API 进行结构化抽取与简历审计
- 生成中文 HR 视角的深度简历分析报告
- 根据岗位要求输出简历优化方向和示例改写
- 一键把优化后的简历送入 a4cv 可视化编辑器二次微调
- 前端界面已中文化，适合中文求职场景

## 实际效果

![实际效果](./ScreenShot_2026-06-15_181108_383.png)
![实际效果](./ScreenShot_2026-06-15_144511_171.png)

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Next.js 15、React 19、TypeScript、Tailwind CSS |
| 后端 | FastAPI、Pydantic、SQLAlchemy、aiosqlite |
| 数据库 | SQLite |
| AI 接入 | 任意 OpenAI 兼容 API（智谱、DeepSeek、Tencent TokenHub 等） |
| 默认模型 | `glm-5.1`，可在 `.env` 改 `LL_MODEL` / `LLM_BASE_URL` |
| 文档解析 | `pdfminer.six` 解析 PDF，标准库解析 DOCX |

## 目录结构

```text
.
├── apps/
│   ├── backend/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── agent/        # OpenAI 兼容调用封装
│   │   │   ├── api/          # API 路由
│   │   │   ├── core/         # 配置、数据库、日志
│   │   │   ├── models/       # SQLAlchemy 数据模型
│   │   │   ├── prompt/       # 提示词模板
│   │   │   ├── schemas/      # Pydantic / JSON Schema
│   │   │   ├── services/     # 简历、岗位、分析服务
│   │   │   └── utils/        # 工具函数
│   │   ├── .env.sample       # 后端环境变量示例
│   │   ├── pyproject.toml
│   │   └── test_e2e.py       # 端到端冒烟测试
│   └── frontend/             # Next.js 前端
│       ├── app/              # 页面路由
│       ├── components/       # UI 与业务组件
│       ├── lib/api/          # 前端 API 客户端
│       └── public/a4cv/      # a4cv 编辑器静态资源
├── docs/
│   ├── INSTALLATION_AUDIT.md # 安装配置审查报告
│   └── a4cv-integration/     # a4cv 集成资料
├── docker-compose.yml
└── package.json
```

## 环境要求

### Docker 方式

- Docker Desktop 或 Docker Engine
- Docker Compose v2
- 一个 OpenAI 兼容 API Key

### 本地源码方式

| 工具 | 版本 |
| --- | --- |
| Node.js | 20 LTS+（最低 20） |
| Python | 3.12+ |
| uv | 最新版 |

安装 uv：

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 快速开始

### 方式 A：Docker Compose（推荐体验）

```bash
cp apps/backend/.env.sample apps/backend/.env
```

编辑 `apps/backend/.env`，至少填写：

```env
SESSION_SECRET_KEY="change-me-to-a-random-string"
LLM_API_KEY="your-llm-api-key"
LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
LL_MODEL="glm-5.1"
```

> **必填**：`LLM_API_KEY`。生产部署（`ENV=production`）下，`LLM_API_KEY` 为空或 `SESSION_SECRET_KEY` 仍为 `change-me` 时，后端会拒绝启动。

启动：

```bash
docker compose up --build
```

访问：

- 前端：http://localhost:3000
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/api/docs
- 健康检查：http://localhost:8000/ping

停止：

```bash
docker compose down
```

Docker 会把 SQLite 与日志保存在 named volumes：`backend-data`、`backend-logs`。

### 方式 B：本地源码运行（适合开发）

配置环境变量：

```bash
cp apps/backend/.env.sample apps/backend/.env
cp apps/frontend/.env.sample apps/frontend/.env
```

编辑 `apps/backend/.env`，填写 `LLM_API_KEY`。本地开发时，`apps/frontend/.env` 默认即可：

```env
NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
```

安装依赖：

```bash
npm run setup
```

启动开发服务：

```bash
npm run dev
```

访问：

- 前端：http://localhost:3000
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/api/docs

## 环境变量

### 后端：`apps/backend/.env`

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `ENV` | 否 | `local` | 可选：`local`、`staging`、`production`；production 会强制校验下面的 Key/密钥 |
| `SESSION_SECRET_KEY` | production 必填 | `change-me` | Session 签名密钥，production 下不能是默认值 |
| `LLM_API_KEY` | 是 | 空 | OpenAI 兼容 API Key，production 下为空会拒绝启动 |
| `LLM_BASE_URL` | 是 | 智谱 API 地址 | OpenAI 兼容 API Base URL |
| `LL_MODEL` | 是 | `glm-5.1` | 模型名称 |
| `SYNC_DATABASE_URL` | 是 | `sqlite:///./app.db` | 同步数据库地址；服务器部署建议改绝对路径（四个斜杠） |
| `ASYNC_DATABASE_URL` | 是 | `sqlite+aiosqlite:///./app.db` | 异步数据库地址；同上 |
| `ALLOWED_ORIGINS` | 否 | 本地端口 | CORS 来源，逗号分隔；同源反代留空即可 |
| `LOG_DIR` | 否 | `apps/backend/logs` | 日志目录；服务器部署建议用绝对路径 |

Docker Compose 会读取 `apps/backend/.env`，并把容器内数据库路径覆盖到 `/app/data/app.db`。

### 前端：`apps/frontend/.env`

| 变量 | 示例 | 说明 |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | 浏览器请求后端 API 的基础地址 |

取值规则：

- 未设置：默认 `http://127.0.0.1:8000`，适合本地开发。
- 空字符串：请求相对路径 `/api/...`，适合 Docker / nginx 同源反代。
- 服务器或内网部署：填浏览器能访问到的后端地址，例如 `https://yourdomain.com` 或 `http://192.168.x.x:8000`。

## 常用命令

```bash
npm run setup            # 安装根目录、前端和后端依赖
npm run dev              # 同时启动前端和后端开发服务
npm run dev:frontend     # 只启动前端
npm run dev:backend      # 只启动后端
npm run build            # 构建前端并检查后端 build 占位步骤
npm run start            # 生产模式启动前端和后端
npm run lint             # 前端 ESLint
npm run test:e2e:fast    # 后端快速冒烟测试，不调用 LLM
npm run test:e2e         # 后端完整 E2E，会调用 LLM
npm run docker:up        # docker compose up
npm run docker:down      # docker compose down
```

## 验证安装

基础验证：

```bash
curl http://127.0.0.1:8000/ping
# 期望返回 {"message":"pong","database":"reachable"}
```

浏览器打开：

```text
http://localhost:3000
http://localhost:8000/api/docs
```

> 如果简历分析接口报 500 或返回空，优先检查 `apps/backend/.env` 的 `LLM_API_KEY` 是否有效、`LLM_BASE_URL` / `LL_MODEL` 是否匹配该供应商。

代码检查：

```bash
npm run lint
npm run build
cd apps/backend && uv run python -m compileall app
```

## 使用流程

1. 打开前端页面。
2. 上传 PDF 或 DOCX 简历。
3. 页面跳转到岗位描述输入页。
4. 粘贴目标岗位 JD。
5. 点击“下一步”提交岗位描述。
6. 点击“开始优化”生成分析结果。
7. 查看岗位解析、简历审计报告和优化建议。
8. 点击「在可视化编辑器中继续优化」，把优化后的简历送入 a4cv 编辑器继续微调。

## 服务器部署

> 📖 **宝塔面板部署**：详见 [`docs/BAOTA_DEPLOY.md`](./docs/BAOTA_DEPLOY.md)，含软件安装、Python/Node 守护、Nginx 反代、HTTPS、常见问题全套步骤。

通用方式推荐用 nginx 做同源反向代理：

- `/` 转发到前端 `127.0.0.1:3000`
- `/api/` 转发到后端 `127.0.0.1:8000`
- 前端构建时设置 `NEXT_PUBLIC_API_URL=""`（同源走相对路径，必须显式设为空字符串）

示例：

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # 简历上传体积，默认 1M 太小，建议 20M
    client_max_body_size 20M;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_read_timeout 300s;
        proxy_buffering off;   # /improve?stream=true 流式响应必须关闭缓冲
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

> `/api/` location 写在 `/` 前面更清晰，避免被 `/` 截获。

如果前端和后端不同域名访问（不同源），需要把前端实际域名加入后端 `ALLOWED_ORIGINS`（在 `apps/backend/.env` 用逗号分隔配置）：

```env
ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
```

同源反代部署（前后端同域名）则不需要配置 CORS，`ALLOWED_ORIGINS` 留空即可。

## API 概览

### 简历接口

- `POST /api/v1/resumes/upload`：上传并解析简历
- `GET /api/v1/resumes?resume_id=...`：获取简历数据
- `POST /api/v1/resumes/improve`：根据岗位描述生成简历分析与优化建议
- `POST /api/v1/resumes/improve?stream=true`：流式返回分析过程
- `POST /api/v1/resumes/improved-markdown`：提取或重建可导入 a4cv 的 Markdown

### 岗位接口

- `POST /api/v1/jobs/upload`：上传并解析岗位描述
- `GET /api/v1/jobs?job_id=...`：获取岗位解析结果

## 端到端测试

后端内置 stdlib-only 的端到端冒烟测试。

运行前提：

- 后端已在 `http://127.0.0.1:8000` 运行。
- 项目根目录存在默认样本简历 `苏明远2-简历-20260615.docx`，或通过参数指定其他简历。
- 完整测试需要可用的 `LLM_API_KEY`。

快速测试：

```bash
npm run test:e2e:fast
```

完整测试：

```bash
npm run test:e2e
```

自定义参数：

```bash
python apps/backend/test_e2e.py \
  --base-url http://127.0.0.1:8001 \
  --frontend-url http://127.0.0.1:3001 \
  --resume-file /path/to/your.docx
```

## 可视化编辑器集成（a4cv）

[a4cv](https://github.com/irenerachel/a4cv) 是一个独立的中文可视化简历编辑器。本项目将编辑器静态资源放在 `apps/frontend/public/a4cv/`，由 Next.js 同源托管。

数据流：

```text
dashboard 点击按钮
   └─► POST /api/v1/resumes/improved-markdown
         └─► 从 analysis_result 抽取 Markdown 或重建 fallback
   └─► sessionStorage.setItem('pendingResumeMD', md)
   └─► window.open('/a4cv/index.html?pickup=session')
         └─► a4cv 读取 sessionStorage 并渲染
```

## 常见问题

### `LLM_API_KEY` 为空或模型调用失败

确认已经复制 `apps/backend/.env.sample` 到 `apps/backend/.env`，并填写了有效 Key。Docker 方式也读取同一个文件。

### 前端提示连接后端失败

本地开发检查 `apps/frontend/.env`：

```env
NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
```

服务器部署时，`NEXT_PUBLIC_API_URL` 必须是浏览器能访问到的地址；同源 nginx 反代部署则设为空字符串。

### 浏览器控制台报 CORS

如果前后端不同源访问，需要把前端域名加入后端 `ALLOWED_ORIGINS`。同源 nginx 反代部署不需要 CORS。

### a4cv 编辑器打开后是空白

确认路径是 `/a4cv/index.html?pickup=session`，并检查浏览器 console 是否提示未找到 `pendingResumeMD`。

### `npm run lint` 扫描构建产物

当前 ESLint 已忽略 `.next/`、`out/` 和 `public/a4cv/`。如果仍报构建产物错误，先删除 `apps/frontend/.next` 后重试。

## 说明与致谢

本项目基于开源项目 `srbhr/Resume-Matcher` 二次开发，针对中文求职和国内模型调用场景做了调整：

- 移除本地 Ollama / 本地 embedding provider
- 移除 MarkItDown 等重依赖
- 默认使用智谱 OpenAI 兼容 API
- 保留 SQLite 作为轻量本地状态存储
- 前端界面中文化

提示词模板参考中文 HR / 面试官视角的简历审计风格，用于输出更直接、更适合修改简历的建议。

感谢 a4cv 项目和 https://linux.do 社区佬友支持。
