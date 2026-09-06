"""Tests para el módulo de Posicionamiento (datos reales, max pain, distribución, histórico y variación)."""
import numpy as np
import pandas as pd
import pytest

from gex.app import (
    calc_max_pain,
    build_positioning_cards,
    pos_distribution_fig,
    pos_history_fig,
    oi_change_fig,
    create_app,
)
import gex.store as store


def test_calc_max_pain_empty():
    assert calc_max_pain(pd.DataFrame()) == 0.0
    assert calc_max_pain(None) == 0.0


def test_calc_max_pain_synthetic():
    df = pd.DataFrame([
        {"strike": 90.0, "type": "C", "open_interest": 100.0},
        {"strike": 100.0, "type": "C", "open_interest": 500.0},
        {"strike": 110.0, "type": "C", "open_interest": 100.0},
        {"strike": 90.0, "type": "P", "open_interest": 100.0},
        {"strike": 100.0, "type": "P", "open_interest": 500.0},
        {"strike": 110.0, "type": "P", "open_interest": 100.0},
    ])
    mp = calc_max_pain(df)
    assert mp == 100.0


def test_calc_max_pain_real_spx():
    df = store.load_last_snapshot("SPX", "2026-09-06")
    if df is None or df.empty:
        df = store.load_last_snapshot("SPX", "2026-09-05")
    assert df is not None and not df.empty
    mp = calc_max_pain(df)
    assert 5000 <= mp <= 9000


def test_build_positioning_cards():
    cards = build_positioning_cards("SPX", "es")
    assert cards is not None
    assert "pos-cards" in cards.className
    assert len(cards.children) == 6


def test_pos_distribution_fig():
    df = store.load_last_snapshot("SPX", "2026-09-06")
    if df is None or df.empty:
        df = store.load_last_snapshot("SPX", "2026-09-05")
    spot = float(df["spot"].iloc[0])
    mp = calc_max_pain(df)
    fig = pos_distribution_fig(df, spot, "es", window=0.10, max_pain=mp)
    assert fig is not None
    assert len(fig.data) == 2
    assert fig.layout.barmode == "group"


def test_pos_history_fig():
    fig = pos_history_fig("SPX", "es")
    assert fig is not None
    assert len(fig.data) >= 2


def test_oi_change_zero_delta_fallback():
    df = store.load_last_snapshot("SPX", "2026-09-06")
    spot = float(df["spot"].iloc[0])
    fig = oi_change_fig(pd.DataFrame(), spot, "es", "2026-09-05", 0.15, df_cur=df)
    assert fig is not None
    assert len(fig.data) >= 1
    assert "Net OI" in fig.data[0].name


def test_app_positioning_layout():
    app = create_app()
    layout_str = str(app.layout)
    assert "pane-pos" in layout_str
    assert "pos-cards" in layout_str
    assert "pos-sub" in layout_str
    assert "pos-dist-pane" in layout_str
    assert "pos-delta-pane" in layout_str
    assert "pos-hist-pane" in layout_str
