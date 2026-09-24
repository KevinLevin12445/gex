"""Optional, read-only Alpaca OPRA quote/trade stream.

Alpaca's options stream supplies quotes and trades for subscribed contracts.
It is deliberately not used to build the normalized chain: the stream does
not provide the complete chain, Greeks, or open interest required by GEX.
Those values continue to come from the delayed CBOE adapter.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import websockets

log = logging.getLogger(__name__)

STREAM_URL = "wss://stream.data.alpaca.markets/v1beta1beta1"


def _real(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip().strip("'\"")
    lowered = value.lower()
    return bool(value) and not any(
        marker in lowered for marker in ("your_", "replace_", "xxxx", "pega_aqui")
    )


@dataclass(frozen=True)
class AlpacaConfig:
    api_key: str | None = None
    secret_key: str | None = None
    feed: str = "opra"
    symbols: tuple[str, ...] = ()
    stream_url: str = STREAM_URL

    @classmethod
    def from_env(cls) -> "AlpacaConfig":
        symbols = tuple(
            item.strip().upper()
            for item in os.environ.get("ALPACA_OPTION_SYMBOLS", "").split(",")
            if item.strip()
        )
        return cls(
            api_key=os.environ.get("ALPACA_API_KEY"),
            secret_key=os.environ.get("ALPACA_SECRET_KEY"),
            feed=os.environ.get("ALPACA_DATA_FEED", "opra").strip().lower() or "opra",
            symbols=symbols,
            stream_url=os.environ.get("ALPACA_OPTIONS_STREAM_URL", STREAM_URL),
        )

    @property
    def credentials_present(self) -> bool:
        return _real(self.api_key) and _real(self.secret_key)

    @property
    def configured(self) -> bool:
        return self.credentials_present and bool(self.symbols)


@dataclass(frozen=True)
class OptionEvent:
    event: str
    symbol: str
    timestamp: datetime | None
    bid: float | None = None
    ask: float | None = None
    price: float | None = None
    size: int | None = None


def parse_event(message: dict[str, Any]) -> list[OptionEvent]:
    """Parse Alpaca quote/trade messages without inventing unavailable fields."""
    out: list[OptionEvent] = []
    for item in message if isinstance(message, list) else [message]:
        if not isinstance(item, dict) or item.get("T") not in {"q", "t"}:
            continue
        event = "quote" if item["T"] == "q" else "trade"
        timestamp = item.get("t")
        parsed_ts = None
        if timestamp:
            try:
                parsed_ts = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            except ValueError:
                log.warning("Ignoring invalid Alpaca timestamp for %s", item.get("S"))
        out.append(OptionEvent(
            event=event,
            symbol=str(item.get("S", "")),
            timestamp=parsed_ts,
            bid=float(item["bp"]) if item.get("bp") is not None else None,
            ask=float(item["ap"]) if item.get("ap") is not None else None,
            price=float(item["p"]) if item.get("p") is not None else None,
            size=int(item["s"]) if item.get("s") is not None else None,
        ))
    return out


@dataclass
class AlpacaStatus:
    state: str = "disabled"
    message: str = "Alpaca OPRA disabled; using delayed CBOE data."
    last_event_at: datetime | None = None
    events: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": "alpaca",
            "feed": "opra",
            "state": self.state,
            "message": self.message,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "events": self.events,
            "capabilities": {
                "quotes": True,
                "trades": True,
                "complete_chain": False,
                "spot": False,
                "greeks": False,
                "open_interest": False,
            },
            "fallback": "cboe_delayed",
        }


class AlpacaStream:
    """Small reconnecting read-only stream; no order or trading API exists here."""

    def __init__(self, config: AlpacaConfig | None = None) -> None:
        self._from_environment = config is None
        self.config = config or AlpacaConfig.from_env()
        self.status = AlpacaStatus()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if self._from_environment:
            # dotenv is loaded by the process entry point immediately before
            # background services start.
            self.config = AlpacaConfig.from_env()
        if not self.config.credentials_present:
            self.status = AlpacaStatus(message="Alpaca credentials absent; fallback=cboe_delayed.")
            return
        if not self.config.symbols:
            self.status = AlpacaStatus(
                state="misconfigured",
                message="ALPACA_OPTION_SYMBOLS is empty; fallback=cboe_delayed.",
            )
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="alpaca-opra", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            asyncio.run(self._consume())
        except Exception as exc:  # noqa: BLE001 - status must expose connection failure
            self.status = AlpacaStatus(
                state="error",
                message=f"Alpaca OPRA unavailable ({type(exc).__name__}); fallback=cboe_delayed.",
            )
            log.warning("Alpaca OPRA stream stopped: %s", exc)

    async def _consume(self) -> None:
        async with websockets.connect(self.config.stream_url, open_timeout=10) as socket:
            await socket.send(json.dumps({
                "action": "auth",
                "key": self.config.api_key,
                "secret": self.config.secret_key,
            }))
            await socket.send(json.dumps({
                "action": "subscribe",
                "quotes": list(self.config.symbols),
                "trades": list(self.config.symbols),
            }))
            while not self._stop.is_set():
                try:
                    raw = await asyncio.wait_for(socket.recv(), timeout=5)
                except asyncio.TimeoutError:
                    continue
                payload = json.loads(raw)
                messages = payload if isinstance(payload, list) else [payload]
                for message in messages:
                    if isinstance(message, dict) and message.get("T") == "error":
                        raise RuntimeError(str(message.get("msg", "Alpaca rejected the stream")))
                    if isinstance(message, dict) and message.get("T") == "success":
                        if message.get("msg") == "authenticated":
                            self.status = AlpacaStatus(
                                state="connected",
                                message="Alpaca OPRA quotes/trades connected.",
                            )
                for event in parse_event(payload):
                    self.status.last_event_at = event.timestamp or datetime.now(timezone.utc)
                    self.status.events += 1


ALPACA = AlpacaStream()
