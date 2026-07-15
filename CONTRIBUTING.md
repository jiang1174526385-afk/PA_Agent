# 参与贡献

感谢你对 PA Agent 的关注。本项目欢迎 Issue 与 Pull Request。

## 开发环境

Web 端（`pa_agent/webui/`，主要入口）是本项目当前的主要开发面；`pa_agent/gui/`（PyQt6 桌面端）保留为 legacy 参考实现，独立可运行，但不再新增功能。

1. Windows 10/11，Python 3.11+
2. 安装 MetaTrader 5 并登录（用于真实 K 线联调；Web 端也可用 TradingView/OKX 等无需 MT5 的数据源开发）
3. 克隆仓库后：

   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev]"
   copy config\settings.example.json config\settings.json
   cd pa_agent\webui\frontend && npm install && cd ..\..\..
   ```

4. 在 Web 端（或 GUI）**设置** 中配置 API Key，或仅跑不依赖网络的测试。
5. Web 端前后端联调：`make run-webui`（后端 + 已构建前端）或 `make dev-webui-frontend`（前端热重载，需另开终端跑 `make run-webui`）。

## 提交代码前

```cmd
pytest -m "not e2e"
ruff check pa_agent tests
```

若改动了 `pa_agent/webui/frontend/`，额外跑：

```cmd
cd pa_agent/webui/frontend
npx tsc --noEmit
npx vitest run
npm run build
```

涉及浏览器可见行为的改动，建议再跑一次 Playwright 端到端测试（`.venv` 内）：

```cmd
pytest tests/webui/e2e/ --browser chromium
```

（若已安装 `black`，可按团队习惯格式化。）

## 请勿提交

- `config/settings.json`、`config/exception_state.json`
- `logs/`、`records/pending/`、`experience/` 下的运行数据
- 任何 API Key、`.env`、私钥文件

启用本地 pre-commit 钩子：

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_git_secrets.ps1
```

## Pull Request 建议

- 一个 PR 聚焦一类改动（功能 / 修复 / 文档）
- 说明动机与测试方式
- 若改 JSON schema、提示词或路由，请补充或更新 `tests/` 中相关用例

## 问题反馈

- Bug：附上日志片段（`logs/pa_agent.log`）、复现步骤、品种/周期
- 功能建议：说明使用场景与期望行为

讨论与交流也可加入 README 中的 QQ 群。
