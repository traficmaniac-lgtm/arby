from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from .types import ExchangeStatus, QuoteSnapshot


class ExchangeClient(ABC):
    name: str

    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_pairs(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get_best_quotes(self, pairs: List[str]) -> Dict[str, QuoteSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> ExchangeStatus:
        raise NotImplementedError
