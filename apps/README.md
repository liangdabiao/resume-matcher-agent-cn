# HR批评简历

一个面向中文用户的 AI 简历深度优化工具。上传简历并粘贴目标岗位 JD 后，系统会解析简历与岗位要求，生成岗位匹配分析、HR 视角审计报告和可执行的简历修改建议。

> 完整使用说明、部署指南见项目根目录 [README](../README.md)。

## 项目介绍

HR批评简历旨在通过分析职位描述并提供有针对性的改进建议，帮助求职者优化简历。平台使用 AI 模型从简历和职位发布中提取关键信息，然后提供可操作的见解，以增加通过筛选系统的机会。

应用程序由处理数据处理和 AI 集成的 **Flask 后端**，以及提供用户友好界面的 **Next.js 前端**组成。

## 核心功能

- **简历分析**：上传 PDF 或 DOCX 格式的简历进行分析
- **职位描述解析**：处理职位描述以提取关键要求和关键词
- **AI 驱动的洞察**：根据职位要求获取改进建议（HRBP 视角深度审计）
- **结构化数据提取**：将非结构化的简历和职位数据转换为结构化 JSON
- **可视化编辑器**：优化后的简历可送入 a4cv 编辑器二次微调

## 技术栈

| 技术 | 版本/信息 |
| --- | --- |
| Python | 3.12+ |
| Flask | 3.0+（同步，Gunicorn 部署，无 ASGI/WSGI 坑） |
| Next.js | 15+ |
| OpenAI 兼容 API | 默认智谱 glm-5.1 |
| 存储 | JSON 文件（无数据库） |
| Tailwind CSS | 4.x |

## 目录结构

### 后端 (`apps/backend/`，极简 7 个文件)

```
backend/
├── app.py            # Flask 应用 + 全部路由（8 个端点）
├── config.py         # 配置（os.getenv + dotenv）
├── llm.py            # OpenAI 调用 + JSON 解析
├── parser.py         # PDF/DOCX 文本提取
├── prompts.py        # 3 个提示词模板
├── store.py          # JSON 文件存储
├── run.py            # 本地开发启动入口
├── data/             # JSON 数据（resumes/ jobs/，自动生成）
├── logs/             # 日志
├── requirements.txt  # 仅 5 个依赖
└── .env              # 环境配置
```

### 前端 (`apps/frontend/`)

```
frontend/
├── app/                # Next.js 页面和布局
├── components/         # React 组件
├── lib/api/            # 前端 API 客户端
├── public/a4cv/        # a4cv 可视化编辑器静态资源
├── package.json        # Node.js 依赖
└── tailwind.config.js  # Tailwind CSS 配置
```

## 快速开始

### 后端

```bash
cd apps/backend
cp .env.sample .env          # 编辑 .env 填入 LLM_API_KEY
pip install -r requirements.txt

# 本地开发
python run.py
# 或生产（宝塔/服务器通用）
gunicorn -w 2 -b 127.0.0.1:8000 --timeout 300 app:app
```

后端将在 `http://localhost:8000` 可用。

### 前端

```bash
cd apps/frontend
cp .env.sample .env          # 同源部署：NEXT_PUBLIC_API_URL=""
npm install
npm run dev                  # 开发
# 或生产
npm run build && npm run start
```

前端将在 `http://localhost:3000` 可用。

## API 端点

### 简历接口 (`/api/v1/resumes`)

- `POST /upload` — 上传并解析简历（PDF/DOCX）
- `POST /improve` — 根据岗位描述生成简历分析（支持 `?stream=true` 流式）
- `GET /` — 根据 resume_id 获取简历数据
- `POST /improved-markdown` — 提取优化后的简历 markdown（给 a4cv 编辑器）

### 岗位接口 (`/api/v1/jobs`)

- `POST /upload` — 上传并解析职位描述
- `GET /` — 根据 job_id 获取岗位数据

### 健康检查

- `GET /ping` — 返回 `{"message":"pong","database":"reachable"}`

## 环境配置

详见 [docs/CONFIGURING.md](../docs/CONFIGURING.md)。最小配置只需填 `LLM_API_KEY`。

## 项目参考

代码 fork 自 [resume-ai](https://github.com/junyi-zhu/resume-ai)，感谢原作者。基于其代码大量修改，针对国内用户和国内大模型做了适配。

提示词模板来自资深 HRBP / 面试官视角的简历审计风格。
