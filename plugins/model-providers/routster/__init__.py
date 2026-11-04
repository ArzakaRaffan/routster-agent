"""Routster provider profile (https://routster.trackster.dev): an OpenAI-compatible gateway billed in Rupiah.

Gateway contract this profile encodes (verified against the gateway source):

* ``max_tokens`` defaults to 1024 server-side and is capped at 32768, so the profile always sends one.
  The gateway *reserves* ``input + max_tokens x output_multiplier`` from the balance before calling the
  upstream, so a huge default would make a low balance 402 although the real cost is small: keep it
  moderate (users raise it with ``model.max_tokens`` in config.yaml).
* Model ids are published as ``routster/<name>``; the gateway also accepts the bare name.
* Errors are ``{"error": {"message", "type"?, "code"?}}``. ``type: quota`` is shared by an exhausted
  balance (402) and a per-key token-window quota (429), so the status code tells them apart.
"""

from __future__ import annotations

from typing import Any

from hermes_cli.version_info import hermes_user_agent
from providers import register_provider
from providers.base import LazyHeaders, ProviderProfile

ROUTSTER_SITE_URL = "https://routster.trackster.dev"
ROUTSTER_DEFAULT_BASE_URL = f"{ROUTSTER_SITE_URL}/v1"
ROUTSTER_DASHBOARD_URL = f"{ROUTSTER_SITE_URL}/dashboard"
ROUTSTER_DEFAULT_MODEL = "routster/deepseek-v4.1-flash"
ROUTSTER_DEFAULT_MAX_TOKENS = 8192
ROUTSTER_MAX_TOKENS_CAP = 32768

# Curated for agent work until ``/v1/models`` publishes ``capabilities.tools``. The cheap
# default leads; the rest are the gateway's strongest coding models.
ROUTSTER_AGENT_MODELS = (
    ROUTSTER_DEFAULT_MODEL,
    "routster/deepseek-v4-pro",
    "routster/glm-5.3",
    "routster/glm-5.3-flash",
    "routster/kimi-k2.7",
    "routster/minimax-m3",
)


def _error_fields(body: Any) -> tuple[str, str, str]:
    """``(message, type, code)`` of a Routster error body, lowercased; empty strings when absent."""
    err = body.get("error") if isinstance(body, dict) else None
    if isinstance(err, str):
        return err.strip().lower(), "", ""
    if not isinstance(err, dict):
        return "", "", ""
    return tuple(str(err.get(key) or "").strip().lower() for key in ("message", "type", "code"))  # type: ignore[return-value]


# Hints are spelled out: a verdict without ``retryable=False`` is retried with backoff.
# One key per account, so nothing here rotates credentials.
_STOP = {"retryable": False, "should_rotate_credential": False, "should_fallback": True}

# (status, matcher, verdict). Matchers see (message, type, code); first hit wins.
_RULES: tuple[tuple[int, Any, dict[str, Any]], ...] = (
    (401, lambda m, t, c: True, {"reason": "auth_permanent", **_STOP}),
    (403, lambda m, t, c: "verifikasi" in m, {"reason": "auth_permanent", **_STOP}),
    (402, lambda m, t, c: True, {"reason": "billing", **_STOP}),
    (429, lambda m, t, c: t == "quota", {"reason": "billing", **_STOP}),
    (429, lambda m, t, c: t == "rate_limit",
     {"reason": "rate_limit", "retryable": True, "should_rotate_credential": False}),
    (400, lambda m, t, c: m == "unknown_model", {"reason": "model_not_found", **_STOP}),
    (409, lambda m, t, c: "model_pricing_pending" in m, {"reason": "model_not_found", **_STOP}),
    (503, lambda m, t, c: c == "model_unavailable", {"reason": "model_not_found", **_STOP}),
    (400, lambda m, t, c: m in {"konten terlalu panjang", "terlalu banyak messages"},
     {"reason": "payload_too_large", "should_compress": True}),
    (400, lambda m, t, c: m.startswith("max_tokens must be"), {"reason": "format_error", **_STOP}),
)


