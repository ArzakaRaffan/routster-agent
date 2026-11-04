"""Routster Agent's setup surface: Routster leads provider lists, Nous Portal is not offered, and
Quick Setup's provider step is the Routster key + model flow."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


@pytest.fixture(autouse=True)
def _providers():
    import model_tools  # noqa: F401  (plugin discovery)


def test_routster_leads_the_provider_picker_and_nous_is_not_offered():
    from hermes_cli.main_provider_setup import _build_provider_picker_rows
    from hermes_cli.models_catalog_static import listed_canonical_providers
    from hermes_cli.models import CANONICAL_PROVIDERS

    assert CANONICAL_PROVIDERS[0].slug == "routster"  # TUI/desktop ``/model`` order reads this table

    slugs = [p.slug for p in listed_canonical_providers()]
    assert slugs[0] == "routster"
    assert "nous" not in slugs
    rows, selected = _build_provider_picker_rows({}, "", {}, {})
    assert rows[0][0] == "routster" and selected == 0


def test_nous_still_resolves_by_name():
    from providers import get_provider_profile

    assert get_provider_profile("nous") is not None


@pytest.fixture
def gateway_url():
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
            self._json(200, {"data": [{"id": "routster/glm-5.3", "input_multiplier": 2.7, "output_multiplier": 5.3}]})

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            ok = self.headers.get("Authorization") == "Bearer rk-good"
            self._json(400 if ok else 401, {"error": {"message": "messages kosong" if ok else "invalid api key"}})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    finally:
        server.shutdown()
        server.server_close()


def test_quick_setup_provider_step_saves_routster_key_and_picked_model(monkeypatch, gateway_url):
    from hermes_cli import model_setup_flows_common as common
    from hermes_cli import setup_quick
    from hermes_cli.config import get_env_value, load_config

    monkeypatch.setenv("ROUTSTER_BASE_URL", gateway_url)
    monkeypatch.setattr(common, "_ask", lambda prompt, **kw: "rk-good")
    offered = {}

    def pick(models, prompt, **kw):
        offered.update(models=list(models), notes=kw.get("notes") or {})
        return "routster/glm-5.3"

    monkeypatch.setattr(common, "_pick_model_or_prompt", pick)
    config = load_config()
    setup_quick._quick_setup_routster(config)

    assert get_env_value("ROUTSTER_API_KEY") == "rk-good"
    assert offered["models"] == ["routster/glm-5.3"]  # curated ids the gateway does not serve are not offered
    assert offered["notes"]["routster/glm-5.3"].startswith("input x2.7 / output x5.3")
    assert config["model"]["provider"] == "routster"
    assert config["model"]["default"] == "routster/glm-5.3"
