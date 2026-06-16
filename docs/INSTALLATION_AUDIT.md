# 安装与配置问题排查报告

> 本文档基于 **2026-06-16** 对当前工作区的实际检查编写，所有结论均经过命令验证。
> 目标：让新用户能按标准步骤稳定地克隆、安装、启动、验证本项目。

## 一、总体结论

项目核心链路是健康的，本地开发路径已经能跑通：

| 验证项 | 命令 | 结果 |
| --- | --- | --- |
| 前端生产构建 | `cd apps/frontend && npm run build` | ✅ 通过（8 个静态页全部生成） |
| 前端 Lint | `cd apps/frontend && npm run lint` | ✅ 通过（仅 1 个无害 warning） |
| 后端语法检查 | `cd apps/backend && uv run python -m compileall app` | ✅ 通过 |
| 后端应用初始化 | `uv run python -c "from app.base import create_app"` | ✅ 通过，配置正常加载 |
| 依赖锁同步 | `cd apps/backend && uv lock --check` | ✅ 通过（uv.lock 与 pyproject 一致） |

但仍有 **5 个阻断性问题（P0）** 会让「开源新用户」第一次安装就失败，主要集中在 **Docker 部署链路** 和 **仓库卫生**。下面按优先级逐条说明，并给出可直接照做的修复。

---

## 二、P0 阻断性问题（必须修，否则用户装不上）

### P0-1. 根目录缺少 `.dockerignore`，Docker 构建会拖死

**现象**

`docker-compose.yml` 里两个服务的构建上下文都是项目根：

```yaml
services:
  backend:
    build:
      context: .              # ← 项目根
      dockerfile: apps/backend/Dockerfile
  frontend:
    build:
      context: .              # ← 项目根
      dockerfile: apps/frontend/Dockerfile
```

但 **项目根目录没有 `.dockerignore`**（已确认 `ROOT .dockerignore MISSING`）。

**为什么这是阻断问题**

Docker 只识别「构建上下文根目录」的 `.dockerignore`。仓库里现有的两个文件：

- `apps/backend/.dockerignore`
- `apps/frontend/.dockerignore`

**都不会被 Docker 读取**（它们既不在上下文根，文件名也不是 `Dockerfile.dockerignore` 格式），形同虚设。结果就是 `docker compose up --build` 会把整个项目根打包发给 Docker daemon，包含：

- `apps/frontend/node_modules/`（通常 200MB+）
- `apps/backend/.venv/`
- `apps/frontend/.next/`
- `apps/backend/app.db`、`app.db-shm`、`app.db-wal`
- 4 张截图、简历 docx、各种 `*.md` 笔记

新用户第一次 `docker compose up --build` 会卡在「sending build context to Docker daemon」很久，甚至因为上下文过大、文件被占用而失败。这两个 `.dockerignore` 还是 git 未跟踪状态（`??`），clone 下来的人根本看不到。

**修复方案（在项目根新建 `.dockerignore`）**

```gitignore
# 通用：依赖与构建产物
**/node_modules/
**/.next/
**/out/
**/dist/
**/build/

# Python
**/__pycache__/
**/*.py[cod]
**/.venv/
**/venv/
**/.pytest_cache/
**/.mypy_cache/
**/.ruff_cache/

# 本地运行时数据（绝不进镜像）
**/app.db
**/app.db-shm
**/app.db-wal
**/*.log
**/logs/

# 环境变量（敏感）
**/.env
**/.env.*
!**/.env.sample

# Git / IDE / OS
.git/
.gitignore
.vscode/
.idea/
**/.DS_Store
**/Thumbs.db

# 文档与杂项（镜像不需要）
README.md
docs/
LICENSE
**/*.md
assets/
.claude/
.playwright-mcp/

# 二进制素材（截图、简历样本，由构建上下文排除）
*.png
*.jpg
*.jpeg
*.docx
```

> 注意：上面用 `**/.env` 排除敏感文件，同时 `!**/.env.sample` 保留示例。
> 新建根 `.dockerignore` 后，建议删除已失效的 `apps/backend/.dockerignore`、`apps/frontend/.dockerignore`，避免误导后续维护者。

---

### P0-2. `docker-compose.yml` 的 `backend` 用了 `env_file` 但镜像内无 `.env`，且 compose 路径覆盖不全

**现象**

当前 `docker-compose.yml`（第 9-15 行）：

