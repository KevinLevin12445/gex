"""Contratos mínimos para fuentes de datos de mercado."""

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from gex.adapters.market_data.ingest import ChainSnapshot


class OptionChainPort(Protocol):
    def fetch_chain(self, symbol: str, provider_symbol: str,
                   timeout: int = 60) -> ChainSnapshot: ...


class SpotPricePort(Protocol):
    def fetch_spot(self, provider_symbol: str,
                   timeout: int = 30) -> tuple[float, datetime]: ...


class QuotePort(Protocol):
    def resolve_symbols(self, access_token: str) -> Mapping[str, str]: ...
