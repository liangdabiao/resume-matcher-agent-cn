# 宝塔面板（BT Panel）部署指南

本指南针对在**宝塔 Linux 面板**上部署本项目（前端 Next.js + 后端 FastAPI + SQLite）的全流程。适用于 CentOS 7+ / Ubuntu 18+ + 宝塔面板 7.x/8.x。

> 如果你只想在本机快速体验，请看 README 的「Docker Compose」或「本地开发」章节，不必看本文。
> 本文面向的是：一台云服务器 + 一个域名 + 宝塔面板，要让外网通过域名访问。

---

## 一、部署架构（先看懂再动手）

宝塔部署推荐**同域名 + Nginx 反向代理**架构，前后端共用一个域名，避免跨域（CORS）问题：

```text
浏览器 (https://yourdomain.com)
        │
        ▼
   宝塔 Nginx (:443/:80)
        │
        ├── location / ──────► 前端 Next.js  (:3000, PM2 守护)
        └── location /api/ ──► 后端 FastAPI (:8000, Python项目管理器 守护)
                                  │
                                  └── SQLite (/www/wwwroot/resume-matcher/apps/backend/data/app.db)
```

**关键决策：`/api/` 的转发交给 Nginx，还是交给 Next.js rewrites？**

| 方案 | 谁转发 /api/ | 前端 NEXT_PUBLIC_API_URL | 推荐度 |
| --- | --- | --- | --- |
| A（推荐） | Nginx 直接转发到后端 | 空字符串 `""` | ⭐⭐⭐ 最稳，前端不参与转发 |
| B | Next.js rewrites 转发 | 空字符串 `""` | ⭐⭐ 可用，但前端 Node 进程多一层转发 |

**两种方案下前端 `NEXT_PUBLIC_API_URL` 都是空字符串**（走相对路径 `/api/...`）。区别只在 Nginx 是否单独配 `/api/` location。

> ⚠️ **不要混用**：如果 Nginx 已经配了 `location /api/`，就**不要**再依赖 Next.js rewrites 处理 `/api/`，否则可能双重转发。本文采用**方案 A**。

---

## 二、环境准备（宝塔软件商店安装）

在宝塔「软件商店」安装以下组件：

| 软件 | 版本要求 | 用途 |
| --- | --- | --- |
| **Nginx** | 1.20+ | 反向代理、HTTPS |
| **Node.js 版本管理器** | 装 Node 20 LTS | 前端构建与运行 |
| **Python 项目管理器** | 最新 | 后端运行与守护（含 Gunicorn/Uvicorn） |
| **PM2 管理器** | 最新 | 前端进程守护 |

> SQLite 无需单独安装，Python 的 `aiosqlite` 会自动创建数据库文件。

---

## 三、获取代码与目录约定

宝塔网站根目录约定在 `/www/wwwroot/`。本指南统一用：

```text
/www/wwwroot/resume-matcher/      ← 项目根目录
```

SSH 到服务器后执行：

```bash
cd /www/wwwroot
git clone <你的仓库地址> resume-matcher
cd resume-matcher
```

> 如果用宝塔「网站 → 添加站点 → Git 部署」，注意把项目克隆到 `/www/wwwroot/resume-matcher`，并确保网站运行目录指向**项目根**，而不是默认的 `public`。

---

## 四、后端部署（FastAPI）

### 4.1 配置环境变量

```bash
cd /www/wwwroot/resume-matcher/apps/backend
cp .env.sample .env
```

编辑 `.env`，**务必**修改以下项：

