from __future__ import annotations

import sys
from pathlib import Path

from PySide6 import QtWidgets

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

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
