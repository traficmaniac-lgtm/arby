from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ...core.controller import FilterSettings


class FilterPanel(QtWidgets.QWidget):
    filters_changed = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()

    def settings(self, *, data_source: str) -> FilterSettings:
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
            only_usdt=self._only_usdt.isChecked(),
            exclude_leveraged=self._exclude_leveraged.isChecked(),
            show_only_signals=self._show_only_signals.isChecked(),
            cooldown_seconds=self._cooldown.value(),
            data_source=data_source,
        )

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scanner_group = QtWidgets.QGroupBox("Scanner")
        scanner_layout = QtWidgets.QFormLayout(scanner_group)
        scanner_layout.setLabelAlignment(QtCore.Qt.AlignLeft)

        self._top_n = QtWidgets.QComboBox()
        self._top_n.addItems(["30", "50", "70", "All"])

        self._min_volume = QtWidgets.QComboBox()
        self._min_volume.addItems(["50k", "100k", "250k", "Custom"])
        self._min_volume_custom = QtWidgets.QLineEdit()
        self._min_volume_custom.setPlaceholderText("Custom volume")
        self._min_volume_custom.setEnabled(False)

        self._min_profit = QtWidgets.QComboBox()
        self._min_profit.addItems(["0.2", "0.5", "1.0", "Custom"])
        self._min_profit_custom = QtWidgets.QLineEdit()
        self._min_profit_custom.setPlaceholderText("Custom %")
        self._min_profit_custom.setEnabled(False)

        self._cooldown = QtWidgets.QSpinBox()
        self._cooldown.setRange(3, 10)
        self._cooldown.setValue(5)
        self._cooldown.setSuffix("s")

        scanner_layout.addRow("Top N", self._top_n)
        scanner_layout.addRow("Min 24h Volume", self._min_volume)
        scanner_layout.addRow("Custom volume", self._min_volume_custom)
        scanner_layout.addRow("Min Profit %", self._min_profit)
        scanner_layout.addRow("Custom profit", self._min_profit_custom)
        scanner_layout.addRow("Cooldown per pair", self._cooldown)

        toggles_group = QtWidgets.QGroupBox("Toggles")
        toggles_layout = QtWidgets.QVBoxLayout(toggles_group)
        self._only_usdt = QtWidgets.QCheckBox("Only USDT pairs")
        self._exclude_leveraged = QtWidgets.QCheckBox("Exclude leveraged")
        toggles_layout.addWidget(self._only_usdt)
        toggles_layout.addWidget(self._exclude_leveraged)

        table_group = QtWidgets.QGroupBox("Table")
        table_layout = QtWidgets.QVBoxLayout(table_group)
        self._show_only_signals = QtWidgets.QCheckBox("Show only signals (profit >= min_profit)")
        table_layout.addWidget(self._show_only_signals)

        layout.addWidget(scanner_group)
        layout.addWidget(toggles_group)
        layout.addWidget(table_group)
        layout.addStretch(1)

        self._top_n.currentTextChanged.connect(self.filters_changed.emit)
        self._min_volume.currentTextChanged.connect(self._toggle_custom_volume)
        self._min_profit.currentTextChanged.connect(self._toggle_custom_profit)
        self._min_volume_custom.textChanged.connect(self.filters_changed.emit)
        self._min_profit_custom.textChanged.connect(self.filters_changed.emit)
        self._cooldown.valueChanged.connect(self.filters_changed.emit)
        self._only_usdt.stateChanged.connect(self.filters_changed.emit)
        self._exclude_leveraged.stateChanged.connect(self.filters_changed.emit)
        self._show_only_signals.stateChanged.connect(self.filters_changed.emit)

    def _toggle_custom_profit(self, value: str) -> None:
        custom = value == "Custom"
        self._min_profit_custom.setEnabled(custom)
        self.filters_changed.emit()

    def _toggle_custom_volume(self, value: str) -> None:
        custom = value == "Custom"
        self._min_volume_custom.setEnabled(custom)
        self.filters_changed.emit()

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

    def apply_defaults(self) -> None:
        self._top_n.setCurrentText("50")
        self._min_profit.setCurrentText("0.5")
        self._min_volume.setCurrentText("100k")
