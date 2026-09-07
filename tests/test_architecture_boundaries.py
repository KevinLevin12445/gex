"""Pruebas de caracterización de las nuevas fronteras arquitectónicas."""

import numpy as np
from pathlib import Path

from gex.domain.options.greeks import call_delta, gamma
from gex.domain.gex import metrics


def test_domain_greeks_are_available_without_presentation():
    assert np.isfinite(call_delta(100, 100, 0.25, 0.04, 0.2))
    assert gamma(100, 100, 0.25, 0.04, 0.2) > 0


def test_domain_gex_facade_exposes_existing_calculations():
    assert callable(metrics.exposure_by_strike)
    assert callable(metrics.zero_gamma)


def test_package_root_is_limited_to_bootstrap_files():
    root = Path(__file__).parents[1] / "gex"
    assert {path.name for path in root.glob("*.py")} == {
        "__init__.py", "__main__.py", "legacy.py", "main.py",
    }