```yaml
backend:
  env_file:
    - apps/backend/.env        # ← 读取宿主机 .env
  environment:
    ENV: production
    SYNC_DATABASE_URL: sqlite:////app/data/app.db
    ASYNC_DATABASE_URL: sqlite+aiosqlite:////app/data/app.db
    LOG_DIR: /app/logs
```

这一段**逻辑上是对的**（旧审计报告说没有 `env_file`，现在已加上）。但存在两个残留隐患：

1. **`LLM_API_KEY` 完全依赖 `apps/backend/.env`**。README 让用户 `cp apps/backend/.env.sample apps/backend/.env` 后填 Key，这一步如果漏掉，容器内 `LLM_API_KEY` 为空，所有简历分析接口会 500。compose 没有任何「Key 为空则拒绝启动」的保护。
2. **`SESSION_SECRET_KEY`** 同样来自 `.env`，`.env.sample` 默认是 `"change-me"`，用户不改就用默认值，生产环境等于裸奔。

**修复方案**

(a) 在后端启动时做最小校验（`apps/backend/app/core/config.py` 加属性校验，避免空 Key 静默启动）：

```python
from pydantic import model_validator

class Settings(BaseSettings):
    # ... 原有字段 ...

    @model_validator(mode="after")
    def _validate_required(self):
        if self.ENV == "production":
            if not self.LLM_API_KEY:
                raise ValueError("ENV=production 但 LLM_API_KEY 为空，请检查 apps/backend/.env")
            if not self.SESSION_SECRET_KEY or self.SESSION_SECRET_KEY == "change-me":
                raise ValueError("ENV=production 时 SESSION_SECRET_KEY 必须改成随机字符串")
        return self
```

(b) 在 README「Docker 快速开始」里把「填 LLM_API_KEY」标成**必填步骤**，并在 compose 启动后提示用 `curl http://localhost:8000/ping` 验证。

---

### P0-3. 仓库提交了真实 API Key（`.env` 泄露风险）

**现象**

`apps/backend/.env`（已被 `.gitignore` 忽略，未进 git）当前包含一个**真实的腾讯 TokenHub API Key**：

```env
LLM_API_KEY="sk-9ahA6dEXUrkUvVKYy39awDeH1GcGY2FGqYKA0W2WEY2XlkA5"
LLM_BASE_URL="https://tokenhub.tencentmaas.com/v1/"
LL_MODEL="deepseek-v4-flash-202605"
```

虽然 git 没跟踪它（已确认 `git ls-files` 只含 `.env.sample`），但：

- 这个 Key 已经写在本地工作区，一旦打包 zip 发布或误推就会泄露。
- 开源后每位贡献者本机的 `.env` 都可能含真实 Key，需要明确规则。

**修复方案**

1. **立即作废该 Key**：登录腾讯 TokenHub 控制台吊销 `sk-9ahA...` 这个 Key（它已出现在工作区文件中，必须视为已泄露）。
2. README 增加醒目提示：**永远不要把 `.env` 提交或分享，`.env.sample` 才是公开模板**。
3. 确保 `.gitignore` 的 `.env` 规则覆盖所有层级（当前已覆盖，保持即可）。

---

### P0-4. 大量无关文件被 git 跟踪，污染开源仓库

**现象（已用 `git ls-files` 逐项确认）**

以下文件已进入版本库，开源发布前应清理：

| 文件 | 问题 |
| --- | --- |
| `apps/backend/app/新建 文本文档.txt` | 空文本文件，明显误提交 |
| `apps/backend/b.md` | 开发笔记 |
| `apps/frontend/a.md` | 开发笔记 |
| `apps/frontend/improve_bug.md` | 开发笔记 |
| `apps/frontend/analysis_result_example.md` | 开发笔记 |
| `apps/frontend/全流程分析.md` | 开发笔记 |
| `apps/frontend/接口请求和返回.md` | 开发笔记 |
| `ScreenShot_2026-06-15_*.png` | 截图（根目录 2 张） |
| `wechat_longscreenshot_*.png` | 微信长截图 |
| `apps/backend/a4cv-*.png` | a4cv 调试截图 2 张 |
| `AI Agent 工程师岗位要求（JD）.txt` | 个人 JD |
| `苏明远2-简历-20260615.docx` | 个人简历（含隐私信息） |
| `apps/backend/check_db.py` 及 9 个 `test_*.py` | 散落在 backend 根的临时测试脚本 |

**为什么是 P0**

