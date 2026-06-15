# 简历匹配器

"简历匹配器"是一个AI驱动的平台，旨在逆向工程招聘算法，向您展示如何精准定制简历。获取那些能让你通过初步筛选、进入人工审阅阶段的关键词、格式和洞察。意思就是模拟HR怎样筛选你的简历，提前给你展示筛选的结论，方便你尽快修改好你的简历，以增加通过的可能性。

## 项目介绍

简历匹配器旨在通过分析职位描述并提供有针对性的改进建议，帮助求职者优化简历。该平台使用AI模型从简历和职位发布中提取关键信息，然后提供可操作的见解，以增加通过自动筛选系统的机会。

该应用程序由处理数据处理和AI集成的FastAPI后端，以及提供用户友好界面（操作非常简单）的Next.js前端组成，用于上传简历和职位描述。

## 核心功能

- **简历分析**：上传PDF或DOCX格式的简历进行分析
- **职位描述解析**：处理职位描述以提取关键要求和关键词
- **AI驱动的洞察**：根据职位要求获取改进建议
- **关键词匹配**：识别对ATS（申请人跟踪系统）重要的缺失关键词
- **结构化数据提取**：将非结构化的简历和职位数据转换为结构化JSON格式
- **智谱AI处理**：通过OpenAI兼容协议调用智谱大模型进行结构化抽取和简历分析

## 技术栈

| 技术 | 版本/信息 |
|------------|--------------|
| Python | 3.12+ |
| FastAPI | 0.115.12 |
| Next.js | 15+ |
| 智谱 OpenAI 兼容 API | GLM-5.1 / embedding-3 |
| SQLite | 3.x |
| Tailwind CSS | 4.x |

## 安装方法
 
 backend python项目：
```bash
   pip install -r requirements.txt
 ```

 frontend react项目：
 npm install
 npm run dev


### 后端依赖

后端基于FastAPI构建，需要以下关键依赖：
- FastAPI作为Web框架
- SQLAlchemy作为数据库ORM
- OpenAI SDK用于调用智谱OpenAI兼容API
- pdfminer.six用于PDF文本提取
- Python标准库用于DOCX文本提取

### 前端依赖

前端基于Next.js构建，使用：
- React 19
- Tailwind CSS用于样式设计
- Radix UI组件用于可访问的UI元素
- TypeScript用于类型安全

## 项目结构

### 后端 (`/backend`)

```
backend/
├── app/
│   ├── agent/          # 智谱OpenAI兼容API集成
│   ├── api/            # REST API路由和中间件
│   ├── core/           # 配置、数据库设置、日志
│   ├── models/         # 数据库模型（SQLAlchemy）
│   ├── prompt/         # AI提示模板
│   ├── schemas/        # 数据验证模式（Pydantic）
│   ├── services/       # 业务逻辑实现
│   ├── base.py         # FastAPI应用配置
│   └── main.py         # 应用程序入口点
├── Data/               # SQLite数据库文件
├── logs/               # 应用程序日志文件
├── requirements.txt    # Python依赖
└── .env                # 环境配置
```

### 前端 (`/frontend`)

```
frontend/
├── app/                # Next.js页面和布局
├── components/         # React组件
├── lib/                # 实用函数和API客户端
├── public/             # 静态资源
├── package.json        # Node.js依赖
└── tailwind.config.js  # Tailwind CSS配置
```

## API端点

### 职位端点 (`/api/v1/job`)

- `POST /upload` - 上传并处理职位描述
- `GET /` - 根据职位ID检索职位数据

### 简历端点 (`/api/v1/resume`)

- `POST /upload` - 上传并处理简历（PDF/DOCX）
- `POST /improve` - 根据职位描述获取简历改进建议

## 环境配置

在后端目录中创建一个`.env`文件，包含以下变量：

```env
SESSION_SECRET_KEY="your-secret-key"
SYNC_DATABASE_URL="sqlite:///./app.db"
ASYNC_DATABASE_URL="sqlite+aiosqlite:///./app.db"
PYTHONDONTWRITEBYTECODE=1

LLM_API_KEY="your-zhipu-api-key"
LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
LL_MODEL="glm-5.1"

EMBEDDING_API_KEY="your-zhipu-api-key"
EMBEDDING_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
EMBEDDING_MODEL="embedding-3"
```

## 运行方法

### 后端

1. 导航到后端目录：
   ```bash
   cd backend
   ```

2. 安装Python依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 运行FastAPI服务器：
   ```bash
   uvicorn app.main:app --reload
   ```

后端将在 `http://localhost:8000` 可用

### 前端

1. 导航到前端目录：
   ```bash
   cd frontend
   ```

2. 安装Node.js依赖：
   ```bash
   npm install
   # 或
   yarn install
   ```

3. 运行Next.js开发服务器：
   ```bash
   npm run dev
   # 或
   yarn dev
   ```

前端将在 `http://localhost:3000` 可用

## 数据库结构

应用程序使用SQLite，包含以下关键表：

- `resumes` - 存储原始简历内容
- `processed_resumes` - 存储结构化简历数据
- `jobs` - 存储原始职位描述内容
- `processed_jobs` - 存储结构化职位数据

## AI集成

应用程序通过OpenAI兼容协议调用智谱API，默认使用：
- **LLM**：GLM-5.1
- **Embedding**：embedding-3

AI处理包括：
1. 将简历和职位描述转换为结构化JSON格式
2. 提取关键词和关键要求
3. 根据职位要求提供改进建议

## 日志记录

应用程序使用Python内置的日志模块：
- 开发时的控制台输出
- 生产环境中的文件日志和轮转
- 基于环境的不同日志级别（本地为DEBUG，生产为INFO）


## 项目参考

代码是fork自[https://github.com/junyi-zhu/resume-ai](https://github.com/junyi-zhu/resume-ai) ， 感谢原作者。我基于他的代码进行大量修改，基本上和原来项目的功能不一样，但是适合国内用户，主要功能就是帮忙深度修改简历。

提示语的模板来自 ：【角色】洞察人心的面试官与资深HRBP (v2.0) ，不知道来源作者，是一个公众号大V写的，有知道来源请告知补充上。