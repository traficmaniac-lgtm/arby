from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List

from src.core.exchange_client import ExchangeClient
from src.core.simulator import MarketSimulator
from src.core.types import ExchangeStatus, QuoteSnapshot


class SimulatorClient(ExchangeClient):
    def __init__(self, name: str, simulator: MarketSimulator) -> None:
        self.name = name
        self._simulator = simulator

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def get_pairs(self) -> List[str]:
        return self._simulator.pairs()

    def get_best_quotes(self, pairs: List[str]) -> Dict[str, QuoteSnapshot]:
        last_quotes = self._simulator.last_quotes()
        quotes: Dict[str, QuoteSnapshot] = {}
        for pair in pairs:
            if pair in last_quotes and self.name in last_quotes[pair]:
                quotes[pair] = last_quotes[pair][self.name]
        return quotes

    def status(self) -> ExchangeStatus:
        return self._simulator.statuses()[self.name]


class RealClientStub(ExchangeClient):
    def __init__(self, name: str) -> None:
        self.name = name
        self._status = ExchangeStatus(name=name, status="Disconnected", latency_s=0.0, changed_at=time.time())

    def connect(self) -> None:
        self._status = ExchangeStatus(name=self.name, status="Disconnected", latency_s=0.0, changed_at=time.time())

    def disconnect(self) -> None:
        self._status = ExchangeStatus(name=self.name, status="Disconnected", latency_s=0.0, changed_at=time.time())

    def get_pairs(self) -> List[str]:
        return []

    def get_best_quotes(self, pairs: List[str]) -> Dict[str, QuoteSnapshot]:
        return {}

    def status(self) -> ExchangeStatus:
        return self._status


@dataclass
class ProviderSnapshot:
    quotes: Dict[str, Dict[str, QuoteSnapshot]]
    statuses: Dict[str, ExchangeStatus]
    pair_count: int
    mode: str


class DataProvider:
    def __init__(self, mode: str = "Simulator") -> None:
        self._mode = mode
        self._simulator = MarketSimulator()
        self._pairs: List[str] = []
        self._clients: Dict[str, ExchangeClient] = {}
        self.set_mode(mode)

    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "Simulator":
            self._clients = {
                "Binance": SimulatorClient("Binance", self._simulator),
                "Poloniex": SimulatorClient("Poloniex", self._simulator),
            }
            self.refresh_pairs()
        else:
            self._clients = {
                "Binance": RealClientStub("Binance"),
                "Poloniex": RealClientStub("Poloniex"),
            }
            self._pairs = []

    def refresh_pairs(self) -> List[str]:
        if self._mode != "Simulator":
            self._pairs = []
            return []
        binance_pairs = set(self._clients["Binance"].get_pairs())
        poloniex_pairs = set(self._clients["Poloniex"].get_pairs())
        self._pairs = sorted(binance_pairs.intersection(poloniex_pairs))
        return list(self._pairs)

    def pairs(self) -> List[str]:
        return list(self._pairs)

    def tick(self) -> ProviderSnapshot:
        if self._mode == "Simulator":
            self._simulator.tick()
            quotes: Dict[str, Dict[str, QuoteSnapshot]] = {}
            for pair in self._pairs:
                quotes[pair] = {
                    "Binance": self._clients["Binance"].get_best_quotes([pair]).get(pair),
                    "Poloniex": self._clients["Poloniex"].get_best_quotes([pair]).get(pair),
                }
            statuses = {name: client.status() for name, client in self._clients.items()}
            return ProviderSnapshot(quotes=quotes, statuses=statuses, pair_count=len(self._pairs), mode=self._mode)
        statuses = {name: client.status() for name, client in self._clients.items()}
        return ProviderSnapshot(quotes={}, statuses=statuses, pair_count=0, mode=self._mode)
