from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"


def config_path() -> Path:
    env_path = os.environ.get("ARBY_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_CONFIG_PATH


@dataclass
class AppConfig:
    window_geometry: str | None = None
    splitter_sizes_horizontal: list[int] = field(default_factory=list)
    splitter_sizes_vertical: list[int] = field(default_factory=list)
    top_n: int | None = 50
    min_profit_pct: float = 0.5
    min_volume: float = 100_000.0
    cooldown_sec: int = 5
    only_usdt: bool = False
    exclude_leveraged: bool = False
    show_only_signals: bool = False
    show_favorites_only: bool = False
    max_profit_suspicious: float = 5.0
    stale_sec: int = 3
    update_interval_ms: int = 500
    data_source: str = "Simulator"
    favorites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_geometry": self.window_geometry,
            "splitter_sizes_horizontal": self.splitter_sizes_horizontal,
            "splitter_sizes_vertical": self.splitter_sizes_vertical,
            "top_n": self.top_n,
            "min_profit_pct": self.min_profit_pct,
            "min_volume": self.min_volume,
            "cooldown_sec": self.cooldown_sec,
            "only_usdt": self.only_usdt,
            "exclude_leveraged": self.exclude_leveraged,
            "show_only_signals": self.show_only_signals,
            "show_favorites_only": self.show_favorites_only,
            "max_profit_suspicious": self.max_profit_suspicious,
            "stale_sec": self.stale_sec,
            "update_interval_ms": self.update_interval_ms,
            "data_source": self.data_source,
            "favorites": list(self.favorites),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        return cls(
            window_geometry=payload.get("window_geometry"),
            splitter_sizes_horizontal=payload.get("splitter_sizes_horizontal", []),
            splitter_sizes_vertical=payload.get("splitter_sizes_vertical", []),
            top_n=payload.get("top_n", 50),
            min_profit_pct=payload.get("min_profit_pct", 0.5),
            min_volume=payload.get("min_volume", 100_000.0),
            cooldown_sec=payload.get("cooldown_sec", 5),
            only_usdt=payload.get("only_usdt", False),
            exclude_leveraged=payload.get("exclude_leveraged", False),
            show_only_signals=payload.get("show_only_signals", False),
            show_favorites_only=payload.get("show_favorites_only", False),
            max_profit_suspicious=payload.get("max_profit_suspicious", 5.0),
            stale_sec=payload.get("stale_sec", 3),
            update_interval_ms=payload.get("update_interval_ms", 500),
            data_source=payload.get("data_source", "Simulator"),
            favorites=payload.get("favorites", []),
        )


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        return AppConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return AppConfig()
    return AppConfig.from_dict(data)


def save_config(config: AppConfig) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
