from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, List

from .types import ExchangeStatus, QuoteSnapshot


@dataclass
class PairState:
    base_price: float
    volume_24h: float
    last_update: float


class MarketSimulator:
    def __init__(self, seed: int | None = None) -> None:
        self._rand = random.Random(seed)
        self._pairs: List[str] = []
        self._state: Dict[str, PairState] = {}
        self._last_quotes: Dict[str, Dict[str, QuoteSnapshot]] = {}
        self._exchange_status: Dict[str, ExchangeStatus] = {}
        self._refresh_pairs()
        self._exchange_status = {
            "Binance": ExchangeStatus(name="Binance", status="Connected", latency_s=0.12, changed_at=time.time()),
            "Poloniex": ExchangeStatus(name="Poloniex", status="Connected", latency_s=0.18, changed_at=time.time()),
        }

    def pairs(self) -> List[str]:
        return list(self._pairs)

    def statuses(self) -> Dict[str, ExchangeStatus]:
        return dict(self._exchange_status)

    def refresh_pairs(self) -> None:
        self._refresh_pairs()

    def tick(self) -> Dict[str, Dict[str, QuoteSnapshot]]:
        now = time.time()
        self._maybe_toggle_status(now)
        snapshots: Dict[str, Dict[str, QuoteSnapshot]] = {}
        for pair, state in self._state.items():
            drift = self._rand.uniform(-0.6, 0.6)
            state.base_price = max(0.01, state.base_price * (1 + drift / 100))
            state.volume_24h = max(500.0, state.volume_24h * (1 + self._rand.uniform(-0.8, 0.8) / 100))
            state.last_update = now

            snapshots[pair] = {}
            for exchange in ("Binance", "Poloniex"):
                status = self._exchange_status[exchange]
                if status.status == "Disconnected":
                    snapshots[pair][exchange] = self._last_quotes[pair][exchange]
                    continue
                if status.status == "Degraded":
                    snapshots[pair][exchange] = self._make_quote(exchange, pair, state, now, jitter=0.35)
                else:
                    snapshots[pair][exchange] = self._make_quote(exchange, pair, state, now, jitter=0.18)
            self._last_quotes[pair] = snapshots[pair]
        return snapshots

    def _make_quote(
        self,
        exchange: str,
        pair: str,
        state: PairState,
        now: float,
        jitter: float,
    ) -> QuoteSnapshot:
        exchange_bias = 1 + self._rand.uniform(-jitter, jitter) / 100
        mid = state.base_price * exchange_bias
        spread = max(0.0005, self._rand.uniform(0.05, 0.2) / 100)
        bid = mid * (1 - spread)
        ask = mid * (1 + spread)
        volume = state.volume_24h * self._rand.uniform(0.7, 1.3)
        return QuoteSnapshot(
            exchange=exchange,
            pair=pair,
            bid=bid,
            ask=ask,
            volume_24h=volume,
            timestamp=now,
        )

    def _generate_pairs(self) -> List[str]:
        bases = [
            "BTC",
            "ETH",
            "SOL",
            "XRP",
            "ADA",
            "DOT",
            "AVAX",
            "MATIC",
            "LTC",
            "LINK",
            "ATOM",
            "NEAR",
            "APT",
            "SUI",
        ]
        quotes = ["USDT", "USD", "BTC", "ETH"]
        leveraged = ["UP", "DOWN"]
        pairs: List[str] = []
        total = self._rand.randint(220, 380)
        while len(pairs) < total:
            base = self._rand.choice(bases)
            quote = self._rand.choice(quotes)
            if base == quote:
                continue
            pair = f"{base}/{quote}"
            if self._rand.random() < 0.12:
                pair = f"{base}{self._rand.choice(leveraged)}/{quote}"
            if pair not in pairs:
                pairs.append(pair)
        return pairs

    def _refresh_pairs(self) -> None:
        self._pairs = self._generate_pairs()
        now = time.time()
        self._state = {
            pair: PairState(
                base_price=self._rand.uniform(0.5, 60000.0),
                volume_24h=self._rand.uniform(10_000, 1_000_000),
                last_update=now,
            )
            for pair in self._pairs
        }
        self._last_quotes = {
            pair: {
                "Binance": self._make_quote("Binance", pair, state, now, jitter=0.18),
                "Poloniex": self._make_quote("Poloniex", pair, state, now, jitter=0.18),
            }
            for pair, state in self._state.items()
        }

    def _maybe_toggle_status(self, now: float) -> None:
        for name, status in list(self._exchange_status.items()):
            roll = self._rand.random()
            next_status = status.status
            if status.status == "Connected" and roll < 0.02:
                next_status = "Degraded"
            elif status.status == "Degraded" and roll < 0.04:
                next_status = "Disconnected"
            elif status.status == "Degraded" and roll < 0.18:
                next_status = "Connected"
            elif status.status == "Disconnected" and roll < 0.12:
                next_status = "Connected"

            latency = 0.12 if name == "Binance" else 0.18
            if next_status == "Degraded":
                latency *= 2.5
            elif next_status == "Disconnected":
                latency *= 5

            if next_status != status.status:
                self._exchange_status[name] = ExchangeStatus(
                    name=name,
                    status=next_status,
                    latency_s=latency,
                    changed_at=now,
                )
            else:
                self._exchange_status[name] = ExchangeStatus(
                    name=name,
                    status=status.status,
                    latency_s=latency,
                    changed_at=status.changed_at,
                )