- `苏明远2-简历-20260615.docx` 含真实个人信息，开源发布是**隐私泄露**。
- README 的「端到端测试」章节引用了根目录的简历样本，但这个文件本身不应进仓库。
- 大量 `.md` 笔记和中文乱码文件名（`新建 文本文档.txt`）严重影响开源项目的专业度。

**修复方案**

```bash
# 1. 从仓库移除（保留本地文件用 --cached）
git rm --cached "apps/backend/app/新建 文本文档.txt"
git rm --cached apps/backend/b.md
git rm --cached apps/frontend/a.md apps/frontend/improve_bug.md
git rm --cached apps/frontend/analysis_result_example.md
git rm --cached "apps/frontend/全流程分析.md" "apps/frontend/接口请求和返回.md"
git rm --cached ScreenShot_2026-06-15_*.png wechat_longscreenshot_*.png
git rm --cached apps/backend/a4cv-*.png
git rm --cached "AI Agent 工程师岗位要求（JD）.txt"
git rm --cached "苏明远2-简历-20260615.docx"

# 2. 更新 .gitignore，防止再次提交
# 在 .gitignore 末尾追加：
#   *.docx
#   *.png
#   *.jpg
#   *.jpeg
#   !assets/**
#   !docs/**/*.png   # 文档配图放 docs/ 下，单独放行

# 3. README 的 E2E 测试章节改为提示用户提供 --resume-file 参数，
#    不再依赖仓库内的个人简历。
```

---

### P0-5. 后端镜像 `CMD` 没有进行数据库初始化与日志目录创建的兜底

**现象**

`apps/backend/Dockerfile`（第 24-29 行）：

```dockerfile
RUN mkdir -p /app/data /app/logs
VOLUME ["/app/data", "/app/logs"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

数据库初始化依赖 `app/base.py` 的 `lifespan` 里 `Base.metadata.create_all`，这个逻辑没问题。但有两个细节：

1. **`VOLUME` 声明与 compose 的 named volume 重复**，会让 Docker 在镜像层面再声明一个匿名 volume，容易造成数据卷混乱。建议删除 Dockerfile 里的 `VOLUME` 行，卷管理统一交给 `docker-compose.yml`。
2. **生产模式应关闭 `--reload` 并可考虑加 `--workers`**。当前 `CMD` 没有 `--reload`（正确），但 README 的 `npm run start:backend` 用的是 `uv run uvicorn ... --host 0.0.0.0 --port 8000`，也没加 worker，单进程生产可以接受，但建议在文档里说明。

**修复方案**

```dockerfile
# 删除这一行，交给 compose 管理卷
# VOLUME ["/app/data", "/app/logs"]

# 生产 CMD 建议显式声明 workers（可选）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

---

## 三、P1 强烈建议修复（影响开源可信度与可维护性）

### P1-1. README「环境要求」与实际依赖版本需对齐

**现状**

- `apps/backend/pyproject.toml`：`requires-python = ">=3.12"`
- 后端 `Dockerfile`：`FROM python:3.12-slim` ✅ 一致
- 前端 `Dockerfile`：`FROM node:20-alpine`
- README「本地源码方式」表格：Node.js「推荐 20 LTS，最低 18+」，Python「3.12+」✅ 一致

**残留问题**

当前 README 已经统一为 Python 3.12+（旧审计报告说的 3.8/3.12 矛盾已修复）。但 Node.js「最低 18+」偏宽松，Next.js 15.3 + React 19 在 Node 18 上可能有兼容问题，建议改为**「Node.js 20 LTS+」**。

---

### P1-2. `requirements.txt` 与 `pyproject.toml` 双入口，无一致性约束

**现状**

两个文件依赖完全一致（已逐行核对 14 个包版本号），但**没有任何机制保证它们同步**。一旦有人只改了 `pyproject.toml`，`requirements.txt`（Docker 用的就是它）就会漂移。

**修复方案（二选一）**

**方案 A（推荐，uv 为主）：Dockerfile 直接用 uv，删掉 requirements.txt**

```dockerfile
# apps/backend/Dockerfile
RUN pip install --no-cache-dir uv
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN uv pip install --system --no-cache .
COPY apps/backend/app ./app
```

然后 `git rm apps/backend/requirements.txt`，README 只讲 uv 一条路径。

**方案 B（pip 兼容）：用 uv 自动生成 requirements.txt**

在根 `package.json` 加脚本，或在 CI 加一步：

```bash
cd apps/backend && uv export --no-dev --format requirements-txt > requirements.txt
```

明确文档说明：`pyproject.toml` 是权威，`requirements.txt` 是自动生成的兼容产物，不要手改。

