"""PA Agent GUI package.

Legacy / reference implementation (PyQt6 desktop UI). As of the
docs/webui_migration/ project's completion, `pa_agent/webui/` (FastAPI +
React) is the primary, actively-developed interactive entry point and has
reached full functional parity with this package plus a new trade-record
analysis report page. This package remains supported and independently
runnable (`python -m pa_agent.main`), and its core business logic
(orchestrator/data/indicators/records/notify) is shared with and called by
the web layer unmodified -- but no new user-facing features are planned here;
new functionality is implemented in `pa_agent/webui/` only. See
docs/webui_migration/README.md and
docs/webui_migration/final-acceptance-report.md for the migration history and
final acceptance record.
"""

from pa_agent.gui.main_window import MainWindow
from pa_agent.gui.settings_dialog import SettingsDialog
from pa_agent.gui.chart_widget import ChartWidget
from pa_agent.gui.decision_panel import DecisionPanel
from pa_agent.gui.conversation_widget import ConversationWidget
from pa_agent.gui.debug_widget import DebugWidget

__all__ = [
    "MainWindow",
    "SettingsDialog",
    "ChartWidget",
    "DecisionPanel",
    "ConversationWidget",
    "DebugWidget",
]
