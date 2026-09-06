"""Profil de gamma par strike, pondéré open interest ou volume.

Les deux pondérations racontent des choses différentes : l'open interest décrit
le positionnement installé, le volume ce qui se traite en séance. Le profil les
superpose, d'où l'importance que les deux se calculent de la même façon.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from gex import metrics


def _chain() -> pd.DataFrame:
    return pd.DataFrame({
        "strike": [7400.0, 7400.0, 7450.0, 7450.0],
        "type": ["C", "P", "C", "P"],
        "gamma_bs": [2e-4, 2e-4, 1e-4, 1e-4],
        "open_interest": [1000.0, 3000.0, 500.0, 500.0],
        "volume": [100.0, 100.0, 900.0, 100.0],
    })


def test_calls_positifs_puts_negatifs():
    s = metrics.gex_by_strike_weighted(_chain(), 7400.0)
    # 7400 : 1000 calls contre 3000 puts -> net négatif
    assert s.loc[7400.0] < 0
    # 7450 : autant de calls que de puts, même gamma -> exactement nul
    assert s.loc[7450.0] == 0.0


def test_agregation_par_strike():
    s = metrics.gex_by_strike_weighted(_chain(), 7400.0)
    assert list(s.index) == [7400.0, 7450.0]


def test_ponderation_volume_differe_de_open_interest():
    """C'est tout l'intérêt de tracer les deux : sur 7450, le volume penche
    côté calls alors que l'open interest y est équilibré."""
    df = _chain()
    oi = metrics.gex_by_strike_weighted(df, 7400.0, "open_interest")
    vol = metrics.gex_by_strike_weighted(df, 7400.0, "volume")
    assert oi.loc[7450.0] == 0.0
    assert vol.loc[7450.0] > 0.0


def test_proportionnel_au_carre_du_spot():
    """GEX = γ × poids × 100 × spot² × 1 % : doubler le spot quadruple."""
    df = _chain()
    a = metrics.gex_by_strike_weighted(df, 1000.0).loc[7400.0]
    b = metrics.gex_by_strike_weighted(df, 2000.0).loc[7400.0]
    assert b == 4 * a


def test_chaine_vide():
    vide = pd.DataFrame({"strike": [], "type": [], "gamma_bs": [],
                         "open_interest": [], "volume": []})
    assert metrics.gex_by_strike_weighted(vide, 7400.0).empty


def test_colonne_de_ponderation_absente():
    """Un snapshot sans colonne volume ne doit pas faire tomber le graphique."""
    df = _chain().drop(columns=["volume"])
    assert metrics.gex_by_strike_weighted(df, 7400.0, "volume").empty


def test_build_heatmap_cards():
    from gex.app import build_heatmap_cards
    cards = build_heatmap_cards("SPX", "es")
    assert cards is not None
    assert "heat-cards" in cards.className
    assert len(cards.children) == 4


def test_heatmap_intraday_fig():
    from gex.app import heatmap_intraday_fig
    fig_gex = heatmap_intraday_fig("SPX", "es", metric="gex")
    assert fig_gex is not None
    assert len(fig_gex.data) >= 1  # heatmap + spot trace
    assert fig_gex.data[0].type == "heatmap"

    fig_oi = heatmap_intraday_fig("SPX", "es", metric="oi")
    assert fig_oi is not None
    assert fig_oi.data[0].type == "heatmap"

    fig_vol = heatmap_intraday_fig("SPX", "es", metric="vol")
    assert fig_vol is not None
    assert fig_vol.data[0].type == "heatmap"


def test_heatmap_term_fig():
    from gex.app import heatmap_term_fig
    fig = heatmap_term_fig("SPX", "es", metric="gex")
    assert fig is not None
    assert len(fig.data) >= 1
    assert fig.data[0].type == "heatmap"


def test_heatmap_bubbles_fig():
    from gex.app import heatmap_bubbles_fig
    fig_spx = heatmap_bubbles_fig("SPX", "es")
    assert fig_spx is not None
    assert len(fig_spx.data) >= 1

    fig_btc = heatmap_bubbles_fig("BTC", "es")
    assert fig_btc is not None


def test_heatmap_history_fig():
    from gex.app import heatmap_history_fig
    fig_spx = heatmap_history_fig("SPX", "es")
    assert fig_spx is not None
    assert len(fig_spx.data) >= 2

    fig_btc = heatmap_history_fig("BTC", "es")
    assert fig_btc is not None


def test_app_heatmap_layout():
    from gex.app import create_app
    app = create_app()
    layout_str = str(app.layout)
    assert "pane-heat" in layout_str
    assert "heat-cards" in layout_str
    assert "heat-sub" in layout_str
    assert "heat-metric" in layout_str
    assert "heatmap-intraday" in layout_str
    assert "heatmap-bubbles" in layout_str
    assert "heatmap-term" in layout_str
    assert "heatmap-hist" in layout_str
    assert "heatmap-overlay" in layout_str


