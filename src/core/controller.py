from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from PySide6 import QtCore

from .simulator import MarketSimulator
from .types import ArbRow, ExchangeStatus
from ..utils.formatting import normalize_pair


@dataclass
class FilterSettings:
    top_n: Optional[int]
    min_profit: float
    min_volume: float
    only_usdt: bool
    exclude_leveraged: bool
    show_only_signals: bool
    cooldown_seconds: int
    data_source: str


class RadarController(QtCore.QObject):
    updated = QtCore.Signal(float, int, int, dict)

    def __init__(self, model, log_fn: Callable[[str, str], None]) -> None:
        super().__init__()
        self._model = model
        self._log = log_fn
        self._sim = MarketSimulator()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self.refresh)
        self._filters = FilterSettings(
            top_n=50,
            min_profit=0.5,
            min_volume=100_000,
            only_usdt=False,
            exclude_leveraged=False,
            show_only_signals=False,
            cooldown_seconds=5,
            data_source="Auto",
        )
        self._last_update = time.time()
        self._pair_log_cooldown: Dict[str, float] = {}
        self._last_statuses: Dict[str, str] = {}
        self._last_rows: List[ArbRow] = []
        self._last_status_snapshot: Dict[str, ExchangeStatus] = {}
        self._last_pair_count = 0
        self._stale_sec = 3.0
        self._max_profit_suspicious = 5.0

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
            self._log("INFO", "START scanning")

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
            self._log("INFO", "STOP scanning")

    def refresh_pairs(self) -> None:
        self._sim.refresh_pairs()
        self._pair_log_cooldown.clear()
        self._log("INFO", "Refresh pairs")

    def set_filters(self, filters: FilterSettings) -> None:
        self._filters = filters
        self._model.set_profit_threshold(filters.min_profit)
        if self._last_rows:
            filtered = self._apply_filters(self._last_rows, self._last_status_snapshot)
            self._model.update_rows(filtered)
            signal_count = sum(1 for row in filtered if self._is_signal(row, self._last_status_snapshot))
            self.updated.emit(0.0, self._last_pair_count, signal_count, self._last_status_snapshot)

    def refresh(self) -> None:
        try:
            now = time.time()
            snapshots = self._sim.tick()
            statuses = self._sim.statuses()
            self._log_status_changes(statuses)

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
                spread = sell_price - buy_price
                flags = self._quality_flags(
                    profit_pct=profit_pct,
                    volume_24h=volume,
                    updated_secs=updated_secs,
                    statuses=statuses,
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                )
                quality = self._quality_label(flags)
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
                        spread=spread,
                        quality=quality,
                        quality_flags=tuple(flags),
                        binance_bid=binance.bid,
                        binance_ask=binance.ask,
                        poloniex_bid=poloniex.bid,
                        poloniex_ask=poloniex.ask,
                        data_source=self._filters.data_source,
                    )
                )

            filtered = self._apply_filters(rows, statuses)
            self._model.update_rows(filtered)

            signal_count = sum(1 for row in filtered if self._is_signal(row, statuses))
            last_latency = now - self._last_update
            self._last_update = now
            self._last_rows = rows
            self._last_status_snapshot = statuses
            self._last_pair_count = len(self._sim.pairs())
            self.updated.emit(last_latency, self._last_pair_count, signal_count, statuses)
            self._log_signals(filtered, statuses, now)
        except Exception as exc:  # noqa: BLE001
            self._log("ERROR", f"Controller tick failed: {exc}")

    def _apply_filters(self, rows: List[ArbRow], statuses: Dict[str, ExchangeStatus]) -> List[ArbRow]:
        filtered = [
            row
            for row in rows
            if row.volume_24h >= self._filters.min_volume
            and self._passes_pair_filters(row.pair)
        ]
        if self._filters.show_only_signals:
            filtered = [row for row in filtered if self._is_signal(row, statuses)]
        filtered.sort(key=lambda row: row.profit_pct, reverse=True)
        if self._filters.top_n:
            filtered = filtered[: self._filters.top_n]
        filtered.sort(key=lambda row: row.pair)
        return filtered

    def _passes_pair_filters(self, pair: str) -> bool:
        if self._filters.only_usdt and not pair.endswith("/USDT"):
            return False
        if self._filters.exclude_leveraged and self._is_leveraged(pair):
            return False
        return True

    def _is_leveraged(self, pair: str) -> bool:
        base = pair.split("/")[0]
        return base.endswith("UP") or base.endswith("DOWN")

    def _is_signal(self, row: ArbRow, statuses: Dict[str, ExchangeStatus]) -> bool:
        if row.profit_pct < self._filters.min_profit:
            return False
        for exchange in {row.buy_exchange, row.sell_exchange}:
            if statuses[exchange].status == "Disconnected":
                return False
        return True

    def _quality_flags(
        self,
        *,
        profit_pct: float,
        volume_24h: float,
        updated_secs: float,
        statuses: Dict[str, ExchangeStatus],
        buy_exchange: str,
        sell_exchange: str,
    ) -> List[str]:
        flags: List[str] = []
        if updated_secs > self._stale_sec:
            flags.append("Stale")
        if volume_24h < self._filters.min_volume:
            flags.append("LowVol")
        if profit_pct > self._max_profit_suspicious:
            flags.append("Suspicious")
        for exchange in {buy_exchange, sell_exchange}:
            if statuses[exchange].status == "Disconnected" and "Stale" not in flags:
                flags.append("Stale")
        return flags

    def _quality_label(self, flags: List[str]) -> str:
        if not flags:
            return "OK"
        if "Suspicious" in flags:
            return "Suspicious"
        if "Stale" in flags:
            return "Stale"
        if "LowVol" in flags:
            return "LowVol"
        return flags[0]

    def _log_signals(self, rows: List[ArbRow], statuses: Dict[str, ExchangeStatus], now: float) -> None:
        for row in rows:
            if not self._is_signal(row, statuses):
                continue
            last_time = self._pair_log_cooldown.get(row.pair, 0)
            if now - last_time < self._filters.cooldown_seconds:
                continue
            self._pair_log_cooldown[row.pair] = now
            self._log(
                "SIGNAL",
                f"{row.pair}: Buy {row.buy_exchange} {row.buy_price:,.4f} → "
                f"Sell {row.sell_exchange} {row.sell_price:,.4f} | {row.profit_pct:+.2f}%",
            )

    def _log_status_changes(self, statuses: Dict[str, ExchangeStatus]) -> None:
        for name, status in statuses.items():
            last = self._last_statuses.get(name)
            if last and last != status.status:
                self._log("INFO", f"{name} status → {status.status}")
            self._last_statuses[name] = status.status
