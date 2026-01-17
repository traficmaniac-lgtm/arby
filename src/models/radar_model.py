from __future__ import annotations

from typing import List

from PySide6 import QtCore, QtGui

from ..core.types import ArbRow
from ..utils import formatting


class RadarModel(QtCore.QAbstractTableModel):
    headers = [
        "Pair",
        "Buy @",
        "Buy Price",
        "Sell @",
        "Sell Price",
        "Profit %",
        "Vol 24h",
        "Updated",
        "Spread",
        "Quality",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._rows: List[ArbRow] = []
        self._profit_threshold = 0.5

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QtCore.QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        column = index.column()

        if role == QtCore.Qt.DisplayRole:
            return self._display_data(row, column)
        if role == QtCore.Qt.UserRole:
            return self._sort_value(row, column)
        if role == QtCore.Qt.TextAlignmentRole:
            if column in {2, 4, 5, 6, 7, 8}:
                return QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        if role == QtCore.Qt.FontRole and column == 5:
            font = QtGui.QFont()
            font.setBold(True)
            font.setPointSize(11)
            return font
        if role == QtCore.Qt.ForegroundRole and row.quality == "Stale":
            return QtGui.QBrush(QtGui.QColor(128, 134, 148))
        if role == QtCore.Qt.BackgroundRole:
            return self._background_brush(row)
        return None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            return self.headers[section]
        return str(section + 1)

    def set_profit_threshold(self, value: float) -> None:
        self._profit_threshold = value
        if self._rows:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._rows) - 1, len(self.headers) - 1)
            self.dataChanged.emit(top_left, bottom_right, [QtCore.Qt.BackgroundRole])

    def update_rows(self, rows: List[ArbRow]) -> None:
        new_pairs = [row.pair for row in rows]
        old_pairs = [row.pair for row in self._rows]
        if new_pairs != old_pairs:
            self.beginResetModel()
            self._rows = rows
            self.endResetModel()
            return
        changes: List[int] = []
        for idx, (old, new) in enumerate(zip(self._rows, rows)):
            if old != new:
                self._rows[idx] = new
                changes.append(idx)
        for idx in changes:
            top_left = self.index(idx, 0)
            bottom_right = self.index(idx, len(self.headers) - 1)
            self.dataChanged.emit(top_left, bottom_right)

    def row_at(self, row_index: int) -> ArbRow | None:
        if 0 <= row_index < len(self._rows):
            return self._rows[row_index]
        return None

    def _display_data(self, row: ArbRow, column: int) -> str:
        if column == 0:
            return row.pair
        if column == 1:
            return row.buy_exchange
        if column == 2:
            return formatting.format_price(row.buy_price)
        if column == 3:
            return row.sell_exchange
        if column == 4:
            return formatting.format_price(row.sell_price)
        if column == 5:
            text = formatting.format_pct(row.profit_pct)
            if row.profit_pct > 5:
                text += "!"
            return text
        if column == 6:
            return formatting.format_volume(row.volume_24h)
        if column == 7:
            return f"{row.updated_secs:.1f}s"
        if column == 8:
            return formatting.format_price(row.spread)
        if column == 9:
            return row.quality
        return ""

    def _background_brush(self, row: ArbRow) -> QtGui.QBrush | None:
        if row.quality == "Suspicious":
            return QtGui.QBrush(QtGui.QColor(68, 35, 45))
        if row.quality == "Stale":
            return QtGui.QBrush(QtGui.QColor(33, 36, 43))
        if row.profit_pct >= self._profit_threshold:
            return QtGui.QBrush(QtGui.QColor(30, 46, 66))
        return None

    def _sort_value(self, row: ArbRow, column: int):
        if column == 0:
            return row.pair
        if column == 1:
            return row.buy_exchange
        if column == 2:
            return row.buy_price
        if column == 3:
            return row.sell_exchange
        if column == 4:
            return row.sell_price
        if column == 5:
            return row.profit_pct
        if column == 6:
            return row.volume_24h
        if column == 7:
            return row.updated_secs
        if column == 8:
            return row.spread
        if column == 9:
            return row.quality
        return None
