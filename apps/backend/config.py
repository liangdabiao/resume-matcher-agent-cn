"""
极简配置。用 os.getenv + python-dotenv，不要 pydantic-settings。
所有默认值都保证：没有 .env 也能跑（零配置）。
"""
import os

from dotenv import load_dotenv

# 加载 .env（找不到也不报错）
load_dotenv()


def _strip_quotes(value):
    """
    去掉环境变量值两端的引号。
    python-dotenv 加载 .env 文件时会自动去引号，但 docker-compose 的 env_file
    是直接注入环境变量、不经 dotenv 处理，会保留引号（如 ENV="production" 实际值
    是带引号的字符串）。这里统一兼容两种来源。
    """
    if value is None:
        return value
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value

# 项目根目录（apps/backend/），数据/日志用绝对路径，宝塔下不会散落
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = _strip_quotes(os.getenv("LOG_DIR")) or os.path.join(BASE_DIR, "logs")

# 运行环境：local / production
ENV = _strip_quotes(os.getenv("ENV", "local")).lower()

# LLM 配置（核心）
LLM_API_KEY = _strip_quotes(os.getenv("LLM_API_KEY", ""))
LLM_BASE_URL = _strip_quotes(os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"))
# 兼容 LLM_MODEL（标准命名）与 LL_MODEL（历史命名）。
# 推荐新配置用 LLM_MODEL，老 .env 用 LL_MODEL 也能跑。
LL_MODEL = (
    _strip_quotes(os.getenv("LLM_MODEL"))
    or _strip_quotes(os.getenv("LL_MODEL"))
    or "glm-5.1"
)

# Session 密钥（保留以备未来 Flask-Session 扩展；当前未使用）
SESSION_SECRET_KEY = _strip_quotes(os.getenv("SESSION_SECRET_KEY", "change-me"))

# 后端端口
try:
    BACKEND_PORT = int(_strip_quotes(os.getenv("BACKEND_PORT", "8000")))
except (TypeError, ValueError):
    BACKEND_PORT = 8000

# CORS 来源（逗号分隔）。同源反代部署留空即可。
_origins_raw = _strip_quotes(os.getenv("ALLOWED_ORIGINS", "")) or ""
if _origins_raw.strip():
    ALLOWED_ORIGINS = [s.strip() for s in _origins_raw.split(",") if s.strip()]
else:
    # 默认放行本地开发端口
    ALLOWED_ORIGINS = [
        f"http://localhost:{p}" for p in (3000, 3001, 3002)
    ] + [f"http://127.0.0.1:{p}" for p in (3000, 3001, 3002)]

# 子目录（启动时自动创建）
RESUMES_DIR = os.path.join(DATA_DIR, "resumes")
JOBS_DIR = os.path.join(DATA_DIR, "jobs")
for _d in (DATA_DIR, RESUMES_DIR, JOBS_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)


def check_production():
    """生产环境启动校验，避免空 Key / 默认密钥静默启动。"""
    if ENV == "production":
        if not LLM_API_KEY:
            raise SystemExit(
                "[config] ENV=production 时 LLM_API_KEY 不能为空，请在 .env 填写。"
            )
        if not SESSION_SECRET_KEY or SESSION_SECRET_KEY == "change-me":
            raise SystemExit(
                "[config] ENV=production 时 SESSION_SECRET_KEY 必须改成随机字符串。"
            )