def classify_routster_error(
    error: Any, *, status_code: int | None = None, error_code: str | None = None,
    message: str = "", body: Any = None, model: str | None = None,
) -> dict[str, Any] | None:
    """Map a Routster rejection onto a ``FailoverReason`` verdict; None defers to the built-in pipeline.

    ``streaming_unsupported`` is left to the core: its message ("Streaming is not supported…")
    already trips the non-streaming fallback in ``chat_completion_helpers``."""
    msg, typ, code = _error_fields(body)
    if not msg and message:
        msg = str(message).strip().lower()
    for status, matches, verdict in _RULES:
        if status_code == status and matches(msg, typ, code):
            return dict(verdict)
    return None


def _request(url: str, *, api_key: str = "", body: dict | None = None, timeout: float = 15.0) -> tuple[int, Any]:
    """``(status, parsed JSON or None)`` for one gateway call; status 0 = no HTTP answer."""
    import json
    import urllib.error
    import urllib.request

    from hermes_cli.urllib_security import open_credentialed_url

    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="GET" if body is None else "POST")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", hermes_user_agent("routster-agent"))
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with open_credentialed_url(req, timeout=timeout) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except (OSError, ValueError):
        return 0, None
    try:
        return status, json.loads(raw.decode() or "null")
    except ValueError:
        return status, None


def check_api_key(api_key: str, base_url: str) -> tuple[bool, str]:
    """``(valid, message)`` for *api_key* without spending balance.

    ``/v1/models`` is public (it ignores the key), so this posts an empty ``messages`` list: the
    gateway checks the key (401/403) before it parses the body, and rejects an empty list (400
    "messages kosong") before reserving any balance. It costs one request of the per-key rate limit.
    """
    status, body = _request(f"{base_url.rstrip('/')}/chat/completions", api_key=api_key,
                            body={"model": ROUTSTER_DEFAULT_MODEL, "messages": [], "max_tokens": 1})
    msg, _typ, _code = _error_fields(body)
    if status == 400:
        return True, "API key valid."
    if status == 401:
        return False, f"API key ditolak (invalid). Cek lagi key kamu di {ROUTSTER_DASHBOARD_URL}"
    if status == 403:
        return False, f"Akun belum bisa dipakai: {msg or 'forbidden'}"
    if status == 429:
        return True, "API key valid (sedang kena rate limit, coba lagi sebentar lagi)."
    if status == 0:
        return False, f"Tidak bisa menghubungi {base_url}. Cek koneksi internet / ROUTSTER_BASE_URL."
    return False, f"Jawaban tak terduga dari gateway (HTTP {status}): {msg or body!r}"


def fetch_catalog(base_url: str, *, timeout: float = 8.0) -> list[dict[str, Any]]:
    """``[{id, input_multiplier, output_multiplier, streaming}]`` from ``/v1/models``; [] on failure."""
    status, body = _request(f"{base_url.rstrip('/')}/models", timeout=timeout)
    items = body.get("data") if status == 200 and isinstance(body, dict) else None
    rows = []
    for item in items if isinstance(items, list) else ():
        mid = str(item.get("id") or "").strip() if isinstance(item, dict) else ""
        if mid:
            caps = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
            rows.append({"id": mid, "input_multiplier": item.get("input_multiplier"),
                         "output_multiplier": item.get("output_multiplier"),
                         "streaming": caps.get("streaming", True)})
    return rows


def multiplier_note(row: dict[str, Any]) -> str:
    """Picker note such as ``input x1 / output x4`` (+ ``agent`` for the curated rows)."""
    def fmt(value: Any) -> str:
        return "?" if value is None else f"{value:g}" if isinstance(value, (int, float)) else str(value)
    note = f"input x{fmt(row.get('input_multiplier'))} / output x{fmt(row.get('output_multiplier'))}"
    return note + (" · rekomendasi agent" if row.get("id") in ROUTSTER_AGENT_MODELS else "")


def _resolve_base_url(args: Any) -> str:
    from hermes_cli.config import get_env_value

    explicit = str(getattr(args, "base_url", None) or "").strip()
    return (explicit or str(get_env_value("ROUTSTER_BASE_URL") or "").strip()
            or ROUTSTER_DEFAULT_BASE_URL).rstrip("/")