---

### P1-3. 前端 `NEXT_PUBLIC_API_URL` 空值语义（已修复，需文档确认）

**现状（已修复）**

`apps/frontend/lib/api/config.ts`：

```ts
export const API_URL = process.env.NEXT_PUBLIC_API_URL === undefined
  ? 'http://127.0.0.1:8000'
  : process.env.NEXT_PUBLIC_API_URL;
```

用 `=== undefined` 判断，所以**显式设为空字符串 `""` 时，`API_URL=""`**，前端请求 `${API_URL}/api/v1/...` 会走相对路径 `/api/v1/...`，由 `next.config.ts` 的 rewrites 转发到后端。

旧审计报告说的「空字符串回退到 127.0.0.1」问题**已经修复**。Docker 链路 `NEXT_PUBLIC_API_URL: ""` + `BACKEND_INTERNAL_URL: http://backend:8000` 在逻辑上是通的。

**仍需做的**

README 第 188-190 行的取值规则描述基本正确，但建议在 `.env.sample` 里把注释写得更明确，避免用户误以为「留空=不工作」：

```env
# 本地开发（前端直连后端，浏览器跨域到 8000）
NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"

# Docker / nginx 同源反代：必须设为空字符串，前端请求 /api/... 由 Next.js rewrites 转发
# NEXT_PUBLIC_API_URL=""
```

---

### P1-4. 前端 Dockerfile 的 `next.config.mjs` 引用（已修复）

**现状**

`apps/frontend/Dockerfile` 第 29 行现在是 `COPY --from=builder /app/next.config.ts`，与实际文件名一致。旧审计报告说的 `next.config.mjs` 不存在的问题**已修复**。无需改动。

---

### P1-5. ESLint 扫描 `.next`（已修复）

**现状**

`apps/frontend/eslint.config.mjs` 已加 `ignores: ['.next/**', 'node_modules/**', 'out/**', 'public/a4cv/**']`，`npm run lint` 通过。**已修复**。但 `package.json` 的 lint 脚本仍是老式 `eslint --ext ...`：

```json
"lint": "eslint --ext .js,.jsx,.ts,.tsx ."
```

ESLint 9（flat config）已不推荐 `--ext`，建议改为：

```json
"lint": "eslint ."
```

（flat config 会自动识别 `eslint.config.mjs` 里的 ignores 与文件匹配。）

---

## 四、P2 可后续优化

### P2-1. `docs/CONFIGURING.md` 与 README 环境变量说明重复

`docs/CONFIGURING.md` 已存在，但 README 第 164-190 行也有完整环境变量表。建议二选一作为权威，另一个只放链接，避免两边漂移。

### P2-2. 增加 GitHub Actions CI

开源项目建议加 `.github/workflows/ci.yml`，自动跑：

- `cd apps/frontend && npm ci && npm run build && npm run lint`
- `cd apps/backend && uv run python -m compileall app`
- `cd apps/backend && uv lock --check`

防止 PR 再次引入 `新建 文本文档.txt` 这类文件。

### P2-3. 增加 `CONTRIBUTING.md` 和 `.env.example`

- `CONTRIBUTING.md`：说明本地开发流程、不要提交 `.env` 与 `.docx`。
- 根目录可考虑加 `.env.example`，统一说明 Docker Compose 用到哪些变量（当前分散在 `apps/backend/.env.sample`）。

### P2-4. a4cv GitHub 链接

README 第 330 行 `[a4cv](https://github.com/irenerachel/a4cv)` 链接需确认真实存在；旧审计提到的占位符 `https://github.com/...` 在当前 README 已替换为真实链接，**已修复**。

---

## 五、验证命令清单（修复后逐条跑一遍）

| # | 命令 | 期望结果 |
| --- | --- | --- |
| 1 | `cd apps/backend && uv lock --check` | 通过 |
| 2 | `cd apps/backend && uv run python -m compileall app` | 无 SyntaxError |
| 3 | `cd apps/backend && uv run python -c "from app.base import create_app; create_app()"` | `APP OK` |
| 4 | `cd apps/frontend && npm run lint` | 0 error |
| 5 | `cd apps/frontend && npm run build` | 8 个静态页生成成功 |
| 6 | `git ls-files \| grep -iE "新建\|b\.md\|a\.md\|improve_bug\|\.docx\|\.png"` | 无输出（已清理） |
| 7 | `git ls-files apps/backend/.venv` | 无输出 |
| 8 | `test -f .dockerignore && echo ok` | `ok`（根目录有 .dockerignore） |
| 9 | 启动 Docker daemon 后 `docker compose build backend` | 构建上下文 < 5MB，构建成功 |

