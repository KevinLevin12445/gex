import sys
import types

from flask import Flask

from gex.adapters.market_data.ibkr import (
    IBKRConfig,
    IBKRStatus,
    IBKRStream,
    make_contract,
)
from gex.presentation.api.api import register_api


def configured(**overrides):
    values = {
        "enabled": True,
        "acknowledged": True,
        "host": "127.0.0.1",
        "port": 7496,
        "client_id": 61,
        "symbol": "SPX",
        "expiry": "20261016",
        "strike": 6000.0,
        "right": "C",
        "trading_class": "SPXW",
        "exchange": "CBOE",
        "multiplier": "100",
    }
    values.update(overrides)
    return IBKRConfig(**values)


def test_ibkr_disabled_by_default_and_does_not_connect():
    stream = IBKRStream(IBKRConfig())
    stream.start()
    assert stream.status.state == "disabled"
    assert stream.status.to_dict()["fallback"] == "cboe_delayed"
    assert stream._thread is None


def test_enabled_adapter_requires_explicit_api_acknowledgement():
    stream = IBKRStream(configured(acknowledged=False))
    stream.start()
    assert stream.status.state == "approval_required"
    assert stream._thread is None


def test_adapter_rejects_non_loopback_tws_hosts():
    stream = IBKRStream(configured(host="192.0.2.1"))
    stream.start()
    assert stream.status.state == "misconfigured"
    assert stream._thread is None


def test_contract_config_checks_expiry_strike_right_and_trading_class():
    assert configured().valid
    assert not configured(expiry="20261345").valid
    assert not configured(strike=0).valid
    assert not configured(right="X").valid
    assert not configured(trading_class="").valid


def test_make_contract_builds_only_the_selected_spx_option():
    class Contract:
        pass

    contract = make_contract(Contract, configured())
    assert contract.symbol == "SPX"
    assert contract.secType == "OPT"
    assert contract.lastTradeDateOrContractMonth == "20261016"
    assert contract.strike == 6000.0
    assert contract.right == "C"
    assert contract.tradingClass == "SPXW"


def test_mocked_api_requests_one_quote_and_never_places_orders(monkeypatch):
    requests = []

    class FakeWrapper:
        pass

    class FakeClient:
        def __init__(self, wrapper):
            self.wrapper = wrapper

        def connect(self, host, port, client_id):
            assert host == "127.0.0.1"
            assert port == 7496

        def run(self):
            self.wrapper.nextValidId(1)
            self.wrapper.tickPrice(1, 1, 10.25, None)

        def reqMktData(self, *args):
            requests.append(args)

        def cancelMktData(self, req_id):
            pass

        def disconnect(self):
            pass

    class FakeContract:
        pass

    ibapi = types.ModuleType("ibapi")
    ibapi.__path__ = []
    client_module = types.ModuleType("ibapi.client")
    client_module.EClient = FakeClient
    wrapper_module = types.ModuleType("ibapi.wrapper")
    wrapper_module.EWrapper = FakeWrapper
    contract_module = types.ModuleType("ibapi.contract")
    contract_module.Contract = FakeContract
    monkeypatch.setitem(sys.modules, "ibapi", ibapi)
    monkeypatch.setitem(sys.modules, "ibapi.client", client_module)
    monkeypatch.setitem(sys.modules, "ibapi.wrapper", wrapper_module)
    monkeypatch.setitem(sys.modules, "ibapi.contract", contract_module)

    stream = IBKRStream(configured())
    stream.start()
    stream._thread.join(timeout=2)

    assert stream.status.state == "data_received"
    assert stream.status.events == 1
    assert stream.status.to_dict()["quote"]["bid"] == 10.25
    assert len(requests) == 1
    assert requests[0][0] == 1
    assert requests[0][2] == ""
    assert stream.status.to_dict()["capabilities"]["complete_chain"] is False
    assert stream.status.to_dict()["capabilities"]["order_placement"] is False


def test_ibkr_status_route_exposes_health_without_market_values():
    app = Flask(__name__)
    register_api(app)

    response = app.test_client().get("/api/v1/ibkr/status")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["provider"] == "ibkr"
    assert payload["state"] == "disabled"
    assert payload["fallback"] == "cboe_delayed"
    assert payload["quote"] == {"bid": None, "ask": None, "last": None}


def test_combined_market_status_keeps_alpaca_compatibility_and_adds_ibkr():
    app = Flask(__name__)
    register_api(app)

    response = app.test_client().get("/api/v1/market-data/status")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["provider"] == "alpaca"
    assert payload["analytics_chain_source"] == "cboe_delayed"
    assert payload["ibkr"]["provider"] == "ibkr"
