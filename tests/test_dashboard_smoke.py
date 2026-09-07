from pathlib import Path

import pandas as pd

from gex.presentation.dashboard import heatmap
from gex.presentation.dashboard.main import available_overlay_days, create_app


def test_dashboard_uses_packaged_assets_and_registers_callbacks():
    app = create_app()
    assert Path(app.config.assets_folder).is_dir()
    assert any("heatmap-intraday.figure" in key for key in app.callback_map)
    assert any("options-flow-overlay.figure" in key for key in app.callback_map)


def test_overlay_days_require_both_price_and_options_snapshot(monkeypatch):
    monkeypatch.setattr("gex.presentation.dashboard.main.store.price_days", lambda _: ["2026-08-19", "2026-08-20"])
    monkeypatch.setattr("gex.presentation.dashboard.main.store.snapshot_days", lambda _: ["2026-08-20"])
    assert available_overlay_days("SPX") == ["2026-08-20"]


def test_intraday_heatmap_uses_real_spots_and_never_synthesizes_candles(monkeypatch):
    frame = pd.DataFrame({
        "strike": [95.0, 100.0, 105.0],
        "spot": [100.0, 100.0, 100.0],
        "gex": [-2_000_000.0, 4_000_000.0, -1_000_000.0],
        "open_interest": [10, 20, 15],
        "volume": [2, 4, 1],
        "type": ["P", "C", "P"],
    })
    monkeypatch.setattr(
        heatmap,
        "_snapshots",
        lambda *_: ([(pd.Timestamp("2026-09-06 09:30"), frame),
                     (pd.Timestamp("2026-09-06 09:31"), frame)], 100.0),
    )
    monkeypatch.setattr(heatmap.metrics, "key_levels", lambda *_args, **_kwargs: {"call_wall": 105.0, "put_support": 95.0})
    monkeypatch.setattr(heatmap.metrics, "zero_gamma", lambda *_args, **_kwargs: 100.0)

    figure = heatmap.build_intraday_heatmap("SPX", "es", "2026-09-06", 0.05)

    assert figure.data[0].type == "heatmap"
    assert figure.data[1].type == "scatter"
    assert all(trace.type != "candlestick" for trace in figure.data)
    assert len(figure.layout.shapes) == 3


def test_intraday_heatmap_returns_an_empty_state_when_no_snapshot_exists(monkeypatch):
    monkeypatch.setattr(heatmap, "_snapshots", lambda *_: ([], 0.0))
    figure = heatmap.build_intraday_heatmap("SPX", "es", "2026-09-06", 0.05)
    assert figure.layout.annotations
