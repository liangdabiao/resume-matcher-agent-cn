import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from .win_rotating_file_handler import WindowsSafeRotatingFileHandler
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator, field_validator
from typing import List, Optional, Literal


class Settings(BaseSettings):
    # The defaults here are just hardcoded to have 'something'. The main place to set defaults is in apps/backend/.env.sample,
    # which is copied to the user's .env file upon setup.
    PROJECT_NAME: str = "Resume Matcher"
    FRONTEND_PATH: str = os.path.join(os.path.dirname(__file__), "frontend", "assets")
    # CORS 允许的来源（原始配置值，支持逗号分隔或 JSON 数组字符串）。
    # 宝塔/服务器同源反代部署时，浏览器经 nginx 同源访问后端，不需要 CORS，
    # 此时留空或不设置即可；仅当前端用独立域名/端口访问后端时才需要填。
    # 示例：
    #   ALLOWED_ORIGINS="https://example.com,https://www.example.com"
    #   ALLOWED_ORIGINS='["https://example.com","https://www.example.com"]'
    ALLOWED_ORIGINS: str = ",".join([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ])
    DB_ECHO: bool = False
    PYTHONDONTWRITEBYTECODE: int = 1
    SYNC_DATABASE_URL: str = "sqlite:///./app.db"
    ASYNC_DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    SESSION_SECRET_KEY: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    LL_MODEL: str = "glm-5.1"
    LOG_DIR: str = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "logs")
    # 添加ENV属性，默认使用local环境
    ENV: Literal["production", "staging", "local"] = "local"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",  # 容忍 .env 中遗留的未声明字段
    )

    @model_validator(mode="after")
    def _resolve_allowed_origins(self):
        """
        把 ALLOWED_ORIGINS（str）解析成真正的列表，供 CORSMiddleware 使用。
        字段声明为 str 而非 List[str]，是为了绕过 pydantic-settings 对容器类型
        字段强制做 json.loads 解析（普通逗号字符串会被当成非法 JSON 报错）。
        支持：
          - 逗号分隔："https://a.com,https://b.com"
          - JSON 数组：'["https://a.com","https://b.com"]'
          - 空字符串：表示不限制来源（返回空列表，CORS 中间件再处理）
        """
        import json as _json
        raw = (self.ALLOWED_ORIGINS or "").strip()
        parsed: List[str] = []
        if raw:
            if raw.startswith("["):
                try:
                    parsed = [s.strip() for s in _json.loads(raw) if isinstance(s, str) and s.strip()]
                except _json.JSONDecodeError:
                    parsed = [s.strip() for s in raw.split(",") if s.strip()]
            else:
                parsed = [s.strip() for s in raw.split(",") if s.strip()]
        # resolved list
        object.__setattr__(self, "_allowed_origins_list", parsed)
        return self

    @property
    def allowed_origins_list(self) -> List[str]:
        """解析后的 CORS 来源列表，供 CORSMiddleware 使用。"""
        return getattr(self, "_allowed_origins_list", [])

    @model_validator(mode="after")
    def _validate_runtime_required(self):
        """
        生产环境（ENV=production）下做最小启动校验，避免空 Key / 默认密钥
        静默启动后所有 LLM 流程直接 500。本地 / staging 不强制，方便开发。
        """
        if self.ENV == "production":
            if not self.LLM_API_KEY:
                raise ValueError(
                    "ENV=production 时 LLM_API_KEY 不能为空，"
                    "请在 apps/backend/.env 或容器环境变量中填写有效的 OpenAI 兼容 API Key。"
                )
            if not self.SESSION_SECRET_KEY or self.SESSION_SECRET_KEY == "change-me":
                raise ValueError(
                    "ENV=production 时 SESSION_SECRET_KEY 必须改成随机字符串，"
                    "不能使用 .env.sample 里的默认值 change-me。"
                )
        return self


settings = Settings()


_LEVEL_BY_ENV: dict[Literal["production", "staging", "local"], int] = {
    "production": logging.INFO,
    "staging": logging.DEBUG,
    "local": logging.DEBUG,
}


# 初始化logger
def setup_logging() -> None:
    """
    Configure the root logger exactly once,

    * Console only (StreamHandler -> stderr)
    * ISO - 8601 timestamps
    * Env - based log level: production -> INFO, else DEBUG
    * Prevents duplicate handler creation if called twice
    """
    root = logging.getLogger()
    if root.handlers:
        return

    # 确保使用正确的环境变量，防止属性不存在的错误
    env = getattr(settings, "ENV", "local").lower()
    level = _LEVEL_BY_ENV.get(env, logging.DEBUG)

    formatter = logging.Formatter(
        fmt="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # File handler - Create log directory if it doesn't exist
    try:
        # 确保日志目录存在
        log_dir = settings.LOG_DIR
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "resume_matcher.log")
        # 简化日志文件创建过程，直接创建空文件
        with open(log_file, 'a') as f:
            f.write("[LOG INIT] Log file initialized\n")
        # 在Windows环境下使用自定义的安全日志轮转处理器
        file_handler = WindowsSafeRotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10 MB per file
            backupCount=5,          # Keep up to 5 backup files
            encoding="utf-8",
            max_attempts=5,         # 最大尝试次数
            attempt_delay=0.3       # 每次尝试间隔0.3秒
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
        # 使用root logger记录日志
        root.info(f"Log file created at {log_file}")
    except Exception as e:
        # If file logging fails, continue with console logging only
        print(f"Failed to set up file logging: {e}", file=sys.stderr)

    root.setLevel(level)
    # 设置不需要记录详细DEBUG日志的模块
    for noisy in ("sqlalchemy.engine", "uvicorn.access", "aiosqlite", "pdfminer", "python_multipart.multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