```env
# 生产环境，会强制校验 Key 和密钥
ENV="production"

# 【必填】改成随机字符串，生成命令：
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
SESSION_SECRET_KEY="替换成上面命令生成的随机字符串"

# 【必填】你的 OpenAI 兼容 API Key
LLM_API_KEY="sk-你的真实key"
LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
LL_MODEL="glm-5.1"

# 同源部署不需要 CORS，留空即可（默认放行本地端口，生产用不到也无害）
# ALLOWED_ORIGINS=""

# 日志目录用绝对路径，避免工作目录不确定
LOG_DIR="/www/wwwroot/resume-matcher/apps/backend/logs"

# 数据库用绝对路径，确保落到固定位置
SYNC_DATABASE_URL="sqlite:////www/wwwroot/resume-matcher/apps/backend/data/app.db"
ASYNC_DATABASE_URL="sqlite+aiosqlite:////www/wwwroot/resume-matcher/apps/backend/data/app.db"
```

> ⚠️ SQLite 的 URL 里绝对路径是**四个斜杠**：`sqlite:////www/...`（三个是协议头 `sqlite://`，第四个是绝对路径的根 `/`）。

创建数据与日志目录：

```bash
mkdir -p /www/wwwroot/resume-matcher/apps/backend/data
mkdir -p /www/wwwroot/resume-matcher/apps/backend/logs
```

### 4.2 创建 Python 虚拟环境并安装依赖

宝塔下推荐用 `python3.12`（项目要求 ≥3.12）。如果宝塔 Python 项目管理器没装 3.12，先在管理器里安装 Python 3.12。

```bash
cd /www/wwwroot/resume-matcher/apps/backend

# 用 3.12 创建虚拟环境
python3.12 -m venv .venv
source .venv/bin/activate

# 升级 pip 并安装依赖（requirements.txt 是兼容宝塔的依赖清单）
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3 验证后端可启动

```bash
# 先验证配置加载无误（ENV=production 下会校验 Key/密钥）
python -c "from app.core.config import settings; print('config OK, ENV=', settings.ENV)"

# 试启动（Ctrl+C 退出，正式守护用下面的方式）
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

看到 `Uvicorn running on http://127.0.0.1:8000` 即正常。健康检查：

```bash
curl http://127.0.0.1:8000/ping
# 期望: {"message":"pong","database":"reachable"}
```

### 4.4 用宝塔守护后端进程

**方式一：宝塔「Python 项目管理器」（推荐）**

1. 打开 Python 项目管理器 → 添加项目。
2. 填写：
   - 项目路径：`/www/wwwroot/resume-matcher/apps/backend`
   - Python 版本：3.12
   - 框架：FastAPI
   - 启动方式：Uvicorn
   - 启动文件/命令：`app.main:app`
   - 端口：`8000`
   - 绑定地址：`127.0.0.1`（仅本机，由 Nginx 反代对外）
3. 安装依赖时指向 `requirements.txt`。
4. 启动。

**方式二：手动 Gunicorn（如果 Python 项目管理器不适配）**

在项目目录建一个 `start_bt.sh`：

```bash
#!/bin/bash
cd /www/wwwroot/resume-matcher/apps/backend
source .venv/bin/activate
exec gunicorn app.main:app \
  -w 2 -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8000 \
  --timeout 300
```

> 注：gunicorn 不在默认依赖里，需 `pip install gunicorn`。Uvicorn worker 依赖项目已有的 `uvicorn`。

然后用宝塔「计划任务」或 PM2 守护：

```bash
pm2 start /www/wwwroot/resume-matcher/apps/backend/start_bt.sh --name resume-backend
pm2 save
```

---

## 五、前端部署（Next.js）

### 5.1 配置环境变量（同源关键）

```bash
cd /www/wwwroot/resume-matcher/apps/frontend
cp .env.sample .env
```

编辑 `.env`：

```env
# 同源部署：必须是空字符串，前端走相对路径 /api/...，由 Nginx 转发到后端
NEXT_PUBLIC_API_URL=""
```

> ⚠️ **空字符串和「不设置」不同**。不设置（删除该变量）会回退到 `http://127.0.0.1:8000`，导致外网浏览器去访问用户本机的 8000 端口而失败。**同源部署必须显式设为空字符串 `""`。**

