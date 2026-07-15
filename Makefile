.PHONY: run test lint setup-secrets run-webui dev-webui-frontend build-webui-frontend

# 启动 GUI
run:
	python -m pa_agent.main

# 启动 Web 前端后端（FastAPI，需先 build-webui-frontend 或使用 dev-webui-frontend）
run-webui:
	python start_webui.py

# 启动 Web 前端开发服务器（Vite，proxy /api /ws 到 127.0.0.1:8765）
dev-webui-frontend:
	cd pa_agent/webui/frontend && npm run dev

# 构建 Web 前端产物到 pa_agent/webui/static/pa_agent_app/
build-webui-frontend:
	cd pa_agent/webui/frontend && npm run build

# 运行测试
test:
	pytest -q

# 代码检查
lint:
	ruff check . && black --check .

# 启用 pre-commit，防止 settings / 日志 / 记录被提交
setup-secrets:
	powershell -ExecutionPolicy Bypass -File tools/setup_git_secrets.ps1
