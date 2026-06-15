# 简历匹配智能体

简历匹配智能体是一个面向中文用户的 AI 简历深度优化工具。你上传简历并粘贴目标岗位 JD 后，系统会解析简历与岗位要求，生成岗位匹配分析、HR 视角审计报告和可执行的简历修改建议。

本项目保留 SQLite 作为轻量本地状态存储，用于保存简历、岗位描述、结构化解析结果和流程 ID。SQLite 不需要单独部署数据库服务，适合本地使用、演示和轻量部署。

## 核心功能

- 上传 PDF / DOCX 简历并提取文本
- 粘贴岗位 JD 并解析岗位职责、要求和关键词
- 使用智谱 OpenAI 兼容 API 进行结构化抽取与简历审计
- 生成中文 HR 视角的深度简历分析报告
- 根据岗位要求输出简历优化方向和示例改写
- 前端界面已中文化，适合中文求职场景

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Next.js 15、React 19、TypeScript、Tailwind CSS |
| 后端 | FastAPI、Pydantic、SQLAlchemy、aiosqlite |
| 数据库 | SQLite |
| AI 接入 | 智谱 OpenAI 兼容 API |
| 默认模型 | `glm-5.1` |
| 默认 Embedding | `embedding-3` |
| 文档解析 | `pdfminer.six` 解析 PDF，标准库解析 DOCX |

## 目录结构

```text
.
├── apps/
│   ├── backend/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── agent/        # 智谱 OpenAI 兼容调用封装
│   │   │   ├── api/          # API 路由
│   │   │   ├── core/         # 配置、数据库、日志
│   │   │   ├── models/       # SQLAlchemy 数据模型
│   │   │   ├── prompt/       # 提示词模板
│   │   │   ├── schemas/      # Pydantic / JSON Schema
│   │   │   └── services/     # 简历、岗位、评分与优化逻辑
│   │   ├── .env.sample       # 后端环境变量示例
│   │   ├── requirements.txt
│   │   └── pyproject.toml
│   └── frontend/             # Next.js 前端
│       ├── app/              # 页面路由
│       ├── components/       # UI 与业务组件
│       ├── lib/api/          # 前端 API 客户端
│       └── .env.sample       # 前端环境变量示例
├── docs/
├── setup.sh
├── setup.ps1
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

LLM_API_KEY="your-zhipu-api-key"
LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
LL_MODEL="glm-5.1"

EMBEDDING_API_KEY="your-zhipu-api-key"
EMBEDDING_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
EMBEDDING_MODEL="embedding-3"
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

## 说明

本项目基于开源项目 `srbhr/Resume-Matcher` 二次开发，已针对中文求职和国内模型调用场景做了较大调整：

- 移除本地 Ollama / 本地 embedding provider
- 移除 MarkItDown 等重依赖
- 默认使用智谱 OpenAI 兼容 API
- 保留 SQLite 作为轻量本地状态存储
- 前端界面中文化

提示词模板参考了中文 HR / 面试官视角的简历审计风格，用于输出更直接、更适合修改简历的建议。
