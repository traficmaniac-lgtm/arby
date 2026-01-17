from __future__ import annotations

from typing import List, Set

from PySide6 import QtCore, QtGui

from src.core.types import ArbRow
from src.utils import formatting


class RadarModel(QtCore.QAbstractTableModel):
    headers = [
        "★",
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
        self._favorites: Set[str] = set()
        self._show_favorites_only = False

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
            if column in {3, 5, 6, 7, 8, 9}:
                return QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            if column == 0:
                return QtCore.Qt.AlignCenter
            return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        if role == QtCore.Qt.FontRole and column == 6:
            font = QtGui.QFont()
            font.setBold(True)
            font.setPointSize(11)
            return font
        if role == QtCore.Qt.ForegroundRole and row.quality == "Stale":
            return QtGui.QBrush(QtGui.QColor(128, 134, 148))
        if role == QtCore.Qt.BackgroundRole:
            return self._background_brush(row, column)
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

    def set_show_favorites_only(self, enabled: bool) -> None:
        self._show_favorites_only = enabled

    def set_favorites(self, favorites: List[str]) -> None:
        self._favorites = {pair.upper() for pair in favorites}
        self._sync_favorites()

    def is_favorite(self, pair: str) -> bool:
        return pair.upper() in self._favorites

    def toggle_favorite(self, pair: str) -> None:
        normalized = pair.upper()
        if normalized in self._favorites:
            self._favorites.remove(normalized)
        else:
            self._favorites.add(normalized)
        self._sync_favorites()

    def favorites(self) -> List[str]:
        return sorted(self._favorites)

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
            return "★" if row.favorite else ""
        if column == 1:
            return row.pair
        if column == 2:
            return row.buy_exchange
        if column == 3:
            return formatting.format_price(row.buy_price)
        if column == 4:
            return row.sell_exchange
        if column == 5:
            return formatting.format_price(row.sell_price)
        if column == 6:
            text = formatting.format_pct(row.profit_pct)
            if row.profit_pct > 5:
                text += "!"
            return text
        if column == 7:
            return formatting.format_volume(row.volume_24h)
        if column == 8:
            return f"{row.updated_secs:.1f}s"
        if column == 9:
            return formatting.format_price(row.spread)
        if column == 10:
            return row.quality
        return ""

    def _background_brush(self, row: ArbRow, column: int) -> QtGui.QBrush | None:
        if column == 6 and row.profit_pct > 0:
            intensity = min(row.profit_pct / max(self._profit_threshold, 0.01), 2.0)
            alpha = int(min(180, 40 + intensity * 60))
            return QtGui.QBrush(QtGui.QColor(35, 62, 88, alpha))
        if row.quality == "Suspicious":
            return QtGui.QBrush(QtGui.QColor(68, 35, 45))
        if row.quality == "Stale":
            return QtGui.QBrush(QtGui.QColor(33, 36, 43))
        if row.profit_pct >= self._profit_threshold:
            return QtGui.QBrush(QtGui.QColor(30, 46, 66))
        return None

    def _sort_value(self, row: ArbRow, column: int):
        if column == 0:
            return 1 if row.favorite else 0
        if column == 1:
            return row.pair
        if column == 2:
            return row.buy_exchange
        if column == 3:
            return row.buy_price
        if column == 4:
            return row.sell_exchange
        if column == 5:
            return row.sell_price
        if column == 6:
            return row.profit_pct
        if column == 7:
            return row.volume_24h
        if column == 8:
            return row.updated_secs
        if column == 9:
            return row.spread
        if column == 10:
            return row.quality
        return None

    def _sync_favorites(self) -> None:
        if not self._rows:
            return
        changes: List[int] = []
        for idx, row in enumerate(self._rows):
            is_favorite = row.pair.upper() in self._favorites
            if row.favorite != is_favorite:
                self._rows[idx] = ArbRow(
                    favorite=is_favorite,
                    pair=row.pair,
                    buy_exchange=row.buy_exchange,
                    buy_price=row.buy_price,
                    sell_exchange=row.sell_exchange,
                    sell_price=row.sell_price,
                    profit_pct=row.profit_pct,
                    volume_24h=row.volume_24h,
                    updated_secs=row.updated_secs,
                    spread=row.spread,
                    quality=row.quality,
                    quality_flags=row.quality_flags,
                    updated_ts=row.updated_ts,
                    binance_bid=row.binance_bid,
                    binance_ask=row.binance_ask,
                    poloniex_bid=row.poloniex_bid,
                    poloniex_ask=row.poloniex_ask,
                    data_source=row.data_source,
                )
                changes.append(idx)
        for idx in changes:
            top_left = self.index(idx, 0)
            bottom_right = self.index(idx, len(self.headers) - 1)
            self.dataChanged.emit(top_left, bottom_right)