def _obtain_api_key(args: Any, base_url: str) -> str | None:
    """A validated key: ``--api-key``, else the saved one (kept on Enter), else a masked prompt."""
    from hermes_cli.config import get_env_value
    from hermes_cli.model_setup_flows_common import _ask, _say

    given = str(getattr(args, "api_key", None) or "").strip()
    saved = str(get_env_value("ROUTSTER_API_KEY") or "").strip()
    for attempt in range(3):
        key = given
        if not key:
            if attempt == 0:
                _say("", f"  Ambil API key di {ROUTSTER_DASHBOARD_URL} (daftar + top up saldo dulu).")
            hint = f" [Enter = pakai key tersimpan …{saved[-4:]}]" if saved else ""
            answer = _ask(f"  Routster API key{hint}: ", secret=True)
            if answer is None:
                return None
            key = answer or saved
        if not key:
            print("  Tidak ada API key. Dibatalkan.")
            return None
        ok, message = check_api_key(key, base_url)
        print(f"  {'✓' if ok else '✗'} {message}")
        if ok:
            return key
        if given:  # a non-interactive key that fails stays failed
            return None
    return None


def routster_model_setup_flow(config: Any, current_model: str = "", args: Any = None, *,
                              pick_model: bool = True) -> dict | None:
    """``routster login`` / ``routster model`` → Routster: validate + save the key, pick a model, persist.

    Returns the saved model section, None when cancelled or the key was rejected."""
    del config
    from hermes_cli.config import save_env_value
    from hermes_cli.model_setup_flows_common import _finish_model, _pick_model_or_prompt

    base_url = _resolve_base_url(args)
    api_key = _obtain_api_key(args, base_url)
    if not api_key:
        return None
    save_env_value("ROUTSTER_API_KEY", api_key)

    requested = str(getattr(args, "model", None) or "").strip()
    catalog = fetch_catalog(base_url)
    ids = [row["id"] for row in catalog]
    if requested:
        selected = requested
    elif not pick_model:
        selected = current_model if current_model.startswith("routster/") else ROUTSTER_DEFAULT_MODEL
    else:
        ordered = [m for m in ROUTSTER_AGENT_MODELS if not ids or m in ids]
        ordered += [m for m in ids if m not in ordered]
        notes = {row["id"]: multiplier_note(row) for row in catalog}
        selected = _pick_model_or_prompt(
            ordered, "Model name: ", current_model=current_model or ROUTSTER_DEFAULT_MODEL,
            confirm_provider="routster", confirm_base_url=base_url, confirm_api_key=api_key, notes=notes)
    if ids and selected and selected not in ids:
        print(f"  ⚠ {selected} tidak ada di /v1/models saat ini; tetap disimpan.")
    custom_base = base_url != ROUTSTER_DEFAULT_BASE_URL
    return _finish_model(selected, "routster", f"  ✓ Model default: {selected} (via Routster)",
                         base_url=base_url if custom_base else None, drop_base_url=not custom_base,
                         drop_api_mode=True)


class RoutsterProfile(ProviderProfile):
    """Routster gateway: always sends an explicit, in-range ``max_tokens``."""

    def get_max_tokens(self, model: str | None) -> int | None:
        return min(self.default_max_tokens or ROUTSTER_DEFAULT_MAX_TOKENS, ROUTSTER_MAX_TOKENS_CAP)

    def missing_credentials_hint(self) -> str | None:
        return (f"Run `routster login` with an API key from {ROUTSTER_DASHBOARD_URL} "
                "(or set ROUTSTER_API_KEY).")


routster = RoutsterProfile(
    name="routster",
    aliases=("routster-ai", "trackster"),
    display_name="Routster",
    description="Routster — one API key, many models, Rupiah billing",
    signup_url=ROUTSTER_DASHBOARD_URL,
    env_vars=("ROUTSTER_API_KEY",),
    base_url=ROUTSTER_DEFAULT_BASE_URL,
    base_url_env_var="ROUTSTER_BASE_URL",
    fallback_models=ROUTSTER_AGENT_MODELS,
    default_aux_model=ROUTSTER_DEFAULT_MODEL,
    default_max_tokens=ROUTSTER_DEFAULT_MAX_TOKENS,
    classify_api_error=classify_routster_error,
    model_setup_flow=routster_model_setup_flow,
    picker_after="^",  # first row of every provider list
    # The CLI identifies as itself, never as another client.
    default_headers=LazyHeaders({"User-Agent": lambda: hermes_user_agent("routster-agent")}),
)

register_provider(routster)
