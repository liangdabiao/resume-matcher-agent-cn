# 前端（Next.js）

简历优化工具的前端界面。基于 Next.js 15 + React 19 + TypeScript + Tailwind CSS。

## 开发

```bash
cd apps/frontend
npm install
npm run dev          # 开发模式，http://localhost:3000
```

## 生产构建

```bash
npm run build
npm run start        # 生产模式
```

## 环境变量

复制 `.env.sample` 为 `.env`：

```env
# 同源部署（Docker / 宝塔 / nginx 反代）：必须是空字符串
NEXT_PUBLIC_API_URL=""

# 本地开发（浏览器直连后端 8000）：
# NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
```

> `NEXT_PUBLIC_*` 是构建时注入的，改了 `.env` 必须重新 `npm run build`。

## 自定义端口

默认 3000，改端口用 `-p`：

```bash
npm run dev -- -p 3001      # 开发
npm run start -- -p 3001    # 生产
```

## 目录说明

```
app/              # 页面路由（首页、上传简历、粘贴 JD、dashboard）
components/       # UI 与业务组件
lib/api/          # 后端 API 客户端
hooks/            # React hooks
public/a4cv/      # a4cv 可视化简历编辑器静态资源
```

后端 API 地址由 `lib/api/config.ts` 的 `API_URL` 决定，所有请求形如 `${API_URL}/api/v1/...`。
