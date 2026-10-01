"""Opt-in, read-only IBKR option quote monitor.

This adapter requests market data for one explicitly configured option
contract. It does not enumerate the option chain, request account data, or
place orders. CBOE remains GEX's authoritative analytics-chain source.
"""
from __future__ import annotations

import importlib
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "on"}
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUE_VALUES


@dataclass(frozen=True)
class IBKRConfig:
    enabled: bool = False
    acknowledged: bool = False
    host: str = "127.0.0.1"
    port: int = 7496
    client_id: int = 61
    symbol: str = "SPX"
    expiry: str = ""
    strike: float | None = None
    right: str = ""
    trading_class: str = ""
    exchange: str = "CBOE"
    multiplier: str = "100"

    @classmethod
    def from_env(cls) -> "IBKRConfig":
        raw_strike = os.environ.get("IBKR_OPTION_STRIKE", "").strip()
        try:
            strike = float(raw_strike) if raw_strike else None
        except ValueError:
            strike = None
        try:
            port = int(os.environ.get("IBKR_API_PORT", "7496"))
            client_id = int(os.environ.get("IBKR_CLIENT_ID", "61"))
        except ValueError:
            port, client_id = 0, -1
        return cls(
            enabled=_enabled(os.environ.get("IBKR_API_ENABLED")),
            acknowledged=_enabled(os.environ.get("IBKR_API_ACKNOWLEDGED")),
            host=os.environ.get("IBKR_API_HOST", "127.0.0.1").strip(),
            port=port,
            client_id=client_id,
            symbol=os.environ.get("IBKR_OPTION_SYMBOL", "SPX").strip().upper(),
            expiry=os.environ.get("IBKR_OPTION_EXPIRY", "").strip(),
            strike=strike,
            right=os.environ.get("IBKR_OPTION_RIGHT", "").strip().upper(),
            trading_class=os.environ.get("IBKR_OPTION_TRADING_CLASS", "").strip().upper(),
            exchange=os.environ.get("IBKR_OPTION_EXCHANGE", "CBOE").strip().upper(),
            multiplier=os.environ.get("IBKR_OPTION_MULTIPLIER", "100").strip(),
        )

    @property
    def contract_configured(self) -> bool:
        try:
            datetime.strptime(self.expiry, "%Y%m%d")
            valid_expiry = True
        except ValueError:
            valid_expiry = False
        return (
            valid_expiry
            and self.strike is not None
            and self.strike > 0
            and self.right in {"C", "P"}
            and bool(self.trading_class)
        )

    @property
    def valid(self) -> bool:
        return (
            self.host.lower() in _LOOPBACK_HOSTS
            and 1 <= self.port <= 65535
            and self.client_id >= 0
            and self.symbol == "SPX"
            and self.contract_configured
        )


@dataclass
class IBKRStatus:
    state: str = "disabled"
    message: str = "IBKR API disabled; using delayed CBOE analytics chain."
    contract: str | None = None
    last_event_at: datetime | None = None
    events: int = 0
    bid: float | None = None
    ask: float | None = None
    last: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": "ibkr",
            "state": self.state,
            "message": self.message,
            "contract": self.contract,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "events": self.events,
            "quote": {
                "bid": self.bid,
                "ask": self.ask,
                "last": self.last,
            },
            "capabilities": {
                "single_option_quote": True,
                "complete_chain": False,
                "spot": False,
                "greeks": False,
                "open_interest": False,
                "order_placement": False,
            },
            "fallback": "cboe_delayed",
        }


