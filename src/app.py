from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6 import QtWidgets

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ui.main_window import MainWindow
from src.utils.theme import dark_theme


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ARBY Trading Terminal Lite")
    parser.add_argument("--smoke", action="store_true", help="Run headless smoke mode")
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    smoke = args.smoke or os.environ.get("ARBY_SMOKE") == "1"
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(dark_theme())
    window = MainWindow()
    if smoke:
        window.run_smoke(ticks=3)
        window.close()
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
