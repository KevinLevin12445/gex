from datetime import timezone

from gex.adapters.market_data.alpaca import AlpacaConfig, AlpacaStatus, AlpacaStream, parse_event


def test_parse_event_preserves_quote_and_trade_capabilities_only():
    events = parse_event([
        {"T": "q", "S": "SPXW260924C06000000", "bp": 12.5, "ap": 13.0, "t": "2026-09-24T10:00:00Z"},
        {"T": "t", "S": "SPXW260924C06000000", "p": 12.75, "s": 2, "t": "2026-09-24T10:00:01Z"},
        {"T": "b", "S": "ignored"},
    ])
    assert events[0].event == "quote"
    assert events[0].bid == 12.5 and events[0].ask == 13.0
    assert events[1].event == "trade"
    assert events[1].price == 12.75 and events[1].size == 2
    assert events[1].timestamp.tzinfo == timezone.utc


def test_config_reads_safe_environment_and_requires_symbols(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")
    monkeypatch.setenv("ALPACA_OPTION_SYMBOLS", " a, b ")
    config = AlpacaConfig.from_env()
    assert config.credentials_present
    assert config.configured
    assert config.symbols == ("A", "B")


def test_status_declares_delayed_cboe_fallback_and_missing_capabilities():
    payload = AlpacaStatus().to_dict()
    assert payload["state"] == "disabled"
    assert payload["fallback"] == "cboe_delayed"
    assert payload["capabilities"]["greeks"] is False
    assert payload["capabilities"]["open_interest"] is False


def test_start_without_credentials_is_explicit_fallback():
    stream = AlpacaStream(AlpacaConfig(symbols=("A",)))
    stream.start()
    assert stream.status.state == "disabled"
    assert "cboe_delayed" in stream.status.message


def test_start_with_credentials_but_without_symbols_is_misconfigured(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")
    stream = AlpacaStream()
    stream.start()
    assert stream.status.state == "misconfigured"
    assert "ALPACA_OPTION_SYMBOLS" in stream.status.message
