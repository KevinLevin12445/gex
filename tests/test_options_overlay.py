from __future__ import annotations

import pandas as pd

from gex.presentation.dashboard import options_overlay


def _chain() -> pd.DataFrame:
    return pd.DataFrame({
        "strike": [95.0, 100.0, 105.0, 105.0, 95.0],
        "type": ["P", "C", "C", "P", "P"],
        "gex": [-1_000_000.0, 3_000_000.0, 9_000_000.0, -2_000_000.0, -8_000_000.0],
        "open_interest": [100, 200, 400, 50, 500],
        "volume": [10, 20, 40, 5, 50],
    })


def test_overlay_uses_real_candles_and_hoverable_gex_levels(monkeypatch):
    bars = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-09-06 09:30", "2026-09-06 09:31"]),
        "open": [100.0, 101.0], "high": [102.0, 103.0],
        "low": [99.0, 100.0], "close": [101.0, 102.0],
    })
    monkeypatch.setattr(options_overlay.store, "load_prices", lambda *_: bars)

    fig = options_overlay.build_options_overlay(
        "SPY", _chain(), 101.0, 100.0,
        {"call_wall": 105.0, "put_support": 95.0}, "2026-09-06", 0.05,
    )

    assert fig.data[0].type == "candlestick"
    names = {trace.name for trace in fig.data}
    assert {"Call Wall", "Put Wall", "Gamma Flip", "Current price"} <= names
    call_wall = next(trace for trace in fig.data if trace.name == "Call Wall")
    assert "Open interest" in call_wall.hovertemplate
    assert call_wall.customdata[0][1] == 400


def test_overlay_preserves_manual_zoom_and_renders_snapshot_activity(monkeypatch):
    bars = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-09-06 09:30", "2026-09-06 09:31"]),
        "open": [100.0, 101.0], "high": [102.0, 103.0],
        "low": [99.0, 100.0], "close": [101.0, 102.0],
    })
    monkeypatch.setattr(options_overlay.store, "load_prices", lambda *_: bars)
    snapshots = [(pd.Timestamp("2026-09-06 09:30"), _chain()),
                 (pd.Timestamp("2026-09-06 09:31"), _chain())]

    fig = options_overlay.build_options_overlay(
        "SPY", _chain(), 101.0, 100.0,
        {"call_wall": 105.0, "put_support": 95.0}, "2026-09-06", 0.05,
        snapshots=snapshots,
        relayout={"yaxis.range[0]": 98.0, "yaxis.range[1]": 106.0},
    )

    assert fig.layout.yaxis.range == (98.0, 106.0)
    assert "Active call GEX" in {trace.name for trace in fig.data}


def test_overlay_merges_partial_axis_events_with_current_ranges():
    merged = options_overlay.merge_relayout_ranges(
        {"yaxis.range[0]": 98.0, "yaxis.range[1]": 106.0},
        {"layout": {
            "xaxis": {"range": ["2026-09-06 09:30", "2026-09-06 10:30"]},
            "yaxis": {"range": [98.0, 106.0]},
        }},
    )

    assert merged["xaxis.range"] == ["2026-09-06 09:30", "2026-09-06 10:30"]
    assert merged["yaxis.range[0]"] == 98.0
    assert merged["yaxis.range[1]"] == 106.0


def test_overlay_keeps_both_axes_scrollable(monkeypatch):
    bars = pd.DataFrame({
        "timestamp": pd.date_range("2026-09-07 09:30", periods=2, freq="min"),
        "open": [100.0, 101.0], "high": [101.0, 102.0],
        "low": [99.0, 100.0], "close": [100.5, 101.5],
    })
    monkeypatch.setattr(options_overlay.store, "load_prices", lambda *_: bars)
    monkeypatch.setattr(options_overlay.store, "price_days", lambda *_: [])
    fig = options_overlay.build_options_overlay(
        "SPY", _chain(), 101.0, None, {}, "2026-09-07", 0.05,
    )
    assert fig.layout.yaxis.fixedrange is False
    assert fig.layout.xaxis.fixedrange is False


def test_overlay_does_not_create_synthetic_candles(monkeypatch):
    monkeypatch.setattr(options_overlay.store, "load_prices", lambda *_: pd.DataFrame())

    fig = options_overlay.build_options_overlay(
        "SPY", _chain(), 100.0, None, {}, "2026-09-06", 0.05,
    )

    assert not fig.data
    assert fig.layout.annotations


