from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

from app.ai.usage import AIUsageManager
from app.utils.config import RuntimeSettings


class AIUsageDialog(QDialog):
    def __init__(self, usage: AIUsageManager, runtime: RuntimeSettings, provider: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI 使用记录")
        self.resize(650, 390)
        status = usage.status()
        limit = "已禁用" if not status.cloud_enabled else f"{status.today_count} / {status.daily_limit}"
        summary = QLabel(
            f"今天：{limit}\n本月：{status.month_count}\n当前 Provider：{provider}\n当前模型：{runtime.gemini_model}\n\n这是本地安全上限，并不代表 Google 官方实时剩余额度。"
        )
        summary.setWordWrap(True)
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["时间", "Provider", "模型", "结果", "Token（如 SDK 返回）"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        for event in usage.recent_events(20):
            row = table.rowCount()
            table.insertRow(row)
            tokens = "/".join(str(value) for value in (event.get("input_tokens"), event.get("output_tokens"), event.get("total_tokens")) if value is not None) or "—"
            for column, value in enumerate((event.get("time", ""), event.get("provider", ""), event.get("model", ""), event.get("result", ""), tokens)):
                table.setItem(row, column, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()
        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        layout.addWidget(table, 1)
