# 简历匹配智能体

简历匹配智能体是一个面向中文用户的 AI 简历深度优化工具。你上传简历并粘贴目标岗位 JD 后，系统会解析简历与岗位要求，生成岗位匹配分析、HR 视角审计报告和可执行的简历修改建议。

本项目保留 SQLite 作为轻量本地状态存储，用于保存简历、岗位描述、结构化解析结果和流程 ID。SQLite 不需要单独部署数据库服务，适合本地使用、演示和轻量部署。

本项目一个亮点是整合了阿真的开源简历编辑器：https://github.com/irenerachel/a4cv 

## 核心功能

- 上传 PDF / DOCX 简历并提取文本
- 粘贴岗位 JD 并解析岗位职责、要求和关键词
- 使用智谱 OpenAI 兼容 API 进行结构化抽取与简历审计
- 生成中文 HR 视角的深度简历分析报告
- 根据岗位要求输出简历优化方向和示例改写
- 一键把优化后的简历送入 a4cv 可视化编辑器二次微调（详见 [「在可视化编辑器中继续优化」](#可视化编辑器集成-a4cv)）
- 前端界面已中文化，适合中文求职场景

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Next.js 15、React 19、TypeScript、Tailwind CSS |
| 后端 | FastAPI、Pydantic、SQLAlchemy、aiosqlite |
| 数据库 | SQLite |
| AI 接入 | 任意 OpenAI 兼容 API（智谱、DeepSeek、Tencent TokenHub 等） |
| 默认模型 | `glm-5.1`（可在 `.env` 改 `LL_MODEL` / `LLM_BASE_URL` 切到 `deepseek-chat`） |
| 文档解析 | `pdfminer.six` 解析 PDF，标准库解析 DOCX |

## 目录结构

```text
.
├── a4cv-main/                # 第三方可视化简历编辑器源码
├── apps/
│   ├── backend/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── agent/        # 通用 OpenAI 兼容调用封装（chat.completions）
│   │   │   ├── api/          # API 路由
│   │   │   ├── core/         # 配置、数据库、日志
│   │   │   ├── models/       # SQLAlchemy 数据模型
│   │   │   ├── prompt/       # 提示词模板
│   │   │   ├── schemas/      # Pydantic / JSON Schema
│   │   │   ├── services/     # 简历、岗位、分析服务
│   │   │   └── utils/        # markdown_extractor 等工具
│   │   ├── .env.sample       # 后端环境变量示例
│   │   ├── requirements.txt
│   │   └── pyproject.toml
│   └── frontend/             # Next.js 前端
│       ├── app/              # 页面路由
│       ├── components/       # UI 与业务组件
│       ├── lib/api/          # 前端 API 客户端
│       └── public/a4cv/      # a4cv 编辑器静态资源（同源托管）
├── docs/
├── setup.sh
├── setup.ps1
├── copy-a4cv.ps1             # 同步 a4cv-main -> public/a4cv 的脚本
└── package.json
```

## 环境配置

### 后端环境变量

复制示例文件：

```bash
cp apps/backend/.env.sample apps/backend/.env
```

然后填写智谱 API Key：

```env
SESSION_SECRET_KEY="change-me"
SYNC_DATABASE_URL="sqlite:///./app.db"
ASYNC_DATABASE_URL="sqlite+aiosqlite:///./app.db"
PYTHONDONTWRITEBYTECODE=1
ENV="local"

LLM_API_KEY="your-llm-api-key"
LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
LL_MODEL="glm-5.1"
```

### 前端环境变量

复制示例文件：

```bash
cp apps/frontend/.env.sample apps/frontend/.env
```

默认后端地址：

```env
NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
```

## 安装依赖

在项目根目录执行：

```bash
npm run install
```

也可以分别安装：

```bash
npm run install:backend
npm run install:frontend
```

## 本地运行

同时启动前后端：

```bash
npm run dev
```

分别启动：

```bash
npm run dev:backend
npm run dev:frontend
```

默认地址：

- 前端：`http://127.0.0.1:3000`
- 后端：`http://127.0.0.1:8000`

## 使用流程

1. 打开前端页面
2. 上传 PDF 或 DOCX 简历
3. 页面跳转到岗位描述输入页
4. 粘贴目标岗位 JD
5. 点击“下一步”提交岗位描述
6. 点击“开始优化”生成分析结果
7. 在控制台查看岗位解析、简历审计报告和优化建议
8. 点击右上角「✦ 在可视化编辑器中继续优化」按钮，把 LLM 优化后的简历送入 a4cv 编辑器继续微调

> 第 8 步需要 a4cv 资源已经同步到 `apps/frontend/public/a4cv/`，参见 [可视化编辑器集成](#可视化编辑器集成-a4cv)。

## API 概览

### 简历接口

- `POST /api/v1/resumes/upload`：上传并解析简历
- `GET /api/v1/resumes?resume_id=...`：获取简历数据
- `POST /api/v1/resumes/improve`：根据岗位描述生成简历分析与优化建议
- `POST /api/v1/resumes/improve?stream=true`：流式返回分析过程

### 岗位接口

- `POST /api/v1/jobs/upload`：上传并解析岗位描述
- `GET /api/v1/jobs?job_id=...`：获取岗位解析结果

## 为什么保留 SQLite

SQLite 在本项目中用于保存本地流程状态：

- 上传后的 `resume_id`
- 简历原文与结构化简历
- 岗位原文与结构化岗位
- `job_id` 与简历优化流程所需的关联数据

它的作用不是引入复杂数据库系统，而是避免所有数据只存在内存中。这样刷新页面、重新请求接口或重启后端时，仍能通过 ID 找回已上传的数据。对于当前项目，SQLite 是最轻量、最稳妥的方案。

## 构建与检查

```bash
npm run build
npm run lint
```

后端也可以单独做语法检查：

```bash
cd apps/backend
python -m compileall app
```

## 端到端测试

后端内置了一个 stdlib-only 的端到端冒烟测试，覆盖全部公开 API。

### 运行前提

- 后端已经在 `http://127.0.0.1:8000` 跑起来（`npm run dev:backend`）
- 项目根目录存在 `苏明远2-简历-20260615.docx`（默认样本简历）
- 可选：前端跑在 `http://127.0.0.1:3000`，用于 a4cv 静态资源检查

### 快速测试（不含 LLM，约 1 分钟）

```bash
npm run test:e2e:fast
# 或：
cd apps/backend && python test_e2e.py --skip-llm
```

### 完整测试（含 LLM 调优，约 4-5 分钟）

```bash
npm run test:e2e
# 或：
cd apps/backend && python test_e2e.py
```

### 自定义参数

```bash
# 改端口、跳过前端检查、用别的样本简历
python apps/backend/test_e2e.py \
  --base-url http://127.0.0.1:8001 \
  --frontend-url http://127.0.0.1:3001 \
  --resume-file /path/to/your.docx
```

### 测试覆盖

| 测试 | 路径 | 验证点 | LLM? |
| --- | --- | --- | --- |
| `test_health` | `GET /ping` | 200 + DB 可达 | ❌ |
| `test_resume_upload` | `POST /api/v1/resumes/upload` | DOCX 解析 + `resume_id` | ❌ |
| `test_job_upload` | `POST /api/v1/jobs/upload` | JD 解析 + `job_id` | ✅ |
| `test_improve_nonstream` | `POST /api/v1/resumes/improve` | 中文报告 ≥ 200 字 + ≥ 3 个 Step | ✅ |
| `test_improve_stream` | `POST /api/v1/resumes/improve?stream=true` | SSE 事件顺序 + TTFT | ✅ |
| `test_improved_markdown` | `POST /api/v1/resumes/improved-markdown` | markdown 提取 / fallback | ❌ |
| `test_a4cv_static` | `GET /a4cv/` | 标题 + pickup hook | ❌ |

退出码 0 = 全部通过；非 0 = 有失败。

## 可视化编辑器集成（a4cv）

[Resume Studio（a4cv）](https://github.com/...) 是一个独立的中文可视化简历编辑器，仓库内 `a4cv-main/` 是它的源码目录。

为了把它无缝接到本系统里，我们采用**同源托管**方案：

- 把 `a4cv-main/` 下的 `index.html`、`vendor/*`、`assets/*` 复制到 `apps/frontend/public/a4cv/`，随主前端一起由 Next.js 服务
- dashboard 的「在可视化编辑器中继续优化」按钮调用后端 `POST /api/v1/resumes/improved-markdown` 抽取 Markdown，写入 `sessionStorage`，再 `window.open('/a4cv/index.html?pickup=session')`
- a4cv 的 IIFE 在启动时优先读 `sessionStorage.pendingResumeMD`（或 `?md=` URL 参数），把简历直接渲染到画布上

完整数据流：

```text
dashboard 点击按钮
   └─► POST /api/v1/resumes/improved-markdown
         └─► 从 analysis_result 抽取 ```md``` 代码块
              └─► 没有则从 ProcessedResume 重建 fallback
   └─► sessionStorage.setItem('pendingResumeMD', md)
   └─► window.open('/a4cv/index.html?pickup=session')
         └─► a4cv IIFE 读取 sessionStorage，调 loadMD() 渲染
```

### 同步 a4cv 资源

任何时候 `a4cv-main/` 有更新，跑一次同步脚本：

```powershell
# Windows PowerShell
.\copy-a4cv.ps1
```

脚本会清理旧的 `public/a4cv/`，重新复制 `index.html`、`vendor/*`、`assets/*`，并打印每个文件的大小做完整性校验。Linux/macOS 用户可以临时在 PowerShell Core 下运行同一脚本。

### 端到端验证

后端 + 前端启动后，`apps/backend/` 下保留了几个测试脚本，可随时复跑：

```bash
# 后端路由 + Markdown 抽取
python test_extractor.py        # 单元测试 extract/build_fallback
python test_route.py            # 验证 /improved-markdown 已注册
python test_e2e_endpoint.py     # 实际打 HTTP，验证抽取/fallback 路径
python test_static.py           # 验证 a4cv 静态资源可访问
python test_vendor.py           # 验证 5 个 vendor JS 全部 200

# 浏览器端到端（需要 chrome.exe）
node test_e2e_browser.js        # 注入 sessionStorage，验证 a4cv 渲染
node test_e2e_full.js           # 模拟 dashboard fetch + 跳转 a4cv 完整链路
```

## 部署

### 1. 准备环境

- Node.js ≥ 18
- Python ≥ 3.8
- （推荐）[`uv`](https://docs.astral.sh/uv/) —— 后端用 `uv` 创建虚拟环境

### 2. 一键安装依赖

```bash
# 项目根目录
npm run install          # 等价于 install:backend + install:frontend
```

> `install:backend` 是幂等的：已存在 `.venv` 会自动复用并按需升级依赖；首次执行会先创建 venv。

或分别执行：

```bash
npm run install:backend
npm run install:frontend
```

### 3. 配置环境变量

```bash
cp apps/backend/.env.sample apps/backend/.env
cp apps/frontend/.env.sample apps/frontend/.env
```

- 后端：在 `.env` 中填入 `LLM_API_KEY`（智谱）等必填项
- 前端：`NEXT_PUBLIC_API_URL` 指向后端地址（默认 `http://127.0.0.1:8000`）

> 关键 CORS 配置：`apps/backend/app/core/config.py` 的 `ALLOWED_ORIGINS` 默认已包含 `3000/3001/3002`，覆盖开发期常见的端口冲突场景。生产部署时把它改成你前端实际域名即可。

### 4. 同步 a4cv 资源（首次部署必做）

```powershell
.\copy-a4cv.ps1
```

### 5. 启动开发模式

```bash
npm run dev              # 同时启 backend (8000) + frontend (3000)
```

或分别启动：

```bash
npm run dev:backend
npm run dev:frontend
```

前端默认 `http://127.0.0.1:3000`，后端默认 `http://127.0.0.1:8000`，API 文档 `http://127.0.0.1:8000/api/docs`。

### 6. 生产构建

```bash
npm run build
```

- 前端：`apps/frontend/.next/` 静态资源，可用 `next start` 启动
- 后端：无构建步骤（Python），直接 `uvicorn app.main:app` 启动

```bash
# 前端
cd apps/frontend && npm start

# 后端（生产示例）
cd apps/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 7. 反向代理（Nginx 示例）

```nginx
server {
    listen 80;
    server_name resume.example.com;

    # Next.js 前端（包含 /a4cv/ 静态资源）
    location / {
        proxy_pass http://127.0.0.1:3000;
    }

    # FastAPI 后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300;          # 兼容 LLM 长任务
    }
}
```

部署完成后：

- `https://resume.example.com/` —— 主站
- `https://resume.example.com/a4cv/index.html?pickup=session` —— 可视化编辑器入口（必须带 `?pickup=session` 才能从 sessionStorage 取到 Markdown）
- `https://resume.example.com/api/docs` —— OpenAPI 文档

### 8. 数据持久化

- 默认 `apps/backend/app.db`（SQLite）
- 想把数据库放在别的位置，在后端 `.env` 中调整 `SYNC_DATABASE_URL` / `ASYNC_DATABASE_URL`
- 例：`ASYNC_DATABASE_URL=sqlite+aiosqlite:////var/lib/resume-matcher/app.db`

## 常见问题

**问：点「在可视化编辑器中继续优化」按钮没反应？**
答：检查 a4cv 资源是否同步（`apps/frontend/public/a4cv/index.html` 是否存在）。Dev server 不会自动做 directory index 解析，必须用 `/a4cv/index.html?pickup=session` 而不是 `/a4cv/?pickup=session`。

**问：浏览器控制台报 CORS 错？**
答：检查后端 `ALLOWED_ORIGINS` 是否包含前端实际端口（默认 3000/3001/3002）。生产环境把前端域名加进去即可。

**问：a4cv 编辑器打开后是空白？**
答：F12 看 console 是否提示「未找到 pendingResumeMD」。说明抽取没拿到代码块（也不在 fallback 路径上），最常见原因是 LLM 返回里没带 ```` ```md ```` 代码块——检查 `/improve` 接口的 prompt 模板。

## 说明

本项目基于开源项目 `srbhr/Resume-Matcher` 二次开发，已针对中文求职和国内模型调用场景做了较大调整：

- 移除本地 Ollama / 本地 embedding provider
- 移除 MarkItDown 等重依赖
- 默认使用智谱 OpenAI 兼容 API
- 保留 SQLite 作为轻量本地状态存储
- 前端界面中文化

提示词模板参考了中文 HR / 面试官视角的简历审计风格，用于输出更直接、更适合修改简历的建议。