class IBKRStream:
    """Connect to local TWS/IB Gateway and subscribe to one option quote only."""

    def __init__(self, config: IBKRConfig | None = None) -> None:
        self._from_environment = config is None
        self.config = config or IBKRConfig.from_env()
        self.status = IBKRStatus()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._client: Any = None
        self._lock = threading.Lock()
        self._connection_timer: threading.Timer | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if self._from_environment:
            self.config = IBKRConfig.from_env()
        if not self.config.enabled:
            self.status = IBKRStatus()
            return
        if not self.config.acknowledged:
            self.status = IBKRStatus(
                state="approval_required",
                message="Complete IBKR API terms/approval first; fallback=cboe_delayed.",
            )
            return
        if not self.config.valid:
            self.status = IBKRStatus(
                state="misconfigured",
                message=(
                    "Configure one SPX option contract and a local TWS API endpoint; "
                    "fallback=cboe_delayed."
                ),
            )
            return
        self._stop.clear()
        self.status = IBKRStatus(
            state="connecting",
            message="Connecting to local IBKR API; fallback=cboe_delayed.",
            contract=self.contract_label,
        )
        self._thread = threading.Thread(target=self._run, name="ibkr-option-quote", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        client = self._client
        if client is not None:
            try:
                client.cancelMktData(1)
            except Exception:  # noqa: BLE001 - shutdown must not hide the original process exit
                log.warning("IBKR market-data subscription did not cancel cleanly")
            try:
                client.disconnect()
            except Exception:  # noqa: BLE001 - shutdown must not hide the original process exit
                log.warning("IBKR client did not disconnect cleanly")
        if self._connection_timer is not None:
            self._connection_timer.cancel()

    @property
    def contract_label(self) -> str:
        return (
            f"{self.config.symbol} {self.config.expiry} "
            f"{self.config.right}{self.config.strike:g}"
        )

    def record_price(self, tick_type: int, price: float) -> None:
        field = {1: "bid", 2: "ask", 4: "last"}.get(tick_type)
        if field is None:
            return
        with self._lock:
            setattr(self.status, field, price)
            self._record_event()

    def _record_event(self) -> None:
        self.status.events += 1
        self.status.last_event_at = datetime.now(timezone.utc)
        self.status.state = "data_received"
        self.status.message = "IBKR option market-data event received; CBOE remains analytics source."

    def _run(self) -> None:
        try:
            client_module = importlib.import_module("ibapi.client")
            wrapper_module = importlib.import_module("ibapi.wrapper")
            contract_module = importlib.import_module("ibapi.contract")
        except ImportError:
            self.status = IBKRStatus(
                state="dependency_missing",
                message='Install the optional "ibkr" extra; fallback=cboe_delayed.',
                contract=self.contract_label,
            )
            return

        stream = self
        EClient = client_module.EClient
        EWrapper = wrapper_module.EWrapper
        Contract = contract_module.Contract

        class ReadOnlyApp(EWrapper, EClient):
            def __init__(self):
                EWrapper.__init__(self)
                EClient.__init__(self, self)

            def nextValidId(self, orderId):
                # The ID is required by IB's connection handshake; no order is
                # created or transmitted by this adapter.
                stream.status.state = "subscribed"
                stream.status.message = "Connected; requesting one option quote. CBOE chain retained."
                if stream._connection_timer is not None:
                    stream._connection_timer.cancel()
                stream.reqMktData(1, make_contract(Contract, stream.config), "", False, False, [])

            def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
                if errorCode in {354, 502, 504, 1100, 1300, 10089, 10167}:
                    stream.status = IBKRStatus(
                        state="error" if errorCode in {502, 504, 1100, 1300} else "market_data_unavailable",
                        message=f"IBKR API reported issue {errorCode}; fallback=cboe_delayed.",
                        contract=stream.contract_label,
                    )
                    log.warning("IBKR API connection error %s", errorCode)

            def tickPrice(self, reqId, tickType, price, attrib):
                if reqId == 1 and price >= 0:
                    stream.record_price(tickType, float(price))

            def tickSize(self, reqId, tickType, size):
                return None

            def connectionClosed(self):
                if not stream._stop.is_set():
                    stream.status.state = "disconnected"
                    stream.status.message = "IBKR connection closed; fallback=cboe_delayed."

        try:
            app = ReadOnlyApp()
            self._client = app
            app.connect(self.config.host, self.config.port, self.config.client_id)
            self._connection_timer = threading.Timer(10, self._connection_timeout)
            self._connection_timer.daemon = True
            self._connection_timer.start()
            app.run()
        except Exception as exc:  # noqa: BLE001 - surface provider failure, never secrets
            self.status = IBKRStatus(
                state="error",
                message=f"IBKR API unavailable ({type(exc).__name__}); fallback=cboe_delayed.",
                contract=self.contract_label,
            )
            log.warning("IBKR API connection failed: %s", type(exc).__name__)

    def reqMktData(self, req_id, contract, generic_ticks, snapshot, regulatory_snapshot, options):
        """Forward the sole market-data request through the connected TWS client."""
        client = self._client
        if client is not None:
            client.reqMktData(req_id, contract, generic_ticks, snapshot, regulatory_snapshot, options)

    def _connection_timeout(self) -> None:
        if self.status.state == "connecting":
            self.status = IBKRStatus(
                state="timeout",
                message="IBKR API did not complete its connection handshake; fallback=cboe_delayed.",
                contract=self.contract_label,
            )


IBKR = IBKRStream()


def make_contract(contract_class: type, config: IBKRConfig):
    """Build the one explicitly configured option contract for the API request."""
    contract = contract_class()
    contract.symbol = config.symbol
    contract.secType = "OPT"
    contract.exchange = config.exchange
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = config.expiry
    contract.strike = config.strike
    contract.right = config.right
    contract.multiplier = config.multiplier
    contract.tradingClass = config.trading_class
    return contract
