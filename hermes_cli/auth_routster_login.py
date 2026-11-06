"""``routster login``: Routster Agent's sign-in command (upstream Hermes keeps a deprecation stub)."""

from __future__ import annotations


def login_command(args) -> None:
    """``routster login``: validate + save a Routster API key and make Routster the default provider.

    Other providers keep their own setup (``routster model`` / ``routster auth``)."""
    requested = str(getattr(args, "provider", None) or "routster").strip().lower()
    if requested != "routster":
        print(f"`login` only signs in to Routster. For {requested}, use `routster model` or `routster auth add {requested}`.")
        raise SystemExit(2)
    from hermes_cli.config import load_config
    from providers import get_provider_profile

    flow = getattr(get_provider_profile("routster"), "model_setup_flow", None)
    model_cfg = load_config().get("model")
    current = str((model_cfg.get("default") if isinstance(model_cfg, dict) else model_cfg) or "")
    if flow is None or flow({}, current, args, pick_model=False) is None:
        raise SystemExit(1)
    print("\n  Ready! Run `routster` to start, or `routster model` to change the model.")