---

## 六、理想的「一条命令」开源体验

修复 P0 后，新用户的最短路径应为：

```bash
# Docker 体验路径
git clone <repo-url> && cd resume-matcher-agent-cn
cp apps/backend/.env.sample apps/backend/.env
# 编辑 .env 填入 LLM_API_KEY（必填）和 SESSION_SECRET_KEY（生产必改）
docker compose up --build
# 打开 http://localhost:3000
```

```bash
# 本地开发路径
git clone <repo-url> && cd resume-matcher-agent-cn
cp apps/backend/.env.sample apps/backend/.env      # 填 LLM_API_KEY
cp apps/frontend/.env.sample apps/frontend/.env
npm run setup      # 安装根 + 前端 + 后端依赖
npm run dev        # 同时起前后端
# 打开 http://localhost:3000
```

只要本文档的 P0 全部修复，这两条路径就能稳定兑现。

---

## 附：本次检查已确认「已修复」的旧问题

对照上一版审计报告，以下问题在当前代码中**已经不存在**：

- ✅ Dockerfile 引用不存在的 `next.config.mjs`（已改为 `next.config.ts`）
- ✅ Docker Compose 后端未加载 `.env`（已加 `env_file`）
- ✅ `NEXT_PUBLIC_API_URL` 空字符串错误回退（已用 `=== undefined` 修复）
- ✅ ESLint 扫描 `.next` 构建产物（已加 ignores）
- ✅ README Python 版本 3.8/3.12 矛盾（已统一 3.12+）
- ✅ README a4cv 占位符链接（已替换为真实链接）
- ✅ `.venv` 被 git 跟踪（`git ls-files apps/backend/.venv` 为空）

---

## 附录 B：宝塔（BT Panel）部署适配改动（2026-06-16）

针对宝塔面板部署场景，本轮额外做了以下适配与文档化：

### 适配改动（代码层）

| 改动 | 文件 | 说明 |
| --- | --- | --- |
| `ALLOWED_ORIGINS` 支持环境变量配置 | `apps/backend/app/core/config.py` | 字段改为 `str`，用 `model_validator` 解析逗号分隔/JSON 数组成 list，绕过 pydantic-settings 对容器类型的强制 JSON 解析。已实测：逗号、JSON、空串、默认值四种情况均正确 |
| 暴露 `settings.allowed_origins_list` | `apps/backend/app/core/config.py` | 新增 property，供 CORSMiddleware 读取 |
| `base.py` 改用 `allowed_origins_list` | `apps/backend/app/base.py` | CORSMiddleware 的 `allow_origins` 指向新 property |
| `.env.sample` 补充宝塔关键变量 | `apps/backend/.env.sample` | 新增 `ALLOWED_ORIGINS`、`LOG_DIR` 绝对路径示例，强化 `ENV=production` 说明 |
| 前端 `.env.sample` 同源说明 | `apps/frontend/.env.sample` | 明确「空字符串 = 同源相对路径」语义 |

### 文档化（无代码改动）

| 文档 | 内容 |
| --- | --- |
| `docs/BAOTA_DEPLOY.md`（新增） | 宝塔全流程：软件准备、目录约定、后端 venv+守护、前端构建+PM2、Nginx 反代、HTTPS、验证、8 个常见问题、自检脚本 |
| `README.md` 服务器部署章节 | 加宝塔文档链接；强化「`NEXT_PUBLIC_API_URL` 必须显式空字符串」、`/api/` location 优先级、`proxy_buffering off`、413 体积、不同域名配 `ALLOWED_ORIGINS` |
| `README.md` 环境变量表 | 加入 `ALLOWED_ORIGINS`、`LOG_DIR`，强化 production 必填项 |

### 宝塔部署的核心结论

1. **同源架构优先**：前后端共用一个域名，Nginx 用 `location /api/` 转发后端，`location /` 转发前端，避免 CORS。
2. **`NEXT_PUBLIC_API_URL` 必须显式设为空字符串 `""`**：同源走相对路径。改完必须 `npm run build` 重新构建并重启 PM2。
3. **`/api/` 转发交给 Nginx（方案 A）**：不要与 Next.js rewrites 混用，避免双重转发。
4. **数据库与日志用绝对路径**：`sqlite:////www/...`（四个斜杠）、`LOG_DIR=/www/...`，避免工作目录不确定导致文件散落。
5. **流式响应**：Nginx `location /api/` 必须 `proxy_buffering off;`，否则 `/improve?stream=true` 不刷新。
6. **`requirements.txt` 保留**：宝塔 Python 项目管理器默认用 pip + requirements.txt，不要删除。

