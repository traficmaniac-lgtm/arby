from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class Toast(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget, message: str, timeout_ms: int = 3000) -> None:
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.ToolTip)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        label = QtWidgets.QLabel(message)
        layout.addWidget(label)

        self.setStyleSheet(
            "QFrame {"
            "background-color: #1c2230;"
            "border: 1px solid #2a3345;"
            "border-radius: 6px;"
            "color: #e3e7ef;"
            "}"
        )
        self.adjustSize()
        self._timer.start(timeout_ms)

    def show_at_bottom_right(self, margin: int = 16) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        parent_rect = parent.geometry()
        x = parent_rect.right() - self.width() - margin
        y = parent_rect.bottom() - self.height() - margin
        self.move(x, y)
        self.show()
