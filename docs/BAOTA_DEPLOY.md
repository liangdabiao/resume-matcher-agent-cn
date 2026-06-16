# 宝塔面板（BT Panel）部署指南

> 目标：clone 下来，按本文填几个框就能跑，**不需要懂 Python、不需要装数据库**。
> 适合 CentOS 7+ / Ubuntu 18+ + 宝塔面板。
> 后端是标准 Flask，宝塔原生支持，**无任何 ASGI/WSGI 配置坑**。

---

## 架构（30 秒看懂）

```text
浏览器 (https://你的域名)
      │
  宝塔 Nginx (:443)
      ├── /     ──► 前端 Next.js  (:3000, Node + PM2)
      └── /api/ ──► 后端 Flask    (:8000, Python项目管理器/Gunicorn)
                        └── JSON 文件存储（无需安装数据库）
```

前后端**共用一个域名**，Nginx 转发，没有跨域问题。**没有数据库**，简历和 JD 存成 JSON 文件，零运维。

---

## 第一步：装软件（宝塔软件商店）

在宝塔「软件商店」安装：

| 软件 | 版本 | 干嘛用的 |
| --- | --- | --- |
| **Nginx** | 任意 | 反向代理 |
| **Node.js 版本管理器** | 装 Node 20 | 跑前端 |
| **Python 项目管理器** | 最新 | 跑后端（Flask 原生支持） |

> 不需要安装 MySQL/Redis/任何数据库。

---

## 第二步：拉代码

SSH 登录服务器：

```bash
cd /www/wwwroot
git clone <你的仓库地址> resume-matcher
```

---

## 第三步：配置后端（只改 3 行）

```bash
cd /www/wwwroot/resume-matcher/apps/backend
cp .env.sample .env
```

编辑 `.env`，**只改这 3 行**（其余保持默认）：

```env
ENV="production"
LLM_API_KEY="sk-你的真实key"
SESSION_SECRET_KEY="随便一串随机字符，别用默认的change-me"
```

> `SESSION_SECRET_KEY` 生成方法：`python -c "import secrets; print(secrets.token_urlsafe(32))"`

存储路径**全部不用配**——后端用 JSON 文件，自动存在 `apps/backend/data/` 目录。

---

## 第四步：宝塔启动后端（最简单）

打开宝塔「**Python 项目管理器**」→ 添加项目：

| 字段 | 填什么 |
| --- | --- |
| 项目名称 | `resume-backend` |
| 路径 | `/www/wwwroot/resume-matcher/apps/backend` |
| Python 版本 | **3.12**（没有就先在管理器里装） |
| 框架 | **Flask** |
| 启动文件/模块 | **`app:app`** |
| 启动方式 | **Gunicorn** |
| 端口 | `8000` |
| 安装依赖 | 勾选，指向 `requirements.txt` |

点「启动」。**就这一步，没有任何 worker class / ASGI 配置**——因为 Flask 是同步框架，Gunicorn 原生支持。

> 如果宝塔面板里「Flask + Gunicorn」选项不直接可见，按通用方式：框架选 Flask，启动模块填 `app:app`，让宝塔自动用 Gunicorn 启动即可。

### 备选：PM2 守护（如果你的宝塔版本 Python 管理器不好用）

```bash
cd /www/wwwroot/resume-matcher/apps/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 用 PM2 跑 Gunicorn
pm2 start "gunicorn -w 2 -b 127.0.0.1:8000 --timeout 300 app:app" \
    --name resume-backend \
    --cwd /www/wwwroot/resume-matcher/apps/backend
pm2 save
pm2 startup
```

---

## 第五步：验证后端

```bash
curl http://127.0.0.1:8000/ping
```

**期望返回**：
```json
{"message":"pong","database":"reachable"}
```

> 注意：`database` 字段在新版里恒为 `"reachable"`（因为用 JSON 文件存储，没有真正的数据库连接），这是正常的，代表存储就绪。

如果连不上：
- 看进程：`ss -tlnp | grep 8000`，应显示 `gunicorn` 在听。
- 看日志：Python 项目管理器面板有日志按钮，或 `pm2 logs resume-backend`。

---

## 第六步：构建并启动前端

宝塔 Node 版本管理器切换到 **Node 20**，SSH：

```bash
cd /www/wwwroot/resume-matcher/apps/frontend
cp .env.sample .env
```

**编辑 `.env`，确认这一行**（同源部署必须是空字符串）：

```env
NEXT_PUBLIC_API_URL=""
```