### 5.2 构建生产产物

宝塔 Node 版本管理器里切换到 Node 20，然后在项目目录：

```bash
cd /www/wwwroot/resume-matcher/apps/frontend

# 安装依赖
npm install

# 构建（NEXT_PUBLIC_API_URL 在构建时被编译进产物，所以构建前 .env 必须正确）
npm run build
```

构建成功会生成 `.next/` 目录。

### 5.3 用 PM2 守护前端

```bash
cd /www/wwwroot/resume-matcher/apps/frontend
pm2 start npm --name resume-frontend -- start
pm2 save
```

或直接：

```bash
pm2 start "npm run start" --name resume-frontend --cwd /www/wwwroot/resume-matcher/apps/frontend
pm2 save
```

验证前端能访问：

```bash
curl -I http://127.0.0.1:3000
# 期望: HTTP/1.1 200 OK
```

> 设置 PM2 开机自启：`pm2 startup` + `pm2 save`。

---

## 六、Nginx 反向代理配置（核心）

宝塔「网站 → 添加站点」绑定你的域名后，进入站点「设置 → 配置文件」，**在 server 块内**插入下面两个 location（替换或补充原有配置）。

> 建议先在宝塔站点设置里申请 SSL 证书（Let's Encrypt），开启强制 HTTPS。

### 完整 server 段参考（方案 A：Nginx 转发 /api/）

```nginx
server {
    listen 80;
    # 如已配 SSL，还会有 listen 443 ssl; 和证书配置，保留宝塔生成的即可
    server_name yourdomain.com;

    # 简历上传体积，默认 1M 太小
    client_max_body_size 20M;

    # ---------- 后端 API：Nginx 直接转发 ----------
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        # LLM 流式响应可能较慢
        proxy_read_timeout 300s;
        proxy_buffering off;   # /api/v1/resumes/improve?stream=true 需要
    }

    # ---------- 前端：其余全部转 Next.js ----------
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

    # 静态资源长缓存（可选优化）
    location /_next/static/ {
        proxy_pass http://127.0.0.1:3000;
        expires 365d;
        add_header Cache-Control "public, immutable";
    }
}
```

保存后重载 Nginx：

```bash
nginx -t && nginx -s reload
```

> **为什么 `location /api/` 要写在 `location /` 前面？** Nginx 匹配 location 时，`/api/` 是前缀匹配，优先级高于 `/`，但放前面更清晰，避免被 `/` 的 rewrite 规则截获。

---

## 七、验证部署

按顺序验证，哪一步不通就查哪一步：

```bash
# 1. 后端进程在 8000
curl http://127.0.0.1:8000/ping
# → {"message":"pong","database":"reachable"}

# 2. 前端进程在 3000
curl -I http://127.0.0.1:3000
# → HTTP/1.1 200

# 3. 域名访问前端首页
curl -I https://yourdomain.com/
# → HTTP/1.1 200

# 4. 域名访问后端 API（经 Nginx 转发）
curl https://yourdomain.com/api/docs
# → 返回 Swagger HTML

# 5. 浏览器打开 https://yourdomain.com ，上传简历测试全流程
```

---

## 八、常见问题（宝塔专项）

### Q1：前端页面打开正常，但点「开始优化」报错 / 一直转圈

**最常见原因：前端 `.env` 的 `NEXT_PUBLIC_API_URL` 没设成空字符串，或没重新构建。**

- `NEXT_PUBLIC_*` 是**构建时**注入的，改了 `.env` 必须 `npm run build` 重构并重启 PM2。
- 检查：浏览器 F12 → Network，看请求的 URL。如果是 `http://127.0.0.1:8000/api/...`，说明回退到了本机地址，需把 `.env` 设为 `NEXT_PUBLIC_API_URL=""` 后重新 `npm run build` + `pm2 restart resume-frontend`。

