from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, List

from .types import QuoteSnapshot


@dataclass
class PairState:
    base_price: float
    volume_24h: float
    last_update: float


class MarketSimulator:
    def __init__(self, seed: int | None = None) -> None:
        self._rand = random.Random(seed)
        self._pairs = self._generate_pairs()
        now = time.time()
        self._state: Dict[str, PairState] = {
            pair: PairState(
                base_price=self._rand.uniform(0.5, 60000.0),
                volume_24h=self._rand.uniform(10_000, 1_000_000),
                last_update=now,
            )
            for pair in self._pairs
        }

    def pairs(self) -> List[str]:
        return list(self._pairs)

    def tick(self) -> Dict[str, Dict[str, QuoteSnapshot]]:
        now = time.time()
        snapshots: Dict[str, Dict[str, QuoteSnapshot]] = {}
        for pair, state in self._state.items():
            drift = self._rand.uniform(-0.6, 0.6)
            state.base_price = max(0.01, state.base_price * (1 + drift / 100))
            state.volume_24h = max(500.0, state.volume_24h * (1 + self._rand.uniform(-0.8, 0.8) / 100))
            state.last_update = now

            snapshots[pair] = {
                "Binance": self._make_quote("Binance", pair, state, now),
                "Poloniex": self._make_quote("Poloniex", pair, state, now),
            }
        return snapshots

    def _make_quote(self, exchange: str, pair: str, state: PairState, now: float) -> QuoteSnapshot:
        exchange_bias = 1 + self._rand.uniform(-0.15, 0.15) / 100
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