> ⚠️ 空字符串 `""` 不能删掉。删掉会回退到 `http://127.0.0.1:8000`，导致外网浏览器访问用户自己电脑的 8000 端口而失败。

构建并启动：

```bash
npm install
npm run build

pm2 start "npm run start" --name resume-frontend --cwd /www/wwwroot/resume-matcher/apps/frontend
pm2 save
```

验证：
```bash
curl -I http://127.0.0.1:3000
# 期望: HTTP/1.1 200 OK
```

### 想换前端端口？（比如 3000 被占用，用 3001）

```bash
pm2 delete resume-frontend
pm2 start "npm run start -- -p 3001" --name resume-frontend --cwd /www/wwwroot/resume-matcher/apps/frontend
```
然后第七步 Nginx 里 `proxy_pass` 端口也改成 3001。

---

## 第七步：配置 Nginx 反向代理

宝塔「网站 → 添加站点」绑定域名后，进站点「设置 → 配置文件」，在 `server { }` 块加入：

> 建议先在站点设置里申请 SSL 证书，开启强制 HTTPS。

```nginx
server {
    listen 80;
    # 已配 SSL 的还有 listen 443 ssl; 和证书配置，保留宝塔生成的
    server_name 你的域名;

    # 简历上传体积
    client_max_body_size 20M;

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_read_timeout 300s;
        proxy_buffering off;   # 流式响应必须关
    }

    # 前端（其余全部）
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

保存后重载：
```bash
nginx -t && nginx -s reload
```

---

## 第八步：完成验证

浏览器打开 `https://你的域名`，上传简历 → 粘贴 JD → 点「开始优化」。

或命令行逐项验证：
```bash
curl https://你的域名/              # 前端首页 200
curl https://你的域名/api/docs 2>nul || curl https://你的域名/ping   # 后端响应
```

---

## 常见问题

### 1. 后端 `/ping` 返回 `Internal Server Error`

检查 8000 上是什么进程：`ss -tlnp | grep 8000`
- 显示 `gunicorn` → 正常，看后端日志找具体错误（多半是 `.env` 的 Key 没填）。
- 显示 `uwsgi` → 错误，宝塔用了 WSGI 模式；确认 Python 项目管理器里框架选 **Flask**、启动方式 **Gunicorn**。

### 2. 后端启动失败：提示 `LLM_API_KEY 不能为空` / `SESSION_SECRET_KEY 必须改成随机字符串`

`.env` 里 `ENV="production"` 但 Key 没填或密钥是默认值。改 `.env` 后重启后端。

### 3. 前端页面能打开，但点「开始优化」报错/转圈

`NEXT_PUBLIC_API_URL` 没设成空字符串，或改了没重新构建：
```bash
cd /www/wwwroot/resume-matcher/apps/frontend
# 确认 .env 里 NEXT_PUBLIC_API_URL=""
npm run build
pm2 restart resume-frontend
```

### 4. 上传简历报 `413 Request Entity Too Large`

Nginx 默认限 1M。第七步配置里有 `client_max_body_size 20M;`，确认加了，`nginx -s reload`。

### 5. 「开始优化」进度条不刷新（流式响应失效）

Nginx 缓冲了流。第七步 `location /api/` 里要有 `proxy_buffering off;`。

### 6. 数据存在哪？怎么备份？

JSON 文件存在 `apps/backend/data/` 目录：
```text
data/
├── resumes/<uuid>.json   # 每份简历一个文件
└── jobs/<uuid>.json      # 每个 JD 一个文件
```
备份直接打包这个目录即可：`tar czf backup.tar.gz apps/backend/data/`

### 7. 更新代码后如何生效

```bash
cd /www/wwwroot/resume-matcher
git pull

# 后端（依赖没变就只需重启）
cd apps/backend && pip install -r requirements.txt
pm2 restart resume-backend    # 或宝塔面板重启

# 前端（必须重新构建）
cd ../frontend && npm install && npm run build
pm2 restart resume-frontend
```

---

## 目录结构速查

```text
/www/wwwroot/resume-matcher/
├── apps/
│   ├── backend/
│   │   ├── .env              # 第三步配置的
│   │   ├── app.py            # Flask 应用 ← 宝塔启动模块 app:app
│   │   ├── requirements.txt  # 宝塔装依赖用
│   │   ├── data/             # JSON 存储（自动生成，无需配置）
│   │   │   ├── resumes/
│   │   │   └── jobs/
│   │   └── logs/
│   └── frontend/
│       ├── .env              # NEXT_PUBLIC_API_URL=""
│       └── .next/            # 构建产物
└── docs/BAOTA_DEPLOY.md      # 本文档
```
