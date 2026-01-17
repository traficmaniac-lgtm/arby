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

        update_interval = self._parse_int(self._update_interval.currentText(), 500)
        if self._update_interval.currentText() == "Custom":
            update_interval = self._parse_int(self._update_interval_custom.text(), 500)

        return FilterSettings(
            top_n=top_n,
            min_profit=min_profit,
            min_volume=min_volume,
            only_usdt=self._only_usdt.isChecked(),
            exclude_leveraged=self._exclude_leveraged.isChecked(),
            show_only_signals=self._show_only_signals.isChecked(),
            show_favorites_only=self._show_favorites_only.isChecked(),
            cooldown_seconds=self._cooldown.value(),
            max_profit_suspicious=float(self._suspicious_profit.value()),
            stale_sec=self._stale.value(),
            update_interval_ms=update_interval,
            data_source=data_source,
        )

    def set_from_config(self, config: dict) -> None:
        if config.get("top_n") is None:
            self._top_n.setCurrentText("All")
        else:
            self._top_n.setCurrentText(str(config.get("top_n", 50)))
        min_profit = config.get("min_profit_pct", 0.5)
        min_volume = config.get("min_volume", 100_000)
        update_interval = config.get("update_interval_ms", 500)

        self._set_combo_or_custom(self._min_profit, self._min_profit_custom, min_profit, ["0.2", "0.5", "1.0"])
        volume_map = {50_000: "50k", 100_000: "100k", 250_000: "250k"}
        volume_label = volume_map.get(int(min_volume))
        if volume_label:
            self._min_volume.setCurrentText(volume_label)
            self._min_volume_custom.setEnabled(False)
        else:
            self._min_volume.setCurrentText("Custom")
            self._min_volume_custom.setEnabled(True)
            self._min_volume_custom.setText(str(min_volume))
        self._set_combo_or_custom(self._update_interval, self._update_interval_custom, update_interval, ["250", "500", "1000"])

        self._cooldown.setValue(int(config.get("cooldown_sec", 5)))
        self._only_usdt.setChecked(config.get("only_usdt", False))
        self._exclude_leveraged.setChecked(config.get("exclude_leveraged", False))
        self._show_only_signals.setChecked(config.get("show_only_signals", False))
        self._show_favorites_only.setChecked(config.get("show_favorites_only", False))
        self._stale.setValue(int(config.get("stale_sec", 3)))
        self._suspicious_profit.setValue(float(config.get("max_profit_suspicious", 5.0)))

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
        self._show_favorites_only = QtWidgets.QCheckBox("Show favorites only")
        toggles_layout.addWidget(self._only_usdt)
        toggles_layout.addWidget(self._exclude_leveraged)
        toggles_layout.addWidget(self._show_favorites_only)

        table_group = QtWidgets.QGroupBox("Table")
        table_layout = QtWidgets.QVBoxLayout(table_group)
        self._show_only_signals = QtWidgets.QCheckBox("Show only signals (profit >= min_profit)")
        table_layout.addWidget(self._show_only_signals)

        advanced_group = QtWidgets.QGroupBox("Advanced")
        advanced_layout = QtWidgets.QFormLayout(advanced_group)
        self._update_interval = QtWidgets.QComboBox()
        self._update_interval.addItems(["250", "500", "1000", "Custom"])
        self._update_interval_custom = QtWidgets.QLineEdit()
        self._update_interval_custom.setPlaceholderText("Custom ms")
        self._update_interval_custom.setEnabled(False)

        self._stale = QtWidgets.QSpinBox()
        self._stale.setRange(1, 10)
        self._stale.setValue(3)
        self._stale.setSuffix("s")

        self._suspicious_profit = QtWidgets.QDoubleSpinBox()
        self._suspicious_profit.setRange(2.0, 20.0)
        self._suspicious_profit.setSingleStep(0.5)
        self._suspicious_profit.setValue(5.0)
        self._suspicious_profit.setSuffix("%")

        advanced_layout.addRow("Update interval (ms)", self._update_interval)
        advanced_layout.addRow("Custom interval", self._update_interval_custom)
        advanced_layout.addRow("Stale (sec)", self._stale)
        advanced_layout.addRow("Suspicious profit %", self._suspicious_profit)

        layout.addWidget(scanner_group)
        layout.addWidget(toggles_group)
        layout.addWidget(table_group)
        layout.addWidget(advanced_group)
        layout.addStretch(1)

        self._top_n.currentTextChanged.connect(self.filters_changed.emit)
        self._min_volume.currentTextChanged.connect(self._toggle_custom_volume)
        self._min_profit.currentTextChanged.connect(self._toggle_custom_profit)
        self._update_interval.currentTextChanged.connect(self._toggle_custom_interval)
        self._min_volume_custom.textChanged.connect(self.filters_changed.emit)
        self._min_profit_custom.textChanged.connect(self.filters_changed.emit)
        self._update_interval_custom.textChanged.connect(self.filters_changed.emit)
        self._cooldown.valueChanged.connect(self.filters_changed.emit)
        self._only_usdt.stateChanged.connect(self.filters_changed.emit)
        self._exclude_leveraged.stateChanged.connect(self.filters_changed.emit)
        self._show_only_signals.stateChanged.connect(self.filters_changed.emit)
        self._show_favorites_only.stateChanged.connect(self.filters_changed.emit)
        self._stale.valueChanged.connect(self.filters_changed.emit)
        self._suspicious_profit.valueChanged.connect(self.filters_changed.emit)

    def _toggle_custom_profit(self, value: str) -> None:
        custom = value == "Custom"
        self._min_profit_custom.setEnabled(custom)
        self.filters_changed.emit()

    def _toggle_custom_volume(self, value: str) -> None:
        custom = value == "Custom"
        self._min_volume_custom.setEnabled(custom)
        self.filters_changed.emit()

    def _toggle_custom_interval(self, value: str) -> None:
        custom = value == "Custom"
        self._update_interval_custom.setEnabled(custom)
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

    def _parse_int(self, value: str, fallback: int) -> int:
        try:
            return int(value.strip())
        except ValueError:
            return fallback

    def _set_combo_or_custom(
        self,
        combo: QtWidgets.QComboBox,
        custom_field: QtWidgets.QLineEdit,
        value: float | int,
        presets: list[str],
    ) -> None:
        str_value = (
            str(int(value))
            if isinstance(value, int) or (isinstance(value, float) and value.is_integer())
            else str(value)
        )
        if str_value in presets:
            combo.setCurrentText(str_value)
            custom_field.setEnabled(False)
        else:
            combo.setCurrentText("Custom")
            custom_field.setEnabled(True)
            custom_field.setText(str_value)

    def apply_defaults(self) -> None:
        self._top_n.setCurrentText("50")
        self._min_profit.setCurrentText("0.5")
        self._min_volume.setCurrentText("100k")
        self._update_interval.setCurrentText("500")
