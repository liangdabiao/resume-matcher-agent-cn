"""
本地开发启动入口。生产用 gunicorn app:app，不需要这个文件。

用法：
    python run.py
    python run.py --port 8001 --host 0.0.0.0
"""
import argparse

from app import app
import config


def main():
    ap = argparse.ArgumentParser(description="启动 Resume Matcher 后端（Flask）")
    ap.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    ap.add_argument("--port", type=int, default=config.BACKEND_PORT, help="端口，默认读 .env 的 BACKEND_PORT")
    args = ap.parse_args()

    print(f"[run.py] Flask 启动: http://{args.host}:{args.port}")
    print(f"[run.py] API 文档:   http://{args.host}:{args.port}/ping")
    print(f"[run.py] 生产请用:   gunicorn -w 2 -b 127.0.0.1:{args.port} app:app")

    app.run(
        host=args.host,
        port=args.port,
        debug=(config.ENV != "production"),
    )


if __name__ == "__main__":
    main()