def test_overlay_renders_three_call_and_put_levels(monkeypatch):
    bars = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-09-06 09:30", "2026-09-06 09:31"]),
        "open": [100.0, 101.0], "high": [102.0, 103.0],
        "low": [99.0, 100.0], "close": [101.0, 102.0],
    })
    monkeypatch.setattr(options_overlay.store, "load_prices", lambda *_: bars)
    chain = pd.DataFrame({
        "strike": [102.0, 103.0, 104.0, 98.0, 97.0, 96.0],
        "type": ["C", "C", "C", "P", "P", "P"],
        "gex": [6.0, 5.0, 4.0, -6.0, -5.0, -4.0],
        "open_interest": [1, 2, 3, 4, 5, 6],
        "volume": [1, 2, 3, 4, 5, 6],
    })

    fig = options_overlay.build_options_overlay(
        "SPY", chain, 101.0, None,
        {
            "call_walls": [102.0, 103.0, 104.0],
            "put_supports": [98.0, 97.0, 96.0],
        },
        "2026-09-06", 0.05,
    )

    names = {trace.name for trace in fig.data}
    assert {"Call Wall", "Call Wall 2", "Call Wall 3",
            "Put Wall", "Put Wall 2", "Put Wall 3"} <= names


def test_overlay_includes_previous_session_and_keeps_walls_in_view(monkeypatch):
    current = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-09-07 09:30", "2026-09-07 09:31"]),
        "open": [100.0, 101.0], "high": [102.0, 103.0],
        "low": [99.0, 100.0], "close": [101.0, 102.0],
    })
    previous = current.copy()
    previous["timestamp"] = previous["timestamp"] - pd.Timedelta(days=1)
    monkeypatch.setattr(options_overlay.store, "load_prices",
                        lambda symbol, day: previous if day == "2026-09-06" else current)
    monkeypatch.setattr(options_overlay.store, "price_days",
                        lambda symbol: ["2026-09-06"])

    fig = options_overlay.build_options_overlay(
        "SPY", _chain(), 101.0, None,
        {"call_walls": [105.0, 106.0, 107.0],
         "put_supports": [95.0, 94.0, 93.0]},
        "2026-09-07", 0.05, timeframe="2d",
    )

    assert len(fig.data[0].x) == 4
    assert fig.layout.yaxis.range[0] < 93.0
    assert fig.layout.yaxis.range[1] > 107.0
    wall = next(trace for trace in fig.data if trace.name == "Call Wall")
    assert wall.line.width <= 2.5


def test_overlay_timeframe_changes_candle_count(monkeypatch):
    bars = pd.DataFrame({
        "timestamp": pd.date_range("2026-09-07 09:30", periods=12, freq="min"),
        "open": range(100, 112), "high": range(101, 113),
        "low": range(99, 111), "close": range(100, 112),
    })
    monkeypatch.setattr(options_overlay.store, "load_prices", lambda *_: bars)
    monkeypatch.setattr(options_overlay.store, "price_days", lambda *_: [])

    one_minute = options_overlay.build_options_overlay(
        "SPY", _chain(), 101.0, None, {}, "2026-09-07", 0.05, timeframe="1m",
    )
    five_minutes = options_overlay.build_options_overlay(
        "SPY", _chain(), 101.0, None, {}, "2026-09-07", 0.05, timeframe="5m",
    )

    assert len(one_minute.data[0].x) == 12
    assert len(five_minutes.data[0].x) == 3


def test_overlay_preserves_selected_pan_or_zoom_mode(monkeypatch):
    bars = pd.DataFrame({
        "timestamp": pd.date_range("2026-09-07 09:30", periods=3, freq="min"),
        "open": [100.0, 101.0, 102.0], "high": [101.0, 102.0, 103.0],
        "low": [99.0, 100.0, 101.0], "close": [100.5, 101.5, 102.5],
    })
    monkeypatch.setattr(options_overlay.store, "load_prices", lambda *_: bars)
    monkeypatch.setattr(options_overlay.store, "price_days", lambda *_: [])

    fig = options_overlay.build_options_overlay(
        "SPY", _chain(), 101.0, None, {}, "2026-09-07", 0.05,
        relayout={"dragmode": "zoom"},
    )

    assert fig.layout.dragmode == "zoom"


def test_overlay_short_timeframes_do_not_prepend_dead_session(monkeypatch):
    live = pd.DataFrame({
        "timestamp": pd.date_range("2026-09-07 09:30", periods=2, freq="min"),
        "open": [100.0, 101.0], "high": [101.0, 102.0],
        "low": [99.0, 100.0], "close": [100.5, 101.5],
    })
    previous = live.copy()
    previous["timestamp"] -= pd.Timedelta(days=1)
    monkeypatch.setattr(options_overlay.store, "load_prices",
                        lambda symbol, day: previous if day == "2026-09-06" else live)
    monkeypatch.setattr(options_overlay.store, "price_days", lambda symbol: ["2026-09-06"])

    fig = options_overlay.build_options_overlay(
        "SPY", _chain(), 101.0, None, {}, "2026-09-07", 0.05, timeframe="1m",
    )

    assert len(fig.data[0].x) == 2
    assert not fig.layout.xaxis.rangebreaks
