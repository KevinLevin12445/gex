"""Contrato mínimo de persistencia usado por los casos de uso."""

from datetime import datetime
from pathlib import Path
from typing import Protocol

import pandas as pd


class SnapshotStoragePort(Protocol):
    def save_snapshot(self, symbol: str, frame: pd.DataFrame,
                      timestamp: datetime) -> Path: ...

    def load_latest_snapshot(self, symbol: str): ...
