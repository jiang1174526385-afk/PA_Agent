"""启动 PA Agent Web 前端（FastAPI + React SPA）。

用法：
    python start_webui.py [--host 127.0.0.1] [--port 8765] [--reload]

默认只绑定 127.0.0.1（单用户本地使用，不引入鉴权/多用户支持）。
"""

from __future__ import annotations

import argparse
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
os.chdir(_here)


def main() -> int:
    import uvicorn

    parser = argparse.ArgumentParser(description="启动 PA Agent Web 前端")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "pa_agent.webui.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
