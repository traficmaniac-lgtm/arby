from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.controller import RadarController
from ..models.radar_model import RadarModel
from .widgets.filter_panel import FilterPanel
from .widgets.inspector import InspectorPanel
from .widgets.log_panel import LogPanel


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
        self.resize(1280, 820)

        self._model = RadarModel()
        self._proxy = PairFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._proxy.setSortRole(QtCore.Qt.UserRole)

        self._log_panel = LogPanel()

        self._controller = RadarController(self._model, self._append_log)
        self._controller.updated.connect(self._on_updated)

        self._setup_ui()
        self._apply_defaults()

    def _setup_ui(self) -> None:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.addLayout(self._build_control_bar())

        middle = QtWidgets.QHBoxLayout()
        self._filter_panel = FilterPanel()
        self._filter_panel.setFixedWidth(280)
        self._filter_panel.filters_changed.connect(self._update_filters)

        center_group = QtWidgets.QGroupBox("Arbitrage Radar")
        center_layout = QtWidgets.QVBoxLayout(center_group)
        search_row = QtWidgets.QHBoxLayout()
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search: BTC/USDT")
        search_row.addWidget(self._search)
        center_layout.addLayout(search_row)

        self._table = QtWidgets.QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(5, QtCore.Qt.DescendingOrder)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        center_layout.addWidget(self._table)
        for column in [0, 1, 3, 9]:
            self._table.resizeColumnToContents(column)

        self._inspector = InspectorPanel()
        self._inspector.setFixedWidth(330)

        middle.addWidget(self._filter_panel)
        middle.addWidget(center_group, 1)
        middle.addWidget(self._inspector)

        layout.addLayout(middle, 1)

        self._log_panel.setFixedHeight(200)
        layout.addWidget(self._log_panel, 0)

        self.setCentralWidget(container)

        self._search.textChanged.connect(self._proxy.set_search_text)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _build_control_bar(self) -> QtWidgets.QHBoxLayout:
        bar = QtWidgets.QHBoxLayout()

        self._binance_toggle = QtWidgets.QCheckBox("Binance")
        self._binance_toggle.setChecked(True)
        self._poloniex_toggle = QtWidgets.QCheckBox("Poloniex")
        self._poloniex_toggle.setChecked(True)
        self._binance_toggle.stateChanged.connect(self._validate_exchange_toggles)
        self._poloniex_toggle.stateChanged.connect(self._validate_exchange_toggles)

        self._data_source = QtWidgets.QComboBox()
        self._data_source.addItems(["Auto", "WS+REST", "REST only"])
        self._data_source.currentTextChanged.connect(self._update_filters)

        self._start_button = QtWidgets.QPushButton("Start")
        self._stop_button = QtWidgets.QPushButton("Stop")
        self._refresh_button = QtWidgets.QPushButton("Refresh Pairs")
        self._stop_button.setEnabled(False)
        self._start_button.clicked.connect(self._on_start)
        self._stop_button.clicked.connect(self._on_stop)
        self._refresh_button.clicked.connect(self._on_refresh_pairs)

        bar.addWidget(self._binance_toggle)
        bar.addWidget(self._poloniex_toggle)
        bar.addSpacing(12)
        bar.addWidget(QtWidgets.QLabel("Data source"))
        bar.addWidget(self._data_source)
        bar.addSpacing(12)
        bar.addWidget(self._start_button)
        bar.addWidget(self._stop_button)
        bar.addWidget(self._refresh_button)
        bar.addStretch(1)

        self._status_binance = self._make_status_badge("Binance")
        self._status_poloniex = self._make_status_badge("Poloniex")
        self._status_update = QtWidgets.QLabel("Last update: 0.0s")
        self._status_pairs = QtWidgets.QLabel("Pairs: 0")
        self._status_signals = QtWidgets.QLabel("Signals: 0")
        for widget in [
            self._status_binance["container"],
            self._status_poloniex["container"],
            self._status_update,
            self._status_pairs,
            self._status_signals,
        ]:
            bar.addWidget(widget)

        return bar

    def _apply_defaults(self) -> None:
        self._filter_panel.apply_defaults()
        self._update_filters()
        self._set_status_badge(self._status_binance, "Connected")
        self._set_status_badge(self._status_poloniex, "Connected")

    def _append_log(self, level: str, message: str) -> None:
        self._log_panel.append(level, message)

    def _on_updated(self, latency: float, pair_count: int, signal_count: int, statuses: dict) -> None:
        self._status_update.setText(f"Last update: {latency:.1f}s")
        self._status_pairs.setText(f"Pairs: {pair_count}")
        self._status_signals.setText(f"Signals: {signal_count}")
        self._set_status_badge(self._status_binance, statuses["Binance"].status)
        self._set_status_badge(self._status_poloniex, statuses["Poloniex"].status)

    def _on_start(self) -> None:
        self._controller.start()
        self._start_button.setEnabled(False)
        self._stop_button.setEnabled(True)

    def _on_stop(self) -> None:
        self._controller.stop()
        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)

    def _on_refresh_pairs(self) -> None:
        self._controller.refresh_pairs()

    def _update_filters(self) -> None:
        settings = self._filter_panel.settings(data_source=self._data_source.currentText())
        self._controller.set_filters(settings)

    def _validate_exchange_toggles(self) -> None:
        if not self._binance_toggle.isChecked() and not self._poloniex_toggle.isChecked():
            QtWidgets.QMessageBox.warning(self, "Selection", "Select at least one exchange.")
            self._binance_toggle.setChecked(True)

    def _on_selection_changed(self) -> None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            self._inspector.set_row(None)
            return
        proxy_index = indexes[0]
        source_index = self._proxy.mapToSource(proxy_index)
        row = self._model.row_at(source_index.row())
        self._inspector.set_row(row)

    def _make_status_badge(self, name: str) -> dict:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(f"{name}:")
        badge = QtWidgets.QLabel("Connected")
        badge.setObjectName("statusBadge")
        badge.setMinimumWidth(90)
        badge.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(badge)
        return {"container": container, "badge": badge}

    def _set_status_badge(self, badge: dict, status: str) -> None:
        badge_label: QtWidgets.QLabel = badge["badge"]
        badge_label.setText(status)
        palette = {
            "Connected": "#1f8f5f",
            "Degraded": "#b8891f",
            "Disconnected": "#9d3b3b",
        }
        color = palette.get(status, "#3a475d")
        badge_label.setStyleSheet(
            "QLabel {"
            f"background-color: {color};"
            "color: #f0f2f5;"
            "border-radius: 4px;"
            "padding: 2px 6px;"
            "}"
        )
