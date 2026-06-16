# 配置说明

本项目用两个环境文件，都从对应的 `.env.sample` 复制而来：

- `apps/backend/.env` — 后端、AI 设置
- `apps/frontend/.env` — 前端 API 地址

## 后端 `apps/backend/.env`

```env
ENV="local"
LLM_API_KEY=""
LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
LL_MODEL="glm-5.1"
SESSION_SECRET_KEY="change-me"
BACKEND_PORT=8000
```

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `ENV` | 否 | `local` | `local` / `production`；production 会强制校验 Key/密钥 |
| `LLM_API_KEY` | 是 | 空 | OpenAI 兼容 API Key，production 下为空会拒绝启动 |
| `LLM_BASE_URL` | 是 | 智谱 API 地址 | OpenAI 兼容 API Base URL |
| `LL_MODEL` | 是 | `glm-5.1` | 模型名称 |
| `SESSION_SECRET_KEY` | production 必填 | `change-me` | Session 密钥，production 下不能是默认值 |
| `BACKEND_PORT` | 否 | `8000` | 本地 `run.py` 默认监听端口 |
| `ALLOWED_ORIGINS` | 否 | 本地端口 | CORS 来源，逗号分隔；同源反代留空 |
| `LOG_DIR` | 否 | `apps/backend/logs` | 日志目录，服务器建议绝对路径 |

> 后端用 JSON 文件存储（`apps/backend/data/`），**无需配置任何数据库地址**。

### AI 模型配置

后端通过 OpenAI 兼容协议调用大模型（用官方 `openai` Python SDK）。默认智谱 `glm-5.1`，可改成 DeepSeek、腾讯 TokenHub 等任意 OpenAI 兼容服务：

```env
# DeepSeek 示例
LLM_BASE_URL="https://api.deepseek.com/v1/"
LL_MODEL="deepseek-chat"
LLM_API_KEY="sk-你的deepseek-key"

# 腾讯 TokenHub 示例
LLM_BASE_URL="https://tokenhub.tencentmaas.com/v1/"
LL_MODEL="deepseek-v4-flash-202605"
LLM_API_KEY="你的tokenhub-key"
```

调用参数固定为 `temperature=0, top_p=0.9`（在 `llm.py` 里），追求稳定输出。

## 前端 `apps/frontend/.env`

```env
# 同源部署（Docker / 宝塔 / nginx 反代）：必须是空字符串
NEXT_PUBLIC_API_URL=""

# 本地开发（浏览器直连后端 8000）：
# NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
```

`NEXT_PUBLIC_API_URL` 取值规则：

- **空字符串 `""`**：前端走相对路径 `/api/...`，由 Nginx/Next.js rewrites 转发到后端。**生产同源部署用这个**。
- **完整地址**：浏览器直接请求该地址，用于本地开发或前端独立域名场景。
- **不设置（删除该变量）**：回退到 `http://127.0.0.1:8000`（仅本地开发适用，外网访问会失败）。

> ⚠️ `NEXT_PUBLIC_*` 变量在**构建时**注入，改了必须重新 `npm run build` 并重启前端进程。
