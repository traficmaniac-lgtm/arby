from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from src.core.config import load_config, save_config
from src.core.controller import RadarController
from src.models.radar_model import RadarModel
from src.ui.widgets.filter_panel import FilterPanel
from src.ui.widgets.inspector import InspectorPanel
from src.ui.widgets.log_panel import LogPanel
from src.ui.widgets.toast import Toast
from src.utils.shortcuts import bind_shortcut


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
        index = self.sourceModel().index(source_row, 1, source_parent)
        pair = self.sourceModel().data(index, QtCore.Qt.DisplayRole)
        return self._search_text in str(pair).lower()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ARBY Trading Terminal Lite")
        self.resize(1280, 820)

        self._config = load_config()

        self._model = RadarModel()
        self._model.set_favorites(self._config.favorites)
        self._proxy = PairFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._proxy.setSortRole(QtCore.Qt.UserRole)

        self._log_panel = LogPanel()

        self._controller = RadarController(self._model, self._append_log)
        self._controller.updated.connect(self._on_updated)

        self._save_timer = QtCore.QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._save_config)

        self._filters_timer = QtCore.QTimer(self)
        self._filters_timer.setSingleShot(True)
        self._filters_timer.setInterval(300)
        self._filters_timer.timeout.connect(self._apply_filters)

        self._setup_ui()
        self._apply_config()
        self._schedule_filters()
        self._bind_shortcuts()

    def _setup_ui(self) -> None:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.addLayout(self._build_control_bar())

        self._filter_panel = FilterPanel()
        self._filter_panel.setFixedWidth(280)
        self._filter_panel.filters_changed.connect(self._schedule_filters)

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
        self._table.sortByColumn(6, QtCore.Qt.DescendingOrder)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_table_menu)
        self._table.doubleClicked.connect(self._open_details_dialog)
        center_layout.addWidget(self._table)
        for column in [0, 1, 2, 4, 10]:
            self._table.resizeColumnToContents(column)

        self._inspector = InspectorPanel()
        self._inspector.setFixedWidth(330)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self._splitter.addWidget(self._filter_panel)
        self._splitter.addWidget(center_group)
        self._splitter.addWidget(self._inspector)
        self._splitter.splitterMoved.connect(lambda *_: self._schedule_save())

        self._main_vertical = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self._main_vertical.addWidget(self._splitter)
        self._log_panel.setMinimumHeight(160)
        self._main_vertical.addWidget(self._log_panel)
        self._main_vertical.splitterMoved.connect(lambda *_: self._schedule_save())
        layout.addWidget(self._main_vertical, 1)

        self.setCentralWidget(container)

        self._search.textChanged.connect(self._proxy.set_search_text)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _build_control_bar(self) -> QtWidgets.QHBoxLayout:
        bar = QtWidgets.QHBoxLayout()

        self._data_source = QtWidgets.QComboBox()
        self._data_source.addItems(["Simulator", "Real"])
        self._data_source.currentTextChanged.connect(self._schedule_filters)

        self._start_button = QtWidgets.QPushButton("Start")
        self._stop_button = QtWidgets.QPushButton("Stop")
        self._refresh_button = QtWidgets.QPushButton("Refresh Pairs")
        self._stop_button.setEnabled(False)
        self._start_button.setToolTip("Start scanning (Ctrl+Enter)")
        self._stop_button.setToolTip("Stop scanning (Ctrl+Shift+S)")
        self._refresh_button.setToolTip("Refresh pairs (Ctrl+R)")
        self._start_button.clicked.connect(self._on_start)
        self._stop_button.clicked.connect(self._on_stop)
        self._refresh_button.clicked.connect(self._on_refresh_pairs)

        bar.addWidget(QtWidgets.QLabel("Provider"))
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
        self._status_tick_rate = QtWidgets.QLabel("Tick rate: 0.0/s")
        self._status_provider = QtWidgets.QLabel("Provider: Simulator")
        for widget in [
            self._status_binance["container"],
            self._status_poloniex["container"],
            self._status_update,
            self._status_pairs,
            self._status_signals,
            self._status_tick_rate,
            self._status_provider,
        ]:
            bar.addWidget(widget)

        return bar

    def _apply_config(self) -> None:
        if self._config.window_geometry:
            self.restoreGeometry(QtCore.QByteArray.fromHex(self._config.window_geometry.encode()))
        if self._config.splitter_sizes_horizontal:
            self._splitter.setSizes(self._config.splitter_sizes_horizontal)
        if self._config.splitter_sizes_vertical:
            self._main_vertical.setSizes(self._config.splitter_sizes_vertical)
        if self._data_source.findText(self._config.data_source) >= 0:
            self._data_source.setCurrentText(self._config.data_source)
        self._filter_panel.set_from_config(self._config.to_dict())

    def _apply_defaults(self) -> None:
        self._filter_panel.apply_defaults()
        self._schedule_filters()
        self._set_status_badge(self._status_binance, "Connected")
        self._set_status_badge(self._status_poloniex, "Connected")

    def _bind_shortcuts(self) -> None:
        bind_shortcut(self, "Ctrl+R", self._refresh_shortcut)
        bind_shortcut(self, "Ctrl+F", self._focus_search)
        bind_shortcut(self, "Ctrl+Enter", self._start_shortcut)
        bind_shortcut(self, "Ctrl+Shift+S", self._stop_shortcut)
        bind_shortcut(self, "Ctrl+C", self._copy_signal_shortcut)

    def run_smoke(self, ticks: int = 3) -> None:
        self._apply_filters()
        for _ in range(ticks):
            self._controller.refresh()

    def _append_log(self, level: str, message: str) -> None:
        self._log_panel.append(level, message)

    def _on_updated(self, latency: float, pair_count: int, signal_count: int, statuses: dict, health: dict) -> None:
        self._status_update.setText(f"Last update: {latency:.1f}s")
        self._status_pairs.setText(f"Pairs: {pair_count}")
        self._status_signals.setText(f"Signals: {signal_count}")
        tick_rate = 1.0 / latency if latency > 0 else 0.0
        self._status_tick_rate.setText(f"Tick rate: {tick_rate:.1f}/s")
        self._status_provider.setText(f"Provider: {health.get('provider_mode', '-')}")
        self._set_status_badge(self._status_binance, statuses["Binance"].status)
        self._set_status_badge(self._status_poloniex, statuses["Poloniex"].status)
        self._inspector.set_exchange_status("Binance", statuses["Binance"].status)
        self._inspector.set_exchange_status("Poloniex", statuses["Poloniex"].status)
        self._inspector.set_health(health)

    def _on_start(self) -> None:
        if self._data_source.currentText() == "Real":
            self._append_log("ERROR", "Real provider not implemented")
            Toast(self, "Real provider not implemented").show_at_bottom_right()
            return
        self._controller.start()
        self._start_button.setEnabled(False)
        self._stop_button.setEnabled(True)

    def _on_stop(self) -> None:
        self._controller.stop()
        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)

    def _on_refresh_pairs(self) -> None:
        self._controller.refresh_pairs()

    def _schedule_filters(self) -> None:
        self._filters_timer.start()
        self._schedule_save()

    def _apply_filters(self) -> None:
        settings = self._filter_panel.settings(data_source=self._data_source.currentText())
        self._controller.set_filters(settings)
        self._update_provider_state()

    def _update_provider_state(self) -> None:
        is_real = self._data_source.currentText() == "Real"
        if is_real and self._stop_button.isEnabled():
            self._on_stop()
        self._start_button.setEnabled(not is_real and not self._stop_button.isEnabled())
        if is_real:
            self._append_log("INFO", "Real provider selected (stub)")

    def _schedule_save(self) -> None:
        self._save_timer.start()

    def _save_config(self) -> None:
        self._config.window_geometry = self.saveGeometry().toHex().data().decode()
        self._config.splitter_sizes_horizontal = self._splitter.sizes()
        self._config.splitter_sizes_vertical = self._main_vertical.sizes()
        filters = self._filter_panel.settings(data_source=self._data_source.currentText())
        self._config.top_n = filters.top_n
        self._config.min_profit_pct = filters.min_profit
        self._config.min_volume = filters.min_volume
        self._config.cooldown_sec = filters.cooldown_seconds
        self._config.only_usdt = filters.only_usdt
        self._config.exclude_leveraged = filters.exclude_leveraged
        self._config.show_only_signals = filters.show_only_signals
        self._config.show_favorites_only = filters.show_favorites_only
        self._config.max_profit_suspicious = filters.max_profit_suspicious
        self._config.stale_sec = filters.stale_sec
        self._config.update_interval_ms = filters.update_interval_ms
        self._config.data_source = filters.data_source
        self._config.favorites = self._model.favorites()
        save_config(self._config)

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

    def _focus_search(self) -> None:
        if self._is_text_input_focused():
            return
        self._search.setFocus()
        self._search.selectAll()

    def _start_shortcut(self) -> None:
        if self._is_text_input_focused():
            return
        self._on_start()

    def _stop_shortcut(self) -> None:
        if self._is_text_input_focused():
            return
        self._on_stop()

    def _refresh_shortcut(self) -> None:
        if self._is_text_input_focused():
            return
        self._on_refresh_pairs()

    def _copy_signal_shortcut(self) -> None:
        if self._is_text_input_focused():
            return
        self._copy_selected_signal()

    def _show_table_menu(self, position: QtCore.QPoint) -> None:
        index = self._table.indexAt(position)
        if index.isValid():
            self._table.selectRow(index.row())
        row = self._selected_row()
        menu = QtWidgets.QMenu(self)
        copy_signal = menu.addAction("Copy signal")
        copy_pair = menu.addAction("Copy pair")
        if row:
            if row.favorite:
                toggle_fav = menu.addAction("Remove from Favorites")
            else:
                toggle_fav = menu.addAction("Add to Favorites")
        else:
            toggle_fav = None
        menu.addSeparator()
        export_csv = menu.addAction("Export visible rows to CSV")

        action = menu.exec(self._table.viewport().mapToGlobal(position))
        if action == copy_signal:
            self._copy_selected_signal()
        elif action == copy_pair:
            self._copy_selected_pair()
        elif toggle_fav and action == toggle_fav:
            self._toggle_favorite(row)
        elif action == export_csv:
            self._export_visible_rows()

    def _open_details_dialog(self, *_: object) -> None:
        row = self._selected_row()
        if not row:
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Signal Details")
        layout = QtWidgets.QFormLayout(dialog)
        layout.addRow("Pair", QtWidgets.QLabel(row.pair))
        layout.addRow("Direction", QtWidgets.QLabel(f"Buy {row.buy_exchange} → Sell {row.sell_exchange}"))
        layout.addRow("Buy price", QtWidgets.QLabel(f"{row.buy_exchange} {row.buy_price:,.4f}"))
        layout.addRow("Sell price", QtWidgets.QLabel(f"{row.sell_exchange} {row.sell_price:,.4f}"))
        layout.addRow("Profit %", QtWidgets.QLabel(f"{row.profit_pct:+.2f}%"))
        layout.addRow("Volume 24h", QtWidgets.QLabel(f"{row.volume_24h:,.0f}"))
        layout.addRow("Updated", QtWidgets.QLabel(f"{row.updated_secs:.1f}s"))
        layout.addRow("Quality", QtWidgets.QLabel(row.quality))
        layout.addRow("Formula", QtWidgets.QLabel("profit% = (sell_bid - buy_ask) / buy_ask * 100"))
        dialog.setLayout(layout)
        dialog.exec()

    def _selected_row(self) -> Optional[object]:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        source_index = self._proxy.mapToSource(indexes[0])
        return self._model.row_at(source_index.row())

    def _copy_selected_signal(self) -> None:
        row = self._selected_row()
        if not row:
            return
        text = (
            f"{row.pair} | Buy {row.buy_exchange} {row.buy_price:,.4f} "
            f"-> Sell {row.sell_exchange} {row.sell_price:,.4f} | {row.profit_pct:+.2f}%"
        )
        QtWidgets.QApplication.clipboard().setText(text)

    def _copy_selected_pair(self) -> None:
        row = self._selected_row()
        if not row:
            return
        QtWidgets.QApplication.clipboard().setText(row.pair)

    def _toggle_favorite(self, row) -> None:
        if not row:
            return
        self._model.toggle_favorite(row.pair)
        self._schedule_save()
        self._schedule_filters()

    def _export_visible_rows(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export CSV", str(Path.cwd()), "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self._model.headers)
            for row_index in range(self._proxy.rowCount()):
                source_index = self._proxy.mapToSource(self._proxy.index(row_index, 0))
                row = self._model.row_at(source_index.row())
                if not row:
                    continue
                writer.writerow(
                    [
                        "★" if row.favorite else "",
                        row.pair,
                        row.buy_exchange,
                        f"{row.buy_price:,.4f}",
                        row.sell_exchange,
                        f"{row.sell_price:,.4f}",
                        f"{row.profit_pct:+.2f}%",
                        f"{row.volume_24h:,.0f}",
                        f"{row.updated_secs:.1f}s",
                        f"{row.spread:,.4f}",
                        row.quality,
                    ]
                )
        self._append_log("INFO", f"Exported CSV: {path}")

    def _is_text_input_focused(self) -> bool:
        focused = QtWidgets.QApplication.focusWidget()
        return isinstance(focused, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._save_config()
        super().closeEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._schedule_save()
        super().resizeEvent(event)

    def moveEvent(self, event: QtGui.QMoveEvent) -> None:
        self._schedule_save()
        super().moveEvent(event)