### Q2：浏览器控制台报 CORS 错误

同源部署不该出现 CORS。如果出现，说明你用了**方案 B 的混合**或前端访问了非同源后端。解决：

- 同源部署：确保走域名访问，前端 `NEXT_PUBLIC_API_URL=""`。
- 若确实前后端不同域名：在后端 `.env` 配 `ALLOWED_ORIGINS="https://前端域名"`，重启后端。

### Q3：后端启动报 `ENV=production 时 LLM_API_KEY 不能为空` 或 `SESSION_SECRET_KEY 必须改成随机字符串`

这是项目的生产环境保护机制。检查后端 `.env`：
- `LLM_API_KEY` 必须非空。
- `SESSION_SECRET_KEY` 不能是默认值 `change-me`，用 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成新值。

改完重启后端进程。

### Q4：上传简历报 413 Request Entity Too Large

Nginx 默认限制请求体 1M。在 Nginx server 块加 `client_max_body_size 20M;`（见第六章配置），重载 Nginx。

### Q5：流式响应（`improve?stream=true`）不刷新 / 一次性返回

Nginx 缓冲了流式响应。在 `location /api/` 加 `proxy_buffering off;`（见第六章配置）。

### Q6：app.db 文件找不到 / 数据库写入报权限错误

- 用**绝对路径**配置 `SYNC_DATABASE_URL` / `ASYNC_DATABASE_URL`（四个斜杠）。
- 确保数据目录可写：
  ```bash
  chown -R www:www /www/wwwroot/resume-matcher/apps/backend/data
  chmod -R 755 /www/wwwroot/resume-matcher/apps/backend/data
  ```
  （宝塔 Web 进程用户一般是 `www`，按实际情况调整。）

### Q7：PM2 重启后进程起不来

- 用 `pm2 logs resume-frontend` / `pm2 logs resume-backend` 看日志。
- 确认 Node 版本是 20+：`pm2` 可能用了系统默认 Node，用 `pm2 install node` 或在启动时指定解释器。

### Q8：更新代码后如何生效

```bash
cd /www/wwwroot/resume-matcher
git pull

# 后端：依赖若变化需重装
cd apps/backend && source .venv/bin/activate && pip install -r requirements.txt
pm2 restart resume-backend

# 前端：依赖若变化需重装 + 必须重新构建
cd ../frontend && npm install && npm run build
pm2 restart resume-frontend
```

---

## 九、更新后的目录结构速查

```text
/www/wwwroot/resume-matcher/
├── apps/
│   ├── backend/
│   │   ├── .env                 # ← 生产配置（ENV=production + Key）
│   │   ├── .venv/               # ← Python 虚拟环境
│   │   ├── requirements.txt     # ← 宝塔用这个装依赖
│   │   ├── data/app.db          # ← SQLite 数据库（绝对路径指向这里）
│   │   ├── logs/                # ← 日志（绝对路径指向这里）
│   │   └── app/
│   └── frontend/
│       ├── .env                 # ← NEXT_PUBLIC_API_URL=""
│       ├── .next/               # ← 构建产物
│       └── ...
└── docs/BAOTA_DEPLOY.md         # ← 本文档
```

---

## 十、一键自检脚本（可选）

把下面存为 `/www/wwwroot/resume-matcher/check_bt.sh`，部署完跑一遍：

```bash
#!/bin/bash
set -e
echo "== 后端 /ping =="
curl -s http://127.0.0.1:8000/ping && echo
echo "== 前端首页 =="
curl -sI http://127.0.0.1:3000 | head -1
echo "== PM2 进程 =="
pm2 list | grep -E "resume-frontend|resume-backend"
echo "== 数据库文件 =="
ls -lh /www/wwwroot/resume-matcher/apps/backend/data/app.db
echo "== 完成 =="
```

```bash
chmod +x check_bt.sh && ./check_bt.sh
```
