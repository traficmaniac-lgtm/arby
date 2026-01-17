from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from PySide6 import QtCore

from .simulator import MarketSimulator
from .types import ArbRow
from ..utils.formatting import normalize_pair


@dataclass
class FilterSettings:
    top_n: Optional[int]
    min_profit: float
    min_volume: float
    search_pair: str


class RadarController(QtCore.QObject):
    updated = QtCore.Signal(float, int, int)

    def __init__(self, model, log_fn: Callable[[str], None]) -> None:
        super().__init__()
        self._model = model
        self._log = log_fn
        self._sim = MarketSimulator()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self.refresh)
        self._filters = FilterSettings(top_n=50, min_profit=0.5, min_volume=100_000, search_pair="")
        self._last_update = time.time()
        self._pair_log_cooldown: Dict[str, float] = {}

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
            self._log("START scanning")

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
            self._log("STOP scanning")

    def set_filters(self, filters: FilterSettings) -> None:
        self._filters = filters
        self._model.set_profit_threshold(filters.min_profit)

    def refresh(self) -> None:
        now = time.time()
        snapshots = self._sim.tick()
        rows: List[ArbRow] = []
        for pair, quotes in snapshots.items():
            binance = quotes["Binance"]
            poloniex = quotes["Poloniex"]
            buy_exchange, buy_price = ("Binance", binance.ask)
            sell_exchange, sell_price = ("Poloniex", poloniex.bid)
            if poloniex.ask < binance.ask:
                buy_exchange, buy_price = ("Poloniex", poloniex.ask)
            if binance.bid > poloniex.bid:
                sell_exchange, sell_price = ("Binance", binance.bid)
            profit_pct = ((sell_price - buy_price) / buy_price) * 100
            volume = min(binance.volume_24h, poloniex.volume_24h)
            updated_secs = now - max(binance.timestamp, poloniex.timestamp)
            rows.append(
                ArbRow(
                    pair=normalize_pair(pair),
                    buy_exchange=buy_exchange,
                    buy_price=buy_price,
                    sell_exchange=sell_exchange,
                    sell_price=sell_price,
                    profit_pct=profit_pct,
                    volume_24h=volume,
                    updated_secs=updated_secs,
                )
            )

        filtered = self._apply_filters(rows)
        self._model.update_rows(filtered)
        signal_count = sum(1 for row in filtered if row.profit_pct >= self._filters.min_profit)
        last_latency = now - self._last_update
        self._last_update = now
        self.updated.emit(last_latency, len(self._sim.pairs()), signal_count)
        self._log_signals(filtered, now)

    def _apply_filters(self, rows: List[ArbRow]) -> List[ArbRow]:
        filtered = [
            row
            for row in rows
            if row.profit_pct >= self._filters.min_profit
            and row.volume_24h >= self._filters.min_volume
        ]
        filtered.sort(key=lambda row: row.profit_pct, reverse=True)
        if self._filters.top_n:
            filtered = filtered[: self._filters.top_n]
        filtered.sort(key=lambda row: row.pair)
        return filtered

    def _log_signals(self, rows: List[ArbRow], now: float) -> None:
        for row in rows:
            last_time = self._pair_log_cooldown.get(row.pair, 0)
            if now - last_time < 5:
                continue
            self._pair_log_cooldown[row.pair] = now
            self._log(
                f"SIGNAL {row.pair}: Buy {row.buy_exchange} {row.buy_price:,.4f} → "
                f"Sell {row.sell_exchange} {row.sell_price:,.4f} | {row.profit_pct:+.2f}%"
            )
