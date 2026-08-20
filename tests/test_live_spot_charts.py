"""Tests de validation du spot en temps réel et du tracé de la ligne de spot sur tous les graphiques.
"""
from __future__ import annotations

import time
import pandas as pd
import pytest

from gex.app import (
    exposure_fig,
    profile_fig,
    profile_by_expiry_fig,
    smile_fig,
    second_order_fig,
    oi_change_fig,
    heatmap_fig,
    spot_zg_fig,
    live_spot,
)
from gex.rtquote import QUOTES, Tick


def _sample_chain(spot: float = 7500.0) -> pd.DataFrame:
    rows = []
    for strike in [7400.0, 7450.0, 7500.0, 7550.0, 7600.0]:
        for typ in ["C", "P"]:
            rows.append({
                "strike": strike,
                "type": typ,
                "expiry": "2026-08-21",
                "open_interest": 1000.0,
                "volume": 200.0,
                "iv": 0.15,
                "delta": 0.5 if typ == "C" else -0.5,
                "gamma": 0.002,
                "gamma_bs": 0.002,
                "gex": 1e8 if typ == "C" else -1e8,
                "dex": 5e8 if typ == "C" else -5e8,
                "vex": 1e6,
                "cex": 1e6,
                "spot": spot,
                "t_years": 0.05,
            })
    return pd.DataFrame(rows)


def test_live_spot_retrieval():
    """Vérifie que live_spot renvoie le prix temps réel quand disponible."""
    test_spot = 7654.25
    with QUOTES.lock:
        QUOTES.ticks["SPX"] = Tick(bid=7654.0, ask=7654.5, last=test_spot, ts=time.time())
    
    px, is_live = live_spot("SPX", 7500.0)
    assert is_live is True
    assert px == 7654.25


def test_exposure_fig_spot_line():
    """Vérifie que exposure_fig trace la ligne Spot à la valeur exacte passée."""
    df = _sample_chain(7500.0)
    spot = 7520.0
    fig = exposure_fig(df, spot, zg=7480.0, col="gex", title="GEX Test", lang="es")
    
    # Vérifie la présence de la ligne Spot dans les formes / annotations / hlines
    shapes = fig.layout.shapes or []
    has_spot_line = any(s.y0 == spot and s.y1 == spot for s in shapes)
    assert has_spot_line is True, "La ligne horizontale de Spot doit être à y=spot"


def test_profile_fig_spot_line():
    """Vérifie que profile_fig trace la ligne Spot verticale à la valeur exacte passée."""
    df = _sample_chain(7500.0)
    spot = 7530.0
    fig = profile_fig(df, spot, zg=7480.0, lang="es", window=0.04)
    
    shapes = fig.layout.shapes or []
    has_spot_vline = any(s.x0 == spot and s.x1 == spot for s in shapes)
    assert has_spot_vline is True, "La ligne verticale de Spot doit être à x=spot"


def test_smile_fig_spot_line():
    """Vérifie que smile_fig trace la ligne Spot verticale à la valeur exacte passée."""
    df = _sample_chain(7500.0)
    spot = 7515.0
    fig = smile_fig(df, spot, lang="es")
    
    shapes = fig.layout.shapes or []
    has_spot_vline = any(s.x0 == spot and s.x1 == spot for s in shapes)
    assert has_spot_vline is True, "La ligne verticale de Spot doit être à x=spot"


def test_second_order_fig_spot_line():
    """Vérifie que second_order_fig (Vanna/Charm) trace la ligne Spot horizontale."""
    df = _sample_chain(7500.0)
    spot = 7510.0
    fig = second_order_fig(df, spot, col="vex", title="Vanna Test", window=0.04)
    
    shapes = fig.layout.shapes or []
    has_spot_line = any(s.y0 == spot and s.y1 == spot for s in shapes)
    assert has_spot_line is True, "La ligne horizontale de Spot doit être à y=spot"


def test_oi_change_fig_spot_line():
    """Vérifie que oi_change_fig trace la ligne Spot horizontale."""
    chg = pd.DataFrame({
        "strike": [7400.0, 7500.0, 7600.0],
        "d_call": [100.0, 200.0, -50.0],
        "d_put": [-100.0, 50.0, 150.0],
    })
    spot = 7525.0
    fig = oi_change_fig(chg, spot, lang="es", prev_day="2026-08-19", window=0.04)
    
    shapes = fig.layout.shapes or []
    has_spot_line = any(s.y0 == spot and s.y1 == spot for s in shapes)
    assert has_spot_line is True, "La ligne horizontale de Spot doit être à y=spot"


def test_nq_realtime_chain_and_cards():
    """Vérifie que NQ dispose d'une chaîne enrichie en temps réel et de tuiles actives."""
    from gex.app import chain_state, build_cards, _figure_for
    with QUOTES.lock:
        QUOTES.ticks["NQ"] = Tick(bid=29280.0, ask=29282.0, last=29281.5, ts=time.time())
    
    st = chain_state("NQ")
    assert st.enriched is not None, "NQ doit avoir une chaîne enrichie valide"
    assert not st.enriched.empty
    
    cards = build_cards("NQ", "es")
    assert len(cards) >= 6, "NQ doit afficher toutes les tuiles statistiques"
    
    fig = _figure_for("NQ", "gex")
    assert fig is not None, "NQ doit générer le graphique GEX"
    shapes = fig.layout.shapes or []
    assert len(shapes) > 0, "Le graphique GEX de NQ doit contenir les lignes de niveaux et Spot"
