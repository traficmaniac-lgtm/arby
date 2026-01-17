from __future__ import annotations

from src.core.config import AppConfig, load_config, save_config
from src.core.controller import FilterSettings, RadarController
from src.core.types import ArbRow
from src.models.radar_model import RadarModel


def test_imports() -> None:
    from src.app import main
    from src.ui.main_window import MainWindow

    assert callable(main)
    assert MainWindow is not None
    assert RadarModel is not None
    assert RadarController is not None


def test_config_load_save(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("ARBY_CONFIG_PATH", str(config_path))

    config = AppConfig(
        window_geometry="deadbeef",
        splitter_sizes_horizontal=[1, 2],
        splitter_sizes_vertical=[3, 4],
        top_n=25,
        min_profit_pct=1.5,
        min_volume=250_000.0,
        cooldown_sec=7,
        only_usdt=True,
        exclude_leveraged=True,
        show_only_signals=True,
        show_favorites_only=True,
        max_profit_suspicious=9.0,
        stale_sec=4,
        update_interval_ms=750,
        data_source="Simulator",
        favorites=["BTC/USDT"],
    )
    save_config(config)
    loaded = load_config()

    assert loaded.top_n == 25
    assert loaded.min_profit_pct == 1.5
    assert loaded.only_usdt is True
    assert loaded.favorites == ["BTC/USDT"]


def test_model_basic() -> None:
    model = RadarModel()
    row = ArbRow(
        favorite=False,
        pair="BTC/USDT",
        buy_exchange="Binance",
        buy_price=30000.0,
        sell_exchange="Poloniex",
        sell_price=30100.0,
        profit_pct=0.33,
        volume_24h=500_000.0,
        updated_secs=0.5,
        spread=100.0,
        quality="OK",
        quality_flags=tuple(),
        updated_ts=1700000000.0,
        binance_bid=29950.0,
        binance_ask=30000.0,
        poloniex_bid=30100.0,
        poloniex_ask=30150.0,
        data_source="Simulator",
    )
    model.update_rows([row])

    assert model.rowCount() == 1
    assert model.columnCount() == len(model.headers)
    assert model.data(model.index(0, 1)) == "BTC/USDT"
    assert model.data(model.index(0, 6)).endswith("%")


def test_controller_tick_mock() -> None:
    model = RadarModel()
    logs: list[tuple[str, str]] = []

    def log_fn(level: str, message: str) -> None:
        logs.append((level, message))

    controller = RadarController(model, log_fn)
    controller.set_filters(
        FilterSettings(
            top_n=5,
            min_profit=0.0,
            min_volume=0.0,
            only_usdt=False,
            exclude_leveraged=False,
            show_only_signals=False,
            show_favorites_only=False,
            cooldown_seconds=1,
            max_profit_suspicious=10.0,
            stale_sec=5,
            update_interval_ms=500,
            data_source="Simulator",
        )
    )
    controller.refresh()

    assert model.rowCount() > 0
