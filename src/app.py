from __future__ import annotations

import sys

from PySide6 import QtWidgets

from src.ui.main_window import MainWindow
from src.utils.theme import dark_theme


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(dark_theme())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
