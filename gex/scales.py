"""Transposition des niveaux vers une autre échelle de prix.

Deux régimes, volontairement distincts :

1. **Indice vers son propre future** (SPX→ES, NDX→NQ) : décalage ADDITIF du
   basis. C'est la conversion exacte — le future converge vers l'indice à
   l'échéance, un strike K se lit donc K + basis sur le future.

2. **Toute autre transposition** (SPX→SPY, SPX→NQ…) : conversion
   PROPORTIONNELLE, qui préserve la distance relative au spot. Un mur situé
   1,2 % au-dessus du spot SPX s'affiche 1,2 % au-dessus du spot cible.

La transposition CROISÉE (entre familles SP et ND) est mathématiquement
valide mais son ratio dérive en permanence : c'est un repère instantané, pas
un niveau stable. `Scale.cross_family()` permet à l'interface de le signaler.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import UNDERLYINGS, targets


@dataclass(frozen=True)
class Scale:
    key: str            # identifiant d'échelle : "SPX", "ES", "QQQ"…
    label: str          # libellé affiché
    family: str         # "SP" ou "ND" — familles d'indices distinctes
    source: str         # sous-jacent fournissant le spot ("SPX" pour "ES")
    is_future: bool = False

    def cross_family(self, src_underlying: str) -> bool:
        """La transposition depuis ce sous-jacent change-t-elle de famille ?"""
        src = UNDERLYINGS.get(src_underlying)
        return src is not None and src.family != self.family


def available_scales() -> list[Scale]:
    """Échelles proposées : chaque sous-jacent analysé, plus son future.

    Les constituants (NVDA, SMH…) en sont exclus : ils alimentent les niveaux
    de confluence, ils ne sont pas des échelles d'affichage.
    """
    out: list[Scale] = []
    for u in targets():
        out.append(Scale(u.key, u.key, u.family, u.key))
        if u.future:
            out.append(Scale(u.future, u.future, u.family, u.key, is_future=True))
    return out


def scale_by_key(key: str) -> Scale | None:
    return next((s for s in available_scales() if s.key == key), None)


def reference_price(scale: Scale, spots: dict[str, float],
                    bases: dict[str, float | None]) -> float | None:
    """Prix de référence de l'échelle : le spot du sous-jacent, augmenté du
    basis s'il s'agit du future."""
    spot = spots.get(scale.source)
    if spot is None:
        return None
    if scale.is_future:
        basis = bases.get(scale.source)
        if basis is None:
            return None
        return spot + basis
    return spot


def transform(src_underlying: str, target: Scale | None,
              spots: dict[str, float], bases: dict[str, float | None],
              cfd_offset: float = 0.0):
    """Retourne (fonction de conversion, ratio, mode) pour passer des prix du
    sous-jacent source à l'échelle cible, avec prise en charge optionnelle
    d'un offset CFD (+/- différence de cotation courtier).

    mode ∈ {"native", "basis", "ratio", "cfd"} — "native" = aucune conversion.
    Retourne l'identité si la conversion est impossible (spot cible absent),
    plutôt que d'afficher des niveaux faux.
    """
    identity = (lambda x: x), 1.0, "native"
    u_src = UNDERLYINGS.get(src_underlying)
    if (u_src and u_src.family not in ("SP", "ND")) or src_underlying in ("GC", "BTC", "GLD", "IBIT"):
        base_fn, ratio, mode = identity
    elif target is None or target.key == src_underlying:
        base_fn, ratio, mode = identity
    else:
        src_spot = spots.get(src_underlying)
        if not src_spot:
            base_fn, ratio, mode = identity
        elif target.is_future and target.source == src_underlying:
            # cas exact : l'indice vers son propre future
            basis = bases.get(src_underlying)
            if basis is None:
                base_fn, ratio, mode = identity
            else:
                base_fn, ratio, mode = (lambda x: x + basis), 1.0, "basis"
        elif target.family != (u_src.family if u_src else ""):
            if (u_src and u_src.family in ("SP", "ND")) and target.family in ("SP", "ND"):
                tgt = reference_price(target, spots, bases)
                if not tgt:
                    base_fn, ratio, mode = identity
                else:
                    ratio = tgt / src_spot
                    base_fn, ratio, mode = (lambda x: x * ratio), ratio, "ratio"
            else:
                base_fn, ratio, mode = identity
        else:
            tgt = reference_price(target, spots, bases)
            if not tgt:
                base_fn, ratio, mode = identity
            else:
                ratio = tgt / src_spot
                base_fn, ratio, mode = (lambda x: x * ratio), ratio, "ratio"

    if cfd_offset:
        fn = (lambda x: None if x is None else base_fn(x) + cfd_offset)
        return fn, ratio, (mode if mode != "native" else "cfd")

    return base_fn, ratio, mode


YAHOO_CFD_TICKERS = {
    "NQ": "^NDX",
    "ES": "^GSPC",
    "NQ_FUT": "NQ=F",
    "ES_FUT": "ES=F",
    "GC": "GC=F",
    "BTC": "BTC-USD",
}

_YAHOO_CACHE: dict[str, tuple[float, float]] = {}


def get_yahoo_cfd_price(symbol: str) -> float | None:
    """Récupère le cours au comptant / CFD de référence depuis Yahoo Finance."""
    import time
    import requests

    ticker = YAHOO_CFD_TICKERS.get(symbol)
    if not ticker:
        return None
    now = time.time()
    cached = _YAHOO_CACHE.get(ticker)
    if cached and now - cached[0] < 15:  # cache de 15s
        return cached[1]

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, timeout=4)
        if r.status_code == 200:
            meta = r.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = float(meta.get("regularMarketPrice", 0.0))
            if price > 0:
                _YAHOO_CACHE[ticker] = (now, price)
                return price
    except Exception:
        pass

    return cached[1] if cached else None


def get_auto_cfd_offset(symbol: str, fut_spot: float) -> float:
    """Calcule l'écart exact (Spot CFD Yahoo - Spot Futurs CME) pour transposer les niveaux."""
    if not fut_spot or fut_spot <= 0:
        return 0.0
    cfd_px = get_yahoo_cfd_price(symbol)
    if cfd_px and cfd_px > 0:
        return round(cfd_px - fut_spot, 2)
    return 0.0
