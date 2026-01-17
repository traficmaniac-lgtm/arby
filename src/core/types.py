from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuoteSnapshot:
    exchange: str
    pair: str
    bid: float
    ask: float
    volume_24h: float
    timestamp: float


@dataclass(frozen=True)
class ArbRow:
    pair: str
    buy_exchange: str
    buy_price: float
    sell_exchange: str
    sell_price: float
    profit_pct: float
    volume_24h: float
    updated_secs: float


@dataclass(frozen=True)
class ExchangeStatus:
    name: str
    connected: bool
    latency_s: float
