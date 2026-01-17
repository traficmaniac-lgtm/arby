from __future__ import annotations

import time
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..core.controller import FilterSettings, RadarController
from ..models.radar_model import RadarModel


class PairFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self._search_text = ""

    def set_search_text(self, text: str) -> None:
        self._search_text = text.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        if not self._search_text:
            return True
        index = self.sourceModel().index(source_row, 0, source_parent)
        pair = self.sourceModel().data(index, QtCore.Qt.DisplayRole)
        return self._search_text in str(pair).lower()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ARBY Trading Terminal Lite")
        self.resize(1200, 800)

        self._model = RadarModel()
        self._proxy = PairFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self._log_view = QtWidgets.QPlainTextEdit()
        self._log_view.setReadOnly(True)

        self._controller = RadarController(self._model, self._append_log)
        self._controller.updated.connect(self._on_updated)

        self._setup_ui()
        self._apply_defaults()

    def _setup_ui(self) -> None:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.addLayout(self._build_control_bar())

        table_group = QtWidgets.QGroupBox("Arbitrage Radar")
        table_layout = QtWidgets.QVBoxLayout(table_group)
        self._table = QtWidgets.QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(5, QtCore.Qt.DescendingOrder)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table_layout.addWidget(self._table)
        layout.addWidget(table_group, 1)

        log_group = QtWidgets.QGroupBox("Log")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        log_layout.addWidget(self._log_view)
        layout.addWidget(log_group, 0)

        self.setCentralWidget(container)

    def _build_control_bar(self) -> QtWidgets.QHBoxLayout:
        bar = QtWidgets.QHBoxLayout()

        self._start_button = QtWidgets.QPushButton("Start")
        self._stop_button = QtWidgets.QPushButton("Stop")
        self._stop_button.setEnabled(False)
        self._start_button.clicked.connect(self._on_start)
        self._stop_button.clicked.connect(self._on_stop)

        self._top_n = QtWidgets.QComboBox()
        self._top_n.addItems(["30", "50", "70", "All"])

        self._min_profit = QtWidgets.QComboBox()
        self._min_profit.addItems(["0.2", "0.5", "1.0", "Custom"])
        self._min_profit_custom = QtWidgets.QLineEdit()
        self._min_profit_custom.setPlaceholderText("Custom %")
        self._min_profit_custom.setEnabled(False)

        self._min_volume = QtWidgets.QComboBox()
        self._min_volume.addItems(["50k", "100k", "250k", "Custom"])
        self._min_volume_custom = QtWidgets.QLineEdit()
        self._min_volume_custom.setPlaceholderText("Custom volume")
        self._min_volume_custom.setEnabled(False)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search: BTC/USDT")

        for widget in [
            self._top_n,
            self._min_profit,
            self._min_profit_custom,
            self._min_volume,
            self._min_volume_custom,
            self._search,
        ]:
            widget.textChanged.connect(self._update_filters)

        self._min_profit.currentTextChanged.connect(self._toggle_custom_profit)
        self._min_volume.currentTextChanged.connect(self._toggle_custom_volume)
        self._top_n.currentTextChanged.connect(self._update_filters)

        bar.addWidget(self._start_button)
        bar.addWidget(self._stop_button)
        bar.addSpacing(10)
        bar.addWidget(QtWidgets.QLabel("Top N"))
        bar.addWidget(self._top_n)
        bar.addWidget(QtWidgets.QLabel("Min Profit %"))
        bar.addWidget(self._min_profit)
        bar.addWidget(self._min_profit_custom)
        bar.addWidget(QtWidgets.QLabel("Min 24h Volume"))
        bar.addWidget(self._min_volume)
        bar.addWidget(self._min_volume_custom)
        bar.addWidget(self._search)
        bar.addStretch(1)

        self._status_binance = QtWidgets.QLabel("Binance: Connected")
        self._status_poloniex = QtWidgets.QLabel("Poloniex: Connected")
        self._status_update = QtWidgets.QLabel("Last update: 0.0s")
        self._status_pairs = QtWidgets.QLabel("Pairs: 0")
        self._status_signals = QtWidgets.QLabel("Signals: 0")
        for label in [
            self._status_binance,
            self._status_poloniex,
            self._status_update,
            self._status_pairs,
            self._status_signals,
        ]:
            bar.addWidget(label)

        self._search.textChanged.connect(self._proxy.set_search_text)
        return bar

    def _apply_defaults(self) -> None:
        self._top_n.setCurrentText("50")
        self._min_profit.setCurrentText("0.5")
        self._min_volume.setCurrentText("100k")
        self._update_filters()

    def _toggle_custom_profit(self, value: str) -> None:
        custom = value == "Custom"
        self._min_profit_custom.setEnabled(custom)
        self._update_filters()

    def _toggle_custom_volume(self, value: str) -> None:
        custom = value == "Custom"
        self._min_volume_custom.setEnabled(custom)
        self._update_filters()

    def _update_filters(self) -> None:
        self._controller.set_filters(self._collect_filters())

    def _collect_filters(self) -> FilterSettings:
        top_n_text = self._top_n.currentText()
        top_n = None if top_n_text == "All" else int(top_n_text)

        min_profit = self._parse_float(self._min_profit.currentText(), 0.5)
        if self._min_profit.currentText() == "Custom":
            min_profit = self._parse_float(self._min_profit_custom.text(), 0.5)

        min_volume = self._parse_volume(self._min_volume.currentText(), 100_000)
        if self._min_volume.currentText() == "Custom":
            min_volume = self._parse_float(self._min_volume_custom.text(), 100_000)

        return FilterSettings(
            top_n=top_n,
            min_profit=min_profit,
            min_volume=min_volume,
            search_pair=self._search.text(),
        )

    def _parse_float(self, value: str, fallback: float) -> float:
        try:
            return float(value.replace("%", "").strip())
        except ValueError:
            return fallback

    def _parse_volume(self, value: str, fallback: float) -> float:
        lowered = value.lower().strip()
        if lowered.endswith("k"):
            return self._parse_float(lowered[:-1], fallback) * 1000
        return self._parse_float(lowered, fallback)

    def _append_log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self._log_view.appendPlainText(f"[{timestamp}] {message}")

    def _on_updated(self, latency: float, pair_count: int, signal_count: int) -> None:
        self._status_update.setText(f"Last update: {latency:.1f}s")
        self._status_pairs.setText(f"Pairs: {pair_count}")
        self._status_signals.setText(f"Signals: {signal_count}")

    def _on_start(self) -> None:
        self._controller.start()
        self._start_button.setEnabled(False)
        self._stop_button.setEnabled(True)

    def _on_stop(self) -> None:
        self._controller.stop()
        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)
