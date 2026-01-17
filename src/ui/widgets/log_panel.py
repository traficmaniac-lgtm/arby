from __future__ import annotations

import time

from PySide6 import QtWidgets


class LogPanel(QtWidgets.QTabWidget):
    def __init__(self) -> None:
        super().__init__()
        self._all_logs = self._build_view()
        self._signals = self._build_view()
        self._errors = self._build_view()
        self.addTab(self._all_logs, "Logs")
        self.addTab(self._signals, "Signals")
        self.addTab(self._errors, "Errors")

    def append(self, level: str, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {level} {message}"
        self._all_logs.appendPlainText(line)
        if level == "SIGNAL":
            self._signals.appendPlainText(line)
        if level == "ERROR":
            self._errors.appendPlainText(line)

    def _build_view(self) -> QtWidgets.QPlainTextEdit:
        view = QtWidgets.QPlainTextEdit()
        view.setReadOnly(True)
        return view
