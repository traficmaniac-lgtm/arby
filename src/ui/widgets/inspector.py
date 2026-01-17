from __future__ import annotations

from PySide6 import QtWidgets

from ...core.types import ArbRow
from ...utils import formatting


class InspectorPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._current_row: ArbRow | None = None
        self._build_ui()

    def set_row(self, row: ArbRow | None) -> None:
        self._current_row = row
        if not row:
            self._pair_label.setText("Select a pair")
            self._direction_label.setText("-")
            self._binance_bid.setText("-")
            self._binance_ask.setText("-")
            self._poloniex_bid.setText("-")
            self._poloniex_ask.setText("-")
            self._formula_label.setText("profit% = (sell_bid - buy_ask) / buy_ask * 100")
            self._volume_label.setText("-")
            self._updated_label.setText("-")
            self._quality_label.setText("-")
            self._source_label.setText("-")
            return

        self._pair_label.setText(row.pair)
        self._direction_label.setText(self._direction_text(row))
        self._binance_bid.setText(formatting.format_price(row.binance_bid))
        self._binance_ask.setText(formatting.format_price(row.binance_ask))
        self._poloniex_bid.setText(formatting.format_price(row.poloniex_bid))
        self._poloniex_ask.setText(formatting.format_price(row.poloniex_ask))
        self._formula_label.setText("profit% = (sell_bid - buy_ask) / buy_ask * 100")
        self._volume_label.setText(formatting.format_volume(row.volume_24h))
        self._updated_label.setText(f"{row.updated_secs:.1f}s")
        quality_flags = ", ".join(row.quality_flags) if row.quality_flags else "OK"
        self._quality_label.setText(quality_flags)
        self._source_label.setText(row.data_source)

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_group = QtWidgets.QGroupBox("Inspector")
        header_layout = QtWidgets.QVBoxLayout(header_group)
        self._pair_label = QtWidgets.QLabel("Select a pair")
        self._pair_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._direction_label = QtWidgets.QLabel("-")
        header_layout.addWidget(self._pair_label)
        header_layout.addWidget(self._direction_label)

        price_group = QtWidgets.QGroupBox("Prices")
        price_layout = QtWidgets.QFormLayout(price_group)
        self._binance_bid = QtWidgets.QLabel("-")
        self._binance_ask = QtWidgets.QLabel("-")
        self._poloniex_bid = QtWidgets.QLabel("-")
        self._poloniex_ask = QtWidgets.QLabel("-")
        price_layout.addRow("Binance bid", self._binance_bid)
        price_layout.addRow("Binance ask", self._binance_ask)
        price_layout.addRow("Poloniex bid", self._poloniex_bid)
        price_layout.addRow("Poloniex ask", self._poloniex_ask)

        formula_group = QtWidgets.QGroupBox("Formula")
        formula_layout = QtWidgets.QVBoxLayout(formula_group)
        self._formula_label = QtWidgets.QLabel("profit% = (sell_bid - buy_ask) / buy_ask * 100")
        self._formula_label.setWordWrap(True)
        formula_layout.addWidget(self._formula_label)

        metrics_group = QtWidgets.QGroupBox("Metrics")
        metrics_layout = QtWidgets.QFormLayout(metrics_group)
        self._volume_label = QtWidgets.QLabel("-")
        self._updated_label = QtWidgets.QLabel("-")
        self._quality_label = QtWidgets.QLabel("-")
        self._source_label = QtWidgets.QLabel("-")
        metrics_layout.addRow("Volume 24h", self._volume_label)
        metrics_layout.addRow("Updated age", self._updated_label)
        metrics_layout.addRow("Quality flags", self._quality_label)
        metrics_layout.addRow("Data source", self._source_label)

        buttons = QtWidgets.QHBoxLayout()
        self._copy_signal = QtWidgets.QPushButton("Copy signal")
        self._copy_pair = QtWidgets.QPushButton("Copy pair")
        buttons.addWidget(self._copy_signal)
        buttons.addWidget(self._copy_pair)

        layout.addWidget(header_group)
        layout.addWidget(price_group)
        layout.addWidget(formula_group)
        layout.addWidget(metrics_group)
        layout.addLayout(buttons)
        layout.addStretch(1)

        self._copy_signal.clicked.connect(self._copy_signal_text)
        self._copy_pair.clicked.connect(self._copy_pair_text)

    def _direction_text(self, row: ArbRow) -> str:
        return f"Buy {row.buy_exchange} → Sell {row.sell_exchange}"

    def _copy_signal_text(self) -> None:
        if not self._current_row:
            return
        row = self._current_row
        text = (
            f"{row.pair} | Buy {row.buy_exchange} {row.buy_price:,.4f} "
            f"-> Sell {row.sell_exchange} {row.sell_price:,.4f} | {row.profit_pct:+.2f}%"
        )
        QtWidgets.QApplication.clipboard().setText(text)

    def _copy_pair_text(self) -> None:
        if not self._current_row:
            return
        QtWidgets.QApplication.clipboard().setText(self._current_row.pair)
