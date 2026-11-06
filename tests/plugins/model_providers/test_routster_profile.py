"""Routster provider profile: error mapping, key check, catalog notes and ``routster login``.

The fake gateway below answers the way the real one does (key checked before the body; an empty
``messages`` list rejected with 400 before any balance is reserved), so ``check_api_key`` and the
login flow are exercised over real HTTP without spending anything.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

GOOD_KEY = "rk-good"
CATALOG = {"object": "list", "data": [
    {"id": "routster/deepseek-v4.1-flash", "input_multiplier": 1, "output_multiplier": 1,
     "capabilities": {"streaming": True}},
    {"id": "routster/glm-5.3", "input_multiplier": 2.7, "output_multiplier": 5.3,
     "capabilities": {"streaming": True}},
]}


@pytest.fixture
def routster():
    import model_tools  # plugin discovery registers the profile
    import providers

    profile = providers.get_provider_profile("routster")
    assert profile is not None, "routster provider profile must be registered"
    return profile


@pytest.fixture
def plugin_module(routster):
    import sys

    return sys.modules[type(routster).__module__]


@pytest.fixture
def gateway():
    seen: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def _json(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._json(200, CATALOG) if self.path.rstrip("/") == "/v1/models" else self._json(404, {})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            seen.append({"auth": self.headers.get("Authorization"), "ua": self.headers.get("User-Agent"),
                         "body": body})
            if self.headers.get("Authorization") != f"Bearer {GOOD_KEY}":
                return self._json(401, {"error": {"message": "invalid api key"}})
            if not body.get("messages"):
                return self._json(400, {"error": {"message": "messages kosong"}})
            self._json(500, {"error": {"message": "a key check must never reach inference"}})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield SimpleNamespace(base_url=f"http://127.0.0.1:{server.server_address[1]}/v1", seen=seen)
    finally:
        server.shutdown()
        server.server_close()


class TestErrorMapping:
    @pytest.mark.parametrize("status,error,reason,retryable", [
        (401, {"message": "invalid api key"}, "auth_permanent", False),
        (403, {"message": "email belum diverifikasi. verifikasi dulu di https://x/login"}, "auth_permanent", False),
        (403, {"message": "email not verified. verify it at https://x/login"}, "auth_permanent", False),
        (402, {"message": "token balance exhausted. top up first.", "type": "quota"}, "billing", False),
        (429, {"message": "24h token quota reached", "type": "quota"}, "billing", False),
        (429, {"message": "per-key rate limit reached. slow down.", "type": "rate_limit"}, "rate_limit", True),
        (400, {"message": "unknown_model"}, "model_not_found", False),
        (409, {"message": "model_pricing_pending"}, "model_not_found", False),
        (503, {"message": "This model is unavailable.", "code": "model_unavailable"}, "model_not_found", False),
        (400, {"message": "konten terlalu panjang"}, "payload_too_large", None),
        (400, {"message": "max_tokens must be integer within 1..32768"}, "format_error", False),
    ])
    def test_gateway_rejections_map_to_recovery_reasons(self, routster, status, error, reason, retryable):
        verdict = routster.classify_api_error(None, status_code=status, body={"error": error})
        assert verdict["reason"] == reason
        assert verdict.get("retryable") == retryable
        assert not verdict.get("should_rotate_credential")

    def test_streaming_unsupported_is_left_to_the_core_fallback(self, routster):
        body = {"error": {"message": "Streaming is not supported for this model; use stream=false.",
                          "code": "streaming_unsupported"}}
        assert routster.classify_api_error(None, status_code=400, body=body) is None

    def test_classifier_verdict_flows_through_the_pipeline(self, routster):
        from agent.error_classifier import FailoverReason, classify_api_error

        class Fake402(Exception):
            status_code = 402
            body = {"error": {"message": "token balance exhausted. top up first.", "type": "quota"}}

        classified = classify_api_error(Fake402("402"), provider="routster", model="routster/glm-5.3")
        assert classified.reason is FailoverReason.billing
        assert classified.retryable is False


def test_max_tokens_is_always_explicit_and_in_range(routster):
    assert routster.get_max_tokens("routster/glm-5.3") == 8192
    assert 1 <= routster.get_max_tokens(None) <= 32768


def test_billing_link_points_at_the_dashboard():
    from agent.billing_links import build_billing_block

    block = build_billing_block(provider="routster", base_url="", model="routster/glm-5.3")
    assert block.billing_url == "https://routster.trackster.dev/dashboard"
    assert block.provider_label == "Routster"


class TestKeyCheck:
    def test_good_key_passes_without_inference(self, plugin_module, gateway):
        ok, _ = plugin_module.check_api_key(GOOD_KEY, gateway.base_url)
        assert ok
        (call,) = gateway.seen
        assert call["body"]["messages"] == []  # never a billable request
        assert call["ua"].startswith("routster-agent/")

    def test_bad_key_is_rejected(self, plugin_module, gateway):
        ok, message = plugin_module.check_api_key("rk-wrong", gateway.base_url)
        assert not ok and "rejected" in message

    def test_unreachable_gateway_is_reported(self, plugin_module):
        ok, message = plugin_module.check_api_key(GOOD_KEY, "http://127.0.0.1:9/v1")
        assert not ok and "Cannot reach" in message


def test_catalog_notes_show_multipliers(plugin_module, gateway):
    rows = {r["id"]: r for r in plugin_module.fetch_catalog(gateway.base_url)}
    assert set(rows) == {"routster/deepseek-v4.1-flash", "routster/glm-5.3"}
    assert plugin_module.multiplier_note(rows["routster/glm-5.3"]).startswith("input x2.7 / output x5.3")


class TestLogin:
    def test_login_saves_key_and_makes_routster_the_default(self, gateway):
        from hermes_cli.auth_routster_login import login_command
        from hermes_cli.config import get_env_value, load_config

        login_command(SimpleNamespace(provider=None, base_url=gateway.base_url, model=None, api_key=GOOD_KEY))

        assert get_env_value("ROUTSTER_API_KEY") == GOOD_KEY
        model = load_config()["model"]
        assert model["provider"] == "routster"
        assert model["default"] == "routster/deepseek-v4.1-flash"
        assert model["base_url"] == gateway.base_url  # non-default gateway is kept
        env_file = Path(os.environ["HERMES_HOME"]) / ".env"
        assert oct(env_file.stat().st_mode & 0o777) == "0o600"

    def test_rejected_key_saves_nothing(self, gateway):
        from hermes_cli.auth_routster_login import login_command
        from hermes_cli.config import get_env_value

        with pytest.raises(SystemExit):
            login_command(SimpleNamespace(provider=None, base_url=gateway.base_url, model=None, api_key="rk-wrong"))
        assert not get_env_value("ROUTSTER_API_KEY")

    def test_other_providers_are_pointed_elsewhere(self, gateway):
        from hermes_cli.auth_routster_login import login_command

        with pytest.raises(SystemExit) as exc:
            login_command(SimpleNamespace(provider="openrouter", base_url=None, model=None, api_key=None))
        assert exc.value.code == 2
        assert gateway.seen == []
