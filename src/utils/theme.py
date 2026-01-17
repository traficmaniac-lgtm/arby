from __future__ import annotations


def dark_theme() -> str:
    return """
    QWidget {
        background-color: #0f1115;
        color: #d0d4dc;
        font-family: "Segoe UI", "Inter", "Arial";
        font-size: 12px;
    }
    QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QTableView {
        background-color: #141821;
        border: 1px solid #232838;
        border-radius: 4px;
        padding: 4px 6px;
    }
    QPushButton {
        background-color: #1d2330;
        border: 1px solid #2b3142;
        border-radius: 4px;
        padding: 6px 10px;
    }
    QPushButton:disabled {
        color: #697184;
        background-color: #151922;
    }
    QPushButton:hover {
        background-color: #232a3a;
    }
    QHeaderView::section {
        background-color: #171c25;
        color: #aeb6c6;
        border: 1px solid #232838;
        padding: 6px;
    }
    QTableView {
        gridline-color: #222838;
        selection-background-color: #2a3550;
        selection-color: #e6e9ef;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background: #11151d;
    }
    """