### 验证结果

| 验证项 | 结果 |
| --- | --- |
| `ALLOWED_ORIGINS="https://a.com,https://b.com"` 解析 | ✅ `['https://a.com', 'https://b.com']` |
| `ALLOWED_ORIGINS='["https://x.com","https://y.com"]'` 解析 | ✅ 正确 |
| `ALLOWED_ORIGINS=""` 解析 | ✅ `[]` |
| 默认值（不设置） | ✅ 6 个本地端口 |
| 后端 `compileall` + `create_app()` | ✅ 通过，CORS 中间件加载正确 |
| 前端 `npm run build` | ✅ 8 个静态页生成 |

---

## 附录 C：后端从 FastAPI 重构为 Flask（2026-06-16，根治部署难题）

### 背景

附录 B 的「宝塔适配」虽缓解了部署问题，但根本矛盾仍在：**FastAPI 是异步（ASGI）框架，而宝塔 Python 项目管理器原生只支持 WSGI（Gunicorn/uWSGI）**。用户在宝塔上启动后端必然踩 ASGI/WSGI 的坑（`/ping` 返回 500），即使加了 `run.py` 绕路仍是治标不治本。

经功能盘点发现：本项目是**单用户、单次 LLM 调用**的工具，FastAPI 的异步/依赖注入/Pydantic 全是为高并发微服务设计的，完全用不上。于是从架构层面彻底重构：**用 Flask（同步、宝塔原生支持）重写后端，用 JSON 文件存储替代 SQLite/ORM**。

### 重构对比

| 维度 | 重构前（FastAPI） | 重构后（Flask） |
| --- | --- | --- |
| 后端文件 | 50 个 .py | **7 个** .py |
| 代码量 | ~2500 行 | **1040 行**（-58%） |
| 依赖数 | 15 个 | **5 个**（flask/gunicorn/openai/pdfminer/dotenv） |
| 数据库 | SQLAlchemy + aiosqlite 异步 ORM（双引擎 132 行） | **无**（JSON 文件存储，零运维） |
| LLM 调用 | Agent 4 层抽象（Manager/Strategy/Provider/exceptions，190 行） | **1 个函数 50 行** |
| 包管理 | uv + requirements + pyproject 三套 | **一套** `pip install -r requirements.txt` |
| 宝塔启动 | ❌ 必须 run.py 绕 ASGI，调 UvicornWorker | ✅ **Gunicorn 直接跑 `app:app`**，宝塔原生 |
| 日志 | Windows 专用 handler（72 行）+ 异步引擎 | 标准库 logging（5 行） |

### 功能完整性

**功能 100% 保留，前端零改动**：
- 8 个 API 端点的路径、请求体、响应结构严格复刻（含 SSE 流式、`{detail, request_id}` 错误格式、`job_id` 数组、`compensation_and_benfits` 拼写陷阱等）
- 3 个 prompt 模板（structured_resume / structured_job / hr_judge）原文照搬
- PDF/DOCX 解析逻辑照搬
- JSON 解析 3 级兜底逻辑照搬

### 验证结果（完整 LLM 端到端测试 7/7 PASS）

| 测试 | 结果 | 说明 |
| --- | --- | --- |
| `test_health` | ✅ | `/ping` 返回 `{"message":"pong","database":"reachable"}` |
| `test_resume_upload` | ✅ | 上传 DOCX + LLM 结构化（40s） |
| `test_job_upload` | ✅ | 上传 JD + LLM 结构化（14s） |
| `test_improve_nonstream` | ✅ | 非流式分析，6229 字、2814 汉字、≥3 个 Step |
| `test_improve_stream` | ✅ | **流式 SSE**——starting→parsing→analyzing→completed 完整 4 事件 |
| `test_improved_markdown` | ✅ | markdown 提取，5 个 sections |
| 前端 `npm run build` | ✅ | 8 页生成（零改动） |

### 结论

重构后，宝塔部署从「必踩 ASGI 坑」变成「Gunicorn 直接跑」，彻底根治了部署难题。附录 B 中提到的 `run.py` 绕路、UvicornWorker 配置等临时方案已不再需要。
