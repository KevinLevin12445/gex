"""Guía de migración de rutas públicas eliminadas.

Desde la versión arquitectónica actual, los módulos se organizan por capa:
``gex.domain``, ``gex.application``, ``gex.adapters``,
``gex.infrastructure`` y ``gex.presentation``. Los módulos planos como
``gex.metrics`` o ``gex.store`` ya no forman parte de la API pública.
"""

MIGRATION_GUIDE = {
    "gex.metrics": "gex.domain.gex.metrics",
    "gex.greeks": "gex.domain.options.greeks",
    "gex.store": "gex.adapters.persistence.store",
    "gex.app": "gex.presentation.dashboard.main",
    "gex.scheduler": "gex.infrastructure.scheduling.scheduler",
    "gex.run": "gex.main",
}
