from __future__ import annotations


def format_price(value: float) -> str:
    return f"{value:,.4f}"


def format_pct(value: float) -> str:
    return f"{value:.2f}%"


def format_volume(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:.0f}"


def normalize_pair(pair: str) -> str:
    return pair.replace("-", "/").upper()
