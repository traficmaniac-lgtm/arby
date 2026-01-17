from __future__ import annotations

import time

from PySide6 import QtGui, QtWidgets


class LogPanel(QtWidgets.QTabWidget):
    def __init__(self) -> None:
        super().__init__()
        self._all_logs = self._build_view()
        self._signals = self._build_view()
        self._errors = self._build_view()
        self._counts = {"Logs": 0, "Signals": 0, "Errors": 0}
        self.addTab(self._all_logs, "Logs(0)")
        self.addTab(self._signals, "Signals(0)")
        self.addTab(self._errors, "Errors(0)")
        self._max_lines = 5000

        actions = QtWidgets.QWidget()
        actions_layout = QtWidgets.QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        self._clear_button = QtWidgets.QPushButton("Clear")
        self._copy_button = QtWidgets.QPushButton("Copy")
        actions_layout.addWidget(self._clear_button)
        actions_layout.addWidget(self._copy_button)
        self.setCornerWidget(actions)

        self._clear_button.clicked.connect(self._clear_current)
        self._copy_button.clicked.connect(self._copy_current)

    def append(self, level: str, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {level} {message}"
        self._append_line(self._all_logs, line, level)
        self._counts["Logs"] += 1
        if level == "SIGNAL":
            self._append_line(self._signals, line, level)
            self._counts["Signals"] += 1
        if level == "ERROR":
            self._append_line(self._errors, line, level)
            self._counts["Errors"] += 1
        self._update_tab_titles()

    def _build_view(self) -> QtWidgets.QTextEdit:
        view = QtWidgets.QTextEdit()
        view.setReadOnly(True)
        view.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        return view

    def _append_line(self, view: QtWidgets.QTextEdit, line: str, level: str) -> None:
        cursor = view.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        fmt = QtGui.QTextCharFormat()
        if level == "ERROR":
            fmt.setForeground(QtGui.QColor(196, 92, 92))
        elif level == "SIGNAL":
            fmt.setForeground(QtGui.QColor(120, 204, 146))
        else:
            fmt.setForeground(QtGui.QColor(160, 166, 178))
        cursor.insertText(line + "\n", fmt)
        view.setTextCursor(cursor)
        self._trim_lines(view)

    def _trim_lines(self, view: QtWidgets.QTextEdit) -> None:
        doc = view.document()
        while doc.blockCount() > self._max_lines:
            cursor = QtGui.QTextCursor(doc)
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.select(QtGui.QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _update_tab_titles(self) -> None:
        self.setTabText(0, f"Logs({self._counts['Logs']})")
        self.setTabText(1, f"Signals({self._counts['Signals']})")
        self.setTabText(2, f"Errors({self._counts['Errors']})")

    def _current_view(self) -> QtWidgets.QTextEdit:
        widget = self.currentWidget()
        if isinstance(widget, QtWidgets.QTextEdit):
            return widget
        return self._all_logs

    def _clear_current(self) -> None:
        current = self._current_view()
        current.clear()
        if current == self._all_logs:
            self._counts["Logs"] = 0
        elif current == self._signals:
            self._counts["Signals"] = 0
        elif current == self._errors:
            self._counts["Errors"] = 0
        self._update_tab_titles()

    def _copy_current(self) -> None:
        current = self._current_view()
        QtWidgets.QApplication.clipboard().setText(current.toPlainText())
